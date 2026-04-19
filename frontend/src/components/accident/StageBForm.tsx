'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

export type StageBData = {
  detailed_narrative: string
  damage_summary: string
  weather_conditions: string
  road_conditions: string
  police_report_number: string
  adjuster_name: string
  repair_shop_name: string
  follow_up_notes: string
}

export const EMPTY_STAGE_B: StageBData = {
  detailed_narrative: '',
  damage_summary: '',
  weather_conditions: '',
  road_conditions: '',
  police_report_number: '',
  adjuster_name: '',
  repair_shop_name: '',
  follow_up_notes: '',
}

export function StageBForm({
  initial,
  onSubmit,
  loading,
  error,
}: {
  initial: StageBData
  onSubmit: (data: StageBData) => Promise<void>
  loading: boolean
  error: string
}) {
  const [form, setForm] = useState<StageBData>(initial)

  function set(key: keyof StageBData, value: string) {
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
        <h3 className="font-semibold text-slate-900">Narrative</h3>
        <div className="mt-3 space-y-4">
          <Textarea
            label="Detailed Account"
            value={form.detailed_narrative}
            onChange={(e) => set('detailed_narrative', e.target.value)}
            placeholder="Describe what happened step by step…"
            rows={5}
          />
          <Textarea
            label="Damage Summary"
            value={form.damage_summary}
            onChange={(e) => set('damage_summary', e.target.value)}
            placeholder="Front bumper, hood, right headlight…"
            rows={3}
          />
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold text-slate-900">Conditions</h3>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <Input
            label="Weather"
            value={form.weather_conditions}
            onChange={(e) => set('weather_conditions', e.target.value)}
            placeholder="Clear, rainy…"
          />
          <Input
            label="Road Conditions"
            value={form.road_conditions}
            onChange={(e) => set('road_conditions', e.target.value)}
            placeholder="Dry, wet, icy…"
          />
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold text-slate-900">Contacts & Records</h3>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <Input
            label="Police Report #"
            value={form.police_report_number}
            onChange={(e) => set('police_report_number', e.target.value)}
          />
          <Input
            label="Adjuster Name"
            value={form.adjuster_name}
            onChange={(e) => set('adjuster_name', e.target.value)}
          />
          <Input
            label="Repair Shop"
            value={form.repair_shop_name}
            onChange={(e) => set('repair_shop_name', e.target.value)}
          />
        </div>
      </Card>

      <Card>
        <Textarea
          label="Follow-up Notes"
          value={form.follow_up_notes}
          onChange={(e) => set('follow_up_notes', e.target.value)}
          placeholder="Anything else to track…"
          rows={3}
        />
      </Card>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}
      <div className="flex justify-end">
        <Button type="submit" loading={loading}>
          Save & Continue →
        </Button>
      </div>
    </form>
  )
}
