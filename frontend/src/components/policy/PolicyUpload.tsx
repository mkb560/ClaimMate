'use client'

import { useRef, useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

export function PolicyUpload({
  onUpload,
}: {
  onUpload: (file: File) => Promise<void>
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleUpload() {
    if (!file) return
    setLoading(true)
    try {
      await onUpload(file)
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <h3 className="font-semibold text-slate-900">
        Upload Your Own Policy PDF
      </h3>
      <p className="mt-1 text-sm text-slate-600">
        We&apos;ll index it and answer your questions.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          aria-label="Policy PDF file"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="text-sm text-slate-600"
        />
        <Button
          variant="secondary"
          loading={loading}
          disabled={!file}
          onClick={handleUpload}
        >
          Upload
        </Button>
      </div>
    </Card>
  )
}
