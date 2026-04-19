'use client'

import { useState } from 'react'

type CitationItem = {
  source_label: string
  source_type: string
  page_num: number | null
  section: string | null
  excerpt: string
}

export type DisplayMessage = {
  id: string
  role: 'user' | 'ai' | 'system'
  text: string
  citations?: unknown[]
}

export function ChatBubble({ message }: { message: DisplayMessage }) {
  const [showCitations, setShowCitations] = useState(false)

  if (message.role === 'system') {
    return (
      <div className="text-center">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-400">
          {message.text}
        </span>
      </div>
    )
  }

  const isUser = message.role === 'user'
  const citations = (message.citations ?? []) as CitationItem[]

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-slate-100 text-slate-900'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.text}</p>
        {!isUser && citations.length > 0 && (
          <div className="mt-2 border-t border-slate-200 pt-2">
            <button
              onClick={() => setShowCitations(!showCitations)}
              className="text-xs text-slate-500 underline hover:text-slate-700"
            >
              {showCitations ? 'Hide' : 'Show'} {citations.length} source
              {citations.length > 1 ? 's' : ''}
            </button>
            {showCitations && (
              <div className="mt-2 space-y-2">
                {citations.map((c, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-slate-200 bg-white p-2 text-xs"
                  >
                    <p className="font-medium text-slate-800">
                      {c.source_label}
                    </p>
                    <p className="text-slate-500">
                      {c.source_type === 'kb_a' ? 'Your Policy' : 'Regulation'}
                      {c.page_num ? ` · Page ${c.page_num}` : ''}
                    </p>
                    <p className="mt-1 text-slate-700">{c.excerpt}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
