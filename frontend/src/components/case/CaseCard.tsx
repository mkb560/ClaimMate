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

  return (
    <Card className="flex items-center justify-between gap-3">
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
            className="w-full rounded-lg border border-blue-400 px-2 py-1 text-sm font-medium text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
          />
        ) : (
          <button
            onClick={() => { setDraft(name); setEditing(true) }}
            className="group flex items-center gap-1 text-left"
            title="Click to rename"
          >
            <p className="font-medium text-slate-900">{name}</p>
            <span className="text-xs text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">✎</span>
          </button>
        )}
        <p className="text-xs text-slate-400">{caseId}</p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
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
