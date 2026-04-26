'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { IncidentPhotoUpload } from './IncidentPhotoUpload'

type TriState = 'unknown' | 'true' | 'false'

export type StageAData = {
  occurred_at: string
  address: string
  quick_summary: string
  owner_name: string
  owner_phone: string
  owner_insurer: string
  owner_policy_number: string
  other_name: string
  other_phone: string
  other_insurer: string
  other_policy_number: string
  injuries_reported: TriState
  police_called: TriState
  drivable: TriState
  tow_requested: TriState
}

export const EMPTY_STAGE_A: StageAData = {
  occurred_at: '',
  address: '',
  quick_summary: '',
  owner_name: '',
  owner_phone: '',
  owner_insurer: '',
  owner_policy_number: '',
  other_name: '',
  other_phone: '',
  other_insurer: '',
  other_policy_number: '',
  injuries_reported: 'unknown',
  police_called: 'unknown',
  drivable: 'unknown',
  tow_requested: 'unknown',
}

function TriStateToggle({
  label,
  value,
  onChange,
}: {
  label: string
  value: TriState
  onChange: (v: TriState) => void
}) {
  const opts: { val: TriState; display: string }[] = [
    { val: 'unknown', display: '?' },
    { val: 'true', display: 'Yes' },
    { val: 'false', display: 'No' },
  ]
  return (
    <div>
      <p className="mb-1 text-sm font-medium text-slate-700">{label}</p>
      <div className="flex gap-2">
        {opts.map(({ val, display }) => (
          <button
            key={val}
            type="button"
            onClick={() => onChange(val)}
            className={`rounded-lg border px-3 py-1.5 text-sm transition ${
              value === val
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {display}
          </button>
        ))}
      </div>
    </div>
  )
}

export function StageAForm({
  caseId,
  initial,
  onSubmit,
  loading,
  error,
  readOnly = false,
}: {
  caseId: string
  initial: StageAData
  onSubmit: (data: StageAData) => Promise<void>
  loading: boolean
  error: string
  readOnly?: boolean
}) {
  const [form, setForm] = useState<StageAData>(initial)

  function set<K extends keyof StageAData>(key: K, value: StageAData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault()
        await onSubmit(form)
      }}
      className="space-y-6"
    >
      <Card>
        <h3 className="font-semibold text-slate-900">Accident Details</h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Input
            label="Date & Time"
            type="datetime-local"
            value={form.occurred_at}
            onChange={(e) => set('occurred_at', e.target.value)}
          />
          <Input
            label="Location"
            value={form.address}
            onChange={(e) => set('address', e.target.value)}
            placeholder="123 Main St, Los Angeles, CA"
          />
        </div>
        <div className="mt-4">
          <Textarea
            label="Quick Summary"
            value={form.quick_summary}
            onChange={(e) => set('quick_summary', e.target.value)}
            placeholder="Rear-end collision at a red light…"
            rows={3}
          />
        </div>
      </Card>

      <div className="grid gap-6 sm:grid-cols-2">
        <Card>
          <h3 className="font-semibold text-slate-900">Your Information</h3>
          <div className="mt-3 space-y-3">
            <Input
              label="Name"
              value={form.owner_name}
              onChange={(e) => set('owner_name', e.target.value)}
              placeholder="Full name"
            />
            <Input
              label="Phone"
              value={form.owner_phone}
              onChange={(e) => set('owner_phone', e.target.value)}
              placeholder="+1 (555) 000-0000"
            />
            <Input
              label="Insurer"
              value={form.owner_insurer}
              onChange={(e) => set('owner_insurer', e.target.value)}
              placeholder="Allstate"
            />
            <Input
              label="Policy #"
              value={form.owner_policy_number}
              onChange={(e) => set('owner_policy_number', e.target.value)}
            />
          </div>
        </Card>
        <Card>
          <h3 className="font-semibold text-slate-900">Other Party</h3>
          <div className="mt-3 space-y-3">
            <Input
              label="Name"
              value={form.other_name}
              onChange={(e) => set('other_name', e.target.value)}
              placeholder="Full name"
            />
            <Input
              label="Phone"
              value={form.other_phone}
              onChange={(e) => set('other_phone', e.target.value)}
              placeholder="+1 (555) 000-0000"
            />
            <Input
              label="Insurer"
              value={form.other_insurer}
              onChange={(e) => set('other_insurer', e.target.value)}
              placeholder="Progressive"
            />
            <Input
              label="Policy #"
              value={form.other_policy_number}
              onChange={(e) => set('other_policy_number', e.target.value)}
            />
          </div>
        </Card>
      </div>

      <Card>
        <h3 className="font-semibold text-slate-900">Quick Facts</h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <TriStateToggle
            label="Injuries reported?"
            value={form.injuries_reported}
            onChange={(v) => set('injuries_reported', v)}
          />
          <TriStateToggle
            label="Police called?"
            value={form.police_called}
            onChange={(v) => set('police_called', v)}
          />
          <TriStateToggle
            label="Vehicle drivable?"
            value={form.drivable}
            onChange={(v) => set('drivable', v)}
          />
          <TriStateToggle
            label="Tow requested?"
            value={form.tow_requested}
            onChange={(v) => set('tow_requested', v)}
          />
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold text-slate-900">Incident Photos</h3>
        <p className="mt-1 text-xs text-slate-500">Upload photos right after the accident — JPG, PNG, or WEBP, max 10 MB each.</p>
        <div className="mt-4">
          <IncidentPhotoUpload caseId={caseId} />
        </div>
      </Card>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}
      {readOnly ? (
        <p className="text-center text-sm text-slate-500">
          View only — you don&apos;t have permission to edit this.
        </p>
      ) : (
        <div className="flex justify-end">
          <Button type="submit" loading={loading}>
            Save & Continue →
          </Button>
        </div>
      )}
    </form>
  )
}
