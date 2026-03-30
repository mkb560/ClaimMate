# Team Tasks

This is the current no-PR task split for the ClaimMate prototype. It is derived from the current Phase 1 scope in `plan.md` plus the team ownership recorded in `AGENTS.md`.

Everyone works on a short-lived personal branch, pushes it for backup, and merges into `main` only after syncing and rerunning checks locally.

## Daily Working Rules

1. Start from latest `main`
2. Work on your own branch only
3. Push your branch at least once per day
4. Announce before editing shared contract files
5. Merge into `main` only after local checks pass

## Current Task Split

| Owner | Branch | Main Goal | Concrete Deliverables | Blockers / Notes |
|---|---|---|---|---|
| Mingtao | `mingtao/ai-demo-polish` | Finish AI demo quality | stabilize local RAG, keep KB-A + KB-B indexing reproducible, improve policy fact extraction, expose simple demo scripts, document env + model choices | Coordinate with Ke before changing shared API contracts |
| Ke Wu | `ke/backend-integration` | Turn AI scaffold into usable app endpoints | add FastAPI routes for upload / ask-AI / case lookup, wire shared DB engine at startup, define minimal `cases` and chat message schema, connect policy upload flow | Should avoid editing AI internals unless contract changes are discussed first |
| Yi-Hsien Lou | `lou/demo-ui` | Build the demo-facing product shell | accident intake form, policy upload screen, simple case dashboard, chat or Q&A panel for AI answers, clean demo flow from upload to answer | Needs endpoint contracts from Ke and sample payloads from Mingtao |

## Suggested Order

These phases stay aligned with the current `plan.md` direction:

- keep Mingtao focused on AI core quality, RAG, dispute, deadline, and chat behavior
- keep Ke focused on app-layer integration around the existing AI scaffold
- keep Lou focused on the minimal demo shell needed to show the AI flow end to end
- avoid introducing out-of-scope Phase 1 work such as production auth, Stripe billing, or full deployment hardening
### Phase 1: Make the demo path complete

- Mingtao: lock down question-answer quality on the three real policies
- Ke: add one upload endpoint and one ask-AI endpoint
- Lou: build one happy-path upload and ask page

### Phase 2: Make the chat story believable

- Mingtao: keep dispute detection and stage prompts stable
- Ke: add message persistence plus `@AI` trigger wiring
- Lou: add chat timeline UI and stage-specific entry points

### Phase 3: Make the final presentation smooth

- Mingtao: prepare fixed demo questions and answer references
- Ke: add seeded demo data and startup instructions
- Lou: polish UX copy, screenshots, and flow transitions

## High-Coordination Files

- `backend/main.py`
- `backend/models/ai_types.py`
- `backend/.env.example`
- DB schema or migration files
- any request/response schema shared by backend and frontend
