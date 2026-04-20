'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import {
  getAccidentReport,
  generateAccidentReport,
  GenerateReportResponse,
} from '@/lib/api'
import { ReportView } from '@/components/report/ReportView'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'

export default function ReportPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const [report, setReport] = useState<GenerateReportResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      setLoading(false)
      router.replace('/login')
      return
    }

    let cancelled = false

    async function load() {
      try {
        const r = await getAccidentReport(caseId)
        if (!cancelled) setReport(r)
      } catch (err) {
        // 404 = not generated yet, that's fine — show the generate button
        if (!cancelled && !(err instanceof Error && err.message.includes('404'))) {
          setError(err instanceof Error ? err.message : 'Load failed')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [token, caseId, router])

  async function handleGenerate() {
    setGenerating(true)
    setError('')
    try {
      const r = await generateAccidentReport(caseId)
      setReport(r)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setGenerating(false)
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
      <Button variant="ghost" onClick={() => router.push(`/cases/${caseId}/stage-b`)}>
        ← Back
      </Button>
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Step 4: Accident Report
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            AI-generated summary of your accident details.
          </p>
        </div>
        <div className="flex gap-2">
          {!report && (
            <Button loading={generating} onClick={handleGenerate}>
              Generate Report
            </Button>
          )}
          {report && (
            <Button variant="secondary" loading={generating} onClick={handleGenerate}>
              Regenerate
            </Button>
          )}
        </div>
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      {!report && !generating && !error && (
        <div className="rounded-2xl border-2 border-dashed border-slate-200 px-6 py-16 text-center">
          <p className="text-slate-600">
            Complete Stages A &amp; B, then generate your report.
          </p>
        </div>
      )}

      {report && <ReportView report={report} />}

      {report && (
        <div className="flex justify-end">
          <Button onClick={() => router.push(`/cases/${caseId}/chat`)}>
            Go to AI Chat →
          </Button>
        </div>
      )}
    </div>
  )
}
