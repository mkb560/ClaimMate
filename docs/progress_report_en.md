# ClaimMate Project Progress and Repository Structure

This document uses the product vision and role division outlined in the root [`README.md`](../README.md) as a baseline, **synchronously detailing the actual current progress of the repository** (some details are more up-to-date than the "Minimum API" section in the README). It is intended to help the team align on status and plan next steps.

---

## Product Vision (Three Main Tracks)

Consistent with the README, the complete story is divided into:

| Track | Content | Current Status (Summary) |
|------|------|------------------|
| **1** | Dual-Source RAG (Policy KB-A + Regulations KB-B) | **Most Complete**: ingest, retrieval, grounded answering, citations, dispute/staged chat logic, etc., are implemented in `backend/ai/`. |
| **2** | Two-Stage Accident Intake and Reporting | **Contracts + Backend APIs + Storage** are connected; **Frontend demo can read snapshot / report**; **Complete forms and finalized PDF export** are still pending. |
| **3** | AI Support in Claims Group Chat | Modules like **`handle_chat_event` exist**; **HTTP endpoints are connected**; **Frontend demo can display chat responses**; **Complete WebSocket room / invite product layer** is still pending. |

The project positioning remains a **course project / prototype**: The AI core and product backend are largely connected, but it is **not** a production-grade platform (lacking comprehensive auth, billing, and migration systems, etc.).

---

## Completed Components

### 1. Dual-Source RAG (Track 1)

* **KB-A:** User-uploaded policy PDF, chunking + embedding + retrieval by `case_id`.
* **KB-B:** Index of California / U.S. regulations and reference materials (see `claimmate_rag_docs/`).
* OpenAI + **pgvector** + SQLAlchemy AsyncEngine.
* Default available models and dimensionality strategies are detailed in the README (e.g., `gpt-5.4-mini`, 1536-dim embedding to remain compatible with schema).
* Citations, policy field extraction, dispute / mention / deadline detection, and other AI modules complementing RAG.

**Core Directories:** `backend/ai/ingestion/`, `backend/ai/rag/`, `backend/ai/policy/`, plus `backend/ai/chat/`, `backend/ai/deadline/`, `backend/ai/dispute/`, etc.

### 2. Track 2: Data Contract and Report Middleware

* `StageAAccidentIntake` / `StageBAccidentIntake` / `AccidentReportPayload` / `AccidentChatContext`
* Deterministic `report_payload_builder` (avoids LLM-hallucinated structures).

**Core Files:** `backend/models/accident_types.py`, `backend/ai/accident/report_payload_builder.py`  
**Contract Details:** [`ACCIDENT_WORKFLOW_CONTRACT_ZH.md`](ACCIDENT_WORKFLOW_CONTRACT_ZH.md)

### 3. Application-Layer FastAPI and `cases` Persistence

Compared to the README which only lists three routes, the current backend includes:

* **Startup & DB:** Creates a shared engine in `lifespan`; `bootstrap` ensures the **vector table** + **`cases` table** (including `claim_notice_at`, `proof_of_claim_at`, `last_deadline_alert_at`, etc., for the deadline module).
* **Routing Layer:** `main.py` handles app assembly; specific endpoints are in `backend/app/routers/`.
* **Policy + Ask (Main Frontend Demo Path)** * `GET /health`  
    * `GET /demo/policies`
    * `GET /cases/{case_id}/policy`
    * `POST /cases/{case_id}/demo/seed-policy`
    * `POST /cases/{case_id}/policy` (`multipart/form-data`, field name `file`)  
    * `POST /cases/{case_id}/ask` (JSON `question`)  
* **Accident Workflow APIs** * `POST /cases`  
    * `GET /cases/{case_id}`  
    * `POST /cases/{case_id}/demo/seed-accident`  
    * `PATCH /cases/{case_id}/accident/stage-a`  
    * `PATCH /cases/{case_id}/accident/stage-b`  
    * `POST /cases/{case_id}/accident/report`  
    * `GET /cases/{case_id}/accident/report`  
* **Claim Dates & Chat Entry** * `PATCH /cases/{case_id}/claim-dates`  
    * `POST /cases/{case_id}/chat/event` → `handle_chat_event` (persists user/AI messages to DB)  
    * `GET /cases/{case_id}/chat/messages`, `POST /cases/{case_id}/chat/messages` (simplified `@AI` posting)  
    * `DELETE /cases/{case_id}` — Deletes the case, chat history, and the KB-A vectors for that case (minimum lifecycle / demo reset).  

