# Frontend Rewrite Design — ClaimMate
**Date:** 2026-04-13  
**Branch:** `brian/ui`  
**Author:** Yi-Hsien Lou  
**Status:** Approved

---

## 1. Overview

Full rewrite of the ClaimMate frontend from a single-file developer demo (`page.tsx`) into a consumer-grade, multi-page Next.js App Router application. The new UI guides policyholders through a linear wizard: authenticate → create case → upload policy → fill accident details → view report → chat with AI copilot.

**Backend:** `https://exasperatingly-unprologued-elease.ngrok-free.dev` (ngrok tunnel to teammate's backend)  
**Tech:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4

---

## 2. Architecture

### File Structure

```
frontend/src/
├── app/
│   ├── layout.tsx                  # Global layout — mounts AuthProvider
│   ├── page.tsx                    # Root redirect (/ → /cases or /login)
│   ├── login/page.tsx
│   ├── register/page.tsx
│   ├── cases/
│   │   ├── page.tsx                # Case list (localStorage-backed)
│   │   ├── new/page.tsx            # Create new case
│   │   └── [id]/
│   │       ├── layout.tsx          # Case shell with StepIndicator
│   │       ├── policy/page.tsx     # Step 1: Upload or select demo policy
│   │       ├── stage-a/page.tsx    # Step 2: Accident basics form
│   │       ├── stage-b/page.tsx    # Step 3: Accident details form
│   │       ├── report/page.tsx     # Step 4: View / generate report
│   │       └── chat/page.tsx       # Step 5: AI chat (WebSocket)
├── components/
│   ├── ui/                         # Button, Input, Textarea, Card, Badge, Spinner
│   ├── auth/                       # LoginForm, RegisterForm
│   ├── case/                       # StepIndicator, CaseCard
│   ├── policy/                     # PolicyUpload, DemoPolicyPicker, AskPanel
│   ├── accident/                   # StageAForm, StageBForm
│   ├── report/                     # ReportView, PartyTable, TimelineList
│   └── chat/                       # ChatWindow, ChatBubble, ChatInput
├── context/
│   └── AuthContext.tsx
├── hooks/
│   ├── useAuth.ts
│   └── useWebSocketChat.ts
└── lib/
    ├── api.ts                      # All API calls (updated with Bearer token)
    └── auth.ts                     # localStorage token helpers
```

---

## 3. Routing & User Flow

```
/login  ←→  /register
    ↓ on success
/cases  (list; if empty → /cases/new)
    ↓ select or create
/cases/[id]/policy    Step 1 — Policy
    ↓
/cases/[id]/stage-a   Step 2 — Accident Basics
    ↓
/cases/[id]/stage-b   Step 3 — Accident Details
    ↓
/cases/[id]/report    Step 4 — Report
    ↓
/cases/[id]/chat      Step 5 — AI Chat
```

All `/cases/*` routes guard against unauthenticated access via client-side redirect to `/login`.

---

## 4. Auth & State Management

### JWT Flow
- Login/register calls return `access_token` (Bearer JWT)
- Token stored in `localStorage` under key `claimmate_token`
- `AuthContext` exposes `{ token, user, login(), register(), logout() }`
- All API calls use `getAuthHeaders()` to inject `Authorization: Bearer <token>`
- No server-side middleware — pure client-side guard with `useEffect` redirect

### AuthContext Shape
```typescript
type AuthState = {
  token: string | null
  user: { id: string; email: string; display_name: string | null } | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName?: string) => Promise<void>
  logout: () => void
}
```

### Route Guard Pattern
```typescript
const { token } = useAuth()
useEffect(() => {
  if (!token) router.replace('/login')
}, [token])
```

---

## 5. UI Design System

### Colors (Tailwind)
| Role | Class |
|------|-------|
| Page background | `bg-slate-50` |
| Card background | `bg-white` |
| Primary CTA | `bg-blue-600 hover:bg-blue-700 text-white` |
| Body text | `text-slate-900` |
| Muted text | `text-slate-600` |
| Border | `border-slate-200` |
| Error | `text-red-600 bg-red-50` |
| Success | `text-green-700 bg-green-50` |

### Shared Components (`components/ui/`)
- **Button** — `primary` / `secondary` / `ghost` variants, `loading` prop (inline spinner)
- **Input** — label + input + error message, forwarded ref
- **Textarea** — same pattern as Input
- **Card** — white, rounded-2xl, shadow-sm, p-6
- **Badge** — small status chip (`pending` gray, `done` green)
- **Spinner** — SVG animate-spin

### StepIndicator
Shown in `cases/[id]/layout.tsx`. Displays 5 steps with filled/current/empty states.
```
✓ Policy  →  ● Stage A  →  ○ Stage B  →  ○ Report  →  ○ Chat
```
Step state inferred from case snapshot data (stage_a present → step 2 complete, etc.).

---

## 6. Page-by-Page Data Flow

### `/login` & `/register`
- Client component only
- On submit: `POST /auth/login` or `POST /auth/register`
- Success: store token + user in AuthContext → `router.push('/cases')`
- Error: inline message below form

### `/cases`
- Reads case ID list from `localStorage` key `claimmate_cases`
- Renders `CaseCard` for each; "New Case" button always visible
- If list is empty, immediately renders `/cases/new` inline

### `/cases/new`
- Calls `POST /cases` (backend auto-generates `case_id`)
- On success: prepend `case_id` to localStorage list → `router.push('/cases/[id]/policy')`

### `/cases/[id]/policy` (Step 1)
- On mount: `GET /cases/[id]/policy` to check if policy exists
- If no policy: show `DemoPolicyPicker` (3 demo cards) + `PolicyUpload` (PDF file input)
- If policy exists: show current policy name + "Replace" option
- Below: `AskPanel` (textarea + "Ask AI" button → `POST /cases/[id]/ask` → display answer + citations)
- "Next" button → `/cases/[id]/stage-a`

### `/cases/[id]/stage-a` (Step 2)
- On mount: `GET /cases/[id]` → populate form from `stage_a` field
- Fields: occurred_at (datetime), address, quick_summary, owner party (name/phone/insurer/policy#), other party (same), 4 tri-state toggles (injuries, police called, drivable, tow requested)
- Submit: `PATCH /cases/[id]/accident/stage-a` → on success → `router.push('.../stage-b')`

### `/cases/[id]/stage-b` (Step 3)
- Same load pattern from snapshot `stage_b`
- Fields: detailed_narrative, damage_summary, weather/road conditions, police report#, adjuster name, repair shop, follow-up notes
- Submit: `PATCH /cases/[id]/accident/stage-b` → on success → `router.push('.../report')`

### `/cases/[id]/report` (Step 4)
- On mount: `GET /cases/[id]/accident/report`
  - 200: render `ReportView`
  - 404: show "Generate Report" button → `POST /cases/[id]/accident/report` → render
- `ReportView` shows: title, summary, location, detailed narrative, `TimelineList`, `PartyTable`, damage summary, missing items
- "Go to AI Chat" CTA → `/cases/[id]/chat`

### `/cases/[id]/chat` (Step 5)
- Establishes WebSocket: `wss://<ngrok>/ws/cases/[id]?token=<jwt>`
- On mount: also `GET /cases/[id]/chat/messages` to load history
- Send: `{"type":"chat","message_text":"...","sender_role":"owner","invite_sent":false,"run_ai":true}`
- Receive `user_message` → render right-aligned ChatBubble
- Receive `ai_message` → render left-aligned ChatBubble with collapsible citations
- Receive `system` → render subtle system notice
- Reconnect: exponential backoff, max 5 attempts, 3s initial delay

---

## 7. WebSocket Hook

```typescript
// hooks/useWebSocketChat.ts
function useWebSocketChat(caseId: string, token: string | null): {
  messages: ChatMessage[]
  sendMessage: (text: string) => void
  status: 'connecting' | 'open' | 'closed' | 'error'
}
```

- Initializes connection on mount, cleans up on unmount
- Merges WS incoming messages with REST-loaded history (deduplicated by `id`)
- Does not reconnect if `token` is null

---

## 8. api.ts Changes

- `API_BASE_URL` defaults to `https://exasperatingly-unprologued-elease.ngrok-free.dev`
- New helper: `getAuthHeaders()` reads token from localStorage, returns `{ Authorization: 'Bearer <token>', 'ngrok-skip-browser-warning': 'true' }`
- All existing functions updated to spread `getAuthHeaders()` instead of just `NGROK_HEADERS`
- New functions added: `loginUser()`, `registerUser()`, `getMe()`
- Existing function signatures unchanged

---

## 9. Out of Scope

The following are explicitly **not** part of this rewrite:
- Invite link UI (`/invites/*` flow)
- Claim dates management UI
- PDF report download / print
- Push notifications / deadline reminders UI
- WebSocket multi-party simulation (adjuster/repair shop roles)
- Mobile native app

---

## 10. Dependencies

No new npm packages required — Tailwind CSS 4, Next.js 16, React 19, TypeScript already in `package.json`.
