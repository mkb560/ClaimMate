'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import { getChatMessages, ChatMessageRow } from '@/lib/api'
import { useWebSocketChat, WsMessage } from '@/hooks/useWebSocketChat'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { ChatInput } from '@/components/chat/ChatInput'
import { DisplayMessage } from '@/components/chat/ChatBubble'
import { Card } from '@/components/ui/Card'

function rowToDisplay(row: ChatMessageRow): DisplayMessage {
  return {
    id: row.id,
    role: row.message_type === 'ai' ? 'ai' : 'user',
    text: row.body_text,
    citations: row.ai_payload?.citations,
  }
}

function wsToDisplay(msg: WsMessage): DisplayMessage | null {
  if (msg.type === 'user_message') {
    return { id: msg.id, role: 'user', text: msg.message_text || '' }
  }
  if (msg.type === 'ai_message' && msg.payload) {
    return {
      id: msg.id,
      role: 'ai',
      text: msg.payload.text,
      citations: msg.payload.citations,
    }
  }
  if (msg.type === 'system' && msg.event) {
    return { id: msg.id, role: 'system', text: msg.event }
  }
  return null
}

export default function ChatPage() {
  const { token } = useAuth()
  const params = useParams<{ id: string }>()
  const caseId = params.id
  const router = useRouter()
  const [history, setHistory] = useState<DisplayMessage[]>([])
  const { messages: wsMessages, sendMessage, status } = useWebSocketChat(
    caseId,
    token
  )

  useEffect(() => {
    if (!token) {
      router.replace('/login')
      return
    }
    getChatMessages(caseId)
      .then((r) => setHistory(r.messages.map(rowToDisplay)))
      .catch(() => {})
  }, [token, caseId, router])

  const allMessages = useMemo(() => {
    const historyIds = new Set(history.map((m) => m.id))
    const wsDisplay = wsMessages.flatMap((m) => {
      const d = wsToDisplay(m)
      return d && !historyIds.has(d.id) ? [d] : []
    })
    return [...history, ...wsDisplay]
  }, [history, wsMessages])

  const statusColor =
    status === 'open'
      ? 'text-green-600'
      : status === 'connecting'
      ? 'text-yellow-600'
      : 'text-red-500'

  return (
    <div className="flex h-[calc(100vh-160px)] flex-col">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Step 5: AI Chat
          </h2>
          <p className="text-xs text-slate-500">
            Connection:{' '}
            <span className={statusColor}>{status}</span>
          </p>
        </div>
      </div>
      <Card className="flex flex-1 flex-col overflow-hidden p-0">
        <ChatWindow messages={allMessages} />
        <div className="border-t border-slate-200 p-4">
          <ChatInput onSend={sendMessage} disabled={status !== 'open'} />
        </div>
      </Card>
    </div>
  )
}
