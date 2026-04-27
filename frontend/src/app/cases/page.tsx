'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getUserCases, deleteCase } from '@/lib/api'
import { getCaseName, setCaseName, removeCaseName } from '@/lib/auth'
import { isPolicyWorkspaceCaseId } from '@/lib/policyWorkspace'
import { CaseCard } from '@/components/case/CaseCard'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

type CaseItem = { id: string; name: string }

export default function CasesPage() {
  const { token } = useAuth()
  const router = useRouter()
  const [cases, setCases] = useState<CaseItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    let active = true
    getUserCases()
      .then((entries) => {
        if (!active) return
        setCases(
          entries
            .filter((e) => !isPolicyWorkspaceCaseId(e.case_id))
            .map((e) => ({ id: e.case_id, name: getCaseName(e.case_id) }))
        )
        setError('')
      })
      .catch((err) => {
        if (!active) return
        setError(err instanceof Error ? err.message : 'Failed to load cases')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [token, router])

  async function handleDelete(id: string) {
    try { await deleteCase(id) } catch { /* best-effort */ }
    removeCaseName(id)
    setCases((prev) => prev.filter((c) => c.id !== id))
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-6 overflow-hidden rounded-[2rem] border border-white/70 bg-gradient-to-br from-slate-950 via-blue-950 to-cyan-800 p-8 text-white shadow-[0_24px_70px_rgba(15,23,42,0.22)]">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-200">
              ClaimMate workspace
            </p>
            <h1 className="mt-3 text-3xl font-black tracking-tight">
              Your Cases
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-blue-100">
              Start the accident intake immediately, then add policy materials,
              generate a report, and collaborate in chat.
            </p>
          </div>
          <div className="flex w-full flex-col gap-3 sm:w-auto sm:items-stretch">
            <Button
              onClick={() => router.push('/cases/new')}
              className="min-w-52 px-7 py-4 text-base shadow-2xl shadow-cyan-500/25"
            >
              + Start New Case
            </Button>
            <Button
              variant="secondary"
              onClick={() => router.push('/policy')}
              className="px-6 py-3"
            >
              Policy Q&A
            </Button>
          </div>
        </div>
      </div>
      {error && (
        <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
      )}
      {loading ? null : cases.length === 0 ? (
        <Card className="border-dashed py-16 text-center">
          <p className="text-lg font-semibold text-slate-900">No cases yet.</p>
          <p className="mt-2 text-sm text-slate-600">
            Create one and ClaimMate will open Accident Basics right away.
          </p>
          <Button className="mt-4" onClick={() => router.push('/cases/new')}>
            Start your first case
          </Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {cases.map((entry) => (
            <CaseCard
              key={entry.id}
              caseId={entry.id}
              name={entry.name}
              onDelete={() => handleDelete(entry.id)}
              onRename={(newName) => {
                setCaseName(entry.id, newName)
                setCases((prev) =>
                  prev.map((c) => (c.id === entry.id ? { ...c, name: newName } : c))
                )
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
