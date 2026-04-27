'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import {
  AuthUser,
  CaseMemberEntry,
  ChatMessageRow,
  createInvite,
  getCaseMembers,
  getChatMessages,
} from '@/lib/api'
import { useWebSocketChat, WsMessage } from '@/hooks/useWebSocketChat'
import { useCaseRole } from '@/hooks/useCaseRole'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { ChatInput } from '@/components/chat/ChatInput'
import { DisplayMessage } from '@/components/chat/ChatBubble'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

function resolveSenderName(
  storedDisplayName: string | null | undefined,
  senderRole: string | null | undefined,
  user: AuthUser | null,
  currentRole: string | null
): string {
  if (storedDisplayName) return storedDisplayName
  if (!senderRole) return 'User'
  if (senderRole === currentRole && user) {
    return user.display_name || user.email
  }
  return senderRole === 'owner' ? 'Owner' : senderRole === 'member' ? 'Member' : senderRole
}

function rowToDisplay(row: ChatMessageRow, user: AuthUser | null, currentRole: string | null): DisplayMessage {
  return {
    id: row.id,
    role: row.message_type === 'ai' ? 'ai' : 'user',
    text: row.body_text,
    citations: row.ai_payload?.citations,
    senderName: row.message_type === 'ai'
      ? 'ClaimMate'
      : resolveSenderName(row.sender_display_name, row.sender_role, user, currentRole),
  }
}

function wsToDisplay(msg: WsMessage, user: AuthUser | null, currentRole: string | null): DisplayMessage | null {
  if (msg.type === 'user_message') {
    return {
      id: msg.id,
      role: 'user',
      text: msg.message_text || '',
      senderName: resolveSenderName(msg.sender_display_name, msg.sender_role, user, currentRole),
    }
  }
  if (msg.type === 'ai_message' && msg.payload) {
    return {
      id: msg.id,
      role: 'ai',
      text: msg.payload.text,
      citations: msg.payload.citations,
      senderName: 'ClaimMate',
    }
  }
  if (msg.type === 'system' && msg.event) {
    return { id: msg.id, role: 'system', text: msg.event }
  }
  return null
}

export default function ChatPage() {
  const { token, user } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const role = useCaseRole(caseId)
  const [history, setHistory] = useState<DisplayMessage[]>([])
  const [isAiTyping, setIsAiTyping] = useState(false)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteLink, setInviteLink] = useState('')
  const [inviteLoading, setInviteLoading] = useState(false)
  const [inviteError, setInviteError] = useState('')
  const [copied, setCopied] = useState(false)
  const [caseMembers, setCaseMembers] = useState<CaseMemberEntry[]>([])
  const [inviteSent, setInviteSent] = useState(false)
  const currentMember = caseMembers.find((member) => member.user_id === user?.user_id)
  const senderRole = currentMember?.role ?? role ?? 'owner'
  const participants = useMemo(
    () =>
      caseMembers.length > 0
        ? caseMembers.map((member) => ({ user_id: member.user_id, role: member.role }))
        : [{ user_id: user?.user_id ?? 'owner-1', role: senderRole }],
    [caseMembers, senderRole, user?.user_id]
  )
  const { messages: wsMessages, sendMessage, status } = useWebSocketChat(
    caseId,
    token,
    {
      senderRole,
      inviteSent: inviteSent || participants.length > 1,
      participants,
    }
  )

  useEffect(() => {
    const last = wsMessages[wsMessages.length - 1]
    if (last && (last.type === 'ai_message' || last.type === 'system')) {
      setIsAiTyping(false)
    }
  }, [wsMessages])

  function handleSend(text: string) {
    sendMessage(text)
    if (/@ai\b/i.test(text)) {
      setIsAiTyping(true)
    }
  }

  async function handleCreateInvite() {
    setInviteLoading(true)
    setInviteError('')
    try {
      const res = await createInvite(caseId, 'adjuster')
      const link = `${window.location.origin}/invites/accept?token=${encodeURIComponent(res.token)}`
      setInviteLink(link)
      setInviteSent(true)
      setShowInviteModal(true)
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : 'Failed to create invite')
    } finally {
      setInviteLoading(false)
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(inviteLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    Promise.all([
      getChatMessages(caseId),
      getCaseMembers(caseId).catch(() => [] as CaseMemberEntry[]),
    ])
      .then(([chat, members]) => {
        const loadedRole = members.find((member) => member.user_id === user?.user_id)?.role ?? role
        setHistory(chat.messages.map((m) => rowToDisplay(m, user, loadedRole)))
        setCaseMembers(members)
        setInviteSent(members.length > 1)
      })
      .catch(() => {})
  }, [token, caseId, router, user, role])

  const allMessages = useMemo(() => {
    const historyIds = new Set(history.map((m) => m.id))
    const wsDisplay = wsMessages.flatMap((m) => {
      const d = wsToDisplay(m, user, role)
      return d && !historyIds.has(d.id) ? [d] : []
    })
    return [...history, ...wsDisplay]
  }, [history, wsMessages, user, role])

  const statusColor =
    status === 'open'
      ? 'text-green-600'
      : status === 'connecting'
      ? 'text-yellow-600'
      : 'text-red-500'

  return (
    <div className="flex h-[calc(100vh-160px)] flex-col">
      <div className="mb-2">
        <Button variant="ghost" onClick={() => router.push(`/cases/${caseId}/report`)}>
          ← Back
        </Button>
      </div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Step 4: AI Chat
          </h2>
          <p className="text-xs text-slate-500">
            Connection:{' '}
            <span className={statusColor}>{status}</span>
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Button variant="secondary" loading={inviteLoading} onClick={handleCreateInvite}>
            Invite Someone
          </Button>
          {inviteError && (
            <p className="text-xs text-red-500">{inviteError}</p>
          )}
        </div>
      </div>

      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="mb-2 text-lg font-bold text-slate-900">Invite Link</h3>
            <p className="mb-4 text-sm text-slate-600">
              Share this link. The recipient will need to log in or register to join the case.
            </p>
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
              <span className="flex-1 break-all text-xs text-slate-700">{inviteLink}</span>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleCopy} className="flex-1">
                {copied ? 'Copied!' : 'Copy Link'}
              </Button>
              <Button variant="secondary" onClick={() => setShowInviteModal(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
      <Card className="flex flex-1 flex-col overflow-hidden p-0">
        <ChatWindow messages={allMessages} isAiTyping={isAiTyping} />
        <div className="border-t border-slate-200 p-4">
          <ChatInput onSend={handleSend} disabled={status !== 'open'} />
        </div>
      </Card>
    </div>
  )
}
