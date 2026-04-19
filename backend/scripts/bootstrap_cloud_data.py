from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
DEMO_KB_B_ROOT = REPO_ROOT / "claimmate_rag_docs"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ai.config import ai_config
from ai.ingestion.kb_b_loader import build_local_kb_b_sources, index_kb_b_sources
from ai.ingestion.vector_store import list_kb_b_chunks
from ai.runtime import bootstrap_vector_store, create_ai_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap cloud data for ClaimMate: KB-B indexing plus optional remote policy-storage validation."
    )
    parser.add_argument(
        "--docs-dir",
        default=str(DEMO_KB_B_ROOT),
        help="Directory containing local KB-B files to index into the target database.",
    )
    parser.add_argument(
        "--base-url",
        help="Optional backend base URL. When provided, validates /health and can trigger remote seed-policy.",
    )
    parser.add_argument(
        "--seed-policy-case-id",
        default="cloud-policy-check",
        help="Case id to use when validating remote seed-policy.",
    )
    parser.add_argument(
        "--seed-policy-key",
        default="allstate-change",
        help="Demo policy key to seed when validating remote policy storage.",
    )
    parser.add_argument(
        "--skip-policy-seed",
        action="store_true",
        help="Skip the remote seed-policy validation step.",
    )
    parser.add_argument(
        "--force-kb-b",
        action="store_true",
        help="Always reindex local KB-B files even if the target database already has KB-B chunks.",
    )
    parser.add_argument("--json-out", help="Optional path to write a JSON summary.")
    return parser.parse_args()


def _normalize_base_url(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip().rstrip("/")
    return value or None


def _write_json(path: str, payload: Any) -> None:
    out = Path(path).expanduser().resolve()
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _http_json(method: str, url: str, *, body: dict[str, Any] | None = None, timeout: float = 180.0) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"method": method, "url": url, "timeout": timeout}
    if body is not None:
        kwargs["json"] = body
    response = requests.request(**kwargs)
    payload = response.json()
    if response.status_code >= 400:
        detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
        raise RuntimeError(f"{method} {url} failed with HTTP {response.status_code}: {detail}")
    if not isinstance(payload, dict):
        raise RuntimeError(f"{method} {url} returned unexpected JSON type.")
    return payload


def _http_json_with_token(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 180.0,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"method": method, "url": url, "timeout": timeout}
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if headers:
        kwargs["headers"] = headers
    if body is not None:
        kwargs["json"] = body
    response = requests.request(**kwargs)
    payload = response.json()
    if response.status_code >= 400:
        detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
        raise RuntimeError(f"{method} {url} failed with HTTP {response.status_code}: {detail}")
    if not isinstance(payload, dict):
        raise RuntimeError(f"{method} {url} returned unexpected JSON type.")
    return payload


async def main() -> None:
    args = parse_args()
    summary: dict[str, Any] = {
        "kb_b_indexed": False,
        "kb_b_document_count": 0,
        "kb_b_chunk_count": 0,
        "remote_health": None,
        "remote_seed_policy": None,
    }

    ai_config.require_database()
    engine = create_ai_engine()
    try:
        await bootstrap_vector_store(engine)
        existing = await list_kb_b_chunks(limit=1)
        if existing and not args.force_kb_b:
            summary["kb_b_indexed"] = True
            summary["kb_b_document_count"] = "existing"
            summary["kb_b_chunk_count"] = "existing"
        else:
            docs_dir = Path(args.docs_dir).expanduser().resolve()
            sources = build_local_kb_b_sources(docs_dir)
            if not sources:
                raise RuntimeError(f"No supported KB-B files found in {docs_dir}")
            results = await index_kb_b_sources(sources)
            summary["kb_b_indexed"] = True
            summary["kb_b_document_count"] = len(results)
            summary["kb_b_chunk_count"] = sum(item.chunk_count for item in results)
    finally:
        await engine.dispose()

    base_url = _normalize_base_url(args.base_url)
    if base_url:
        health_payload = _http_json("GET", f"{base_url}/health")
        summary["remote_health"] = health_payload
        if not args.skip_policy_seed:
            stamp = str(int(time.time()))
            owner = _http_json(
                "POST",
                f"{base_url}/auth/register",
                body={
                    "email": f"owner.bootstrap.{stamp}@example.com",
                    "password": "ClaimMate123",
                    "display_name": "Cloud Bootstrap Owner",
                },
            )
            token = owner["access_token"]
            _http_json_with_token(
                "POST",
                f"{base_url}/cases",
                body={"case_id": args.seed_policy_case_id},
                token=token,
            )
            seed_payload = _http_json_with_token(
                "POST",
                f"{base_url}/cases/{args.seed_policy_case_id}/demo/seed-policy",
                body={"policy_key": args.seed_policy_key},
                token=token,
            )
            summary["remote_seed_policy"] = {
                "case_id": seed_payload.get("case_id"),
                "policy_key": seed_payload.get("policy_key"),
                "filename": seed_payload.get("filename"),
                "chunk_count": seed_payload.get("chunk_count"),
                "status": seed_payload.get("status"),
            }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.json_out:
        _write_json(args.json_out, summary)


if __name__ == "__main__":
    asyncio.run(main())
