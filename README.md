# ClaimMate

ClaimMate is an AI-powered car insurance claims copilot for consumers. It helps users understand policy documents, collect accident details, generate a structured accident report, track claim deadlines, and use AI support inside a case chat.

This repository contains the FastAPI AI/backend service, a Next.js web frontend, and an Android-only Expo React Native app used for demos and team integration.

## Current Capabilities

- Policy Q&A over uploaded or sample insurance PDFs.
- Dual-source RAG: user policy documents as KB-A and curated regulatory/reference material as KB-B.
- Grounded answers with citations and conservative fallback behavior.
- Deterministic policy fact extraction for common fields such as policy number, policyholders, liability limits, vehicle, VIN, and selected coverage details.
- JWT auth, case ownership, case membership, invites, and authenticated case access.
- Accident intake across two stages: on-scene basics and later detailed follow-up.
- Structured accident report payload and chat-ready accident context.
- Incident photo upload and retrieval.
- Claim deadline explanation and reminder logic for California-style 15-calendar-day acknowledgment and 40-day decision windows.
- Chat AI support for `@AI` questions, dispute next-step guidance, deadline questions, and stage-aware tone.
- WebSocket chat room support for live case collaboration.
- Android mobile app with secure auth storage, accident intake, policy Q&A, incident photo upload, report preview, invite sharing, and WebSocket chat.
- Railway backend deployment and Vercel frontend deployment.

## Repository Layout

```text
ClaimMate/
|-- backend/              # FastAPI backend, AI modules, tests, scripts
|-- frontend/             # Next.js demo/product frontend
|-- mobile/               # Expo React Native Android app
|-- claimmate_rag_docs/   # Curated KB-B regulatory/reference sources
|-- demo_policy_pdfs/     # Sample policy PDFs for demo KB-A ingestion
|-- docs/                 # Project plans, handoffs, milestone scripts
|-- railway.json          # Railway backend deployment config
`-- AGENTS.md             # Coding-agent source of truth
```

## Backend

The backend is a FastAPI app in `backend/`.

Important routes include:

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /cases`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/policy`
- `POST /cases/{case_id}/ask`
- `POST /cases/{case_id}/demo/seed-policy`
- `PATCH /cases/{case_id}/accident/stage-a`
- `PATCH /cases/{case_id}/accident/stage-b`
- `POST /cases/{case_id}/accident/report`
- `GET /cases/{case_id}/accident/report`
- `POST /cases/{case_id}/incident-photos`
- `GET /cases/{case_id}/incident-photos/{photo_id}`
- `POST /cases/{case_id}/chat/messages`
- `GET /cases/{case_id}/chat/messages`
- `WS /ws/cases/{case_id}`

## Frontend

The frontend is a Next.js app in `frontend/`.

It currently supports:

- Registration and login.
- User-specific case list.
- Fast case creation for urgent accident intake.
- Accident basics and accident details forms.
- Existing-policy selection and user policy upload.
- Policy Q&A as a standalone page.
- Accident report preview.
- Case chat with AI support.

## Android App

The Android app is an Expo React Native project in `mobile/`.

It currently supports:

- Registration, login, secure token restore, and logout.
- User-specific case list and fast new-case creation.
- Accident Basics and Accident Details screens.
- Camera/gallery incident photo upload.
- Existing-policy selection, policy PDF upload, and Policy Q&A.
- Accident report generation and preview.
- Case chat over WebSocket with invite copy/share.

## Local Setup

### Backend

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Set at least:

```bash
OPENAI_API_KEY=your_key
DATABASE_URL=postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate
```

For auth-enabled local testing, also set:

```bash
AUTH_MODE=required
JWT_SECRET_KEY=your_long_random_secret
```

Run the backend:

```bash
./.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Run the frontend:

```bash
npm run dev
```

### Android

```bash
cd mobile
npm install
npm start
```

The Android app uses the Railway backend by default. For local Android emulator testing, use:

```bash
EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000 npm start
```

## Testing

Backend:

```bash
cd backend
./.venv/bin/pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Android:

```bash
cd mobile
npm run lint
npm run typecheck
EXPO_NO_TELEMETRY=1 npx expo export --platform android --output-dir /tmp/claimmate-mobile-export
```

Demo smoke test against a running backend:

```bash
cd backend
./.venv/bin/python scripts/run_demo_smoke.py --base-url http://127.0.0.1:8000
```

## Deployment

- Backend: Railway, configured by `railway.json` and `backend/Dockerfile`.
- Frontend: Vercel, configured through the Vercel project settings.
- Android: Expo/EAS, configured by `mobile/eas.json`; the preview profile builds an installable APK.
- Backend production health check: `/health`.
- Frontend must set `NEXT_PUBLIC_API_BASE_URL` to the Railway backend URL.

If Railway is linked to the GitHub `main` branch, backend pushes to `main` can auto-deploy in the same style as Vercel.

## Key Documentation

- `docs/README.md`: documentation index.
- `docs/plan.md`: project plan and roadmap.
- `docs/PROJECT_PROGRESS_AND_STRUCTURE.md`: implementation progress.
- `docs/BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md`: backend/frontend integration guide.
- `docs/YI_FRONTEND_API_EXAMPLE_ZH.md`: frontend API examples.
- `docs/AI_CORE_PLAN_ZH.md`: AI core plan.
- `docs/AUTH_AND_WEBSOCKET_KE.md`: auth, invites, and WebSocket notes.

## Team Ownership

- Mingtao Ding: AI core, RAG, dispute detection, deadline tracking, chat AI behavior.
- Ke Wu: FastAPI product layer, auth, invites, WebSocket, deployment.
- Yi-Hsien Lou: frontend UX, accident form, report UX, business/demo deliverables.
