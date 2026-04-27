'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
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

type PolicyWorkspaceProps = {
  caseId: string
  canEdit?: boolean
  title?: string
  intro?: string
  backHref?: string
  backLabel?: string
  nextHref?: string
  nextLabel?: string
}

export function PolicyWorkspace({
  caseId,
  canEdit = true,
  title = 'Step 1: Your Policy',
  intro = 'Upload your policy PDF or choose a demo to get started.',
  backHref,
  backLabel = 'Back',
  nextHref,
  nextLabel = 'Next',
}: PolicyWorkspaceProps) {
  const router = useRouter()
  const [policyStatus, setPolicyStatus] =
    useState<CasePolicyStatusResponse | null>(null)
  const [demoPolicies, setDemoPolicies] = useState<DemoPolicy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [replacing, setReplacing] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      if (!caseId) return
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
  }, [caseId])

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
      {backHref && (
        <Button variant="ghost" onClick={() => router.push(backHref)}>
          ← {backLabel}
        </Button>
      )}
      <Card>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">{title}</h2>
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
            {canEdit && (
              <button
                onClick={() => setReplacing((r) => !r)}
                className="ml-4 shrink-0 text-sm text-blue-600 hover:underline"
              >
                {replacing ? 'Cancel' : 'Replace'}
              </button>
            )}
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-600">{intro}</p>
        )}
        {error && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </p>
        )}
      </Card>

      {canEdit && (!policyStatus?.has_policy || replacing) && (
        <>
          <DemoPolicyPicker
            policies={demoPolicies}
            onSelect={handleDemoSelect}
          />
          <PolicyUpload onUpload={handleUpload} />
        </>
      )}

      {policyStatus?.has_policy && <AskPanel caseId={caseId} />}

      {nextHref && (
        <div className="flex justify-end">
          <Button
            disabled={!policyStatus?.has_policy}
            onClick={() => router.push(nextHref)}
          >
            {nextLabel} →
          </Button>
        </div>
      )}
    </div>
  )
}
