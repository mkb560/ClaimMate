# Frontend Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite ClaimMate frontend from a single-file developer demo into a consumer-grade Next.js App Router app with JWT auth, linear wizard flow (policy → stage-a → stage-b → report → chat), and WebSocket realtime chat.

**Architecture:** All pages are `'use client'` Client Components guarded by an `AuthContext` that stores JWT in `localStorage`. API calls inject `Authorization: Bearer <token>` via `getAuthHeaders()`. Navigation follows a linear wizard inside `cases/[id]/` routes. Chat uses the backend WebSocket endpoint `/ws/cases/[id]?token=<jwt>`.

**Tech Stack:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4. **No new npm packages** — test infrastructure is not set up; verification is done in the browser with `npm run dev`.

**Backend:** `https://exasperatingly-unprologued-elease.ngrok-free.dev`

---

> **Note on testing:** No Jest/Vitest is configured and the spec forbids new packages. Each task ends with a browser verification step instead of automated tests.

---

## File Map

**Modified:**
- `frontend/src/lib/api.ts` — add `getAuthHeaders()`, update `API_BASE_URL`, add `loginUser`, `registerUser`, `getMe`
- `frontend/src/app/layout.tsx` — mount `AuthProvider` + `Header`
- `frontend/src/app/page.tsx` — replace with `redirect('/login')`
- `frontend/src/app/globals.css` — remove dark-mode overrides, pin `bg-slate-50`

**Created:**
```
frontend/src/
├── lib/auth.ts
├── context/AuthContext.tsx            (includes useAuth)
├── components/
│   ├── ui/
│   │   ├── Spinner.tsx
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Textarea.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   └── Header.tsx
│   ├── case/
│   │   ├── CaseCard.tsx
│   │   └── StepIndicator.tsx
│   ├── policy/
│   │   ├── DemoPolicyPicker.tsx
│   │   ├── PolicyUpload.tsx
│   │   └── AskPanel.tsx
│   ├── accident/
│   │   ├── StageAForm.tsx
│   │   └── StageBForm.tsx
│   ├── report/
│   │   ├── ReportView.tsx
│   │   ├── PartyTable.tsx
│   │   └── TimelineList.tsx
│   └── chat/
│       ├── ChatWindow.tsx
│       ├── ChatBubble.tsx
│       └── ChatInput.tsx
├── hooks/
│   └── useWebSocketChat.ts
└── app/
    ├── login/page.tsx
    ├── register/page.tsx
    ├── cases/
    │   ├── page.tsx
    │   ├── new/page.tsx
    │   └── [id]/
    │       ├── layout.tsx
    │       ├── policy/page.tsx
    │       ├── stage-a/page.tsx
    │       ├── stage-b/page.tsx
    │       ├── report/page.tsx
    │       └── chat/page.tsx
```

---

## Task 0: Create branch `brian/ui`

**Files:** none

- [ ] **Step 1: Create and switch to the new branch**

```bash
cd /Users/brianlou/Desktop/ClaimMate
git checkout -b brian/ui
```

Expected: `Switched to a new branch 'brian/ui'`

- [ ] **Step 2: Verify**

```bash
git branch --show-current
```

Expected: `brian/ui`

---

## Task 1: Foundation — `lib/auth.ts` + update `lib/api.ts`

**Files:**
- Create: `frontend/src/lib/auth.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Create `frontend/src/lib/auth.ts`**

```typescript
// frontend/src/lib/auth.ts
const TOKEN_KEY = 'claimmate_token'
const CASES_KEY = 'claimmate_cases'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getCaseIds(): string[] {
  if (typeof window === 'undefined') return []
  try {
    return JSON.parse(localStorage.getItem(CASES_KEY) || '[]') as string[]
  } catch {
    return []
  }
}

export function addCaseId(caseId: string): void {
  const ids = getCaseIds()
  if (!ids.includes(caseId)) {
    localStorage.setItem(CASES_KEY, JSON.stringify([caseId, ...ids]))
  }
}

export function removeCaseId(caseId: string): void {
  const ids = getCaseIds().filter((id) => id !== caseId)
  localStorage.setItem(CASES_KEY, JSON.stringify(ids))
}
```

- [ ] **Step 2: Replace the top of `frontend/src/lib/api.ts`**

Replace the existing `API_BASE_URL` constant and `NGROK_HEADERS` object (lines 1–8) with:

```typescript
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'https://exasperatingly-unprologued-elease.ngrok-free.dev'

function getAuthHeaders(): Record<string, string> {
  const token =
    typeof window !== 'undefined' ? localStorage.getItem('claimmate_token') : null
  return {
    'ngrok-skip-browser-warning': 'true',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}
```

- [ ] **Step 3: Replace all `...NGROK_HEADERS` with `...getAuthHeaders()` in `api.ts`**

There are about 15 occurrences. Use find-and-replace. Every fetch call that spreads `NGROK_HEADERS` must now spread `getAuthHeaders()`.

- [ ] **Step 4: Add auth types and functions at the bottom of `api.ts`**

```typescript
export type AuthUser = {
  id: string
  email: string
  display_name: string | null
}

export type AuthResponse = {
  access_token: string
  token_type: string
  user: AuthUser
}

export async function loginUser(
  email: string,
  password: string
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Login failed')
  }
  return response.json() as Promise<AuthResponse>
}

export async function registerUser(
  email: string,
  password: string,
  display_name?: string
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ email, password, display_name }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Registration failed')
  }
  return response.json() as Promise<AuthResponse>
}

export async function getMe(): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: getAuthHeaders(),
    cache: 'no-store',
  })
  if (!response.ok) throw new Error('Not authenticated')
  return response.json() as Promise<AuthUser>
}
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | head -30
```

Expected: No TypeScript errors (build may fail on missing pages, that's fine — we just want no type errors in api.ts).

---

## Task 2: AuthContext

**Files:**
- Create: `frontend/src/context/AuthContext.tsx`

- [ ] **Step 1: Create `frontend/src/context/AuthContext.tsx`**

```typescript
// frontend/src/context/AuthContext.tsx
'use client'

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react'
import { loginUser, registerUser, AuthUser } from '@/lib/api'
import { getToken, setToken, clearToken } from '@/lib/auth'

