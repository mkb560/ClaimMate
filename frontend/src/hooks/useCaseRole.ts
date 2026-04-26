'use client'

import { useEffect, useState } from 'react'
import { getUserCases } from '@/lib/api'

export function useCaseRole(caseId: string): 'owner' | 'member' | null {
  const [role, setRole] = useState<'owner' | 'member' | null>(null)

  useEffect(() => {
    getUserCases()
      .then((cases) => {
        const found = cases.find((c) => c.case_id === caseId)
        setRole(found ? (found.role as 'owner' | 'member') : null)
      })
      .catch(() => setRole(null))
  }, [caseId])

  return role
}
