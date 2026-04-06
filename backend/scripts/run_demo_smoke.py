from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_POLICY_KEY = "allstate-change"
DEFAULT_ACCIDENT_CASE_ID = "demo-accident-2026-04"
DEFAULT_CHAT_LABEL = "claim_rule_stage_3"
DEFAULT_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True, slots=True)
class SmokePlan:
    base_url: str
    policy_key: str
    policy_case_id: str
    policy_question: str
    accident_case_id: str
    chat_label: str


@dataclass(slots=True)
class SmokeStepResult:
    name: str
    ok: bool
    status_code: int | None
    detail: str
    payload: Any = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the end-to-end ClaimMate demo smoke flow over HTTP.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("CLAIMMATE_API_BASE_URL", DEFAULT_BASE_URL),
        help="Backend base URL. Defaults to CLAIMMATE_API_BASE_URL or http://127.0.0.1:8000.",
    )
    parser.add_argument(
        "--policy-key",
        default=DEFAULT_POLICY_KEY,
        help="Built-in demo policy key to use from GET /demo/policies.",
    )
    parser.add_argument(
        "--policy-case-id",
        help="Optional case_id for the policy demo. Defaults to the selected policy's default_case_id.",
    )
    parser.add_argument(
        "--ask-question",
        help="Optional policy question. Defaults to the first sample question for the selected demo policy.",
    )
    parser.add_argument(
        "--accident-case-id",
        default=DEFAULT_ACCIDENT_CASE_ID,
        help="Case id used for POST /cases/{case_id}/demo/seed-accident.",
    )
    parser.add_argument(
        "--chat-label",
        default=DEFAULT_CHAT_LABEL,
        help="Chat sample label to pull from the seeded accident payload and replay through /chat/event.",
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


def _pick_demo_policy(catalog: list[dict[str, Any]], policy_key: str) -> dict[str, Any]:
    for item in catalog:
        if item.get("policy_key") == policy_key:
            return item
    available = ", ".join(sorted(str(item.get("policy_key")) for item in catalog))
    raise ValueError(f"Unknown policy_key {policy_key!r}. Available policy keys: {available}")


def _build_smoke_plan(
    *,
    base_url: str,
    catalog: list[dict[str, Any]],
    policy_key: str,
    policy_case_id: str | None,
    ask_question: str | None,
    accident_case_id: str,
    chat_label: str,
) -> SmokePlan:
    selected = _pick_demo_policy(catalog, policy_key)
    resolved_case_id = policy_case_id or str(selected["default_case_id"])
    sample_questions = selected.get("sample_questions") or []
    resolved_question = ask_question or (sample_questions[0] if sample_questions else "Who are the policyholders?")
    return SmokePlan(
        base_url=_normalize_base_url(base_url),
        policy_key=str(selected["policy_key"]),
        policy_case_id=resolved_case_id,
        policy_question=resolved_question,
        accident_case_id=accident_case_id,
        chat_label=chat_label,
    )


def _build_seed_policy_body(plan: SmokePlan, selected_policy: dict[str, Any]) -> dict[str, Any] | None:
    default_case_id = selected_policy.get("default_case_id")
    if plan.policy_case_id == default_case_id:
        return None
    return {"policy_key": plan.policy_key}


def _pick_chat_request(seed_accident_payload: dict[str, Any], chat_label: str) -> dict[str, Any]:
    requests_by_label = seed_accident_payload.get("sample_chat_requests")
    if not isinstance(requests_by_label, dict):
        raise ValueError("seed-accident response did not include sample_chat_requests.")
    payload = requests_by_label.get(chat_label)
    if not isinstance(payload, dict):
        available = ", ".join(sorted(str(key) for key in requests_by_label))
        raise ValueError(f"Chat label {chat_label!r} was not found. Available labels: {available}")
    return payload


def _validate_health(payload: dict[str, Any]) -> None:
    if payload.get("status") != "ok":
        raise ValueError(f"Unexpected health status: {payload.get('status')!r}")
    if payload.get("ai_ready") is not True:
        raise ValueError(f"Backend reported ai_ready={payload.get('ai_ready')!r}")


def _validate_policy_seed(payload: dict[str, Any], plan: SmokePlan) -> None:
    if payload.get("case_id") != plan.policy_case_id:
        raise ValueError(f"seed-policy case_id mismatch: {payload.get('case_id')!r}")
    if payload.get("policy_key") != plan.policy_key:
        raise ValueError(f"seed-policy policy_key mismatch: {payload.get('policy_key')!r}")
    if int(payload.get("chunk_count") or 0) < 1:
        raise ValueError("seed-policy returned chunk_count < 1.")


def _validate_answer(payload: dict[str, Any], plan: SmokePlan) -> None:
    if payload.get("case_id") != plan.policy_case_id:
        raise ValueError(f"ask case_id mismatch: {payload.get('case_id')!r}")
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("ask response did not include a non-empty answer.")
    citations = payload.get("citations")
    if not isinstance(citations, list) or not citations:
        raise ValueError("ask response did not include any citations.")
    disclaimer = payload.get("disclaimer")
    if not isinstance(disclaimer, str) or not disclaimer.strip():
        raise ValueError("ask response did not include a disclaimer.")


def _validate_seed_accident(payload: dict[str, Any], plan: SmokePlan) -> None:
    if payload.get("case_id") != plan.accident_case_id:
        raise ValueError(f"seed-accident case_id mismatch: {payload.get('case_id')!r}")
    if not isinstance(payload.get("sample_chat_requests"), dict):
        raise ValueError("seed-accident response did not include sample_chat_requests.")
    if not isinstance(payload.get("case_snapshot"), dict):
        raise ValueError("seed-accident response did not include case_snapshot.")


def _validate_case_snapshot(payload: dict[str, Any], plan: SmokePlan) -> None:
    if payload.get("case_id") != plan.accident_case_id:
        raise ValueError(f"case snapshot mismatch: {payload.get('case_id')!r}")
    room_bootstrap = payload.get("room_bootstrap")
    if not isinstance(room_bootstrap, dict) or not room_bootstrap:
        raise ValueError("case snapshot did not include room_bootstrap.")
    pinned_title = room_bootstrap.get("pinned_document_title")
    if not isinstance(pinned_title, str) or not pinned_title.strip():
        raise ValueError("room_bootstrap did not include pinned_document_title.")
    if not isinstance(room_bootstrap.get("key_facts"), list):
        raise ValueError("room_bootstrap did not include key_facts list.")


def _validate_chat_response(payload: dict[str, Any], plan: SmokePlan) -> None:
    if payload.get("case_id") != plan.accident_case_id:
        raise ValueError(f"chat/event case_id mismatch: {payload.get('case_id')!r}")
    response = payload.get("response")
    if not isinstance(response, dict):
        raise ValueError("chat/event did not return an AI response payload.")
    text = response.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("chat/event response text is empty.")
    if plan.chat_label.endswith("stage_3") and not text.startswith("For reference:"):
        raise ValueError("stage_3 chat response did not preserve the expected neutral prefix.")


def _build_chat_message_body(chat_request: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_text": chat_request["message_text"],
        "sender_role": chat_request["sender_role"],
        "invite_sent": chat_request["invite_sent"],
        "participants": chat_request.get("participants"),
    }


def _validate_chat_messages_payload(payload: dict[str, Any], plan: SmokePlan) -> None:
    if payload.get("case_id") != plan.accident_case_id:
        raise ValueError(f"chat/messages case_id mismatch: {payload.get('case_id')!r}")
    if not isinstance(payload.get("messages"), list):
        raise ValueError("chat/messages response did not include messages list.")


def _validate_chat_messages_growth(
    *,
    before_payload: dict[str, Any],
    after_payload: dict[str, Any],
    posted_message_text: str,
    ai_response_text: str,
    expected_user_metadata: dict[str, Any] | None = None,
) -> None:
    before_messages = before_payload.get("messages")
    after_messages = after_payload.get("messages")
    if not isinstance(before_messages, list) or not isinstance(after_messages, list):
        raise ValueError("chat/messages payloads did not include message lists.")
    if len(after_messages) < len(before_messages) + 2:
        raise ValueError(
            "chat/messages did not grow by at least two rows after posting a user line and AI reply."
        )
    last_two = after_messages[-2:]
    if len(last_two) != 2:
        raise ValueError("chat/messages did not include the expected trailing user and ai rows.")
    user_row, ai_row = last_two
    if user_row.get("message_type") != "user" or user_row.get("body_text") != posted_message_text:
        raise ValueError("Last persisted user chat row did not match the posted message.")
    if ai_row.get("message_type") != "ai" or ai_row.get("body_text") != ai_response_text:
        raise ValueError("Last persisted ai chat row did not match the returned AI response.")
    metadata = user_row.get("metadata")
    if expected_user_metadata is not None:
        if not isinstance(metadata, dict):
            raise ValueError("Persisted user chat row did not include metadata.")
        for key, value in expected_user_metadata.items():
            if metadata.get(key) != value:
                raise ValueError(f"Persisted user chat row did not preserve metadata[{key!r}] = {value!r}.")
    ai_payload = ai_row.get("ai_payload")
    if not isinstance(ai_payload, dict) or ai_payload.get("text") != ai_response_text:
        raise ValueError("Persisted ai chat row did not preserve ai_payload text.")


def _request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    timeout: float,
    json_body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    request_kwargs: dict[str, Any] = {"method": method, "url": url, "timeout": timeout}
    if json_body is not None:
        request_kwargs["json"] = json_body
    response = session.request(**request_kwargs)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"{method} {url} did not return JSON. Status={response.status_code}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{method} {url} returned unexpected JSON type: {type(payload).__name__}")
    if response.status_code >= 400:
        detail = payload.get("detail", payload)
        raise RuntimeError(f"{method} {url} failed with HTTP {response.status_code}: {detail}")
    return response.status_code, payload


