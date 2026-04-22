import { ReactNode } from 'react'

type BadgeVariant = 'pending' | 'done' | 'default'

const styles: Record<BadgeVariant, string> = {
  pending: 'bg-slate-100 text-slate-600',
  done: 'bg-green-50 text-green-700',
  default: 'bg-blue-50 text-blue-700',
}

export function Badge({
  children,
  variant = 'default',
}: {
  children: ReactNode
  variant?: BadgeVariant
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[variant]}`}
    >
      {children}
    </span>
  )
}
