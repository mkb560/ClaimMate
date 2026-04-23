'use client'

import { useEffect, useRef } from 'react'
import { ChatBubble, DisplayMessage } from './ChatBubble'
import { Spinner } from '@/components/ui/Spinner'

export function ChatWindow({
  messages,
  isAiTyping = false,
}: {
  messages: DisplayMessage[]
  isAiTyping?: boolean
}) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isAiTyping])

  return (
    <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
      {messages.length === 0 && (
        <p className="py-8 text-center text-sm text-slate-400">
          Ask ClaimMate a question about your policy or claim…
        </p>
      )}
      {messages.map((msg) => (
        <ChatBubble key={msg.id} message={msg} />
      ))}
      {isAiTyping && (
        <div className="flex justify-start">
          <div className="flex items-center gap-2 rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-500">
            <Spinner className="h-4 w-4" />
            <span>ClaimMate is thinking…</span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
