'use client'

import { useState } from 'react'
import { DemoPolicy } from '@/lib/api'
import { Card } from '@/components/ui/Card'

export function DemoPolicyPicker({
  policies,
  onSelect,
}: {
  policies: DemoPolicy[]
  onSelect: (p: DemoPolicy) => Promise<void>
}) {
  const [loading, setLoading] = useState<string | null>(null)

  async function handleSelect(policy: DemoPolicy) {
    setLoading(policy.policy_key)
    try {
      await onSelect(policy)
    } finally {
      setLoading(null)
    }
  }

  return (
    <Card>
      <h3 className="font-semibold text-slate-900">Choose an Existing Policy</h3>
      <p className="mt-1 text-sm text-slate-600">
        Select one of the prepared policy documents to get started instantly.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {policies.map((p) => (
          <button
            key={p.policy_key}
            onClick={() => handleSelect(p)}
            disabled={!!loading}
            aria-busy={loading === p.policy_key}
            className="rounded-xl border border-slate-200 p-4 text-left transition hover:border-blue-400 hover:bg-blue-50 disabled:opacity-50"
          >
            <p className="font-medium text-slate-900">{p.label}</p>
            <p className="mt-1 text-xs text-slate-500">{p.filename}</p>
            {loading === p.policy_key && (
              <p className="mt-2 text-xs text-blue-600">Loading…</p>
            )}
          </button>
        ))}
      </div>
    </Card>
  )
}
