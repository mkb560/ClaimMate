import { PartyComparisonRow } from '@/lib/api'

export function PartyTable({ rows }: { rows: PartyComparisonRow[] }) {
  return (
    <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-3 py-2 text-left font-medium text-slate-700">
              Field
            </th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">
              You
            </th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">
              Other Party
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field_label} className="border-t border-slate-200">
              <td className="px-3 py-2 font-medium text-slate-700">
                {row.field_label}
              </td>
              <td className="px-3 py-2 text-slate-900">{row.owner_value}</td>
              <td className="px-3 py-2 text-slate-900">
                {row.other_party_value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
