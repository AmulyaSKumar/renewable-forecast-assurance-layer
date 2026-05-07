import type {
  ClusterForecastPoint,
  ClusterMeta,
  ComparisonPoint,
  PlantForecastPoint,
  PlantMeta,
  SummaryResponse,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`API request failed: ${path}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  summary: () => request<SummaryResponse>('/summary'),
  plants: () => request<PlantMeta[]>('/plants'),
  clusters: () => request<ClusterMeta[]>('/clusters'),
  plantForecast: (plantId: string) => request<PlantForecastPoint[]>(`/forecast/plant/${plantId}`),
  clusterForecast: (clusterId: string) => request<ClusterForecastPoint[]>(`/forecast/cluster/${clusterId}`),
  comparison: () => request<ComparisonPoint[]>('/compare/actual-vs-forecast'),
}
