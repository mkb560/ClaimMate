# Backend integration summary & tips for Lou

This document summarizes the current app-layer backend API and gives practical frontend integration notes. It replaces the earlier Ke-only minimal API notes.

---

## What is in place now

### FastAPI structure

- `backend/main.py` assembles the FastAPI app: lifespan bootstrap, CORS, and router includes.
- `backend/app/routers/health.py` exposes `GET /health`.
- `backend/app/routers/policy_ask.py` exposes policy upload, policy status, demo policy seed, demo policy catalog, and policy Q&A.
- `backend/app/routers/cases_and_accident.py` exposes case, accident, report, claim-date, chat event, and chat message routes.
- `backend/app/routers/auth.py`, `invites.py`, and `ws_chat.py` add optional JWT auth, invite links, and a WebSocket room per case. Defaults keep the demo open (`AUTH_MODE=off`). See `docs/AUTH_AND_WEBSOCKET_KE.md`.

### Startup & database

- On startup, if `DATABASE_URL` is set, the app creates a shared async engine and runs `bootstrap_vector_store`.
- Bootstrap ensures the `pgvector` extension and `vector_documents` table for RAG.
- Bootstrap also creates the app-layer `cases` table, `case_chat_messages`, and auth-related tables (`users`, `case_memberships`, `case_invites`) for local/dev environments.
- `backend/ai/runtime.py` wires vector schema and app-layer schema together.

### Minimal case model

- `cases` is keyed by string `id`, which is the same value as `case_id` in URLs and RAG calls.
- Deadline fields: `claim_notice_at`, `proof_of_claim_at`, `last_deadline_alert_at`.
- JSON fields: `stage_a_json`, `stage_b_json`, `report_payload_json`, `chat_context_json`.
- Timestamps: `created_at`, `updated_at`.

---

## Policy + ask

This remains the primary demo path. For copy-paste frontend examples, see `docs/YI_FRONTEND_API_EXAMPLE_ZH.md`.

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/demo/policies` | Read the built-in demo policy catalog with labels, filenames, default case IDs, and sample questions. |
| `GET` | `/cases/{case_id}/policy` | Read the currently indexed policy summary for a case ID. |
| `POST` | `/cases/{case_id}/demo/seed-policy` | Seed one of the built-in demo policy PDFs into KB-A. Optional JSON body: `{"policy_key": "..."}`. |
| `POST` | `/cases/{case_id}/policy` | Upload a PDF with `multipart/form-data`, field name `file`. |
| `POST` | `/cases/{case_id}/ask` | Ask policy/regulatory questions with JSON body `{"question": "..."}`. |

Important notes:

- `case_id` must match `^[A-Za-z0-9_-]{1,64}$`.
- Policy upload, demo `seed-policy`, and `ask` run access checks first, then `ensure_case`, so the case row is created automatically when the caller is allowed and the row is missing.
- `GET /cases/{case_id}/policy` returns `has_policy`, `chunk_count`, `source_label`, `filename`, and optional `demo_policy` metadata.
- Fixed demo policy case IDs are `allstate-change-2025-05`, `allstate-renewal-2025-08`, and `progressive-verification-2026-03`.
- For a custom `case_id`, call `POST /cases/{case_id}/demo/seed-policy` with `{"policy_key": "allstate-change" | "allstate-renewal" | "progressive-verification"}`.

---

## Accident workflow

The accident workflow aligns with `docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md` and `backend/models/accident_types.py`.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/cases` | Create a case. The caller can provide `{"case_id": "my-id"}` or let the server generate one. |
| `GET` | `/cases/{case_id}` | Read the current case snapshot: claim dates, Stage A/B JSON, report/chat caches, and optional `room_bootstrap`. |
| `POST` | `/cases/{case_id}/demo/seed-accident` | Seed the built-in accident/chat demo payloads for a case ID. |
| `PATCH` | `/cases/{case_id}/accident/stage-a` | Deep-merge JSON into Stage A intake. |
| `PATCH` | `/cases/{case_id}/accident/stage-b` | Deep-merge JSON into Stage B intake. |
| `POST` | `/cases/{case_id}/accident/report` | Build and store the deterministic report payload plus chat context. |
| `GET` | `/cases/{case_id}/accident/report` | Read the stored report payload and chat context. |
| `DELETE` | `/cases/{case_id}` | Delete the case row, related chat messages, and KB-A vector chunks for demo cleanup. |

Not implemented yet: real PDF file generation and real WebSocket group-chat rooms. The current API returns JSON suitable for preview and future product wiring.

---

## Claim dates & chat

