# ClaimMate Frontend

This is the Next.js frontend for ClaimMate. It connects to the FastAPI backend for authentication, case management, policy Q&A, accident intake, report preview, incident photos, and chat.

## Main Screens

- Login and registration.
- User case list.
- Fast new-case creation for urgent accident intake.
- Accident basics and accident details forms.
- Existing-policy selection and policy PDF upload.
- Standalone Policy Q&A page.
- Accident report preview.
- Case chat with AI support.

## Setup

```bash
npm install
```

Create `.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Use the Railway backend URL instead for cloud testing:

```bash
NEXT_PUBLIC_API_BASE_URL=https://claimmate-backend-production.up.railway.app
```

## Run

```bash
npm run dev
```

Open `http://localhost:3000`.

## Checks

```bash
npm run lint
npm run build
```

## Deployment

The frontend is deployed on Vercel. Set `NEXT_PUBLIC_API_BASE_URL` in Vercel environment variables so the deployed app points to the Railway backend.
