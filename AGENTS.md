# AGENTS.md

This file gives coding agents the current source of truth for this repository.

## Repository Status

- As of 2026-03-29, this directory is an active Git repository cloned from GitHub.
- The actual codebase in this repo is currently the **AI/backend scaffold** under `backend/`.
- The repository root also contains the curated `claimmate_rag_docs/` directory for local KB-B indexing.
- The root folder may also contain planning documents such as `plan.md`, but those are not application runtime code.
- The FastAPI app currently exposes only a minimal `/health` route in `backend/main.py`.
- Most product behavior currently exists as reusable AI modules plus tests, not as fully wired API endpoints.

## Product Context

**ClaimMate** is an AI-powered car insurance claims copilot for consumers.

Current team ownership:
- **Mingtao Ding:** AI core, RAG, dispute detection, deadline tracking, chat AI behavior
- **Ke Wu:** full-stack product layer, FastAPI integration, database/app layer, deployment, Stripe, chat backend
- **Yi-Hsien Lou:** accident form, PDF generator, UI/UX, business-facing deliverables

## What Is Actually Implemented In This Repo

### Backend package layout

```text
backend/
├── main.py
├── pyproject.toml
├── requirements.txt
├── .env.example
├── ai/
│   ├── clients.py
│   ├── config.py
│   ├── chat/
│   ├── deadline/
│   ├── dispute/
│   ├── ingestion/
│   ├── policy/
│   └── rag/
├── models/
│   └── ai_types.py
└── tests/
```

### Implemented modules

- `backend/main.py`
  - Minimal FastAPI app with `/health`
  - Does **not** yet wire the AI modules into REST routes or WebSocket handlers

- `backend/ai/config.py`
  - Centralized environment-based configuration using `pydantic-settings`
  - Defines model names, DB URL, S3 settings, vector settings, chunk sizes, and deadline thresholds

- `backend/ai/clients.py`
  - Lazily creates a cached `AsyncOpenAI` client

- `backend/ai/ingestion/`
  - `pdf_parser.py`: extracts PDF text and tables
  - `html_parser.py`: converts HTML to text
  - `chunker.py`: token-aware chunking with different KB-A / KB-B settings
  - `embedder.py`: OpenAI embeddings wrapper
  - `vector_store.py`: `pgvector` + SQLAlchemy model and retrieval helpers
  - `ingest_policy.py`: ingests a policy PDF from S3 or a local file, chunks it, embeds it, and stores case chunks
  - `kb_b_loader.py`: indexes KB-B sources from remote URLs or a local docs directory
  - `kb_b_catalog.py`: shared labels and dispute-relevant KB-B document IDs

- `backend/ai/runtime.py`
  - Creates the shared async SQLAlchemy engine from `DATABASE_URL`
  - Bootstraps the `pgvector` schema and sessionmaker for local scripts or FastAPI startup

- `backend/ai/rag/`
  - `query_engine.py`: dual-source retrieval over policy chunks and regulatory chunks
  - `citation_formatter.py`: context packing and citation extraction/fallbacks
  - `prompt_templates.py`: system prompts, disclaimer, and fallback text

- `backend/ai/policy/`
  - `fact_extractor.py`: deterministic extraction for common policy facts such as policyholders, policy number, policy period, insurer, policy change, discount totals, optional coverage, and verification-of-insurance detection
  - Structured policy answers are attempted before general LLM generation for supported question types

- `backend/ai/dispute/`
  - `keyword_filter.py`: fast keyword-based dispute detection
  - `semantic_detector.py`: LLM-based JSON classification for dispute type

- `backend/ai/deadline/`
  - `deadline_checker.py`: computes California deadline windows and can emit reminder responses
  - Uses raw SQL against a shared `cases` table until a shared ORM model exists

- `backend/ai/chat/`
  - `mention_handler.py`: detects `@AI` mentions and extracts the question
  - `stage_router.py`: stage 1 / 2 / 3 routing based on participants and invite state
  - `stage_prompts.py`: stage-specific tone and guidance
  - `chat_ai_service.py`: main orchestration layer for mention-triggered, dispute-triggered, proactive, and deadline-triggered AI responses

- `backend/models/ai_types.py`
  - Shared dataclasses and enums for chat stages, triggers, citations, events, and response payloads

- `backend/tests/`
  - Deterministic tests for mention parsing, stage routing, deadline math, dispute keyword logic, citations, local KB-B source discovery, and chat orchestration

- `backend/scripts/`
  - `index_local_kb_b.py`: indexes local files from `claimmate_rag_docs/` into PostgreSQL + `pgvector`
  - `ingest_local_policy.py`: ingests a local policy PDF into KB-A for a case
  - `query_local_rag.py`: runs a local RAG question against the vector store
  - `run_demo_eval.py`: runs the fixed local demo/eval suite against known policy PDFs and mixed KB-A + KB-B questions

## Current Runtime Behavior

### RAG

- User policy documents are treated as **KB-A**
- Regulatory/reference materials are treated as **KB-B**
- Local curated PDFs under `claimmate_rag_docs/` can be indexed as KB-B without downloading remote sources
- Supported policy-fact questions are answered first through deterministic extraction before falling back to general RAG generation
- `answer_policy_question(case_id, question)` retrieves from both sources and answers with inline `[S#]` citations
- `answer_dispute_question(...)` narrows regulatory retrieval to dispute-relevant documents and applies stage-specific instructions
- If the first generation pass returns a grounded fallback response, the RAG layer performs a narrower rescue pass over top snippets before giving up
- All final answers append a fixed disclaimer

