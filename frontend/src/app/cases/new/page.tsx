'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { createCase } from '@/lib/api'
import { setCaseName } from '@/lib/auth'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'

function generateDefaultCaseName(): string {
  const now = new Date()
  const timestamp = now.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
  const suffix = Math.random().toString(36).slice(2, 6).toUpperCase()
  return `Accident case ${timestamp} ${suffix}`
}

export default function NewCasePage() {
  const { token } = useAuth()
  const router = useRouter()
  const startedRef = useRef(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    if (startedRef.current) return
    startedRef.current = true

    async function createAndEnterCase() {
      setLoading(true)
      setError('')
      try {
        const { case_id } = await createCase()
        setCaseName(case_id, generateDefaultCaseName())
        router.replace(`/cases/${case_id}/stage-a`)
      } catch (err) {
        startedRef.current = false
        setError(err instanceof Error ? err.message : 'Failed to create case')
        setLoading(false)
      }
    }

    createAndEnterCase()
  }, [token, router, attempt])

  function handleRetry() {
    startedRef.current = false
    setError('')
    setAttempt((current) => current + 1)
  }

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <Card>
          <h1 className="text-xl font-bold text-slate-900">
            Starting your case
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            ClaimMate will name it automatically so you can record urgent accident details first.
          </p>
          {loading && (
            <div className="mt-6 flex items-center gap-3 rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-700">
              <Spinner />
              Creating case and opening Accident Basics...
            </div>
          )}
          {error && (
            <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </p>
          )}
          {error && (
            <Button className="mt-4 w-full" onClick={handleRetry}>
              Try Again
            </Button>
          )}
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
