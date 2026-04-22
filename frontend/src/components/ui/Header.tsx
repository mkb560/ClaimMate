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
