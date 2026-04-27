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
    <header className="sticky top-0 z-40 border-b border-white/60 bg-white/80 px-4 py-3 shadow-sm shadow-slate-200/60 backdrop-blur-xl">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <Link href="/cases" className="group flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-400 text-sm font-black text-white shadow-lg shadow-blue-500/20">
            C
          </span>
          <span className="text-xl font-black tracking-tight text-slate-950 group-hover:text-blue-700">
            ClaimMate
          </span>
        </Link>
        {token && (
          <div className="flex items-center gap-3">
            <Link
              href="/policy"
              className="rounded-full px-3 py-1.5 text-sm font-semibold text-slate-600 transition hover:bg-blue-50 hover:text-blue-700"
            >
              Policy Q&A
            </Link>
            <button
              onClick={handleLogout}
              className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
