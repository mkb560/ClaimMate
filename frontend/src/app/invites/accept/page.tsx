'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { lookupInvite, acceptInvite, InviteLookupResponse } from '@/lib/api'
import { setCaseName } from '@/lib/auth'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'

function AcceptInviteContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const { token: authToken } = useAuth()
  const router = useRouter()

  const [invite, setInvite] = useState<InviteLookupResponse | null>(null)
  const [lookupError, setLookupError] = useState('')
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState(false)
  const [acceptError, setAcceptError] = useState('')

  useEffect(() => {
    if (!token) {
      setLookupError('Invalid invite link.')
      setLoading(false)
      return
    }
    lookupInvite(token)
      .then((info) => setInvite(info))
      .catch((err) => setLookupError(err instanceof Error ? err.message : 'Invite not found.'))
      .finally(() => setLoading(false))
  }, [token])

  async function handleAccept() {
    setAccepting(true)
    setAcceptError('')
    try {
      const res = await acceptInvite(token)
      setCaseName(res.case_id, res.case_id)
      router.push(`/cases/${res.case_id}/chat`)
    } catch (err) {
      setAcceptError(err instanceof Error ? err.message : 'Failed to accept invite.')
    } finally {
      setAccepting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-57px)] items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-900">You&apos;ve been invited</h1>
          <p className="mt-1 text-sm text-slate-600">Join a ClaimMate case</p>
        </div>
        <Card>
          {lookupError ? (
            <p className="text-sm text-red-600">{lookupError}</p>
          ) : invite ? (
            <div className="space-y-4">
              <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <p><span className="font-medium">Case:</span> {invite.case_id}</p>
                <p><span className="font-medium">Role:</span> {invite.role}</p>
                <p><span className="font-medium">Expires:</span> {new Date(invite.expires_at).toLocaleDateString()}</p>
              </div>

              {acceptError && (
                <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{acceptError}</p>
              )}

              {authToken ? (
                <Button loading={accepting} onClick={handleAccept} className="w-full">
                  Join Case
                </Button>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-slate-600">You need to log in first to join this case.</p>
                  <Button
                    className="w-full"
                    onClick={() => router.push(`/register?next=/invites/accept?token=${encodeURIComponent(token)}`)}
                  >
                    Register &amp; Join
                  </Button>
                  <Button
                    variant="secondary"
                    className="w-full"
                    onClick={() => router.push(`/login?next=/invites/accept?token=${encodeURIComponent(token)}`)}
                  >
                    Log in &amp; Join
                  </Button>
                </div>
              )}
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  )
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={<div className="flex min-h-[calc(100vh-57px)] items-center justify-center"><Spinner /></div>}>
      <AcceptInviteContent />
    </Suspense>
  )
}
