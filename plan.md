# ClaimMate — Mingtao Ding AI Core MVP Plan (Synced To Current Backend Scaffold)

## Context

Mingtao owns the AI core for ClaimMate: dual-knowledge RAG, dispute detection, deadline reminders, and group chat AI behavior. This document is the **current source of truth** for the MVP backend scaffold that now exists under `backend/` in the project repo.

This version replaces the older Qwen/DashScope plan. The backend AI scaffold is now built around **OpenAI + pgvector + SQLAlchemy AsyncEngine**, with a narrower MVP scope aimed at the Phase 1 prototype.

**Current scope:**
- Dual-source RAG over user policy PDFs (KB-A) and California/U.S. regulatory docs (KB-B)
- Two-layer dispute detection
- Passive deadline reminders based on stored claim dates
- Group chat AI stages 1/2/3 with limited proactive behavior
- Fixed disclaimer + inline source citations

**Explicitly out of Phase 1 scope:**
- Second-pass hallucination validator
- Multi-provider model abstraction
- DashScope / Qwen deployment logic
- Production-grade CCPA retention matrix for logs/observability
- Full evaluation harness beyond deterministic tests

---

## Final Tech Stack

| Component | Final Choice | Why |
|---|---|---|
| Primary LLM | `gpt-5.4-mini` | Strong mini model for grounded QA, coding, and lower-latency production use |
| Classification LLM | `gpt-5.4-nano` | Cheapest GPT-5.4-class option for lightweight dispute routing |
| Embeddings | `text-embedding-3-large` at 1536 dimensions | Better retrieval quality while staying compatible with the current `pgvector(1536)` schema |
| Vector store | PostgreSQL + `pgvector` | Clean relational integration and case-level isolation |
| DB access | shared `SQLAlchemy AsyncEngine` | One pool, one driver, easier handoff with Ke Wu's FastAPI app |
| Chunking | `tiktoken` | Simple token-aware chunking without extra framework overhead |
| PDF parsing | `pdfplumber` + `pypdf` fallback | Handles tables and recovers text from simpler PDFs |
| HTML parsing | `html2text` | Good enough for KB-B HTML sources |
| Storage | AWS S3 | Policy PDFs and optional KB-B backups |

**Final stack:** `openai` + `pgvector` + `sqlalchemy[asyncio]` + `tiktoken` + `pdfplumber` + `pypdf` + `html2text` + `boto3`

---

## Current File Structure

```text
backend/
├── pyproject.toml
├── requirements.txt
├── .env.example
├── main.py
├── models/
│   ├── __init__.py
│   └── ai_types.py
├── ai/
│   ├── __init__.py
│   ├── clients.py
│   ├── config.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── types.py
│   │   ├── pdf_parser.py
│   │   ├── html_parser.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── vector_store.py
│   │   ├── kb_b_loader.py
│   │   └── ingest_policy.py
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── prompt_templates.py
│   │   ├── citation_formatter.py
│   │   └── query_engine.py
│   │
│   ├── dispute/
│   │   ├── __init__.py
│   │   ├── keyword_filter.py
│   │   └── semantic_detector.py
│   │
│   ├── deadline/
│   │   ├── __init__.py
│   │   └── deadline_checker.py
│   │
│   └── chat/
│       ├── __init__.py
│       ├── stage_router.py
│       ├── stage_prompts.py
│       ├── mention_handler.py
│       └── chat_ai_service.py
│
└── tests/
    ├── test_stage_router.py
    ├── test_keyword_filter.py
    ├── test_deadline_checker.py
    ├── test_mention_handler.py
    ├── test_citation_formatter.py
    └── test_chat_ai_service.py
```

---

## Implemented Architecture

```text
Policy PDF / Regulatory HTML or PDF
        │
   pdf_parser.py / html_parser.py
        │
   chunker.py (tiktoken)
        │
   embedder.py (OpenAI embeddings)
        │
   vector_store.py (SQLAlchemy + pgvector)
        │
   query_engine.py
        │
   gpt-5.4-mini
        │
   AnswerResponse with citations + disclaimer
```

### Storage pattern

- `vector_store.py` owns a module-level `async_sessionmaker`.
- `init_engine(engine: AsyncEngine)` is called once at FastAPI startup.
- `get_sessionmaker()` is the public accessor used by AI modules that need DB access outside ingestion.
- `ensure_vector_schema(engine)` can be called during app startup or migration/bootstrap to create the `vector` extension and AI table.
- Retrieval uses `pgvector.sqlalchemy.VECTOR(...)` plus `cosine_distance()` directly.
- No `raw asyncpg`, no second pool, and no manual `CAST(:embedding AS vector)` SQL path.

