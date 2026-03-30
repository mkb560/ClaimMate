# Contributing

This repository currently uses a simple branch-and-sync workflow without pull requests.

## Branch Naming

Use short-lived personal branches so it is obvious who owns each task:

- `mingtao/<task>`
- `ke/<task>`
- `lou/<task>`

Examples:

- `mingtao/rag-policy-extraction`
- `ke/chat-room-api`
- `lou/intake-form-ui`

## Team Ownership

- Mingtao Ding: `backend/ai/`, RAG, embeddings, AI contracts, policy/dispute/deadline logic
- Ke Wu: FastAPI integration, shared DB/app layer, auth, deployment, Stripe, chat backend
- Yi-Hsien Lou: frontend UI, accident form flow, PDF/report UX, design handoff assets

## Recommended Workflow

1. Sync your local `main`.
2. Create a new branch for one focused task.
3. Make the change and run the relevant local checks.
4. Push your branch to GitHub so the team can see it and recover it if needed.
5. Post a short update in the team chat before touching any high-coordination file.
6. When the task is ready, sync `main`, merge your branch locally, rerun checks, and push `main`.

Example commands:

```bash
git checkout main
git pull origin main
git checkout -b mingtao/rag-query-routing
git push -u origin mingtao/rag-query-routing

git checkout main
git pull origin main
git merge mingtao/rag-query-routing
git push origin main
```

## Local Checks

Backend work should run:

```bash
cd backend
./.venv/bin/pytest
```

If a local virtual environment does not exist yet:

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pytest
```

GitHub Actions runs backend tests on every push, including task branches and `main`.

## Push Expectations

- Keep each branch focused on one task
- Explain what changed, why it changed, and how you tested it
- Mention any contract changes affecting teammates
- Update tests when behavior changes
- Update `AGENTS.md` and `backend/.env.example` when new capabilities or environment variables are introduced
- Do not merge stale work into `main`; pull `main` first and resolve conflicts locally

## High-Coordination Files

Coordinate before editing these files in parallel:

- `backend/main.py`
- `backend/models/ai_types.py`
- `backend/.env.example`
- shared database schema or migration files
- any app-layer contract used by both AI modules and product routes

## Review Guidance

Even without PRs, the team should still do lightweight human review in chat or side-by-side before pushing shared changes to `main`:

- AI/core logic changes: check grounding, citations, and regression risk
- API changes: check contract stability and deployment impact
- UI changes: share screenshots or a short demo summary when possible

## Manual GitHub Settings To Prefer

These settings are still best configured in the GitHub repository UI:

- Do not require pull requests if the team is intentionally using direct-sync collaboration
- Keep force-push to `main` disabled
- Keep `Backend CI` visible so teammates can confirm branch pushes are still passing
