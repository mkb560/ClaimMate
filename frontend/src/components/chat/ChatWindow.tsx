'use client'

import { useEffect, useRef } from 'react'
import { ChatBubble, DisplayMessage } from './ChatBubble'

export function ChatWindow({ messages }: { messages: DisplayMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
      <div ref={bottomRef} />
    </div>
  )
}
