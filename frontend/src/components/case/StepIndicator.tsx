const STEPS = ['Accident Basics', 'Accident Details', 'Report', 'Chat']

export function StepIndicator({ current }: { current: number }) {
  return (
    <nav className="flex items-center justify-between overflow-x-auto rounded-[2rem] border border-white/70 bg-white/85 px-6 py-4 shadow-[0_18px_45px_rgba(15,23,42,0.08)] ring-1 ring-slate-200/70 backdrop-blur">
      {STEPS.map((step, i) => (
        <div key={step} className="flex items-center">
          <div className="flex items-center gap-2">
            <div
              className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-black shadow-sm
                ${i < current ? 'bg-emerald-500 text-white shadow-emerald-500/20' : ''}
                ${i === current ? 'bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-blue-500/25' : ''}
                ${i > current ? 'bg-slate-100 text-slate-500' : ''}
              `}
            >
              {i < current ? '✓' : i + 1}
            </div>
            <span
              className={`hidden text-sm font-semibold sm:block ${
                i === current ? 'text-slate-900' : 'text-slate-500'
              }`}
            >
              {step}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className="mx-3 h-px w-8 flex-shrink-0 bg-gradient-to-r from-slate-200 to-slate-100 sm:w-14" />
          )}
        </div>
      ))}
    </nav>
  )
}
