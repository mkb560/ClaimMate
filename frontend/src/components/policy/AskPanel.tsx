'use client'

import { useState } from 'react'
import { askPolicyQuestion, Citation } from '@/lib/api'
import { Card } from '@/components/ui/Card'
import { Textarea } from '@/components/ui/Textarea'
import { Button } from '@/components/ui/Button'

export function AskPanel({ caseId }: { caseId: string }) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [disclaimer, setDisclaimer] = useState('')
  const [citations, setCitations] = useState<Citation[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleAsk() {
    if (!question.trim()) return
    setLoading(true)
    setError('')
    setAnswer('')
    setDisclaimer('')
    setCitations([])
    try {
      const result = await askPolicyQuestion(caseId, question.trim())
      setAnswer(result.answer)
      setDisclaimer(result.disclaimer)
      setCitations(result.citations)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ask failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <h3 className="font-semibold text-slate-900">Ask About Your Policy</h3>
      <div className="mt-3 space-y-3">
        <Textarea
          label="Your question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What is my liability coverage limit?"
          rows={3}
        />
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </p>
        )}
        <Button
          loading={loading}
          disabled={!question.trim()}
          onClick={handleAsk}
        >
          Ask AI
        </Button>
        {answer && (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-slate-900">
              {disclaimer ? answer.replace(disclaimer, '').trim() : answer}
            </p>
            {disclaimer && (
              <p className="text-xs text-slate-500">{disclaimer}</p>
            )}
            {citations.length > 0 && (
              <details className="text-sm">
                <summary className="cursor-pointer text-blue-600">
                  Sources ({citations.length})
                </summary>
                <div className="mt-2 space-y-2">
                  {citations.map((c, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-slate-200 p-3"
                    >
                      <p className="font-medium text-slate-800">
                        {c.source_label}
                      </p>
                      <p className="text-xs text-slate-500">
                        {c.source_type === 'kb_a' ? 'Your Policy' : 'Regulation'}
                        {c.page_num ? ` · Page ${c.page_num}` : ''}
                      </p>
                      <p className="mt-1 text-slate-700">{c.excerpt}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
