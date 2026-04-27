import { GenerateReportResponse } from '@/lib/api'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { PartyTable } from './PartyTable'
import { TimelineList } from './TimelineList'

function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'Not provided'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatBoolean(value: boolean | null | undefined): string {
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  return 'Unknown'
}

function firstUsefulSummary(summary: string): string {
  return summary
    .replace(/^ClaimMate accident report for case [^.]+\.?\s*/i, '')
    .replace(/^Reported accident time:\s*[^.]+\.?\s*/i, '')
    .replace(/^Reported location:\s*/i, '')
    .trim()
}

function FactCard({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 text-sm font-semibold text-slate-900">{value}</p>
    </div>
  )
}

function Section({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <Card>
      <h4 className="text-sm font-bold uppercase tracking-wide text-slate-500">
        {title}
      </h4>
      <div className="mt-3">{children}</div>
    </Card>
  )
}

export function ReportView({ report }: { report: GenerateReportResponse }) {
  const r = report.report_payload
  const summary = r.damage_summary || firstUsefulSummary(r.accident_summary)
  const ownerName = r.owner_party?.name || 'Owner'
  const otherName = r.other_party?.name || 'Other party'

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden p-0">
        <div className="border-b border-slate-100 bg-gradient-to-r from-blue-50 to-white px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">
                Claim-ready accident summary
              </p>
              <h3 className="mt-1 text-2xl font-bold text-slate-950">
                Accident Report
              </h3>
            </div>
            <Badge>Case {r.case_id}</Badge>
          </div>
          {summary && (
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-700">
              {summary}
            </p>
          )}
        </div>

        <div className="grid gap-3 p-6 sm:grid-cols-2 lg:grid-cols-4">
          <FactCard label="Accident Time" value={formatDateTime(r.occurrence_time)} />
          <FactCard label="Location" value={r.location_summary || 'Not provided'} />
          <FactCard label="Police Called" value={formatBoolean(r.police_called)} />
          <FactCard label="Injuries" value={formatBoolean(r.injuries_reported)} />
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <Section title="People & Insurance">
          {r.party_comparison_rows?.length ? (
            <PartyTable rows={r.party_comparison_rows} />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <FactCard label="Owner" value={ownerName} />
              <FactCard label="Other Party" value={otherName} />
            </div>
          )}
        </Section>

        <Section title="Claim Flags">
          <div className="grid gap-3">
            <FactCard label="Vehicle Drivable" value={formatBoolean(r.drivable)} />
            <FactCard label="Tow Requested" value={formatBoolean(r.tow_requested)} />
            <FactCard
              label="Police Report #"
              value={r.police_report_number || 'Not provided'}
            />
          </div>
        </Section>
      </div>

      {r.detailed_narrative && (
        <Section title="Narrative">
          <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">
            {r.detailed_narrative}
          </p>
        </Section>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {r.timeline_entries?.length > 0 && (
          <Section title="Timeline">
            <TimelineList entries={r.timeline_entries} />
          </Section>
        )}

        <Section title="Supporting Details">
          <div className="grid gap-3">
            <FactCard
              label="Photos Attached"
              value={`${r.photo_attachments?.length || 0}`}
            />
            <FactCard
              label="Weather"
              value={r.weather_conditions || 'Not provided'}
            />
            <FactCard
              label="Road Conditions"
              value={r.road_conditions || 'Not provided'}
            />
            <FactCard
              label="Repair Shop"
              value={r.repair_shop_name || 'Not provided'}
            />
          </div>
        </Section>
      </div>

      {r.missing_items?.length > 0 && (
        <Section title="Still Needed">
          <ul className="space-y-2 text-sm text-slate-700">
            {r.missing_items.map((item, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}
