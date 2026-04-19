from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 120.0


@dataclass(slots=True)
class SmokeStepResult:
    name: str
    ok: bool
    status_code: int | None
    detail: str
    payload: Any = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the authenticated collaboration smoke flow over HTTP + WebSocket.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("CLAIMMATE_API_BASE_URL", DEFAULT_BASE_URL),
        help="Backend base URL. Defaults to CLAIMMATE_API_BASE_URL or http://127.0.0.1:8000.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-request timeout in seconds. Default: 120.",
    )
    parser.add_argument("--json-out", help="Optional path to write JSON results.")
    return parser.parse_args()


def _normalize_base_url(raw: str) -> str:
    return raw.strip().rstrip("/")


def _write_json(path: str, payload: Any) -> None:
    out = Path(path).expanduser().resolve()
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    timeout: float,
    json_body: dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = session.request(method=method, url=url, json=json_body, timeout=timeout, headers=headers)
    payload = response.json()
    if response.status_code >= 400:
        detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
        raise RuntimeError(f"{method} {url} failed with HTTP {response.status_code}: {detail}")
    if not isinstance(payload, dict):
        raise RuntimeError(f"{method} {url} returned unexpected JSON type: {type(payload).__name__}")
    return response.status_code, payload


def _log_step(results: list[SmokeStepResult], name: str, status_code: int, payload: Any) -> None:
    results.append(SmokeStepResult(name=name, ok=True, status_code=status_code, detail="ok", payload=payload))


def _ws_base_url(base_url: str) -> str:
    if base_url.startswith("https://"):
        return "wss://" + base_url.removeprefix("https://")
    if base_url.startswith("http://"):
        return "ws://" + base_url.removeprefix("http://")
    raise ValueError(f"Unsupported base URL for websocket conversion: {base_url}")


async def _run_ws_check(base_url: str, case_id: str, token: str) -> dict[str, Any]:
    import websockets

    uri = f"{_ws_base_url(base_url)}/ws/cases/{case_id}?token={token}"
    async with websockets.connect(uri, open_timeout=25, close_timeout=25) as ws1:
        ready = json.loads(await asyncio.wait_for(ws1.recv(), timeout=25))
        await ws1.send(json.dumps({"type": "ping"}))
        pong = json.loads(await asyncio.wait_for(ws1.recv(), timeout=25))
        async with websockets.connect(uri, open_timeout=25, close_timeout=25) as ws2:
            join_notice = json.loads(await asyncio.wait_for(ws1.recv(), timeout=25))
            ready2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=25))
            await ws1.send(
                json.dumps(
                    {
                        "type": "chat",
                        "message_text": "@AI what deadlines should I know for this claim?",
                        "sender_role": "owner",
                        "invite_sent": True,
                        "participants": [
                            {"user_id": "owner-1", "role": "owner"},
                            {"user_id": "adjuster-1", "role": "adjuster"},
                        ],
                        "run_ai": True,
                    }
                )
            )
            user1 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=60))
            user2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=60))
            ai1 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=120))
            ai2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=120))
            return {
                "ready_type": ready.get("type"),
                "pong_type": pong.get("type"),
                "join_event": join_notice.get("event"),
                "ready2_type": ready2.get("type"),
                "user1_type": user1.get("type"),
                "user2_type": user2.get("type"),
                "ai1_type": ai1.get("type"),
                "ai2_type": ai2.get("type"),
                "ai_trigger": (ai1.get("payload") or {}).get("trigger"),
            }