type AuthState = {
  token: string | null
  user: AuthUser | null
  login: (email: string, password: string) => Promise<void>
  register: (
    email: string,
    password: string,
    displayName?: string
  ) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)

  useEffect(() => {
    const stored = getToken()
    if (stored) setTokenState(stored)
  }, [])

  async function login(email: string, password: string) {
    const data = await loginUser(email, password)
    setToken(data.access_token)
    setTokenState(data.access_token)
    setUser(data.user)
  }

  async function register(
    email: string,
    password: string,
    displayName?: string
  ) {
    const data = await registerUser(email, password, displayName)
    setToken(data.access_token)
    setTokenState(data.access_token)
    setUser(data.user)
  }

  function logout() {
    clearToken()
    setTokenState(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
```

- [ ] **Step 2: Verify no TypeScript errors**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: No errors in `context/AuthContext.tsx`. (Errors about missing pages are OK.)

---

## Task 3: UI Primitives

**Files:**
- Create: `frontend/src/components/ui/Spinner.tsx`
- Create: `frontend/src/components/ui/Button.tsx`
- Create: `frontend/src/components/ui/Input.tsx`
- Create: `frontend/src/components/ui/Textarea.tsx`
- Create: `frontend/src/components/ui/Card.tsx`
- Create: `frontend/src/components/ui/Badge.tsx`
- Create: `frontend/src/components/ui/Header.tsx`

- [ ] **Step 1: Create `Spinner.tsx`**

```typescript
// frontend/src/components/ui/Spinner.tsx
export function Spinner({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}
```

- [ ] **Step 2: Create `Button.tsx`**

```typescript
// frontend/src/components/ui/Button.tsx
import { ButtonHTMLAttributes, ReactNode } from 'react'
import { Spinner } from './Spinner'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost'
  loading?: boolean
  children: ReactNode
}

export function Button({
  variant = 'primary',
  loading = false,
  disabled,
  children,
  className = '',
  ...props
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed'
  const variants = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary:
      'border border-slate-200 bg-white hover:bg-slate-50 text-slate-900',
    ghost: 'text-slate-600 hover:bg-slate-100',
  }
  return (
    <button
      className={`${base} ${variants[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner className="h-4 w-4" />}
      {children}
    </button>
  )
}
```

- [ ] **Step 3: Create `Input.tsx`**

```typescript
// frontend/src/components/ui/Input.tsx
import { InputHTMLAttributes, forwardRef } from 'react'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-slate-700"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            error ? 'border-red-400' : ''
          } ${className}`}
          {...props}
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    )
  }
)
Input.displayName = 'Input'
```

- [ ] **Step 4: Create `Textarea.tsx`**

```typescript
// frontend/src/components/ui/Textarea.tsx
import { TextareaHTMLAttributes, forwardRef } from 'react'

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string
  error?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = '', id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-slate-700"
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          className={`rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            error ? 'border-red-400' : ''
          } ${className}`}
          {...props}
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    )
  }
)
Textarea.displayName = 'Textarea'
```

- [ ] **Step 5: Create `Card.tsx`**

```typescript
// frontend/src/components/ui/Card.tsx
import { ReactNode } from 'react'

export function Card({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}
    >
      {children}
    </div>
  )
}
```

- [ ] **Step 6: Create `Badge.tsx`**

```typescript
// frontend/src/components/ui/Badge.tsx
import { ReactNode } from 'react'

type BadgeVariant = 'pending' | 'done' | 'default'

const styles: Record<BadgeVariant, string> = {
  pending: 'bg-slate-100 text-slate-600',
  done: 'bg-green-50 text-green-700',
  default: 'bg-blue-50 text-blue-700',
}

