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
