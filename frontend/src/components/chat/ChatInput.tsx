'use client'

import { KeyboardEvent, useState } from 'react'
import { Button } from '@/components/ui/Button'

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void
  disabled: boolean
}) {
  const [text, setText] = useState('')

  function handleSend() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex gap-2">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        aria-label="Chat message"
        placeholder={
          disabled
            ? 'Connecting to ClaimMate AI…'
            : 'Ask about your claim… (Enter to send, Shift+Enter for new line)'
        }
        rows={2}
        className="flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      />
      <Button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="self-end"
      >
        Send
      </Button>
    </div>
  )
}