export function Badge({
  children,
  variant = 'default',
}: {
  children: ReactNode
  variant?: BadgeVariant
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[variant]}`}
    >
      {children}
    </span>
  )
}
```

- [ ] **Step 7: Create `Header.tsx`**

```typescript
// frontend/src/components/ui/Header.tsx
'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'

export function Header() {
  const { token, logout } = useAuth()
  const router = useRouter()

  function handleLogout() {
    logout()
    router.push('/login')
  }

  return (
    <header className="border-b border-slate-200 bg-white px-4 py-3">
      <div className="mx-auto flex max-w-3xl items-center justify-between">
        <Link href="/cases" className="text-lg font-bold text-blue-600">
          ClaimMate
        </Link>
        {token && (
          <button
            onClick={handleLogout}
            className="text-sm text-slate-500 hover:text-slate-900"
          >
            Sign out
          </button>
        )}
      </div>
    </header>
  )
}
```

- [ ] **Step 8: Verify no TypeScript errors across ui/**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep "components/ui"
```

Expected: no output (no errors).

---

## Task 4: Update Global Layout & Root Page

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Replace `frontend/src/app/layout.tsx`**

```typescript
// frontend/src/app/layout.tsx
import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/context/AuthContext'
import { Header } from '@/components/ui/Header'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'ClaimMate — AI Claims Copilot',
  description:
    'Understand your policy, track deadlines, and dispute claims with AI support.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-slate-50">
        <AuthProvider>
          <Header />
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 2: Replace `frontend/src/app/page.tsx`**

```typescript
// frontend/src/app/page.tsx
import { redirect } from 'next/navigation'

export default function RootPage() {
  redirect('/login')
}
```

- [ ] **Step 3: Update `frontend/src/app/globals.css`** — remove dark-mode body override so Tailwind controls colors

```css
@import "tailwindcss";

:root {
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}
```

- [ ] **Step 4: Start dev server and verify redirect**

```bash
cd frontend && npm run dev
```

Visit `http://localhost:3000` — should redirect to `/login` (404 is expected since we haven't built that page yet, but the redirect should fire).

---

## Task 5: Login & Register Pages

**Files:**
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/app/register/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/login/page.tsx`**

```typescript
// frontend/src/app/login/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'

export default function LoginPage() {
  const { login, token } = useAuth()
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (token) router.replace('/cases')
  }, [token, router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      router.push('/cases')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
          <p className="mt-1 text-sm text-slate-600">Sign in to your account</p>
        </div>
        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {error}
              </p>
            )}
            <Button type="submit" loading={loading} className="w-full">
              Sign in
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-slate-600">
            No account?{' '}
            <Link href="/register" className="text-blue-600 hover:underline">
              Register
            </Link>
          </p>
        </Card>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/app/register/page.tsx`**

```typescript
// frontend/src/app/register/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'

export default function RegisterPage() {
  const { register, token } = useAuth()
  const router = useRouter()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (token) router.replace('/cases')
  }, [token, router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(email, password, displayName || undefined)
      router.push('/cases')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-900">Create account</h1>
          <p className="mt-1 text-sm text-slate-600">
            Start managing your claim today
          </p>
        </div>
        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Name (optional)"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your name"
              autoComplete="name"
            />
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {error}
              </p>
            )}
            <Button type="submit" loading={loading} className="w-full">
              Create Account
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-slate-600">
            Already have an account?{' '}
            <Link href="/login" className="text-blue-600 hover:underline">
              Sign in
            </Link>
          </p>
        </Card>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify in browser**

With `npm run dev` running:
1. Visit `http://localhost:3000/login` — see login form with ClaimMate header
2. Visit `http://localhost:3000/register` — see register form
3. Click the Register/Sign in links — navigation works between the two pages

---

## Task 6: Cases List, New Case, CaseCard

**Files:**
- Create: `frontend/src/components/case/CaseCard.tsx`
- Create: `frontend/src/app/cases/page.tsx`
- Create: `frontend/src/app/cases/new/page.tsx`

- [ ] **Step 1: Create `frontend/src/components/case/CaseCard.tsx`**

```typescript
// frontend/src/components/case/CaseCard.tsx
'use client'

import { useRouter } from 'next/navigation'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

export function CaseCard({ caseId }: { caseId: string }) {
  const router = useRouter()
  return (
    <Card className="flex items-center justify-between">
      <div>
        <p className="font-medium text-slate-900">{caseId}</p>
        <p className="text-xs text-slate-500">Case ID</p>
      </div>
      <Button
        variant="secondary"
        onClick={() => router.push(`/cases/${caseId}/policy`)}
      >
        Open →
      </Button>
    </Card>
  )
}
```

- [ ] **Step 2: Create `frontend/src/app/cases/page.tsx`**

```typescript
// frontend/src/app/cases/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getCaseIds } from '@/lib/auth'
import { CaseCard } from '@/components/case/CaseCard'
import { Button } from '@/components/ui/Button'

export default function CasesPage() {
  const { token } = useAuth()
  const router = useRouter()
  const [caseIds, setCaseIds] = useState<string[]>([])

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    setCaseIds(getCaseIds())
  }, [token, router])

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Your Cases</h1>
        <Button onClick={() => router.push('/cases/new')}>+ New Case</Button>
      </div>
      {caseIds.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-slate-200 px-6 py-16 text-center">
          <p className="text-slate-600">No cases yet.</p>
          <Button className="mt-4" onClick={() => router.push('/cases/new')}>
            Start your first case
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {caseIds.map((id) => (
            <CaseCard key={id} caseId={id} />
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Create `frontend/src/app/cases/new/page.tsx`**

```typescript
// frontend/src/app/cases/new/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { createCase } from '@/lib/api'
import { addCaseId } from '@/lib/auth'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

export default function NewCasePage() {
  const { token } = useAuth()
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) router.replace('/login')
  }, [token, router])

  async function handleCreate() {
    setLoading(true)
    setError('')
    try {
      const { case_id } = await createCase()
      addCaseId(case_id)
      router.push(`/cases/${case_id}/policy`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create case')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <Card>
          <h1 className="text-xl font-bold text-slate-900">
            Start a New Case
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            We&apos;ll create a case and walk you through each step.
          </p>
          {error && (
            <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </p>
          )}
          <Button
            className="mt-6 w-full"
            loading={loading}
            onClick={handleCreate}
          >
            Create Case
          </Button>
          <Button
            variant="ghost"
            className="mt-2 w-full"
            onClick={() => router.push('/cases')}
          >
            Back to cases
          </Button>
        </Card>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Verify in browser**

1. Register a new account at `/register`
2. Should redirect to `/cases` — see empty state
3. Click "Start your first case" → `/cases/new`
4. Click "Create Case" → should create a case and redirect to `/cases/{id}/policy` (404 for now)
5. Go back to `/cases` — the new case ID should appear in the list

---

## Task 7: Case Layout & StepIndicator

**Files:**
- Create: `frontend/src/components/case/StepIndicator.tsx`
- Create: `frontend/src/app/cases/[id]/layout.tsx`

- [ ] **Step 1: Create `frontend/src/components/case/StepIndicator.tsx`**

```typescript
// frontend/src/components/case/StepIndicator.tsx
const STEPS = ['Policy', 'Stage A', 'Stage B', 'Report', 'Chat']

export function StepIndicator({ current }: { current: number }) {
  return (
    <nav className="flex items-center justify-between overflow-x-auto rounded-2xl border border-slate-200 bg-white px-6 py-4 shadow-sm">
      {STEPS.map((step, i) => (
        <div key={step} className="flex items-center">
          <div className="flex items-center gap-2">
            <div
              className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold
                ${i < current ? 'bg-green-500 text-white' : ''}
                ${i === current ? 'bg-blue-600 text-white' : ''}
                ${i > current ? 'bg-slate-100 text-slate-500' : ''}
              `}
            >
              {i < current ? '✓' : i + 1}
            </div>
            <span
              className={`hidden text-sm font-medium sm:block ${
                i === current ? 'text-slate-900' : 'text-slate-500'
              }`}
            >
              {step}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className="mx-2 h-px w-6 flex-shrink-0 bg-slate-200 sm:w-10" />
          )}
        </div>
      ))}
    </nav>
  )
}
```

- [ ] **Step 2: Create `frontend/src/app/cases/[id]/layout.tsx`**

```typescript
// frontend/src/app/cases/[id]/layout.tsx
'use client'

import { usePathname } from 'next/navigation'
import { StepIndicator } from '@/components/case/StepIndicator'

const STEP_PATHS = ['policy', 'stage-a', 'stage-b', 'report', 'chat']

export default function CaseLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const currentStep = STEP_PATHS.findIndex((p) => pathname.endsWith(p))

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <StepIndicator current={currentStep >= 0 ? currentStep : 0} />
        <div className="mt-6">{children}</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify in browser**

Navigate to `/cases/{any-id}/policy` (even before the page exists, the layout should render). The step indicator should show "1" (Policy) highlighted in blue. Navigate to other step paths — the highlighted step should update.

---

## Task 8: Policy Page (Step 1)

**Files:**
- Create: `frontend/src/components/policy/DemoPolicyPicker.tsx`
- Create: `frontend/src/components/policy/PolicyUpload.tsx`
- Create: `frontend/src/components/policy/AskPanel.tsx`
- Create: `frontend/src/app/cases/[id]/policy/page.tsx`

- [ ] **Step 1: Create `DemoPolicyPicker.tsx`**

```typescript
// frontend/src/components/policy/DemoPolicyPicker.tsx
'use client'

import { useState } from 'react'
import { DemoPolicy } from '@/lib/api'
import { Card } from '@/components/ui/Card'

export function DemoPolicyPicker({
  policies,
  onSelect,
}: {
  policies: DemoPolicy[]
  onSelect: (p: DemoPolicy) => Promise<void>
}) {
  const [loading, setLoading] = useState<string | null>(null)

  async function handleSelect(policy: DemoPolicy) {
    setLoading(policy.policy_key)
    try {
      await onSelect(policy)
    } finally {
      setLoading(null)
    }
  }

  return (
    <Card>
      <h3 className="font-semibold text-slate-900">Choose a Demo Policy</h3>
      <p className="mt-1 text-sm text-slate-600">
        Pick one of our sample policies to get started instantly.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {policies.map((p) => (
          <button
            key={p.policy_key}
            onClick={() => handleSelect(p)}
            disabled={!!loading}
            className="rounded-xl border border-slate-200 p-4 text-left transition hover:border-blue-400 hover:bg-blue-50 disabled:opacity-50"
          >
            <p className="font-medium text-slate-900">{p.label}</p>
            <p className="mt-1 text-xs text-slate-500">{p.filename}</p>
            {loading === p.policy_key && (
              <p className="mt-2 text-xs text-blue-600">Loading…</p>
            )}
          </button>
        ))}
      </div>
    </Card>
  )
}
```

- [ ] **Step 2: Create `PolicyUpload.tsx`**

```typescript
// frontend/src/components/policy/PolicyUpload.tsx
'use client'

import { useRef, useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

export function PolicyUpload({
  onUpload,
}: {
  onUpload: (file: File) => Promise<void>
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleUpload() {
    if (!file) return
    setLoading(true)
    try {
      await onUpload(file)
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <h3 className="font-semibold text-slate-900">
        Upload Your Own Policy PDF
      </h3>
      <p className="mt-1 text-sm text-slate-600">
        We&apos;ll index it and answer your questions.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="text-sm text-slate-600"
        />
        <Button
          variant="secondary"
          loading={loading}
          disabled={!file}
          onClick={handleUpload}
        >
          Upload
        </Button>
      </div>
    </Card>
  )
}
```

- [ ] **Step 3: Create `AskPanel.tsx`**

```typescript
// frontend/src/components/policy/AskPanel.tsx
'use client'

import { useState } from 'react'
import { askPolicyQuestion, Citation } from '@/lib/api'
import { Card } from '@/components/ui/Card'
import { Textarea } from '@/components/ui/Textarea'
import { Button } from '@/components/ui/Button'

export function AskPanel({ caseId }: { caseId: string }) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [disclaimer, setDisclaimer] = useState('')
  const [citations, setCitations] = useState<Citation[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleAsk() {
    if (!question.trim()) return
    setLoading(true)
    setError('')
    try {
      const result = await askPolicyQuestion(caseId, question.trim())
      setAnswer(result.answer)
      setDisclaimer(result.disclaimer)
      setCitations(result.citations)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ask failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <h3 className="font-semibold text-slate-900">Ask About Your Policy</h3>
      <div className="mt-3 space-y-3">
        <Textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What is my liability coverage limit?"
          rows={3}
        />
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </p>
        )}
        <Button
          loading={loading}
          disabled={!question.trim()}
          onClick={handleAsk}
        >
          Ask AI
        </Button>
        {answer && (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-slate-900">{answer}</p>
            {disclaimer && (
              <p className="text-xs text-slate-500">{disclaimer}</p>
            )}
            {citations.length > 0 && (
              <details className="text-sm">
                <summary className="cursor-pointer text-blue-600">
                  Sources ({citations.length})
                </summary>
                <div className="mt-2 space-y-2">
                  {citations.map((c, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-slate-200 p-3"
                    >
                      <p className="font-medium text-slate-800">
                        {c.source_label}
                      </p>
                      <p className="text-xs text-slate-500">
                        {c.source_type === 'kb_a' ? 'Your Policy' : 'Regulation'}
                        {c.page_num ? ` · Page ${c.page_num}` : ''}
                      </p>
                      <p className="mt-1 text-slate-700">{c.excerpt}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
```

- [ ] **Step 4: Create `frontend/src/app/cases/[id]/policy/page.tsx`**

```typescript
// frontend/src/app/cases/[id]/policy/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import {
  getCasePolicyStatus,
  getDemoPolicies,
  seedDemoPolicy,
  uploadPolicy,
  CasePolicyStatusResponse,
  DemoPolicy,
} from '@/lib/api'
import { DemoPolicyPicker } from '@/components/policy/DemoPolicyPicker'
import { PolicyUpload } from '@/components/policy/PolicyUpload'
import { AskPanel } from '@/components/policy/AskPanel'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'

export default function PolicyPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()

  const [policyStatus, setPolicyStatus] =
    useState<CasePolicyStatusResponse | null>(null)
  const [demoPolicies, setDemoPolicies] = useState<DemoPolicy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    loadData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function loadData() {
    setLoading(true)
    setError('')
    try {
      const [status, catalog] = await Promise.all([
        getCasePolicyStatus(caseId),
        getDemoPolicies(),
      ])
      setPolicyStatus(status)
      setDemoPolicies(catalog.policies)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  async function handleDemoSelect(policy: DemoPolicy) {
    setError('')
    try {
      await seedDemoPolicy(caseId, policy.policy_key)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to seed policy')
    }
  }

  async function handleUpload(file: File) {
    setError('')
    try {
      await uploadPolicy(caseId, file)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    }
  }

  if (loading) {
    return (
      <div className="py-20 text-center text-slate-500">Loading…</div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">
            Step 1: Your Policy
          </h2>
          {policyStatus?.has_policy && <Badge variant="done">Loaded</Badge>}
        </div>
        {policyStatus?.has_policy ? (
          <div className="mt-3 rounded-xl bg-green-50 px-4 py-3 text-sm text-green-700">
            <strong>
              {policyStatus.filename || policyStatus.source_label}
            </strong>{' '}
            is indexed ({policyStatus.chunk_count} chunks)
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-600">
            Upload your policy PDF or choose a demo to get started.
          </p>
        )}
        {error && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </p>
        )}
      </Card>

      {!policyStatus?.has_policy && (
        <>
          <DemoPolicyPicker
            policies={demoPolicies}
            onSelect={handleDemoSelect}
          />
          <PolicyUpload onUpload={handleUpload} />
        </>
      )}

      {policyStatus?.has_policy && <AskPanel caseId={caseId} />}

      <div className="flex justify-end">
        <Button onClick={() => router.push(`/cases/${caseId}/stage-a`)}>
          Next: Accident Basics →
        </Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Verify in browser**

1. Navigate to `/cases/{id}/policy`
2. Step indicator shows step 1 highlighted
3. Demo policy cards appear — click one — policy loaded badge appears
4. Ask a question in the AskPanel — answer and citations appear
5. "Next" button navigates to `/cases/{id}/stage-a`

---

## Task 9: Stage A Page (Step 2)

**Files:**
- Create: `frontend/src/components/accident/StageAForm.tsx`
- Create: `frontend/src/app/cases/[id]/stage-a/page.tsx`

- [ ] **Step 1: Create `StageAForm.tsx`**

```typescript
// frontend/src/components/accident/StageAForm.tsx
'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

type TriState = 'unknown' | 'true' | 'false'

export type StageAData = {
  occurred_at: string
  address: string
  quick_summary: string
  owner_name: string
  owner_phone: string
  owner_insurer: string
  owner_policy_number: string
  other_name: string
  other_phone: string
  other_insurer: string
  other_policy_number: string
  injuries_reported: TriState
  police_called: TriState
  drivable: TriState
  tow_requested: TriState
}

export const EMPTY_STAGE_A: StageAData = {
  occurred_at: '',
  address: '',
  quick_summary: '',
  owner_name: '',
  owner_phone: '',
  owner_insurer: '',
  owner_policy_number: '',
  other_name: '',
  other_phone: '',
  other_insurer: '',
  other_policy_number: '',
  injuries_reported: 'unknown',
  police_called: 'unknown',
  drivable: 'unknown',
  tow_requested: 'unknown',
}

function TriStateToggle({
  label,
  value,
  onChange,
}: {
  label: string
  value: TriState
  onChange: (v: TriState) => void
}) {
  const opts: { val: TriState; display: string }[] = [
    { val: 'unknown', display: '?' },
    { val: 'true', display: 'Yes' },
    { val: 'false', display: 'No' },
  ]
  return (
    <div>
      <p className="mb-1 text-sm font-medium text-slate-700">{label}</p>
      <div className="flex gap-2">
        {opts.map(({ val, display }) => (
          <button
            key={val}
            type="button"
            onClick={() => onChange(val)}
            className={`rounded-lg border px-3 py-1.5 text-sm transition ${
              value === val
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {display}
          </button>
        ))}
      </div>
    </div>
  )
}

export function StageAForm({
  initial,
  onSubmit,
  loading,
  error,
}: {
  initial: StageAData
  onSubmit: (data: StageAData) => Promise<void>
  loading: boolean
  error: string
}) {
  const [form, setForm] = useState<StageAData>(initial)

  function set<K extends keyof StageAData>(key: K, value: StageAData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault()
        await onSubmit(form)
      }}
      className="space-y-6"
    >
      <Card>
        <h3 className="font-semibold text-slate-900">Accident Details</h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Input
            label="Date & Time"
            type="datetime-local"
            value={form.occurred_at}
            onChange={(e) => set('occurred_at', e.target.value)}
          />
          <Input
            label="Location"
            value={form.address}
            onChange={(e) => set('address', e.target.value)}
            placeholder="123 Main St, Los Angeles, CA"
          />
        </div>
        <div className="mt-4">
          <Textarea
            label="Quick Summary"
            value={form.quick_summary}
            onChange={(e) => set('quick_summary', e.target.value)}
            placeholder="Rear-end collision at a red light…"
            rows={3}
          />
        </div>
      </Card>

      <div className="grid gap-6 sm:grid-cols-2">
        <Card>
          <h3 className="font-semibold text-slate-900">Your Information</h3>
          <div className="mt-3 space-y-3">
            <Input
              label="Name"
              value={form.owner_name}
              onChange={(e) => set('owner_name', e.target.value)}
              placeholder="Full name"
            />
            <Input
              label="Phone"
              value={form.owner_phone}
              onChange={(e) => set('owner_phone', e.target.value)}
              placeholder="+1 (555) 000-0000"
            />
            <Input
              label="Insurer"
              value={form.owner_insurer}
              onChange={(e) => set('owner_insurer', e.target.value)}
              placeholder="Allstate"
            />
            <Input
              label="Policy #"
              value={form.owner_policy_number}
              onChange={(e) => set('owner_policy_number', e.target.value)}
            />
          </div>
        </Card>
        <Card>
          <h3 className="font-semibold text-slate-900">Other Party</h3>
          <div className="mt-3 space-y-3">
            <Input
              label="Name"
              value={form.other_name}
              onChange={(e) => set('other_name', e.target.value)}
              placeholder="Full name"
            />
            <Input
              label="Phone"
              value={form.other_phone}
              onChange={(e) => set('other_phone', e.target.value)}
              placeholder="+1 (555) 000-0000"
            />
            <Input
              label="Insurer"
              value={form.other_insurer}
              onChange={(e) => set('other_insurer', e.target.value)}
              placeholder="Progressive"
            />
            <Input
              label="Policy #"
              value={form.other_policy_number}
              onChange={(e) => set('other_policy_number', e.target.value)}
            />
          </div>
        </Card>
      </div>

      <Card>
        <h3 className="font-semibold text-slate-900">Quick Facts</h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <TriStateToggle
            label="Injuries reported?"
            value={form.injuries_reported}
            onChange={(v) => set('injuries_reported', v)}
          />
          <TriStateToggle
            label="Police called?"
            value={form.police_called}
            onChange={(v) => set('police_called', v)}
          />
          <TriStateToggle
            label="Vehicle drivable?"
            value={form.drivable}
            onChange={(v) => set('drivable', v)}
          />
          <TriStateToggle
            label="Tow requested?"
            value={form.tow_requested}
            onChange={(v) => set('tow_requested', v)}
          />
        </div>
      </Card>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}
      <div className="flex justify-end">
        <Button type="submit" loading={loading}>
          Save & Continue →
        </Button>
      </div>
    </form>
  )
}
```

- [ ] **Step 2: Create `frontend/src/app/cases/[id]/stage-a/page.tsx`**

```typescript
// frontend/src/app/cases/[id]/stage-a/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getCaseSnapshot, patchAccidentStageA } from '@/lib/api'
import {
  StageAForm,
  StageAData,
  EMPTY_STAGE_A,
} from '@/components/accident/StageAForm'

function boolToTriState(v: unknown): 'true' | 'false' | 'unknown' {
  if (v === true) return 'true'
  if (v === false) return 'false'
  return 'unknown'
}

function toDateTimeLocal(v: unknown): string {
  if (!v || typeof v !== 'string') return ''
  const d = new Date(v)
  if (isNaN(d.getTime())) return ''
  return d.toISOString().slice(0, 16)
}

function triStateToBool(v: string): boolean | null {
  if (v === 'true') return true
  if (v === 'false') return false
  return null
}

export default function StageAPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const [initial, setInitial] = useState<StageAData>(EMPTY_STAGE_A)
  const [fetchLoading, setFetchLoading] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    load()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function load() {
    try {
      const snap = await getCaseSnapshot(caseId)
      if (snap.stage_a) {
        const a = snap.stage_a as Record<string, unknown>
        const loc = (a.location as Record<string, unknown>) || {}
        const own = (a.owner_party as Record<string, unknown>) || {}
        const oth = (a.other_party as Record<string, unknown>) || {}
        setInitial({
          occurred_at: toDateTimeLocal(a.occurred_at),
          address: String(loc.address || ''),
          quick_summary: String(a.quick_summary || ''),
          owner_name: String(own.name || ''),
          owner_phone: String(own.phone || ''),
          owner_insurer: String(own.insurer || ''),
          owner_policy_number: String(own.policy_number || ''),
          other_name: String(oth.name || ''),
          other_phone: String(oth.phone || ''),
          other_insurer: String(oth.insurer || ''),
          other_policy_number: String(oth.policy_number || ''),
          injuries_reported: boolToTriState(a.injuries_reported),
          police_called: boolToTriState(a.police_called),
          drivable: boolToTriState(a.drivable),
          tow_requested: boolToTriState(a.tow_requested),
        })
      }
    } catch {
      // blank form is fine for new cases
    } finally {
      setFetchLoading(false)
    }
  }

  async function handleSubmit(data: StageAData) {
    setLoading(true)
    setError('')
    try {
      await patchAccidentStageA(caseId, {
        occurred_at: data.occurred_at
          ? new Date(data.occurred_at).toISOString()
          : null,
        location: { address: data.address || null },
        owner_party: {
          role: 'owner',
          name: data.owner_name,
          phone: data.owner_phone || null,
          insurer: data.owner_insurer || null,
          policy_number: data.owner_policy_number || null,
        },
        other_party: {
          role: 'other_driver',
          name: data.other_name,
          phone: data.other_phone || null,
          insurer: data.other_insurer || null,
          policy_number: data.other_policy_number || null,
        },
        injuries_reported: triStateToBool(data.injuries_reported),
        police_called: triStateToBool(data.police_called),
        drivable: triStateToBool(data.drivable),
        tow_requested: triStateToBool(data.tow_requested),
        quick_summary: data.quick_summary,
        stage_completed_at: new Date().toISOString(),
      })
      router.push(`/cases/${caseId}/stage-b`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setLoading(false)
    }
  }

  if (fetchLoading) {
    return <div className="py-20 text-center text-slate-500">Loading…</div>
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-slate-900">
          Step 2: Accident Basics
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Fill in what you have now — you can update anytime.
        </p>
      </div>
      <StageAForm
        initial={initial}
        onSubmit={handleSubmit}
        loading={loading}
        error={error}
      />
    </div>
  )
}
```

- [ ] **Step 3: Verify in browser**

1. Navigate to `/cases/{id}/stage-a`
2. StepIndicator shows step 2 highlighted
3. Fill in the form and click "Save & Continue" — redirects to `/cases/{id}/stage-b`
4. Go back to `/cases/{id}/stage-a` — form is pre-filled from the saved data

---

## Task 10: Stage B Page (Step 3)

**Files:**
- Create: `frontend/src/components/accident/StageBForm.tsx`
- Create: `frontend/src/app/cases/[id]/stage-b/page.tsx`

- [ ] **Step 1: Create `StageBForm.tsx`**

```typescript
// frontend/src/components/accident/StageBForm.tsx
'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

export type StageBData = {
  detailed_narrative: string
  damage_summary: string
  weather_conditions: string
  road_conditions: string
  police_report_number: string
  adjuster_name: string
  repair_shop_name: string
  follow_up_notes: string
}

export const EMPTY_STAGE_B: StageBData = {
  detailed_narrative: '',
  damage_summary: '',
  weather_conditions: '',
  road_conditions: '',
  police_report_number: '',
  adjuster_name: '',
  repair_shop_name: '',
  follow_up_notes: '',
}

export function StageBForm({
  initial,
  onSubmit,
  loading,
  error,
}: {
  initial: StageBData
  onSubmit: (data: StageBData) => Promise<void>
  loading: boolean
  error: string
}) {
  const [form, setForm] = useState<StageBData>(initial)

  function set(key: keyof StageBData, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault()
        await onSubmit(form)
      }}
      className="space-y-6"
    >
      <Card>
        <h3 className="font-semibold text-slate-900">Narrative</h3>
        <div className="mt-3 space-y-4">
          <Textarea
            label="Detailed Account"
            value={form.detailed_narrative}
            onChange={(e) => set('detailed_narrative', e.target.value)}
            placeholder="Describe what happened step by step…"
            rows={5}
          />
          <Textarea
            label="Damage Summary"
            value={form.damage_summary}
            onChange={(e) => set('damage_summary', e.target.value)}
            placeholder="Front bumper, hood, right headlight…"
            rows={3}
          />
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold text-slate-900">Conditions</h3>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <Input
            label="Weather"
            value={form.weather_conditions}
            onChange={(e) => set('weather_conditions', e.target.value)}
            placeholder="Clear, rainy…"
          />
          <Input
            label="Road Conditions"
            value={form.road_conditions}
            onChange={(e) => set('road_conditions', e.target.value)}
            placeholder="Dry, wet, icy…"
          />
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold text-slate-900">Contacts & Records</h3>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <Input
            label="Police Report #"
            value={form.police_report_number}
            onChange={(e) => set('police_report_number', e.target.value)}
          />
          <Input
            label="Adjuster Name"
            value={form.adjuster_name}
            onChange={(e) => set('adjuster_name', e.target.value)}
          />
          <Input
            label="Repair Shop"
            value={form.repair_shop_name}
            onChange={(e) => set('repair_shop_name', e.target.value)}
          />
        </div>
      </Card>

      <Card>
        <Textarea
          label="Follow-up Notes"
          value={form.follow_up_notes}
          onChange={(e) => set('follow_up_notes', e.target.value)}
          placeholder="Anything else to track…"
          rows={3}
        />
      </Card>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}
      <div className="flex justify-end">
        <Button type="submit" loading={loading}>
          Save & Continue →
        </Button>
      </div>
    </form>
  )
}
```

- [ ] **Step 2: Create `frontend/src/app/cases/[id]/stage-b/page.tsx`**

```typescript
// frontend/src/app/cases/[id]/stage-b/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getCaseSnapshot, patchAccidentStageB } from '@/lib/api'
import {
  StageBForm,
  StageBData,
  EMPTY_STAGE_B,
} from '@/components/accident/StageBForm'

export default function StageBPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const [initial, setInitial] = useState<StageBData>(EMPTY_STAGE_B)
  const [fetchLoading, setFetchLoading] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    load()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function load() {
    try {
      const snap = await getCaseSnapshot(caseId)
      if (snap.stage_b) {
        const b = snap.stage_b as Record<string, unknown>
        setInitial({
          detailed_narrative: String(b.detailed_narrative || ''),
          damage_summary: String(b.damage_summary || ''),
          weather_conditions: String(b.weather_conditions || ''),
          road_conditions: String(b.road_conditions || ''),
          police_report_number: String(b.police_report_number || ''),
          adjuster_name: String(b.adjuster_name || ''),
          repair_shop_name: String(b.repair_shop_name || ''),
          follow_up_notes: String(b.follow_up_notes || ''),
        })
      }
    } catch {
      // blank form is fine
    } finally {
      setFetchLoading(false)
    }
  }

  async function handleSubmit(data: StageBData) {
    setLoading(true)
    setError('')
    try {
      await patchAccidentStageB(caseId, {
        detailed_narrative: data.detailed_narrative || null,
        damage_summary: data.damage_summary || null,
        weather_conditions: data.weather_conditions || null,
        road_conditions: data.road_conditions || null,
        police_report_number: data.police_report_number || null,
        adjuster_name: data.adjuster_name || null,
        repair_shop_name: data.repair_shop_name || null,
        follow_up_notes: data.follow_up_notes || null,
        stage_completed_at: new Date().toISOString(),
      })
      router.push(`/cases/${caseId}/report`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setLoading(false)
    }
  }

  if (fetchLoading) {
    return <div className="py-20 text-center text-slate-500">Loading…</div>
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-slate-900">
          Step 3: Accident Details
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Add more context to strengthen your claim.
        </p>
      </div>
      <StageBForm
        initial={initial}
        onSubmit={handleSubmit}
        loading={loading}
        error={error}
      />
    </div>
  )
}
```

- [ ] **Step 3: Verify in browser**

1. Navigate to `/cases/{id}/stage-b`
2. StepIndicator shows step 3 highlighted
3. Fill form and submit — redirects to `/cases/{id}/report`

---

## Task 11: Report Page (Step 4)

**Files:**
- Create: `frontend/src/components/report/TimelineList.tsx`
- Create: `frontend/src/components/report/PartyTable.tsx`
- Create: `frontend/src/components/report/ReportView.tsx`
- Create: `frontend/src/app/cases/[id]/report/page.tsx`

- [ ] **Step 1: Create `TimelineList.tsx`**

```typescript
// frontend/src/components/report/TimelineList.tsx
type Entry = { label: string; timestamp: string; note: string | null }

export function TimelineList({ entries }: { entries: Entry[] }) {
  return (
    <ol className="mt-3 space-y-4">
      {entries.map((e, i) => (
        <li key={i} className="flex gap-3">
          <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-600">
            {i + 1}
          </div>
          <div>
            <p className="text-sm font-medium text-slate-900">{e.label}</p>
            <p className="text-xs text-slate-500">
              {new Date(e.timestamp).toLocaleString()}
            </p>
            {e.note && (
              <p className="mt-0.5 text-sm text-slate-600">{e.note}</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}
```

- [ ] **Step 2: Create `PartyTable.tsx`**

```typescript
// frontend/src/components/report/PartyTable.tsx
import { PartyComparisonRow } from '@/lib/api'

export function PartyTable({ rows }: { rows: PartyComparisonRow[] }) {
  return (
    <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-3 py-2 text-left font-medium text-slate-700">
              Field
            </th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">
              You
            </th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">
              Other Party
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field_label} className="border-t border-slate-200">
              <td className="px-3 py-2 font-medium text-slate-700">
                {row.field_label}
              </td>
              <td className="px-3 py-2 text-slate-900">{row.owner_value}</td>
              <td className="px-3 py-2 text-slate-900">
                {row.other_party_value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 3: Create `ReportView.tsx`**

```typescript
// frontend/src/components/report/ReportView.tsx
import { GenerateReportResponse } from '@/lib/api'
import { Card } from '@/components/ui/Card'
import { PartyTable } from './PartyTable'
import { TimelineList } from './TimelineList'

export function ReportView({ report }: { report: GenerateReportResponse }) {
  const r = report.report_payload
  return (
    <div className="space-y-4">
      <Card>
        <h3 className="text-lg font-bold text-slate-900">{r.report_title}</h3>
        <p className="mt-2 text-sm text-slate-700">{r.accident_summary}</p>
        {r.location_summary && (
          <p className="mt-1 text-sm text-slate-600">📍 {r.location_summary}</p>
        )}
      </Card>

      {r.detailed_narrative && (
        <Card>
          <h4 className="font-semibold text-slate-900">Narrative</h4>
          <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
            {r.detailed_narrative}
          </p>
        </Card>
      )}

      {r.timeline_entries && r.timeline_entries.length > 0 && (
        <Card>
          <h4 className="font-semibold text-slate-900">Timeline</h4>
          <TimelineList entries={r.timeline_entries} />
        </Card>
      )}

      {r.party_comparison_rows && r.party_comparison_rows.length > 0 && (
        <Card>
          <h4 className="font-semibold text-slate-900">Party Comparison</h4>
          <PartyTable rows={r.party_comparison_rows} />
        </Card>
      )}

      {r.damage_summary && (
        <Card>
          <h4 className="font-semibold text-slate-900">Damage</h4>
          <p className="mt-2 text-sm text-slate-700">{r.damage_summary}</p>
        </Card>
      )}

      {r.missing_items && r.missing_items.length > 0 && (
        <Card>
          <h4 className="font-semibold text-slate-900">Still Needed</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {r.missing_items.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create `frontend/src/app/cases/[id]/report/page.tsx`**

```typescript
// frontend/src/app/cases/[id]/report/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import {
  getAccidentReport,
  generateAccidentReport,
  GenerateReportResponse,
} from '@/lib/api'
import { ReportView } from '@/components/report/ReportView'
import { Button } from '@/components/ui/Button'

export default function ReportPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const [report, setReport] = useState<GenerateReportResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    load()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function load() {
    setLoading(true)
    try {
      const r = await getAccidentReport(caseId)
      setReport(r)
    } catch (err) {
      // 404 = not generated yet, that's fine — show the generate button
      if (!(err instanceof Error && err.message.includes('404'))) {
        setError(err instanceof Error ? err.message : 'Load failed')
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    setGenerating(true)
    setError('')
    try {
      const r = await generateAccidentReport(caseId)
      setReport(r)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return <div className="py-20 text-center text-slate-500">Loading…</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Step 4: Accident Report
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            AI-generated summary of your accident details.
          </p>
        </div>
        {!report && (
          <Button loading={generating} onClick={handleGenerate}>
            Generate Report
          </Button>
        )}
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      {!report && !generating && !error && (
        <div className="rounded-2xl border-2 border-dashed border-slate-200 px-6 py-16 text-center">
          <p className="text-slate-600">
            Complete Stages A &amp; B, then generate your report.
          </p>
        </div>
      )}

      {report && <ReportView report={report} />}

      {report && (
        <div className="flex justify-end">
          <Button onClick={() => router.push(`/cases/${caseId}/chat`)}>
            Go to AI Chat →
          </Button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Verify in browser**

1. Navigate to `/cases/{id}/report`
2. StepIndicator shows step 4 highlighted
3. If no report exists: "Generate Report" button visible
4. Click generate — report sections appear (title, narrative, timeline, etc.)
5. "Go to AI Chat" button navigates to `/cases/{id}/chat`

---

## Task 12: WebSocket Hook

**Files:**
- Create: `frontend/src/hooks/useWebSocketChat.ts`

- [ ] **Step 1: Create `frontend/src/hooks/useWebSocketChat.ts`**

```typescript
// frontend/src/hooks/useWebSocketChat.ts
'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

export type WsMessage = {
  id: string
  type: 'user_message' | 'ai_message' | 'system' | 'ready' | 'pong' | 'error'
  sender_role?: string
  message_text?: string
  payload?: {
    text: string
    citations: unknown[]
    trigger: string
    metadata: Record<string, unknown>
  }
  event?: string
  client_id?: string
  case_id?: string
}

export type WsStatus = 'connecting' | 'open' | 'closed' | 'error'

const BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'https://exasperatingly-unprologued-elease.ngrok-free.dev'
).replace(/^http/, 'ws')

export function useWebSocketChat(
  caseId: string,
  token: string | null
): {
  messages: WsMessage[]
  sendMessage: (text: string) => void
  status: WsStatus
} {
  const [messages, setMessages] = useState<WsMessage[]>([])
  const [status, setStatus] = useState<WsStatus>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const maxRetries = 5
  const unmountedRef = useRef(false)

  const connect = useCallback(() => {
    if (!token || !caseId || unmountedRef.current) return

    const url = `${BASE_URL}/ws/cases/${caseId}?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(url)
    wsRef.current = ws
    setStatus('connecting')

    ws.onopen = () => {
      if (unmountedRef.current) return
      setStatus('open')
      retriesRef.current = 0
    }

    ws.onmessage = (event) => {
      if (unmountedRef.current) return
      try {
        const msg = JSON.parse(event.data as string) as WsMessage
        if (msg.type === 'ready' || msg.type === 'pong') return
        setMessages((prev) => [
          ...prev,
          { ...msg, id: msg.id || `${Date.now()}-${Math.random()}` },
        ])
      } catch {
        // ignore malformed frames
      }
    }

    ws.onclose = () => {
      if (unmountedRef.current) return
      setStatus('closed')
      if (retriesRef.current < maxRetries) {
        const delay = Math.min(3000 * 2 ** retriesRef.current, 30000)
        retriesRef.current++
        setTimeout(connect, delay)
      } else {
        setStatus('error')
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [caseId, token])

  useEffect(() => {
    unmountedRef.current = false
    connect()
    return () => {
      unmountedRef.current = true
      retriesRef.current = maxRetries // stop reconnects
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((text: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(
      JSON.stringify({
        type: 'chat',
        message_text: text,
        sender_role: 'owner',
        invite_sent: false,
        run_ai: true,
      })
    )
  }, [])

  return { messages, sendMessage, status }
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep "useWebSocketChat"
```

Expected: no output.

---

## Task 13: Chat Page (Step 5)

**Files:**
- Create: `frontend/src/components/chat/ChatBubble.tsx`
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/components/chat/ChatWindow.tsx`
- Create: `frontend/src/app/cases/[id]/chat/page.tsx`

- [ ] **Step 1: Create `ChatBubble.tsx`**

```typescript
// frontend/src/components/chat/ChatBubble.tsx
'use client'

import { useState } from 'react'

type CitationItem = {
  source_label: string
  source_type: string
  page_num: number | null
  section: string | null
  excerpt: string
}

export type DisplayMessage = {
  id: string
  role: 'user' | 'ai' | 'system'
  text: string
  citations?: unknown[]
}

export function ChatBubble({ message }: { message: DisplayMessage }) {
  const [showCitations, setShowCitations] = useState(false)

  if (message.role === 'system') {
    return (
      <div className="text-center">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-400">
          {message.text}
        </span>
      </div>
    )
  }

  const isUser = message.role === 'user'
  const citations = (message.citations ?? []) as CitationItem[]

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-slate-100 text-slate-900'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.text}</p>
        {!isUser && citations.length > 0 && (
          <div className="mt-2 border-t border-slate-200 pt-2">
            <button
              onClick={() => setShowCitations(!showCitations)}
              className="text-xs text-slate-500 underline hover:text-slate-700"
            >
              {showCitations ? 'Hide' : 'Show'} {citations.length} source
              {citations.length > 1 ? 's' : ''}
            </button>
            {showCitations && (
              <div className="mt-2 space-y-2">
                {citations.map((c, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-slate-200 bg-white p-2 text-xs"
                  >
                    <p className="font-medium text-slate-800">
                      {c.source_label}
                    </p>
                    <p className="text-slate-500">
                      {c.source_type === 'kb_a' ? 'Your Policy' : 'Regulation'}
                      {c.page_num ? ` · Page ${c.page_num}` : ''}
                    </p>
                    <p className="mt-1 text-slate-700">{c.excerpt}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `ChatInput.tsx`**

```typescript
// frontend/src/components/chat/ChatInput.tsx
'use client'

import { KeyboardEvent, useState } from 'react'
import { Button } from '@/components/ui/Button'

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void
  disabled: boolean
}) {
  const [text, setText] = useState('')

  function handleSend() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex gap-2">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={
          disabled
            ? 'Connecting to ClaimMate AI…'
            : 'Ask about your claim… (Enter to send, Shift+Enter for new line)'
        }
        rows={2}
        className="flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      />
      <Button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="self-end"
      >
        Send
      </Button>
    </div>
  )
}
```

- [ ] **Step 3: Create `ChatWindow.tsx`**

```typescript
// frontend/src/components/chat/ChatWindow.tsx
'use client'

import { useEffect, useRef } from 'react'
import { ChatBubble, DisplayMessage } from './ChatBubble'

export function ChatWindow({ messages }: { messages: DisplayMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
      {messages.length === 0 && (
        <p className="py-8 text-center text-sm text-slate-400">
          Ask ClaimMate a question about your policy or claim…
        </p>
      )}
      {messages.map((msg) => (
        <ChatBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
```

- [ ] **Step 4: Create `frontend/src/app/cases/[id]/chat/page.tsx`**

```typescript
// frontend/src/app/cases/[id]/chat/page.tsx
'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getChatMessages, ChatMessageRow } from '@/lib/api'
import { useWebSocketChat, WsMessage } from '@/hooks/useWebSocketChat'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { ChatInput } from '@/components/chat/ChatInput'
import { DisplayMessage } from '@/components/chat/ChatBubble'
import { Card } from '@/components/ui/Card'

function rowToDisplay(row: ChatMessageRow): DisplayMessage {
  return {
    id: row.id,
    role: row.message_type === 'ai' ? 'ai' : 'user',
    text: row.body_text,
    citations: row.ai_payload?.citations,
  }
}

function wsToDisplay(msg: WsMessage): DisplayMessage | null {
  if (msg.type === 'user_message') {
    return { id: msg.id, role: 'user', text: msg.message_text || '' }
  }
  if (msg.type === 'ai_message' && msg.payload) {
    return {
      id: msg.id,
      role: 'ai',
      text: msg.payload.text,
      citations: msg.payload.citations,
    }
  }
  if (msg.type === 'system' && msg.event) {
    return { id: msg.id, role: 'system', text: msg.event }
  }
  return null
}

export default function ChatPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const [history, setHistory] = useState<DisplayMessage[]>([])
  const { messages: wsMessages, sendMessage, status } = useWebSocketChat(
    caseId,
    token
  )

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    getChatMessages(caseId)
      .then((r) => setHistory(r.messages.map(rowToDisplay)))
      .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const allMessages = useMemo(() => {
    const historyIds = new Set(history.map((m) => m.id))
    const wsDisplay = wsMessages.flatMap((m) => {
      const d = wsToDisplay(m)
      return d && !historyIds.has(d.id) ? [d] : []
    })
    return [...history, ...wsDisplay]
  }, [history, wsMessages])

  const statusColor =
    status === 'open'
      ? 'text-green-600'
      : status === 'connecting'
      ? 'text-yellow-600'
      : 'text-red-500'

  return (
    <div className="flex h-[calc(100vh-160px)] flex-col">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Step 5: AI Chat
          </h2>
          <p className="text-xs text-slate-500">
            Connection:{' '}
            <span className={statusColor}>{status}</span>
          </p>
        </div>
      </div>
      <Card className="flex flex-1 flex-col overflow-hidden p-0">
        <ChatWindow messages={allMessages} />
        <div className="border-t border-slate-200 p-4">
          <ChatInput onSend={sendMessage} disabled={status !== 'open'} />
        </div>
      </Card>
    </div>
  )
}
```

- [ ] **Step 5: Full end-to-end verify in browser**

```bash
cd frontend && npm run dev
```

1. Go to `http://localhost:3000` → redirects to `/login`
2. Register a new account
3. Redirected to `/cases` — empty state
4. Create new case → redirected to `/cases/{id}/policy`
5. Select a demo policy — badge shows "Loaded"
6. Ask a question — AI answer appears with citations
7. Click "Next" → Stage A form with step 2 highlighted
8. Fill in form → saves and goes to Stage B
9. Fill Stage B → saves and goes to Report
10. Click "Generate Report" → report sections render
11. Click "Go to AI Chat" → chat opens with WebSocket connected (status: open)
12. Send a message → AI responds in realtime
13. Sign out → redirected to login, localStorage token cleared

- [ ] **Step 6: Run lint**

```bash
cd frontend && npm run lint
```

Fix any ESLint errors before calling the task done.

---

## Self-Review

**Spec coverage check:**
- ✅ JWT auth (register/login) → Tasks 1, 2, 5
- ✅ `AuthContext` with `login()`, `register()`, `logout()` → Task 2
- ✅ Root `/` redirect → Task 4
- ✅ `/cases` list backed by localStorage → Task 6
- ✅ `/cases/new` create case → Task 6
- ✅ Case layout with `StepIndicator` → Task 7
- ✅ Policy step: demo picker + PDF upload + AskPanel → Task 8
- ✅ Stage A form with tri-state toggles → Task 9
- ✅ Stage B form → Task 10
- ✅ Report generation + view (ReportView, PartyTable, TimelineList) → Task 11
- ✅ WebSocket hook with reconnect → Task 12
- ✅ Chat page with history merge → Task 13
- ✅ `getAuthHeaders()` injected in all API calls → Task 1
- ✅ ngrok URL set as default `API_BASE_URL` → Task 1
- ✅ Header with logout → Task 3

**Type consistency:**
- `StageAData` / `EMPTY_STAGE_A` exported from `StageAForm.tsx`, imported in `stage-a/page.tsx` ✅
- `StageBData` / `EMPTY_STAGE_B` exported from `StageBForm.tsx`, imported in `stage-b/page.tsx` ✅
- `DisplayMessage` exported from `ChatBubble.tsx`, imported in `ChatWindow.tsx` and `chat/page.tsx` ✅
- `WsMessage` / `WsStatus` exported from `useWebSocketChat.ts` ✅
- `AuthUser` / `AuthResponse` exported from `api.ts`, imported in `AuthContext.tsx` ✅

**No placeholders:** All steps contain full code. ✅
