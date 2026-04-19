type Entry = { label: string; timestamp: string; note: string | null }

export function TimelineList({ entries }: { entries: Entry[] }) {
  return (
    <ol className="mt-3 space-y-4">
      {entries.map((e, i) => (
        <li key={i} className="flex gap-3">
          <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-600">
            {i + 1}
          </div>
          <div>
            <p className="text-sm font-medium text-slate-900">{e.label}</p>
            <p className="text-xs text-slate-500">
              {new Date(e.timestamp).toLocaleString()}
            </p>
            {e.note && (
              <p className="mt-0.5 text-sm text-slate-600">{e.note}</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}
