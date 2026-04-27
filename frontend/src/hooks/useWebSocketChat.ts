'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { API_BASE_URL } from '@/lib/api'

export type WsMessage = {
  id: string
  type: 'user_message' | 'ai_message' | 'system' | 'ready' | 'pong' | 'error'
  sender_role?: string
  sender_display_name?: string
  message_text?: string
  payload?: {
    text: string
    citations: unknown[]
    trigger: string
    metadata: Record<string, unknown>
  }
  event?: string
  client_id?: string
  case_id?: string
}

export type WsStatus = 'connecting' | 'open' | 'closed' | 'error'

export type WsParticipant = {
  user_id: string
  role: string
}

export type UseWebSocketChatOptions = {
  senderRole?: string
  inviteSent?: boolean
  participants?: WsParticipant[]
}

const BASE_URL = API_BASE_URL.replace(/^http/, 'ws')

const MAX_RETRIES = 5

export function useWebSocketChat(
  caseId: string,
  token: string | null,
  options: UseWebSocketChatOptions = {}
): {
  messages: WsMessage[]
  sendMessage: (text: string) => void
  status: WsStatus
} {
  const [messages, setMessages] = useState<WsMessage[]>([])
  const [status, setStatus] = useState<WsStatus>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const senderRole = options.senderRole ?? 'owner'
  const inviteSent = options.inviteSent ?? false
  const participants = useMemo(
    () => options.participants ?? [{ user_id: 'owner-1', role: senderRole }],
    [options.participants, senderRole]
  )

  useEffect(() => {
    if (!token || !caseId) {
      setStatus('closed')
      return
    }

    let retries = 0
    let cancelled = false
    let retryTimer: ReturnType<typeof setTimeout> | null = null

    function openConnection() {
      if (cancelled) return
      const url = `${BASE_URL}/ws/cases/${caseId}?token=${encodeURIComponent(token!)}`
      const ws = new WebSocket(url)
      wsRef.current = ws
      setStatus('connecting')

      ws.onopen = () => {
        if (cancelled) return
        setStatus('open')
        retries = 0
      }

      ws.onmessage = (event) => {
        if (cancelled) return
        try {
          const msg = JSON.parse(event.data as string) as WsMessage
          if (msg.type === 'ready' || msg.type === 'pong') return
          setMessages((prev) => [
            ...prev,
            { ...msg, id: msg.id || `${Date.now()}-${Math.random()}` },
          ])
        } catch {
          // ignore malformed frames
        }
      }

      ws.onclose = () => {
        if (cancelled) return
        setStatus('closed')
        if (retries < MAX_RETRIES) {
          const delay = Math.min(3000 * 2 ** retries, 30000)
          retries++
          retryTimer = setTimeout(openConnection, delay)
        } else {
          setStatus('error')
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    openConnection()

    return () => {
      cancelled = true
      if (retryTimer !== null) clearTimeout(retryTimer)
      wsRef.current?.close()
    }
  }, [token, caseId])

  const sendMessage = useCallback((text: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(
      JSON.stringify({
        type: 'chat',
        message_text: text,
        sender_role: senderRole,
        invite_sent: inviteSent,
        participants,
        run_ai: true,
      })
    )
  }, [inviteSent, participants, senderRole])

  return { messages, sendMessage, status }
}
