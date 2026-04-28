import Link from 'next/link'

const STEPS = [
  { label: 'Accident Basics', path: 'stage-a' },
  { label: 'Accident Details', path: 'stage-b' },
  { label: 'Report', path: 'report' },
  { label: 'Chat', path: 'chat' },
]

export function StepIndicator({
  current,
  caseId,
}: {
  current: number
  caseId: string
}) {
  return (
    <nav className="flex items-center justify-between overflow-x-auto rounded-[2rem] border border-white/70 bg-white/85 px-6 py-4 shadow-[0_18px_45px_rgba(15,23,42,0.08)] ring-1 ring-slate-200/70 backdrop-blur">
      {STEPS.map((step, i) => {
        const isCurrent = i === current

        return (
          <div key={step.path} className="flex items-center">
            <Link
              href={`/cases/${caseId}/${step.path}`}
              aria-current={isCurrent ? 'step' : undefined}
              className="group flex items-center gap-2 rounded-full px-2 py-1.5 transition hover:bg-blue-50/80 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              title={`Go to ${step.label}`}
            >
              <div
                className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-black shadow-sm transition group-hover:scale-105
                ${i < current ? 'bg-emerald-500 text-white shadow-emerald-500/20' : ''}
                ${isCurrent ? 'bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-blue-500/25' : ''}
                ${i > current ? 'bg-slate-100 text-slate-500' : ''}
              `}
              >
                {i < current ? '✓' : i + 1}
              </div>
              <span
                className={`hidden text-sm font-semibold sm:block ${
                  isCurrent ? 'text-slate-900' : 'text-slate-500'
                } transition group-hover:text-blue-700`}
              >
                {step.label}
              </span>
            </Link>
            {i < STEPS.length - 1 && (
              <div className="mx-3 h-px w-8 flex-shrink-0 bg-gradient-to-r from-slate-200 to-slate-100 sm:w-14" />
            )}
          </div>
        )
      })}
    </nav>
  )
}