The snapshot from `GET /cases/{case_id}` includes **`room_bootstrap`** (derived from the `chat_context` generated during accident reporting), facilitating display and pinned context in the chat area.

**Note:** Uploaded PDFs are saved locally at `backend/.local_data/policies/{case_id}/` (useful for development and debugging).

### 4. Testing and Integration Support

* **Unit Tests:** `cd backend && pytest` (extensive logic mocking, does not require local Postgres).
* **Optional Integration Tests:** `pytest -m integration` (requires real `DATABASE_URL` for Postgres + pgvector, see `backend/tests/test_integration_cases_db.py`).
* **Demo Policy Seed:** `python scripts/seed_demo_policy.py --case-id allstate-change-2025-05` (indexes fixed demo PDFs into KB-A).
* **End-to-End Smoke Test:** `python scripts/run_demo_smoke.py --base-url http://127.0.0.1:8000` (runs real HTTP paths: `health -> demo/policies -> seed-policy -> ask -> seed-accident -> chat/event`).
* **Remote Shared Local Backend:** `backend/scripts/run_shared_backend.sh` (details in [`REMOTE_SHARED_BACKEND_ZH.md`](REMOTE_SHARED_BACKEND_ZH.md)).

### 5. Documentation and Frontend Integration Guide

* Minimum API Contract: [`KE_API_CONTRACT_ZH.md`](KE_API_CONTRACT_ZH.md)  
* Ke's Handoff Notes: [`KE_WU_HANDOFF_ZH.md`](KE_WU_HANDOFF_ZH.md)  
* Lou's Integration Summary: [`BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md`](BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md)  
* Lou's Direct Call Examples: [`YI_FRONTEND_API_EXAMPLE_ZH.md`](YI_FRONTEND_API_EXAMPLE_ZH.md)  
* Doc Index: [`docs/README.md`](README.md)

---

## Pending Tasks

The following align with the "Incomplete Components" in the README, refined slightly based on the **current implementation**:

| Direction | Description |
|------|------|
| **Accident Frontend** | Stage A / B forms, photo uploads, and report previews need to align with API fields (see accident contract and Lou's docs). |
| **PDF Accident Report Export** | Backend outputs standard JSON; **generating downloadable PDF files** remains to be implemented. |
| **Group Chat Product Layer** | WebSocket rooms, registration-free invite access, and full integration with pinned reports/context. |
| **Payment / Stripe** | Not prioritized for the current prototype scope. |
| **Full Deployment & DevOps** | Lacks a unified production deployment and monitoring solution. |
| **Formal Case CRUD / DB Migration** | Currently uses dev-friendly `create_all` + string `case_id`; long-term evolution to UUID, Alembic, etc. is needed. |
| **End-to-End Automation** | OpenAI-dependent RAG paths are mostly tested manually or via mocks; can add E2E tests with API keys as needed (while minding costs). |

**If the Course Demo is the Priority:** The README suggests ensuring **upload + ask remain stable**, the **remote shared backend is usable**, and **demo questions and flows are fixed** (see [`DEMO_PLAYBOOK_ZH.md`](DEMO_PLAYBOOK_ZH.md)).

---

## Current Repository Structure

Consistent with the top-level README, below is the detailed structure of the **backend** and docs (omitting `.venv`/`venv`, `__pycache__`, `.pytest_cache`, etc.):

```text
ClaimMate/
├── AGENTS.md
├── README.md
├── backend/
│   ├── main.py                 # FastAPI entry: lifespan, CORS, mounts routers
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── .env / .env.example     # Local config (do not commit secrets)
│   ├── ai/                     # AI Core: ingestion, RAG, policy, chat, deadline, dispute, accident...
│   ├── app/                    # App Layer: case service, validation, routers/
│   ├── models/                 # Shared Models: accident_types, ai_types, case_orm, etc.
│   ├── tests/                  # Pytest (including 'integration' marked cases)
│   ├── scripts/                # Scripts for indexing, demo seed, smoke tests, shared backend
│   └── .local_data/            # Local uploads like policies (large files usually uncommitted)
├── frontend/                   # Next.js demo UI: handles policy, snapshot, report, chat preview
├── claimmate_rag_docs/         # KB-B static regulations/corpus
├── demo_policy_pdfs/           # Policy PDF samples for demonstration
└── docs/                       # Contracts, progress, collaboration guides, run instructions
