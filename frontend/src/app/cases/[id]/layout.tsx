'use client'

import { usePathname } from 'next/navigation'
import { StepIndicator } from '@/components/case/StepIndicator'

const STEP_PATHS = ['stage-a', 'stage-b', 'report', 'chat']

export default function CaseLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const currentStep = STEP_PATHS.findIndex((p) => pathname.endsWith(p))

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <StepIndicator current={currentStep >= 0 ? currentStep : 0} />
        <div className="mt-6">{children}</div>
      </div>
    </div>
  )
}
