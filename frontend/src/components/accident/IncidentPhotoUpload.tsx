'use client'

import { useEffect, useRef, useState } from 'react'
import Image from 'next/image'
import { uploadIncidentPhoto, fetchIncidentPhotoBlobUrl, getCaseSnapshot } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'

type PhotoStatus = 'uploading' | 'done' | 'error'

type PhotoItem = {
  id: string
  previewUrl: string
  name: string
  status: PhotoStatus
  errorMsg?: string
}

type Section = {
  label: string
  category: string
  photos: PhotoItem[]
}

const INITIAL_SECTIONS: Section[] = [
  { label: 'My Vehicle Damage', category: 'owner_damage', photos: [] },
  { label: 'Scene / Overview', category: 'overview', photos: [] },
  { label: "Other Party's Vehicle", category: 'other_damage', photos: [] },
  { label: 'Other', category: 'other', photos: [] },
]

export function IncidentPhotoUpload({ caseId }: { caseId: string }) {
  const [sections, setSections] = useState<Section[]>(INITIAL_SECTIONS)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    let cancelled = false
    async function loadExisting() {
      try {
        const snap = await getCaseSnapshot(caseId)
        const attachments: { photo_id: string; category: string }[] =
          (snap?.stage_a as Record<string, unknown> | undefined)?.photo_attachments as { photo_id: string; category: string }[] ?? []
        if (!Array.isArray(attachments) || attachments.length === 0) return

        const loaded: { sectionIdx: number; photo: PhotoItem }[] = await Promise.all(
          attachments.map(async (att) => {
            const sectionIdx = INITIAL_SECTIONS.findIndex((s) => s.category === att.category)
            const idx = sectionIdx === -1 ? INITIAL_SECTIONS.length - 1 : sectionIdx
            try {
              const blobUrl = await fetchIncidentPhotoBlobUrl(caseId, att.photo_id)
              return {
                sectionIdx: idx,
                photo: { id: att.photo_id, previewUrl: blobUrl, name: att.photo_id, status: 'done' as PhotoStatus },
              }
            } catch {
              return null
            }
          })
        ).then((results) => results.filter((r): r is { sectionIdx: number; photo: PhotoItem } => r !== null))

        if (cancelled) return
        setSections((prev) =>
          prev.map((s, i) => {
            const incoming = loaded.filter((x) => x.sectionIdx === i).map((x) => x.photo)
            if (incoming.length === 0) return s
            return { ...s, photos: incoming }
          })
        )
      } catch {
        // silently ignore — blank sections are fine
      }
    }
    loadExisting()
    return () => { cancelled = true }
  }, [caseId])

  function updateSection(idx: number, updater: (s: Section) => Section) {
    setSections((prev) => prev.map((s, i) => (i === idx ? updater(s) : s)))
  }

  async function handleFiles(sectionIdx: number, files: FileList) {
    const section = sections[sectionIdx]
    const newPhotos: PhotoItem[] = Array.from(files).map((file) => ({
      id: `${Date.now()}-${Math.random()}`,
      previewUrl: URL.createObjectURL(file),
      name: file.name,
      status: 'uploading' as PhotoStatus,
    }))

    updateSection(sectionIdx, (s) => ({ ...s, photos: [...s.photos, ...newPhotos] }))

    for (let i = 0; i < newPhotos.length; i++) {
      const photo = newPhotos[i]
      const file = files[i]
      try {
        await uploadIncidentPhoto(caseId, file, section.category)
        updateSection(sectionIdx, (s) => ({
          ...s,
          photos: s.photos.map((p) =>
            p.id === photo.id ? { ...p, status: 'done' } : p
          ),
        }))
      } catch (err) {
        updateSection(sectionIdx, (s) => ({
          ...s,
          photos: s.photos.map((p) =>
            p.id === photo.id
              ? { ...p, status: 'error', errorMsg: err instanceof Error ? err.message : 'Upload failed' }
              : p
          ),
        }))
      }
    }
  }

  function removePhoto(sectionIdx: number, photoId: string) {
    updateSection(sectionIdx, (s) => ({
      ...s,
      photos: s.photos.filter((p) => p.id !== photoId),
    }))
  }

  return (
    <div className="space-y-4">
      {sections.map((section, idx) => (
        <div key={section.category}>
          <p className="mb-2 text-sm font-medium text-slate-700">{section.label}</p>
          <div className="flex flex-wrap gap-3">
            {section.photos.map((photo) => (
              <div key={photo.id} className="relative h-24 w-24 shrink-0">
                <Image
                  src={photo.previewUrl}
                  alt={photo.name}
                  width={96}
                  height={96}
                  unoptimized
                  className="h-full w-full rounded-xl object-cover border border-slate-200"
                />
                {photo.status === 'uploading' && (
                  <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-black/40">
                    <Spinner className="h-5 w-5 text-white" />
                  </div>
                )}
                {photo.status === 'error' && (
                  <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-red-500/70" title={photo.errorMsg}>
                    <span className="text-xs font-bold text-white">✕</span>
                  </div>
                )}
                {photo.status !== 'uploading' && (
                  <button
                    type="button"
                    onClick={() => removePhoto(idx, photo.id)}
                    className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-slate-600 text-white text-xs hover:bg-red-500 transition-colors"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={() => inputRefs.current[idx]?.click()}
              className="flex h-24 w-24 shrink-0 flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed border-slate-300 text-slate-400 hover:border-blue-400 hover:text-blue-500 transition-colors"
            >
              <span className="text-2xl leading-none">+</span>
              <span className="text-xs">Add photo</span>
            </button>
          </div>
          <input
            ref={(el) => { inputRefs.current[idx] = el }}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) handleFiles(idx, e.target.files)
              e.target.value = ''
            }}
          />
        </div>
      ))}
    </div>
  )
}
