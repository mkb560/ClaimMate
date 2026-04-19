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
import { Spinner } from '@/components/ui/Spinner'

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
  const [replacing, setReplacing] = useState(false)

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }

    let cancelled = false

    async function loadData() {
      setLoading(true)
      setError('')
      try {
        const [status, catalog] = await Promise.all([
          getCasePolicyStatus(caseId),
          getDemoPolicies(),
        ])
        if (!cancelled) {
          setPolicyStatus(status)
          setDemoPolicies(catalog.policies)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadData()
    return () => { cancelled = true }
  }, [token, caseId, router])

  async function refresh() {
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
      setReplacing(false)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to seed policy')
    }
  }

  async function handleUpload(file: File) {
    setError('')
    try {
      await uploadPolicy(caseId, file)
      setReplacing(false)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
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
          <div className="mt-3 flex items-center justify-between rounded-xl bg-green-50 px-4 py-3">
            <p className="text-sm text-green-700">
              <strong>
                {policyStatus.filename || policyStatus.source_label}
              </strong>{' '}
              is indexed ({policyStatus.chunk_count} chunks)
            </p>
            <button
              onClick={() => setReplacing((r) => !r)}
              className="ml-4 shrink-0 text-sm text-blue-600 hover:underline"
            >
              {replacing ? 'Cancel' : 'Replace'}
            </button>
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

      {(!policyStatus?.has_policy || replacing) && (
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
        <Button
          disabled={!policyStatus?.has_policy}
          onClick={() => router.push(`/cases/${caseId}/stage-a`)}
        >
          Next: Accident Basics →
        </Button>
      </div>
    </div>
  )
}