### Why shared `AsyncEngine` over raw `asyncpg`

For this project, shared `AsyncEngine` is the better default:

- Ke Wu's application layer will already use SQLAlchemy and psycopg.
- A second asyncpg pool would increase connection management complexity for little MVP gain.
- `pgvector-python` supports SQLAlchemy natively, including vector columns and cosine distance ordering.
- One engine means easier startup wiring, fewer moving parts, and less coupling between app and AI modules.

Use `raw asyncpg` only if a future performance bottleneck is proven and localized to vector queries. Nothing in the current MVP requires that extra complexity.

---

## Data Model

### `vector_documents`

Current scaffold assumes the AI vector table below. The **recommended final integration target** is for `vector_documents.case_id` to match `cases.id` exactly and, if Ke Wu uses UUID primary keys, to become `UUID REFERENCES cases(id) ON DELETE CASCADE`. The current scaffold keeps `case_id` as a string placeholder only to avoid blocking the AI scaffold on Ke Wu's unfinished ORM/model layer.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE vector_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     VARCHAR(64),
    source_type VARCHAR(8) NOT NULL CHECK (source_type IN ('kb_a', 'kb_b')),
    document_id VARCHAR(128),
    chunk_text  TEXT NOT NULL,
    page_num    INT,
    section     VARCHAR(256),
    embedding   vector(1536) NOT NULL,
    metadata    JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON vector_documents (source_type, case_id);
```

**Phase 1 choice:** no ANN index yet. Expected chunk count is small enough that exact cosine ordering is acceptable and simpler.

### `cases` additions

The deadline module now assumes these fields exist on `cases`:

```sql
ALTER TABLE cases
ADD COLUMN claim_notice_at TIMESTAMPTZ NULL,
ADD COLUMN proof_of_claim_at TIMESTAMPTZ NULL,
ADD COLUMN last_deadline_alert_at TIMESTAMPTZ NULL;
```

**Meaning:**
- `claim_notice_at`: when the claim notice/report was submitted or received
- `proof_of_claim_at`: when the material needed for the insurer's 40-day decision clock was submitted
- `last_deadline_alert_at`: cooldown to avoid spamming reminders more than once in 24 hours

### Deadline integration contract

The AI module does **not** own a `Case` ORM model yet. `deadline_checker.py` currently uses raw SQL against `cases` intentionally so the AI scaffold can integrate before Ke Wu's shared ORM layer is finalized.

That means the application layer must guarantee:
- a real `cases` table exists
- the three deadline columns above have been migrated
- `id` is queryable with the `case_id` string passed into AI functions, or the integration layer adapts the AI boundary once the final `cases.id` type is fixed
- case deletion flow clears case-linked S3 objects in addition to DB rows

---

## KB-B Regulatory Sources

The MVP loader indexes these six documents:

| ID | Document | URL | Format |
|---|---|---|---|
| `iso_pp_0001` | ISO Standard Auto Policy PP 00 01 | `https://doi.nv.gov/uploadedFiles/doinvgov/_public-documents/Consumers/PP_00_01_06_98.pdf` | PDF |
| `naic_model_900` | NAIC Model 900 | `https://content.naic.org/sites/default/files/model-law-900.pdf` | PDF |
| `naic_model_902` | NAIC Model 902 | `https://content.naic.org/sites/default/files/model-law-902.pdf` | PDF |
| `ca_fair_claims` | CA Fair Claims Settlement Regulations | `https://www.insurance.ca.gov/01-consumers/130-laws-regs-hearings/05-CCR/fair-claims-regs.cfm` | HTML |
| `iii_nofault` | No-Fault vs At-Fault Reference | `https://www.iii.org/article/background-on-no-fault-auto-insurance` | HTML |
| `naic_complaints` | NAIC Complaint Data | `https://content.naic.org/cis_agg_reason.htm` | HTML |

Implementation notes:
- `kb_b_loader.py` downloads and indexes them sequentially.
- If S3 is configured, it also stores backup copies.
- Policy ingestion requires S3; KB-B backup upload is optional.

---

## Chunking Strategy

**KB-A (policy PDF):**
- `500` token chunks
- `50` token overlap
- section inferred from uppercase headings when possible
- tables converted to markdown where available
- metadata includes `case_id`, `page_num`, `section`

**KB-B (regulatory docs):**
- `250` token chunks
- `30` token overlap
- section inferred from statute-like headings such as `§2695.5` or `§2695.7`
- metadata includes `document_id`, `page_num`, `section`

---

## RAG Query Flow

