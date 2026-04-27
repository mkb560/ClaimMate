'use client'

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { PolicyWorkspace } from '@/components/policy/PolicyWorkspace'
import { useCaseRole } from '@/hooks/useCaseRole'

export default function PolicyPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const role = useCaseRole(caseId)
  const isOwner = role !== 'member'

  useEffect(() => {
    if (!token) {
      router.replace('/login')
    }
  }, [token, router])

  return (
    <PolicyWorkspace
      caseId={caseId}
      canEdit={isOwner}
      title="Step 1: Your Policy"
      backHref="/cases"
      backLabel="Back to Cases"
      nextHref={`/cases/${caseId}/stage-a`}
      nextLabel="Next: Accident Basics"
    />
  )
}