| Method | Path | Purpose |
| --- | --- | --- |
| `PATCH` | `/cases/{case_id}/claim-dates` | Update deadline fields and clear `last_deadline_alert_at`. |
| `POST` | `/cases/{case_id}/chat/event` | Full `ChatEvent` payload into `handle_chat_event`; persists user rows when applicable and AI rows when AI responds. |
| `GET` | `/cases/{case_id}/chat/messages` | Read the persisted chat timeline. Supports `limit` and `offset`. |
| `POST` | `/cases/{case_id}/chat/messages` | Lou-friendly simplified message API. Body: `{"message_text": "...", "sender_role": "owner", "invite_sent": false, "participants": null}`. |

Chat notes:

- Put `@AI` in `message_text` to trigger the same mention path as the AI core.
- `GET /cases/{case_id}/chat/messages` returns `message_type` (`user` or `ai`), `body_text`, timestamps, and optional `ai_payload`.
- `GET /cases/{case_id}` includes `room_bootstrap` when `chat_context_json` exists. This lets the UI seed a future chat room or pinned summary without parsing the full report payload.

---

## Tips for Lou

### Base URL and CORS

- Local backend default: `http://127.0.0.1:8000`.
- The shared backend URL changes when ngrok is restarted; ask Mingtao/Ke for the current base URL.
- CORS is configured through `backend/.env` with `CORS_ALLOW_ORIGINS` and `CORS_ALLOW_ORIGIN_REGEX`.

### Policy upload and demo seed

- For a demo picker, call `GET /demo/policies` first instead of hardcoding the built-in policy choices in multiple places.
- For the fastest demo path, call `POST /cases/{case_id}/demo/seed-policy` instead of manually uploading a PDF.
- After seed or upload, call `GET /cases/{case_id}/policy` to recover indexed-policy state after refresh.
- Real PDF upload uses `POST /cases/{case_id}/policy` with form field `file`; server checks PDF magic bytes.
- Successful policy ingestion returns `chunk_count` and `status: "indexed"`.

### Ask responses

- `POST /cases/{case_id}/ask` requires JSON field `question`.
- Response includes `answer`, `disclaimer`, and `citations`.
- Each citation includes fields like `source_type`, `source_label`, `document_id`, `page_num`, `section`, and `excerpt`.
- Use `source_type` in the UI so users can tell policy sources (`kb_a`) from external reference sources (`kb_b`).

### Accident forms

- Do not invent a parallel schema. Use the snake_case field names in `backend/models/accident_types.py` and `docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md`.
- Stage A/B `PATCH` bodies are deep-merged into stored JSON, so omitted fields are left unchanged.

### Suggested frontend order

1. Optionally create a case with `POST /cases`.
2. For policy demo mode, call `GET /demo/policies`.
3. Use a fixed demo case ID and call `POST /cases/{case_id}/demo/seed-policy`.
4. Call `GET /cases/{case_id}/policy` to confirm which policy is indexed.
5. For accident demo mode, call `POST /cases/{case_id}/demo/seed-accident`.
6. Call `GET /cases/{case_id}` on page load or refresh to rehydrate saved state.
7. Save Stage A with `PATCH /cases/{case_id}/accident/stage-a`.
8. Save Stage B with `PATCH /cases/{case_id}/accident/stage-b`.
9. Generate report preview with `POST /cases/{case_id}/accident/report`.
10. Read timeline with `GET /cases/{case_id}/chat/messages` and send chat lines with `POST /cases/{case_id}/chat/messages`.

### Errors worth handling in UI

- `503`: missing backend config or AI bootstrap failure.
- `400`: invalid `case_id`, non-PDF upload, empty question, or validation issue.
- `404`: missing case or missing accident report.
- `409`: duplicate case ID on `POST /cases`.

### Quick inspection endpoints

- `GET /health` checks `status`, `ai_ready`, and `ai_bootstrap_error`.
- `GET /docs` opens Swagger UI on the running server.

---

## Related docs

| Doc | Content |
| --- | --- |
| `docs/YI_FRONTEND_API_EXAMPLE_ZH.md` | Frontend copy-paste API examples. |
| `docs/AI_CHAT_BEHAVIOR_CONTRACT_ZH.md` | Mingtao AI chat trigger/response contract. |
| `docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md` | Stage A/B, report, and chat context contract. |
| `docs/RUN_DEMO_ZH.md` | Local/shared demo runbook. |
| `backend/.env.example` | Env vars for local/shared backend. |

---

## Environment reminder

- `DATABASE_URL`: Postgres with `pgvector`; use async driver `postgresql+psycopg://...`.
- `OPENAI_API_KEY`: required for policy ingest, ask, and chat AI paths.
- Run `uvicorn` from `backend/` so `.env` is picked up correctly.