### Chat AI

- Stage rules:
  - `stage_1`: owner only
  - `stage_2`: invite sent but no external party joined yet
  - `stage_3`: adjuster or repair shop present
- `handle_chat_event(...)` supports:
  - proactive response when policy indexing finishes in stage 1
  - `@AI` mention handling
  - keyword-triggered dispute escalation
  - fallback deadline reminder checks
- Stage 3 answers are prefixed with `For reference:` to keep the tone neutral in multi-party chat

### Deadline reminders

- Current reminder windows:
  - 15-day acknowledgment window from `claim_notice_at`
  - 40-day decision window from `proof_of_claim_at`
- Reminder cooldown is controlled by `last_deadline_alert_at`

## Important Integration Contracts

### Database / engine wiring

- `backend/ai/ingestion/vector_store.py` requires `init_engine(engine)` to be called before any DB-backed vector or deadline operations
- `ensure_vector_schema(engine)` should be run during bootstrap/migration setup
- `backend/ai/runtime.py` now provides `create_ai_engine()` and `bootstrap_vector_store(engine)` for this setup

### Required `cases` fields

The AI deadline module assumes the application layer provides these columns on `cases`:

- `claim_notice_at TIMESTAMPTZ NULL`
- `proof_of_claim_at TIMESTAMPTZ NULL`
- `last_deadline_alert_at TIMESTAMPTZ NULL`

### Storage assumptions

- Policy ingestion currently expects policy PDFs to be available in S3
- KB-B indexing can optionally back up downloaded source files to S3
- Vector storage uses PostgreSQL + `pgvector`

## What Is Not Yet Implemented Here

Do **not** assume the following already exist in this repo:

- full authentication flows
- case CRUD routes
- chat REST API
- WebSocket room management
- Stripe checkout or webhook handling
- invite-link issuance/validation
- PDF report generation pipeline
- shared SQLAlchemy ORM for application tables
- database migrations
- frontend Next.js app
- deployment config for Railway or Vercel

If you mention those systems, clearly label them as planned integration targets unless you actually add them.

## Local Development

### Recommended commands

```bash
cd backend
./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn main:app --reload
./.venv/bin/pytest
DATABASE_URL=postgresql+psycopg://... ./.venv/bin/python scripts/index_local_kb_b.py
DATABASE_URL=postgresql+psycopg://... ./.venv/bin/python scripts/query_local_rag.py "What is the 15-day claim acknowledgment rule?"
```

If `.venv` does not exist yet:

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

### Environment variables

Use `backend/.env.example` as the template. Current variables:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `RAG_MODEL`
- `CLASSIFICATION_MODEL`
- `EMBEDDING_MODEL`
- `DATABASE_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`
- `AWS_REGION`

### Testing note

- Running `pytest` outside the project virtual environment may fail if required packages such as `pgvector` are not installed in the active interpreter
- In this repo, `./.venv/bin/pytest` is the reliable command
- Local KB-B indexing requires both a working `DATABASE_URL` and an `OPENAI_API_KEY` with available quota
- The local demo/eval suite can be run with `DATABASE_URL=... OPENAI_API_KEY=... ./.venv/bin/python scripts/run_demo_eval.py`

## GitHub Collaboration Recommendations

When this project is moved onto GitHub, use the repository root as the Git root.

### Recommended ownership split

- **Mingtao:** `backend/ai/`, `backend/models/ai_types.py`, AI integration contracts
- **Ke Wu:** product-layer FastAPI routes, shared DB models, auth, Stripe, deployment, app-layer chat backend
- **Yi-Hsien Lou:** frontend UI, accident form, generated report UX, Figma-to-code handoff assets

### Recommended workflow

- Keep `main` always deployable
- Use short-lived feature branches per task
- Open pull requests instead of pushing directly to `main`
- Ask for at least one teammate review before merge on shared or high-risk code
- Merge quickly after approval to avoid long-lived branch drift
- GitHub Actions now runs `Backend CI` on pull requests to `main` and on pushes to `main`
- Use `CONTRIBUTING.md` and `.github/PULL_REQUEST_TEMPLATE.md` as the shared collaboration baseline

### Branch naming examples

- `feature/rag-query-routing`
- `feature/chat-room-api`
- `feature/accident-form-ui`
- `fix/deadline-alert-copy`

### Coordination rules

- Avoid editing the same files in parallel unless coordinated first
- Treat `backend/models/ai_types.py` and shared API contracts as high-coordination files
- When adding a new integration point between AI core and app layer, document the contract in both code comments and PR description
- Keep `.env.example` updated whenever a new required environment variable is introduced

## Guidance For Future Agents

- Read `plan.md` for project intent, but treat the code under `backend/` as the final authority for what is actually implemented
- Do not describe this repository as a complete full-stack app unless that code has been added
- Prefer updating tests when changing AI orchestration or parsing behavior
- After modifying backend code, run `./.venv/bin/pytest`
- If you add new app-layer routes or integrations, also update this file so the next agent sees the real repo state
