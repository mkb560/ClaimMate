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

  function handlePrimaryAction() {
    if (!file) {
      inputRef.current?.click()
      return
    }
    void handleUpload(file)
  }

  async function handleUpload(selectedFile: File) {
    setLoading(true)
    try {
      await onUpload(selectedFile)
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
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          aria-label="Policy PDF file"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="min-h-12 flex-1 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-left text-sm text-slate-600 transition hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700"
        >
          {file ? (
            <>
              <span className="font-medium text-slate-900">{file.name}</span>
              <span className="ml-2 text-xs text-slate-500">Click to change</span>
            </>
          ) : (
            'No PDF selected'
          )}
        </button>
        <Button
          variant="secondary"
          loading={loading}
          onClick={handlePrimaryAction}
        >
          {file ? 'Upload' : 'Choose PDF'}
        </Button>
      </div>
    </Card>
  )
}
