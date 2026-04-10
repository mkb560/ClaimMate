# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClaimMate is an AI-powered car insurance claims copilot for consumers (not insurers). It helps policyholders understand their policy, collect accident details, track claim deadlines, and get AI-backed support in disputes. This is a USC DSCI 560 course project prototype with a working AI backend and minimal demo frontend.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy AsyncEngine, pgvector, OpenAI (`gpt-5.4-mini`, `text-embedding-3-large`)
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4
- **Database:** PostgreSQL 16 + pgvector extension (runs in Docker on port 5433)
- **CI:** GitHub Actions runs `pytest` and `run_chat_ai_eval.py` on every push

## Common Commands

### Backend

All backend commands run from `backend/` using the local venv:

```bash
# Install dependencies
cd backend && python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pip install -e '.[dev]'

# Start backend (requires DATABASE_URL and OPENAI_API_KEY env vars)
./.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run all unit tests
./.venv/bin/pytest

# Run a single test file or test
./.venv/bin/pytest tests/test_mention.py
./.venv/bin/pytest tests/test_mention.py::test_exact_function -v

# Run integration tests (requires live Postgres+pgvector)
DATABASE_URL=postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate ./.venv/bin/pytest -m integration

# Chat AI deterministic eval (no OpenAI/DB needed)
./.venv/bin/python scripts/run_chat_ai_eval.py --json-out /tmp/eval.json

# Full HTTP smoke test (requires running backend)
./.venv/bin/python scripts/run_demo_smoke.py --base-url http://127.0.0.1:8000

# Index KB-B regulatory docs
DATABASE_URL=... OPENAI_API_KEY=... ./.venv/bin/python scripts/index_local_kb_b.py

# Seed a demo policy into KB-A
DATABASE_URL=... OPENAI_API_KEY=... ./.venv/bin/python scripts/seed_demo_policy.py --case-id allstate-change-2025-05
```

### Frontend

```bash
cd frontend && npm install
npm run dev      # dev server
npm run build    # production build
npm run lint     # eslint
```

### Database (Docker)

```bash
docker run -d --platform linux/arm64 \
  --name claimmate-pgvector \
  -e POSTGRES_USER=claimmate -e POSTGRES_PASSWORD=claimmate -e POSTGRES_DB=claimmate \
  -p 5433:5432 pgvector/pgvector:pg16
```

### Environment Variables

See `backend/.env.example`. Minimum required: `OPENAI_API_KEY` and `DATABASE_URL`.

## Architecture

### Dual-Knowledge RAG Pipeline

The core differentiator is dual-source retrieval:
- **KB-A:** User-uploaded policy PDFs (per-case, stored in `backend/.local_data/policies/<case_id>/`)
- **KB-B:** California/U.S. insurance regulations (from `claimmate_rag_docs/`)

Both are chunked, embedded, and stored in pgvector. `answer_policy_question()` retrieves from both sources and generates answers with inline `[S#]` citations. Deterministic extraction handles structured policy facts (limits, VIN, etc.) before falling back to LLM generation. A citation rescue pass runs if the first generation lacks parseable citations.

### Backend Module Layout

- `backend/main.py` — FastAPI app with lifespan bootstrap, CORS, router includes
- `backend/ai/` — All AI logic, organized by domain:
  - `ingestion/` — PDF/HTML parsing, chunking, embedding, pgvector storage, KB-A/KB-B indexing
  - `rag/` — Query engine (dual-source retrieval), citation formatting, prompt templates
  - `policy/` — Deterministic policy fact extraction (tried before LLM generation)
  - `chat/` — Chat AI orchestration: mention detection, stage routing (1/2/3), dispute/deadline triggers
  - `dispute/` — Keyword + LLM-based dispute detection
  - `deadline/` — California deadline window computation and reminders
  - `accident/` — Report payload builder from two-stage intake data
  - `config.py` — Centralized pydantic-settings config
  - `runtime.py` — Async engine creation and schema bootstrap
  - `clients.py` — Lazy cached AsyncOpenAI client
- `backend/app/` — App layer: routers, case service, request validation, demo seed helpers
- `backend/models/` — Shared types: `ai_types.py` (chat/citation enums), `accident_types.py` (intake schemas), `case_orm.py` (SQLAlchemy ORM)
- `backend/tests/` — Deterministic unit tests; integration tests marked with `@pytest.mark.integration`
- `backend/scripts/` — CLI tools for indexing, querying, seeding, evaluation, and remote sharing

### Chat AI Stages

Stage routing is central to chat behavior:
- **Stage 1:** Owner only — proactive tips after policy indexing
- **Stage 2:** Invite sent, no external party yet
- **Stage 3:** Adjuster/repair shop present — answers prefixed with "For reference:" for neutrality

### Frontend

Minimal Next.js demo at `frontend/`. API wrapper in `src/lib/api.ts`, single-page demo in `src/app/page.tsx`. Read Next.js docs in `node_modules/next/dist/docs/` before modifying — this is Next.js 16 with breaking changes from older versions.

### Database Wiring

`vector_store.py` requires `init_engine(engine)` before any DB operations. `bootstrap_vector_store(engine)` in `runtime.py` handles schema creation including the `cases` table. The `cases` table stores accident intake JSON, report/chat payloads, and deadline timestamps (`claim_notice_at`, `proof_of_claim_at`, `last_deadline_alert_at`).

## Key Conventions

- Always use `./.venv/bin/pytest` (not bare `pytest`) — dependencies like `pgvector` must come from the project venv
- `pytest` config: `asyncio_mode = "auto"`, pythonpath = `"."`, testpaths = `["tests"]`
- Demo policy PDFs in `demo_policy_pdfs/` must NOT be indexed as KB-B — they are KB-A only
- Three built-in demo cases: `allstate-change-2025-05`, `allstate-renewal-2025-08`, `progressive-verification-2026-03`
- High-coordination files (edit carefully, coordinate with team): `backend/models/ai_types.py`, `backend/models/accident_types.py`, shared API contracts
- After modifying backend code, run `./.venv/bin/pytest`
- Keep `backend/.env.example` updated when adding new env vars
- Branch naming: `mingtao/...`, `ke/...`, `lou/...`

## Team Ownership

- **Mingtao Ding:** `backend/ai/`, `backend/models/ai_types.py`, AI contracts, RAG, dispute, deadline, chat AI
- **Ke Wu:** `backend/app/`, FastAPI routes, case/DB layer, auth, deployment, chat backend
- **Yi-Hsien Lou:** `frontend/`, accident form UI, report UX, demo flow

## Not Yet Implemented

Do not assume these exist: full auth, WebSocket rooms, Stripe, invite links, PDF report generation, DB migrations, production deployment config.
