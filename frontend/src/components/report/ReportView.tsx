import { GenerateReportResponse } from '@/lib/api'
import { Card } from '@/components/ui/Card'
import { PartyTable } from './PartyTable'
import { TimelineList } from './TimelineList'

export function ReportView({ report }: { report: GenerateReportResponse }) {
  const r = report.report_payload
  return (
    <div className="space-y-4">
      <Card>
        <h3 className="text-lg font-bold text-slate-900">{r.report_title}</h3>
        <p className="mt-2 text-sm text-slate-700">{r.accident_summary}</p>
        {r.location_summary && (
          <p className="mt-1 text-sm text-slate-600">📍 {r.location_summary}</p>
        )}
      </Card>

      {r.detailed_narrative && (
        <Card>
          <h4 className="font-semibold text-slate-900">Narrative</h4>
          <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
            {r.detailed_narrative}
          </p>
        </Card>
      )}

      {r.timeline_entries && r.timeline_entries.length > 0 && (
        <Card>
          <h4 className="font-semibold text-slate-900">Timeline</h4>
          <TimelineList entries={r.timeline_entries} />
        </Card>
      )}

      {r.party_comparison_rows && r.party_comparison_rows.length > 0 && (
        <Card>
          <h4 className="font-semibold text-slate-900">Party Comparison</h4>
          <PartyTable rows={r.party_comparison_rows} />
        </Card>
      )}

      {r.damage_summary && (
        <Card>
          <h4 className="font-semibold text-slate-900">Damage</h4>
          <p className="mt-2 text-sm text-slate-700">{r.damage_summary}</p>
        </Card>
      )}

      {r.missing_items && r.missing_items.length > 0 && (
        <Card>
          <h4 className="font-semibold text-slate-900">Still Needed</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {r.missing_items.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
