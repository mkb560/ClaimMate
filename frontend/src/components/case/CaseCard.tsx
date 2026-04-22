'use client'

import { useRouter } from 'next/navigation'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

export function CaseCard({ caseId }: { caseId: string }) {
  const router = useRouter()
  return (
    <Card className="flex items-center justify-between">
      <div>
        <p className="font-medium text-slate-900">{caseId}</p>
        <p className="text-xs text-slate-500">Case ID</p>
      </div>
      <Button
        variant="secondary"
        onClick={() => router.push(`/cases/${caseId}/policy`)}
      >
        Open →
      </Button>
    </Card>
  )
}
