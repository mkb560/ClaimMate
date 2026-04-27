'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { createCase } from '@/lib/api'
import { getPolicyWorkspaceCaseId } from '@/lib/policyWorkspace'
import { PolicyWorkspace } from '@/components/policy/PolicyWorkspace'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'

export default function StandalonePolicyPage() {
  const { token, user } = useAuth()
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')

  const policyCaseId = useMemo(
    () => (user ? getPolicyWorkspaceCaseId(user.user_id) : ''),
    [user]
  )

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    if (!user || !policyCaseId) return

    let active = true

    async function ensureWorkspace() {
      setReady(false)
      setError('')
      try {
        await createCase(policyCaseId)
      } catch (err) {
        const message = err instanceof Error ? err.message : ''
        if (!message.includes('already exists')) {
          if (active) setError(message || 'Failed to prepare policy workspace')
          return
        }
      }
      if (active) setReady(true)
    }

    ensureWorkspace()
    return () => { active = false }
  }, [token, user, policyCaseId, router])

  if (!token || !user || !ready) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        {error ? (
          <Card>
            <h1 className="text-xl font-bold text-slate-900">
              Could not open Policy Q&A
            </h1>
            <p className="mt-2 text-sm text-red-600">{error}</p>
            <Button className="mt-4" onClick={() => router.push('/cases')}>
              Back to Cases
            </Button>
          </Card>
        ) : (
          <div className="flex justify-center py-20">
            <Spinner />
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">
          Policy Q&A
        </p>
        <h1 className="mt-2 text-3xl font-bold text-slate-950">
          Ask questions about your insurance policy
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          This is a standalone policy workspace. Upload a policy or use a demo
          policy, then ask coverage and policy fact questions without starting
          an accident case.
        </p>
      </div>
      <PolicyWorkspace
        caseId={policyCaseId}
        title="Your Policy"
        intro="Upload your policy PDF or choose a demo policy to start asking questions."
        backHref="/cases"
        backLabel="Back to Cases"
      />
    </div>
  )
}
