'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getCaseSnapshot, patchAccidentStageA } from '@/lib/api'
import {
  StageAForm,
  StageAData,
  EMPTY_STAGE_A,
} from '@/components/accident/StageAForm'
import { Spinner } from '@/components/ui/Spinner'
import { Button } from '@/components/ui/Button'

function boolToTriState(v: unknown): 'true' | 'false' | 'unknown' {
  if (v === true) return 'true'
  if (v === false) return 'false'
  return 'unknown'
}

function toDateTimeLocal(v: unknown): string {
  if (!v || typeof v !== 'string') return ''
  const d = new Date(v)
  if (isNaN(d.getTime())) return ''
  return d.toISOString().slice(0, 16)
}

function triStateToBool(v: string): boolean | null {
  if (v === 'true') return true
  if (v === 'false') return false
  return null
}

export default function StageAPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const [initial, setInitial] = useState<StageAData>(EMPTY_STAGE_A)
  const [fetchLoading, setFetchLoading] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      setFetchLoading(false)
      router.replace('/login')
      return
    }

    let cancelled = false

    async function load() {
      try {
        const snap = await getCaseSnapshot(caseId)
        if (!cancelled && snap.stage_a) {
          const a = snap.stage_a as Record<string, unknown>
          const loc = (a.location as Record<string, unknown>) || {}
          const own = (a.owner_party as Record<string, unknown>) || {}
          const oth = (a.other_party as Record<string, unknown>) || {}
          setInitial({
            occurred_at: toDateTimeLocal(a.occurred_at),
            address: String(loc.address || ''),
            quick_summary: String(a.quick_summary || ''),
            owner_name: String(own.name || ''),
            owner_phone: String(own.phone || ''),
            owner_insurer: String(own.insurer || ''),
            owner_policy_number: String(own.policy_number || ''),
            other_name: String(oth.name || ''),
            other_phone: String(oth.phone || ''),
            other_insurer: String(oth.insurer || ''),
            other_policy_number: String(oth.policy_number || ''),
            injuries_reported: boolToTriState(a.injuries_reported),
            police_called: boolToTriState(a.police_called),
            drivable: boolToTriState(a.drivable),
            tow_requested: boolToTriState(a.tow_requested),
          })
        }
      } catch {
        // blank form is fine for new cases
      } finally {
        if (!cancelled) setFetchLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [token, caseId, router])

  async function handleSubmit(data: StageAData) {
    setLoading(true)
    setError('')
    try {
      await patchAccidentStageA(caseId, {
        occurred_at: data.occurred_at
          ? new Date(data.occurred_at).toISOString()
          : null,
        location: { address: data.address || null },
        owner_party: {
          role: 'owner',
          name: data.owner_name,
          phone: data.owner_phone || null,
          insurer: data.owner_insurer || null,
          policy_number: data.owner_policy_number || null,
        },
        other_party: {
          role: 'other_driver',
          name: data.other_name,
          phone: data.other_phone || null,
          insurer: data.other_insurer || null,
          policy_number: data.other_policy_number || null,
        },
        injuries_reported: triStateToBool(data.injuries_reported),
        police_called: triStateToBool(data.police_called),
        drivable: triStateToBool(data.drivable),
        tow_requested: triStateToBool(data.tow_requested),
        quick_summary: data.quick_summary,
        stage_completed_at: new Date().toISOString(),
      })
      router.push(`/cases/${caseId}/stage-b`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setLoading(false)
    }
  }

  if (fetchLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    )
  }

  return (
    <div>
      <div className="mb-4">
        <Button variant="ghost" onClick={() => router.push(`/cases/${caseId}/policy`)}>
          ← Back
        </Button>
      </div>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-slate-900">
          Step 2: Accident Basics
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Fill in what you have now — you can update anytime.
        </p>
      </div>
      <StageAForm
        key={caseId}
        caseId={caseId}
        initial={initial}
        onSubmit={handleSubmit}
        loading={loading}
        error={error}
      />
    </div>
  )
}