```text
User question
    │
    ├── embed question with text-embedding-3-large (1536 dimensions)
    ├── search KB-A by case_id
    └── search KB-B across shared regulatory corpus
             │
      build <policy_context> + <regulatory_context>
             │
          gpt-5.4-mini
             │
    parse [S1], [S2] inline citations
             │
    return AnswerResponse + fixed disclaimer
```

### Grounding rules

- Answers must come only from retrieved chunks.
- If retrieval is empty or insufficient, the answer must say that information is not available.
- Every factual sentence must carry `[S#]` inline references.
- The final user-visible answer always ends with:

```text
Disclaimer: This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.
```

### Phase 1 simplification

There is **no** `response_validator.py` second-pass hallucination check in the current scaffold. Grounding is enforced through:

- prompt constraints
- limited retrieved context
- inline citation parsing
- a conservative fallback when sources are thin

---

## Prompt Design

### `SYSTEM_PROMPT_RAG`

- Answer only from `<policy_context>` and `<regulatory_context>`
- Say "not enough information" if the answer is not clearly supported
- Add `[S#]` citations after factual statements
- Never give legal advice or settlement recommendations

### `SYSTEM_PROMPT_DISPUTE`

- Explain factual rights and next steps
- Stay grounded in retrieved policy/regulatory text
- Do not advise accepting or rejecting an offer
- Keep tone neutral, especially in multi-party rooms

### Citation format

The implemented parser expects inline references such as:

```text
Your deductible is $500. [S1]
California requires acknowledgment within 15 days. [S2]
```

This is simpler to generate and easier to parse than free-form `[Source: ...]` strings.

---

## Dispute Detection

### Layer 1: keyword filter

Implemented in `keyword_filter.py`.

**Hard triggers:**
- `denied my claim`
- `claim denied`
- `bad faith`
- `underpaid`
- `refuse to pay`
- `wrong amount`
- `rejection letter`

**Soft triggers:**
- `disagree`
- `too low`
- `not fair`
- `no response`
- `delay`
- `ignored`

Soft triggers require at least 2 matches before escalating.

### Layer 2: semantic classifier

Implemented in `semantic_detector.py`.

- Model: `gpt-5.4-nano`
- Output format: JSON
- Labels: `DENIAL | DELAY | AMOUNT | OTHER | NOT_DISPUTE`

Current statute mapping in code:
- `DENIAL` → `10 CCR §2695.7(b)`
- `DELAY` → `10 CCR §2695.5(e) / §2695.7(c)`
- `AMOUNT` → `10 CCR §2695.8`
- `OTHER` → `10 CCR §2695`

When a dispute is confirmed, the service routes to dispute-focused RAG over policy chunks plus a filtered set of regulatory documents.

---

## Deadline Tracker

The old `activated_at` / Stripe-based deadline idea is no longer used.

### Current MVP model

- `claim_notice_at` drives the 15-day acknowledgment reminder
- `proof_of_claim_at` drives the 40-day decision reminder
- reminders are passive and informational only
- reminders are rate-limited to once every 24 hours via `last_deadline_alert_at`

### California timing model used by the MVP

- 15-day reminder from stored claim notice date
- 40-day reminder from stored proof-of-claim date

The AI should **not** infer legal dates from chat text and should **not** make a strong legal conclusion if the stored dates may be incomplete.

### Current reminder style

The deadline reminder explicitly says it is based on saved case dates and tells the user to update those dates if they are incomplete.

---

## Group Chat AI Stages

### Stage routing

Implemented in `stage_router.py`.

```python
def determine_stage(participants: list[Participant], invite_sent: bool) -> ChatStage:
    roles = {participant.role for participant in participants}
    has_external = "adjuster" in roles or "repair_shop" in roles

    if has_external:
        return ChatStage.STAGE_3
    if invite_sent:
        return ChatStage.STAGE_2
    return ChatStage.STAGE_1
```

### Current behavior by stage

| Stage | Condition | Behavior |
|---|---|---|
| `STAGE_1` | Owner only | One proactive "policy indexed" summary, plus `@AI` answers |
| `STAGE_2` | Owner only + invite sent | `@AI` answers and dispute/deadline responses, less unsolicited activity |
| `STAGE_3` | Any external party present | Neutral tone, prefix replies with `For reference:` |

### Mention handling

Implemented in `mention_handler.py` and `chat_ai_service.py`.

Behavior:
1. Detect `@AI` or `@ai`
2. Extract text after the mention
3. If empty, ask the user to provide a question
4. Run dispute detection first
5. If dispute confirmed, run dispute-focused RAG
6. Otherwise run standard policy question RAG
7. In Stage 3, prefix output with `For reference:`

