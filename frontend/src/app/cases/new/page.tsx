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
