import { AlertCircle, Gauge } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ComparisonChart, ForecastChart } from '../components/ForecastChart'
import { MetricCard } from '../components/MetricCard'
import type { ComparisonPoint, PlantForecastPoint, PlantMeta } from '../types'

type PlantPageProps = {
  plant: PlantMeta | undefined
  forecast: PlantForecastPoint[]
  comparison: ComparisonPoint[]
}

export function PlantPage({ plant, forecast, comparison }: PlantPageProps) {
  if (!plant) {
    return (
      <section className="panel">
        <div className="empty-state">
          <h2>Plant not found</h2>
          <p>Select a valid plant from the overview to inspect the forecast and assurance detail.</p>
          <Link className="text-link" to="/">
            Back to overview
          </Link>
        </div>
      </section>
    )
  }

  const latest = forecast.at(-1)
  const latestComparison = comparison.at(-1)

  return (
    <div className="page-grid">
      <section className="panel breadcrumb-panel">
        <Link className="text-link" to="/">
          Overview
        </Link>
        <span>/</span>
        <span>{plant.plant_name}</span>
      </section>

      <section className="hero-surface hero-surface--compact">
        <div className="hero-copy">
          <span className="eyebrow">{plant.cluster_name}</span>
          <h1>{plant.plant_name}</h1>
          <p>
            {plant.asset_type === 'solar'
              ? 'Solar output shifts with cloud cover, irradiation, and temperature stress.'
              : 'Wind output shifts with wind speed, direction alignment, and gust behaviour.'}
          </p>
        </div>
        <div className="hero-status">
          <div className="hero-status__item">
            <span>Asset type</span>
            <strong>{plant.asset_type}</strong>
          </div>
          <div className="hero-status__item">
            <span>Installed capacity</span>
            <strong>{plant.capacity_mw} MW</strong>
          </div>
        </div>
      </section>

      <section className="metric-grid">
        <MetricCard
          label="Forecast median"
          value={latest ? `${latest.forecast_p50_mw.toFixed(1)} MW` : '--'}
          detail="Latest P50 for the selected forecast horizon."
          icon={<Gauge size={16} />}
        />
        <MetricCard
          label="Confidence level"
          value={latest ? latest.confidence_level.toUpperCase() : '--'}
          detail={latest ? `Reliability ${latest.reliability_score.toFixed(0)} / 100` : 'No active forecast yet.'}
          tone={latest?.confidence_level === 'low' ? 'warn' : 'good'}
          icon={<AlertCircle size={16} />}
        />
        <MetricCard
          label="Forecast delta"
          value={latest ? `${latest.forecast_delta_mw.toFixed(1)} MW` : '--'}
          detail="Change compared with the previous forecast run."
        />
        <MetricCard
          label="Latest anomaly hint"
          value={latestComparison?.anomaly_hint ?? '--'}
          detail="Most recent forecast-versus-actual interpretation."
          tone="warn"
        />
      </section>

      <ForecastChart data={forecast} title="Plant next-24h forecast" />
      <ComparisonChart data={comparison.slice(-24)} title="Recent actual vs forecast" />

      <section className="panel">
        <div className="panel__header">
          <div>
            <h3>Operational explanation</h3>
            <p>Use these drivers and forecast-delta notes before balancing or reserve decisions.</p>
          </div>
        </div>
        {latest ? (
          <div className="explanation-grid">
            <div className="explanation-card">
              <span>Top drivers</span>
              <ul>
                {latest.top_drivers.map((driver) => (
                  <li key={driver}>{driver}</li>
                ))}
              </ul>
            </div>
            <div className="explanation-card">
              <span>Forecast change</span>
              <p>{latest.forecast_change_reason}</p>
            </div>
            <div className="explanation-card">
              <span>Latest actual deviation</span>
              <p>{latestComparison?.anomaly_hint ?? 'No recent actual-versus-forecast observation available.'}</p>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  )
}
