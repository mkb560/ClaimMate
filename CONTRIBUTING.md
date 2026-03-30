# Contributing

This repository uses a simple pull-request workflow so the team can move quickly without stepping on each other.

## Branch Naming

Use short-lived branches based on the type of work:

- `feature/<area>-<task>`
- `fix/<area>-<task>`
- `chore/<area>-<task>`

Examples:

- `feature/rag-policy-extraction`
- `feature/chat-room-api`
- `fix/deadline-reminder-copy`
- `chore/github-ci-setup`

## Team Ownership

- Mingtao Ding: `backend/ai/`, RAG, embeddings, AI contracts, policy/dispute/deadline logic
- Ke Wu: FastAPI integration, shared DB/app layer, auth, deployment, Stripe, chat backend
- Yi-Hsien Lou: frontend UI, accident form flow, PDF/report UX, design handoff assets

## Recommended Workflow

1. Sync your local `main`.
2. Create a new branch for one focused task.
3. Make the change and run the relevant local checks.
4. Open a pull request into `main`.
5. Ask for at least one teammate review on shared or risky changes.
6. Merge after review and passing CI.

Example commands:

```bash
git checkout main
git pull origin main
git checkout -b feature/rag-query-routing
git push -u origin feature/rag-query-routing
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

GitHub Actions also runs backend tests on every pull request to `main` and on pushes to `main`.

## Pull Request Expectations

- Keep PRs small enough to review in one sitting
- Explain what changed, why it changed, and how you tested it
- Mention any contract changes affecting teammates
- Update tests when behavior changes
- Update `AGENTS.md` and `backend/.env.example` when new capabilities or environment variables are introduced

## High-Coordination Files

Coordinate before editing these files in parallel:

- `backend/main.py`
- `backend/models/ai_types.py`
- `backend/.env.example`
- shared database schema or migration files
- any app-layer contract used by both AI modules and product routes

## Review Guidance

- AI/core logic changes should be reviewed for grounding, citations, and regression risk
- API changes should be reviewed for contract stability and deployment impact
- UI changes should include screenshots or a short demo summary when possible

## Manual GitHub Settings To Enable

These settings are still best configured in the GitHub repository UI:

- Protect `main`
- Require pull requests before merging
- Require the `Backend CI` status check before merge
- Optionally require one approving review
