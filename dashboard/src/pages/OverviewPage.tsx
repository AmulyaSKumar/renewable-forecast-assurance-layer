import { Activity, AlertTriangle, CircleGauge, MapPinned } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ForecastChart } from '../components/ForecastChart'
import { MetricCard } from '../components/MetricCard'
import type { ClusterForecastPoint, ClusterMeta, PlantMeta, SummaryResponse } from '../types'

type OverviewPageProps = {
  summary: SummaryResponse | null
  plants: PlantMeta[]
  clusters: ClusterMeta[]
  selectedClusterId: string
  clusterForecast: ClusterForecastPoint[]
  onClusterChange: (clusterId: string) => void
}

export function OverviewPage({
  summary,
  plants,
  clusters,
  selectedClusterId,
  clusterForecast,
  onClusterChange,
}: OverviewPageProps) {
  const activeCluster = clusters.find((cluster) => cluster.cluster_id === selectedClusterId)
  const latest = clusterForecast.at(-1)
  const clusterPlants = plants.filter((plant) => plant.cluster_id === selectedClusterId)

  return (
    <div className="page-grid">
      <section className="hero-surface">
        <div className="hero-copy">
          <span className="eyebrow">KREDL / KSPDCL sandbox prototype</span>
          <h1>Renewable Forecast Assurance Layer</h1>
          <p>
            Hourly solar and wind generation forecasts with uncertainty, confidence scoring, and plant-to-cluster
            drilldowns for Karnataka grid planning.
          </p>
        </div>
        <div className="hero-status">
          <div className="hero-status__item">
            <span>Selected cluster</span>
            <strong>{activeCluster?.cluster_name ?? '--'}</strong>
          </div>
          <div className="hero-status__item">
            <span>Latest actual timestamp</span>
            <strong>
              {summary
                ? new Date(summary.health.latest_actual_timestamp).toLocaleString('en-IN', {
                    day: '2-digit',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : '--'}
            </strong>
          </div>
        </div>
      </section>

      <section className="metric-grid">
        <MetricCard
          label="Model MAE"
          value={summary ? `${summary.evaluation.model.mae.toFixed(1)} MW` : '--'}
          detail="Median forecast error on the validation window."
          icon={<CircleGauge size={16} />}
        />
        <MetricCard
          label="P10-P90 Coverage"
          value={summary ? `${(summary.evaluation.model.coverage_p10_p90 * 100).toFixed(0)}%` : '--'}
          detail="Share of observations inside the forecast band."
          tone="good"
          icon={<Activity size={16} />}
        />
        <MetricCard
          label="Telemetry Availability"
          value={summary ? `${(summary.health.telemetry_availability_rate * 100).toFixed(1)}%` : '--'}
          detail="Observed hourly generation records available to the model."
          tone="good"
          icon={<MapPinned size={16} />}
        />
        <MetricCard
          label="Data Quality Issues"
          value={summary ? `${(summary.health.data_quality_issue_rate * 100).toFixed(1)}%` : '--'}
          detail="Missing telemetry or weather inputs across the sandbox."
          tone="warn"
          icon={<AlertTriangle size={16} />}
        />
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <h3>Cluster outlook</h3>
            <p>Select a renewable cluster to review next-day availability and confidence.</p>
          </div>
        </div>
        <div className="chip-row">
          {clusters.map((cluster) => (
            <button
              key={cluster.cluster_id}
              className={cluster.cluster_id === selectedClusterId ? 'chip chip--active' : 'chip'}
              onClick={() => onClusterChange(cluster.cluster_id)}
            >
              {cluster.cluster_name}
            </button>
          ))}
        </div>
        {latest ? (
          <div className="cluster-highlights">
            <div>
              <span>Forecast median</span>
              <strong>{latest.forecast_p50_mw.toFixed(1)} MW</strong>
            </div>
            <div>
              <span>Confidence range</span>
              <strong>
                {latest.forecast_p10_mw.toFixed(1)} - {latest.forecast_p90_mw.toFixed(1)} MW
              </strong>
            </div>
            <div>
              <span>Reliability</span>
              <strong>{latest.reliability_score.toFixed(0)} / 100</strong>
            </div>
          </div>
        ) : null}
      </section>

      <ForecastChart data={clusterForecast} title="Cluster next-24h forecast" />

      <section className="panel">
        <div className="panel__header">
          <div>
            <h3>Plant drilldown</h3>
            <p>Move from a cluster planning view to asset-level forecast accountability.</p>
          </div>
        </div>
        <div className="plant-table">
          {clusterPlants.map((plant) => (
            <Link key={plant.plant_id} to={`/plants/${plant.plant_id}`} className="plant-row">
              <div>
                <strong>{plant.plant_name}</strong>
                <span>
                  {plant.asset_type} · {plant.capacity_mw} MW
                </span>
              </div>
              <span className="plant-row__cta">Open</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