def main() -> None:
    args = parse_args()
    base_url = _normalize_base_url(args.base_url)
    stamp = str(int(time.time()))
    owner_email = f"owner.cloud.{stamp}@example.com"
    invitee_email = f"adjuster.cloud.{stamp}@example.com"
    case_id = f"cloud-collab-{stamp}"

    session = requests.Session()
    results: list[SmokeStepResult] = []

    try:
        status, owner_reg = _request_json(
            session,
            "POST",
            f"{base_url}/auth/register",
            timeout=args.timeout,
            json_body={
                "email": owner_email,
                "password": "ClaimMate123",
                "display_name": "Cloud Owner",
            },
        )
        _log_step(results, "owner_register", status, owner_reg)
        owner_token = owner_reg["access_token"]

        status, owner_me = _request_json(
            session,
            "GET",
            f"{base_url}/auth/me",
            timeout=args.timeout,
            token=owner_token,
        )
        _log_step(results, "owner_me", status, owner_me)

        status, created = _request_json(
            session,
            "POST",
            f"{base_url}/cases",
            timeout=args.timeout,
            json_body={"case_id": case_id},
            token=owner_token,
        )
        _log_step(results, "create_case", status, created)

        status, seeded = _request_json(
            session,
            "POST",
            f"{base_url}/cases/{case_id}/demo/seed-accident",
            timeout=max(args.timeout, 180.0),
            token=owner_token,
        )
        _log_step(results, "seed_accident", status, {"keys": sorted(seeded.keys())})

        status, snapshot = _request_json(
            session,
            "GET",
            f"{base_url}/cases/{case_id}",
            timeout=args.timeout,
            token=owner_token,
        )
        _log_step(
            results,
            "get_case",
            status,
            {key: (snapshot.get(key) is not None) for key in ("stage_a", "stage_b", "report_payload", "chat_context", "room_bootstrap")},
        )

        status, invite = _request_json(
            session,
            "POST",
            f"{base_url}/cases/{case_id}/invites",
            timeout=args.timeout,
            json_body={"role": "member", "expires_in_hours": 168},
            token=owner_token,
        )
        _log_step(results, "create_invite", status, invite)
        invite_token = invite["token"]

        status, looked_up = _request_json(
            session,
            "GET",
            f"{base_url}/invites/lookup?token={invite_token}",
            timeout=args.timeout,
        )
        _log_step(results, "lookup_invite", status, looked_up)

        status, invitee_reg = _request_json(
            session,
            "POST",
            f"{base_url}/auth/register",
            timeout=args.timeout,
            json_body={
                "email": invitee_email,
                "password": "ClaimMate123",
                "display_name": "Cloud Invitee",
            },
        )
        _log_step(results, "invitee_register", status, invitee_reg)
        invitee_token = invitee_reg["access_token"]

        status, accepted = _request_json(
            session,
            "POST",
            f"{base_url}/auth/accept-invite",
            timeout=args.timeout,
            json_body={"token": invite_token},
            token=invitee_token,
        )
        _log_step(results, "accept_invite", status, accepted)

        status, chat_payload = _request_json(
            session,
            "POST",
            f"{base_url}/cases/{case_id}/chat/messages",
            timeout=max(args.timeout, 180.0),
            json_body={
                "message_text": "@AI what deadlines should I know for this claim?",
                "sender_role": "owner",
                "invite_sent": True,
                "participants": [
                    {"user_id": "owner-1", "role": "owner"},
                    {"user_id": "adjuster-1", "role": "adjuster"},
                ],
            },
            token=invitee_token,
        )
        response = chat_payload.get("response") or {}
        _log_step(
            results,
            "post_chat_messages",
            status,
            {
                "trigger": response.get("trigger"),
                "stage": (response.get("metadata") or {}).get("stage"),
                "deadline_intent": (response.get("metadata") or {}).get("deadline_intent"),
            },
        )

        status, messages = _request_json(
            session,
            "GET",
            f"{base_url}/cases/{case_id}/chat/messages",
            timeout=args.timeout,
            token=invitee_token,
        )
        _log_step(results, "get_chat_messages", status, {"count": len(messages.get("messages", []))})

        ws_result = asyncio.run(_run_ws_check(base_url, case_id, invitee_token))
        results.append(SmokeStepResult(name="websocket", ok=True, status_code=101, detail="ok", payload=ws_result))
    except Exception as exc:
        results.append(SmokeStepResult(name="failure", ok=False, status_code=None, detail=str(exc)))

    payload = {
        "base_url": base_url,
        "passed": all(item.ok for item in results),
        "results": [asdict(item) for item in results],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if args.json_out:
        _write_json(args.json_out, payload)
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
