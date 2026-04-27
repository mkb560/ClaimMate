'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

type CaseCardProps = {
  caseId: string
  name: string
  onDelete?: () => void
  onRename?: (newName: string) => void
}

export function CaseCard({ caseId, name, onDelete, onRename }: CaseCardProps) {
  const router = useRouter()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(name)

  function handleRenameSubmit() {
    const trimmed = draft.trim()
    if (trimmed && trimmed !== name) {
      onRename?.(trimmed)
    } else {
      setDraft(name)
    }
    setEditing(false)
  }

  function startEditing() {
    setDraft(name)
    setEditing(true)
  }

  return (
    <Card className="group flex flex-col gap-4 transition hover:-translate-y-0.5 hover:shadow-[0_24px_70px_rgba(37,99,235,0.13)] sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 flex-1 items-start gap-4">
        <div className="mt-0.5 flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-sm font-black text-blue-700 ring-1 ring-blue-100">
          CM
        </div>
        <div className="min-w-0 flex-1">
          {editing ? (
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={handleRenameSubmit}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRenameSubmit()
                if (e.key === 'Escape') { setDraft(name); setEditing(false) }
              }}
              className="w-full rounded-xl border border-blue-400 bg-white px-3 py-2 text-base font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
            />
          ) : (
            <p className="truncate text-lg font-bold tracking-tight text-slate-950">{name}</p>
          )}
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
              Active
            </span>
            <p className="text-xs font-medium text-slate-400">{caseId}</p>
          </div>
        </div>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
        <Button
          variant="secondary"
          onClick={startEditing}
        >
          Rename
        </Button>
        <Button
          variant="secondary"
          onClick={() => router.push(`/cases/${caseId}/stage-a`)}
        >
          Open →
        </Button>
        {onDelete && (
          <button
            onClick={onDelete}
            className="rounded-xl px-3 py-2 text-sm font-medium text-red-500 hover:bg-red-50 transition-colors"
          >
            Delete
          </button>
        )}
      </div>
    </Card>
  )
}
