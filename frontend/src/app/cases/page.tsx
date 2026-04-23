'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getUserCases, deleteCase } from '@/lib/api'
import { getCaseName, setCaseName, removeCaseName } from '@/lib/auth'
import { CaseCard } from '@/components/case/CaseCard'
import { Button } from '@/components/ui/Button'

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
    setLoading(true)
    setError('')
    getUserCases()
      .then((entries) => {
        setCases(entries.map((e) => ({ id: e.case_id, name: getCaseName(e.case_id) })))
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load cases')
      })
      .finally(() => setLoading(false))
  }, [token, router])

  async function handleDelete(id: string) {
    try { await deleteCase(id) } catch { /* best-effort */ }
    removeCaseName(id)
    setCases((prev) => prev.filter((c) => c.id !== id))
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Your Cases</h1>
        <Button onClick={() => router.push('/cases/new')}>+ New Case</Button>
      </div>
      {error && (
        <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
      )}
      {loading ? null : cases.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-slate-200 px-6 py-16 text-center">
          <p className="text-slate-600">No cases yet.</p>
          <Button className="mt-4" onClick={() => router.push('/cases/new')}>
            Start your first case
          </Button>
        </div>
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
