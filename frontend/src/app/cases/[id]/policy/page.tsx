'use client'

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { Spinner } from '@/components/ui/Spinner'

export default function PolicyPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    router.replace(`/cases/${caseId}/stage-b`)
  }, [token, caseId, router])

  return (
    <div className="flex justify-center py-20">
      <Spinner />
    </div>
  )
}
