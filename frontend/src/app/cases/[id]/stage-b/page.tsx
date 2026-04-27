'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getCaseSnapshot, patchAccidentStageB } from '@/lib/api'
import {
  StageBForm,
  StageBData,
  EMPTY_STAGE_B,
} from '@/components/accident/StageBForm'
import { PolicyWorkspace } from '@/components/policy/PolicyWorkspace'
import { useCaseRole } from '@/hooks/useCaseRole'
import { Spinner } from '@/components/ui/Spinner'
import { Button } from '@/components/ui/Button'

export default function StageBPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const role = useCaseRole(caseId)
  const isOwner = role !== 'member'
  const [initial, setInitial] = useState<StageBData>(EMPTY_STAGE_B)
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
        if (!cancelled && snap.stage_b) {
          const b = snap.stage_b as Record<string, unknown>
          setInitial({
            detailed_narrative: String(b.detailed_narrative || ''),
            damage_summary: String(b.damage_summary || ''),
            weather_conditions: String(b.weather_conditions || ''),
            road_conditions: String(b.road_conditions || ''),
            police_report_number: String(b.police_report_number || ''),
            adjuster_name: String(b.adjuster_name || ''),
            repair_shop_name: String(b.repair_shop_name || ''),
            follow_up_notes: String(b.follow_up_notes || ''),
          })
        }
      } catch {
        // blank form is fine
      } finally {
        if (!cancelled) setFetchLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [token, caseId, router])

  async function handleSubmit(data: StageBData) {
    setLoading(true)
    setError('')
    try {
      await patchAccidentStageB(caseId, {
        detailed_narrative: data.detailed_narrative || null,
        damage_summary: data.damage_summary || null,
        weather_conditions: data.weather_conditions || null,
        road_conditions: data.road_conditions || null,
        police_report_number: data.police_report_number || null,
        adjuster_name: data.adjuster_name || null,
        repair_shop_name: data.repair_shop_name || null,
        follow_up_notes: data.follow_up_notes || null,
        stage_completed_at: new Date().toISOString(),
      })
      router.push(`/cases/${caseId}/report`)
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
        <Button variant="ghost" onClick={() => router.push(`/cases/${caseId}/stage-a`)}>
          ← Back
        </Button>
      </div>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-slate-900">
          Step 2: Accident Details
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Add more context and attach your policy once the urgent basics are saved.
        </p>
      </div>
      <div className="mb-6">
        <PolicyWorkspace
          caseId={caseId}
          canEdit={isOwner}
          title="Policy & Coverage Materials"
          intro="Choose an existing policy or upload your own PDF here. ClaimMate can use it later for coverage questions and claim support."
          showAskPanel={false}
        />
      </div>
      <StageBForm
        key={caseId}
        initial={initial}
        onSubmit={handleSubmit}
        loading={loading}
        error={error}
        readOnly={!isOwner}
      />
    </div>
  )
}