### Non-mention behavior

If an event does not trigger a higher-priority proactive, mention, or dispute response, the fallback path is a deadline reminder if one is due.

---

## Public Interfaces

These are the public AI-core functions now exposed from `backend/ai/__init__.py`:

```python
def init_engine(engine: AsyncEngine) -> None
async def ingest_policy(s3_key: str, case_id: str) -> None
async def answer_policy_question(case_id: str, question: str) -> AnswerResponse
async def handle_chat_event(event: ChatEvent) -> AIResponse | None
async def on_claim_dates_updated(
    case_id: str,
    claim_notice_at: datetime | None,
    proof_of_claim_at: datetime | None,
) -> None
```

### Shared types

Shared types live in `backend/models/ai_types.py`.

Important enums and dataclasses:
- `ChatStage`
- `AITrigger`
- `ChatEventTrigger`
- `Participant`
- `Citation`
- `AnswerResponse`
- `AIResponse`
- `ChatEvent`

`ChatEvent` still contains:
- `case_id`
- `sender_role`
- `message_text`
- `participants`
- `invite_sent`
- `trigger`
- optional `metadata`
- optional `occurred_at`

---

## Environment Variables

Current `AIConfig` shape:

```python
openai_api_key: str = ""
openai_base_url: str = "https://api.openai.com/v1"
rag_model: str = "gpt-5.4-mini"
classification_model: str = "gpt-5.4-nano"
embedding_model: str = "text-embedding-3-large"
database_url: str = ""

aws_access_key_id: str = ""
aws_secret_access_key: str = ""
s3_bucket_name: str = ""
aws_region: str = "us-east-1"

vector_table_name: str = "vector_documents"
vector_dimensions: int = 1536

kb_a_chunk_size: int = 500
kb_a_chunk_overlap: int = 50
kb_b_chunk_size: int = 250
kb_b_chunk_overlap: int = 30
rag_top_k_per_source: int = 4
deadline_alert_threshold_days: int = 5
deadline_alert_cooldown_hours: int = 24
```

See `backend/.env.example` for the current starter template.

---

## Dependencies

Current backend dependencies:

```text
fastapi
openai
pgvector
sqlalchemy[asyncio]
psycopg[binary]
pydantic-settings
tiktoken
pdfplumber
pypdf
html2text
boto3
requests
pytest
pytest-asyncio
```

No LangChain, no LlamaIndex, no DashScope.

---

## Testing Status

The current scaffold includes deterministic tests for:

- stage routing
- dispute keyword filtering
- deadline calculation
- `@AI` mention extraction
- citation parsing/fallback
- chat service routing behavior

Current local verification:

```bash
cd backend
.venv/bin/pytest -q
```

Expected result in the current scaffold:

```text
15 passed
```

---

## Remaining Integration Tasks

### Ke Wu / app integration

- Wire `init_engine(engine)` into FastAPI startup
- Decide final `cases.id` type and align `vector_documents.case_id` accordingly
- Add `claim_notice_at`, `proof_of_claim_at`, `last_deadline_alert_at` to `cases`
- Add routes/webhooks that call:
  - `ingest_policy(...)`
  - `answer_policy_question(...)`
  - `handle_chat_event(...)`
  - `on_claim_dates_updated(...)`
- Ensure case deletion also removes case-linked S3 policy/attachment objects

### Mingtao next-step options

- Add a live evaluation harness for policy Q&A
- Add migration files instead of relying on `ensure_vector_schema()`
- Add real integration tests against a local Postgres instance with `pgvector`
- Tune prompts once real policy PDFs and live chats are available

---

## Important Assumptions

- OpenAI is the only AI provider in the current MVP scaffold.
- Policy ingestion expects PDFs in S3.
- KB-B backup upload is optional if S3 is not configured.
- The current AI scaffold is intentionally decoupled from Ke Wu's unfinished ORM models, so some DB types may need alignment during integration.
- Deadline reminders are informational and date-driven, not inferred from chat.

---

## References

- [OpenAI API Pricing](https://openai.com/api/pricing)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [pgvector Python SQLAlchemy support](https://github.com/pgvector/pgvector-python)
- [California Fair Claims Regulations](https://www.insurance.ca.gov/01-consumers/130-laws-regs-hearings/05-CCR/fair-claims-regs.cfm)
- [California DOI claim timing guide](https://www.insurance.ca.gov/0200-industry/0050-renew-license/0200-requirements/upload/Guide-for-Adjusting-Property-Claims-in-California-After-a-Major-Disaster.pdf)
