import type { ReactNode } from 'react'

type MetricCardProps = {
  label: string
  value: string
  detail?: string
  tone?: 'neutral' | 'good' | 'warn'
  icon?: ReactNode
}

export function MetricCard({ label, value, detail, tone = 'neutral', icon }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <div className="metric-card__header">
        <span>{label}</span>
        {icon ? <span>{icon}</span> : null}
      </div>
      <strong>{value}</strong>
      {detail ? <p>{detail}</p> : null}
    </article>
  )
}
