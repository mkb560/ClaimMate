# Backend integration summary & tips for Lou

This document summarizes what the **app-layer backend integration** added (per `KE_WU_HANDOFF_ZH.md` / `KE_API_CONTRACT_ZH.md`) and gives **practical guidance for frontend** work.

---

## What is in place now

### FastAPI structure

- `**backend/main.py`** — App factory: lifespan (DB engine + bootstrap), CORS, router includes only.
- `**backend/app/routers/**` — App-layer routes:
  - `health.py` — `GET /health`
  - `policy_ask.py` — policy upload + RAG ask
  - `cases_and_accident.py` — cases, accident intake, report, claim dates, chat event

### Startup & database

- On startup, if `DATABASE_URL` is set, the app creates a shared async engine and runs `**bootstrap_vector_store**`:
  - Ensures **pgvector** extension and `**vector_documents`** table (RAG).
  - Creates the `**cases**` table (app + deadline checker).
- `**backend/ai/runtime.py**` wires vector schema + case schema together.

### Minimal `cases` model

- Table `**cases**` (`backend/models/case_orm.py`), keyed by string `**id**` (same value as `**case_id**` in URLs and RAG).
- Columns used by the AI deadline checker: `**claim_notice_at**`, `**proof_of_claim_at**`, `**last_deadline_alert_at**`.
- JSON columns: `**stage_a_json**`, `**stage_b_json**`, cached `**report_payload_json**`, `**chat_context_json**`, plus timestamps.

### Policy + ask (Lou’s first milestone)

Still the primary demo path; contract details remain in `**docs/KE_API_CONTRACT_ZH.md**`.


| Method | Path                      | Notes                                                  |
| ------ | ------------------------- | ------------------------------------------------------ |
| `POST` | `/cases/{case_id}/policy` | `multipart/form-data`, field name `**file**`, PDF only |
| `POST` | `/cases/{case_id}/ask`    | JSON `{"question": "..."}`                             |


- `**case_id**` must match `^[A-Za-z0-9_-]{1,64}$`.
- Upload/ask call `**ensure_case**`: the row is created automatically if missing (no strict requirement to call `POST /cases` first for RAG-only flows).

### Accident workflow (second line)

Aligned with `**docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md**` and `**backend/models/accident_types.py**`.


| Method  | Path                                | Purpose                                                                          |
| ------- | ----------------------------------- | -------------------------------------------------------------------------------- |
| `POST`  | `/cases`                            | Create a case; optional body `{"case_id": "my-id"}` or server-generated `case-…` |
| `PATCH` | `/cases/{case_id}/accident/stage-a` | Merge JSON into Stage A intake                                                   |
| `PATCH` | `/cases/{case_id}/accident/stage-b` | Merge JSON into Stage B intake                                                   |
| `POST`  | `/cases/{case_id}/accident/report`  | Build report via `report_payload_builder`, store payload + chat context          |
| `GET`   | `/cases/{case_id}/accident/report`  | Read stored report + chat context                                                |


**PDF file generation** and **real group-chat rooms** are not implemented yet; the API returns **JSON** suitable for preview and future PDF/chat wiring.

### Claim dates & chat (app hooks)


| Method  | Path                           | Purpose                                                                                         |
| ------- | ------------------------------ | ----------------------------------------------------------------------------------------------- |
| `PATCH` | `/cases/{case_id}/claim-dates` | Update claim dates; clears `**last_deadline_alert_at`** for deadline alerts                     |
| `POST`  | `/cases/{case_id}/chat/event`  | Body maps to `**ChatEvent**` → `**handle_chat_event**`; response may be `null` or an AI payload |


### Tests

- **Unit tests** — `pytest` from `backend` (many paths mocked; no live DB required).
- **Integration tests** — `pytest -m integration` — real `**DATABASE_URL`** (Postgres + pgvector); see `**backend/tests/test_integration_cases_db.py**`. These cover case + accident + claim-dates, **not** OpenAI/RAG.

### Local paths

- Uploaded policies are stored under `**backend/.local_data/policies/{case_id}/`** (configurable via `app/paths.py`).

---

## Tips for Lou (frontend)

### 1. Base URL and CORS

- Default dev server: e.g. `http://127.0.0.1:8000` (see `APP_HOST` / `APP_PORT` in `.env`).
- CORS allow-lists are configured in `**backend/.env**` (`CORS_ALLOW_ORIGINS`, `CORS_ALLOW_ORIGIN_REGEX`). Add your dev origin if the browser blocks requests.

### 2. Policy upload

- Use `**POST /cases/{case_id}/policy**` with form field `**file**` (not `upload` or `document`).
- Only **PDF**; server checks magic bytes `%PDF`.
- Response includes `**chunk_count`** and `**status: "indexed"**` when ingest succeeds.

### 3. Ask

- `**POST /cases/{case_id}/ask**` with JSON `**question**` (string, required, max length 4000).
- Response includes `**answer**`, `**disclaimer**`, `**citations**`. Each citation should expose at least: `**source_type**` (`kb_a` vs `kb_b`), `**source_label**`, `**document_id**`, `**page_num**`, `**section**`, `**excerpt**` — use `**source_type**` in the UI so users can tell “my policy” vs “external reference”.

### 4. Accident forms — field names

- **Do not invent a parallel schema.** Use the same **snake_case** names as in `**backend/models/accident_types.py`** (and `**ACCIDENT_WORKFLOW_CONTRACT_ZH.md**`): e.g. `occurred_at`, `quick_summary`, `owner_party`, `photo_attachments`, `detailed_narrative`, `witness_contacts`, enums like `role`, `category`.
- **PATCH** bodies are **deep-merged** into stored JSON; omit fields you are not changing.

### 5. Suggested UX order

1. `**POST /cases`** (optional if you only use RAG with a known `case_id` string).
2. Stage A form → `**PATCH .../accident/stage-a**`
3. Stage B form → `**PATCH .../accident/stage-b**`
4. `**POST .../accident/report**` then `**GET .../accident/report**` for preview / pinned summary data.
5. Claim dates when the user has them → `**PATCH .../claim-dates**` (ISO-8601 datetimes).

### 6. Errors worth handling in UI

- **503** — `DATABASE_URL is not configured`, `OPENAI_API_KEY is not configured`, or `**AI bootstrap failed: …`** (show a friendly “backend not ready” message).
- **400** — invalid `case_id`, non-PDF upload, empty question, etc.
- **404** — missing case or accident report not generated yet on `**GET .../accident/report`**
- **409** — `**POST /cases`** with a duplicate `case_id`

### 7. Health check

- `**GET /health**` — use to gate the demo: `status`, `ai_ready`, `ai_bootstrap_error`.

### 8. OpenAPI

- `**GET /docs**` (Swagger UI) on the running server for quick experiments.

---

## Related docs


| Doc                                     | Content                             |
| --------------------------------------- | ----------------------------------- |
| `docs/KE_API_CONTRACT_ZH.md`            | Minimal policy + ask contract       |
| `docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md` | Stage A/B + report + chat context   |
| `docs/KE_WU_HANDOFF_ZH.md`              | Original integration scope          |
| `backend/.env.example`                  | Env vars for local / shared backend |


---

## Environment reminder (for anyone running the stack)

- `**DATABASE_URL**` — Postgres with **pgvector**; use async driver `**postgresql+psycopg://...`**
- `**OPENAI_API_KEY**` — Required for policy ingest + ask + chat AI paths
- Run `**uvicorn**` from `**backend/**` so `**.env**` is picked up (`ai/config.py` loads `env_file=".env"` relative to the process working directory)

