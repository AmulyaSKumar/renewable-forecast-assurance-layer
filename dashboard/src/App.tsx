import { BarChart3, Database, LineChart, LoaderCircle, RadioTower, Zap } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import { api } from './api'
import { OverviewPage } from './pages/OverviewPage'
import { PlantPage } from './pages/PlantPage'
import type {
  ClusterForecastPoint,
  ClusterMeta,
  ComparisonPoint,
  PlantForecastPoint,
  PlantMeta,
  SummaryResponse,
} from './types'

function PlantRoute({ plants, comparisons }: { plants: PlantMeta[]; comparisons: ComparisonPoint[] }) {
  const { plantId } = useParams()
  const [forecast, setForecast] = useState<PlantForecastPoint[]>([])

  useEffect(() => {
    if (!plantId) return
    api.plantForecast(plantId).then(setForecast).catch(() => setForecast([]))
  }, [plantId])

  const plant = plants.find((entry) => entry.plant_id === plantId)
  const comparison = useMemo(() => comparisons.filter((row) => row.plant_id === plantId), [comparisons, plantId])

  return <PlantPage plant={plant} forecast={forecast} comparison={comparison} />
}

export default function App() {
  const navigate = useNavigate()
  const [summary, setSummary] = useState<SummaryResponse | null>(null)
  const [plants, setPlants] = useState<PlantMeta[]>([])
  const [clusters, setClusters] = useState<ClusterMeta[]>([])
  const [clusterForecast, setClusterForecast] = useState<ClusterForecastPoint[]>([])
  const [comparisons, setComparisons] = useState<ComparisonPoint[]>([])
  const [selectedClusterId, setSelectedClusterId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function boot() {
      try {
        const [summaryData, plantsData, clustersData, comparisonData] = await Promise.all([
          api.summary(),
          api.plants(),
          api.clusters(),
          api.comparison(),
        ])
        setSummary(summaryData)
        setPlants(plantsData)
        setClusters(clustersData)
        setComparisons(comparisonData)
        setSelectedClusterId(clustersData[0]?.cluster_id ?? '')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load dashboard data.')
      } finally {
        setLoading(false)
      }
    }
    void boot()
  }, [])

  useEffect(() => {
    if (!selectedClusterId) return
    api.clusterForecast(selectedClusterId).then(setClusterForecast).catch(() => setClusterForecast([]))
  }, [selectedClusterId])

  const activePlantRoute = window.location.pathname.includes('/plants/')

  if (loading) {
    return (
      <main className="app-shell loading-shell">
        <LoaderCircle className="spin" />
        <p>Loading renewable forecast assurance workspace...</p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="app-shell loading-shell">
        <Database />
        <p>{error}</p>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">
            <Zap size={18} />
          </div>
          <div>
            <strong>Forecast Assurance</strong>
            <span>Karnataka renewable sandbox</span>
          </div>
        </div>

        <nav className="nav-stack">
          <Link className={!activePlantRoute ? 'nav-link nav-link--active' : 'nav-link'} to="/">
            <BarChart3 size={16} />
            Overview
          </Link>
          <button
            className={activePlantRoute ? 'nav-link nav-link--active' : 'nav-link'}
            onClick={() => {
              const fallbackPlant = plants[0]?.plant_id
              if (fallbackPlant) navigate(`/plants/${fallbackPlant}`)
            }}
          >
            <LineChart size={16} />
            Plant Drilldown
          </button>
        </nav>

        <section className="sidebar-panel">
          <span className="sidebar-panel__label">Scope</span>
          <ul>
            <li>{summary?.plant_count ?? plants.length} plants</li>
            <li>{summary?.cluster_count ?? clusters.length} clusters</li>
            <li>Day-ahead and intra-day ready</li>
          </ul>
        </section>

        <section className="sidebar-panel">
          <span className="sidebar-panel__label">Outputs</span>
          <ul>
            <li>P10 / P50 / P90 bands</li>
            <li>Reliability scores</li>
            <li>Forecast-change explanations</li>
          </ul>
        </section>

        <section className="sidebar-panel sidebar-panel--status">
          <RadioTower size={16} />
          <div>
            <strong>Read-only forecasting layer</strong>
            <p>The prototype works beside existing systems and only consumes sandbox data.</p>
          </div>
        </section>
      </aside>

      <section className="content-shell">
        <Routes>
          <Route
            path="/"
            element={
              <OverviewPage
                summary={summary}
                plants={plants}
                clusters={clusters}
                selectedClusterId={selectedClusterId}
                clusterForecast={clusterForecast}
                onClusterChange={setSelectedClusterId}
              />
            }
          />
          <Route path="/plants/:plantId" element={<PlantRoute plants={plants} comparisons={comparisons} />} />
        </Routes>
      </section>
    </main>
  )
}
