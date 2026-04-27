const STEPS = ['Accident Basics', 'Accident Details', 'Report', 'Chat']

export function StepIndicator({ current }: { current: number }) {
  return (
    <nav className="flex items-center justify-between overflow-x-auto rounded-2xl border border-slate-200 bg-white px-6 py-4 shadow-sm">
      {STEPS.map((step, i) => (
        <div key={step} className="flex items-center">
          <div className="flex items-center gap-2">
            <div
              className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold
                ${i < current ? 'bg-green-500 text-white' : ''}
                ${i === current ? 'bg-blue-600 text-white' : ''}
                ${i > current ? 'bg-slate-100 text-slate-500' : ''}
              `}
            >
              {i < current ? '✓' : i + 1}
            </div>
            <span
              className={`hidden text-sm font-medium sm:block ${
                i === current ? 'text-slate-900' : 'text-slate-500'
              }`}
            >
              {step}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className="mx-2 h-px w-6 flex-shrink-0 bg-slate-200 sm:w-10" />
          )}
        </div>
      ))}
    </nav>
  )
}