def _run_step(
    results: list[SmokeStepResult],
    *,
    name: str,
    request_fn,
    validate_fn,
) -> dict[str, Any]:
    try:
        status_code, payload = request_fn()
        validate_fn(payload)
    except Exception as exc:
        results.append(
            SmokeStepResult(
                name=name,
                ok=False,
                status_code=None,
                detail=str(exc),
            )
        )
        raise
    results.append(
        SmokeStepResult(
            name=name,
            ok=True,
            status_code=status_code,
            detail="ok",
            payload=payload,
        )
    )
    return payload


def _write_json(path: str, payload: Any) -> None:
    output_path = Path(path).expanduser().resolve()
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    session = requests.Session()
    results: list[SmokeStepResult] = []

    try:
        health_payload = _run_step(
            results,
            name="health",
            request_fn=lambda: _request_json(
                session,
                "GET",
                f"{_normalize_base_url(args.base_url)}/health",
                timeout=args.timeout,
            ),
            validate_fn=_validate_health,
        )

        catalog_payload = _run_step(
            results,
            name="demo_policies",
            request_fn=lambda: _request_json(
                session,
                "GET",
                f"{_normalize_base_url(args.base_url)}/demo/policies",
                timeout=args.timeout,
            ),
            validate_fn=lambda payload: _pick_demo_policy(payload.get("policies") or [], args.policy_key),
        )

        catalog = catalog_payload["policies"]
        selected_policy = _pick_demo_policy(catalog, args.policy_key)
        plan = _build_smoke_plan(
            base_url=args.base_url,
            catalog=catalog,
            policy_key=args.policy_key,
            policy_case_id=args.policy_case_id,
            ask_question=args.ask_question,
            accident_case_id=args.accident_case_id,
            chat_label=args.chat_label,
        )

        seed_policy_body = _build_seed_policy_body(plan, selected_policy)
        _run_step(
            results,
            name="seed_policy",
            request_fn=lambda: _request_json(
                session,
                "POST",
                f"{plan.base_url}/cases/{plan.policy_case_id}/demo/seed-policy",
                timeout=args.timeout,
                json_body=seed_policy_body,
            ),
            validate_fn=lambda payload: _validate_policy_seed(payload, plan),
        )

        _run_step(
            results,
            name="ask",
            request_fn=lambda: _request_json(
                session,
                "POST",
                f"{plan.base_url}/cases/{plan.policy_case_id}/ask",
                timeout=args.timeout,
                json_body={"question": plan.policy_question},
            ),
            validate_fn=lambda payload: _validate_answer(payload, plan),
        )

        accident_payload = _run_step(
            results,
            name="seed_accident",
            request_fn=lambda: _request_json(
                session,
                "POST",
                f"{plan.base_url}/cases/{plan.accident_case_id}/demo/seed-accident",
                timeout=args.timeout,
            ),
            validate_fn=lambda payload: _validate_seed_accident(payload, plan),
        )

        chat_payload = _pick_chat_request(accident_payload, plan.chat_label)
        _run_step(
            results,
            name="case_snapshot",
            request_fn=lambda: _request_json(
                session,
                "GET",
                f"{plan.base_url}/cases/{plan.accident_case_id}",
                timeout=args.timeout,
            ),
            validate_fn=lambda payload: _validate_case_snapshot(payload, plan),
        )

        before_messages_payload = _run_step(
            results,
            name="chat_messages_before",
            request_fn=lambda: _request_json(
                session,
                "GET",
                f"{plan.base_url}/cases/{plan.accident_case_id}/chat/messages",
                timeout=args.timeout,
            ),
            validate_fn=lambda payload: _validate_chat_messages_payload(payload, plan),
        )

        post_message_body = _build_chat_message_body(chat_payload)
        post_message_response = _run_step(
            results,
            name="chat_messages_post",
            request_fn=lambda: _request_json(
                session,
                "POST",
                f"{plan.base_url}/cases/{plan.accident_case_id}/chat/messages",
                timeout=args.timeout,
                json_body=post_message_body,
            ),
            validate_fn=lambda payload: _validate_chat_response(payload, plan),
        )

        after_post_messages_payload = _run_step(
            results,
            name="chat_messages_after",
            request_fn=lambda: _request_json(
                session,
                "GET",
                f"{plan.base_url}/cases/{plan.accident_case_id}/chat/messages",
                timeout=args.timeout,
            ),
            validate_fn=lambda payload: (
                _validate_chat_messages_payload(payload, plan),
                _validate_chat_messages_growth(
                    before_payload=before_messages_payload,
                    after_payload=payload,
                    posted_message_text=post_message_body["message_text"],
                    ai_response_text=post_message_response["response"]["text"],
                    expected_user_metadata={
                        "source": "post_chat_messages",
                        "chat_event_trigger": "MESSAGE",
                    },
                ),
            ),
        )

        chat_event_response = _run_step(
            results,
            name="chat_event",
            request_fn=lambda: _request_json(
                session,
                "POST",
                f"{plan.base_url}/cases/{plan.accident_case_id}/chat/event",
                timeout=args.timeout,
                json_body=chat_payload,
            ),
            validate_fn=lambda payload: _validate_chat_response(payload, plan),
        )

        _run_step(
            results,
            name="chat_event_messages_after",
            request_fn=lambda: _request_json(
                session,
                "GET",
                f"{plan.base_url}/cases/{plan.accident_case_id}/chat/messages",
                timeout=args.timeout,
            ),
            validate_fn=lambda payload: (
                _validate_chat_messages_payload(payload, plan),
                _validate_chat_messages_growth(
                    before_payload=after_post_messages_payload,
                    after_payload=payload,
                    posted_message_text=chat_payload["message_text"],
                    ai_response_text=chat_event_response["response"]["text"],
                    expected_user_metadata={
                        **dict(chat_payload.get("metadata") or {}),
                        "chat_event_trigger": chat_payload["trigger"],
                    },
                ),
            ),
        )
    finally:
        session.close()

    passed = sum(item.ok for item in results)
    print(f"Smoke summary: {passed}/{len(results)} passed")
    for item in results:
        status = "PASS" if item.ok else "FAIL"
        suffix = "" if item.status_code is None else f" (HTTP {item.status_code})"
        print(f"[{status}] {item.name}{suffix}: {item.detail}")

    if args.json_out:
        _write_json(
            args.json_out,
            {
                "plan": asdict(plan),
                "results": [asdict(item) for item in results],
                "health": health_payload,
            },
        )
        print(f"Saved JSON results to {Path(args.json_out).expanduser().resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"Demo smoke failed: {error}") from error
