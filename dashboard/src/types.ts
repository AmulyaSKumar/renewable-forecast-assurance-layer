export type SummaryResponse = {
  health: {
    data_quality_issue_rate: number
    telemetry_availability_rate: number
    latest_actual_timestamp: string
    plant_count: number
    cluster_count: number
  }
  evaluation: {
    baselines: Record<string, { mae: number; rmse: number }>
    model: {
      mae: number
      rmse: number
      pinball_p10: number
      pinball_p50: number
      pinball_p90: number
      coverage_p10_p90: number
    }
  }
  cluster_count: number
  plant_count: number
}

export type PlantMeta = {
  plant_id: string
  plant_name: string
  cluster_id: string
  cluster_name: string
  asset_type: 'solar' | 'wind'
  capacity_mw: number
  lat: number
  lon: number
}

export type ClusterMeta = {
  cluster_id: string
  cluster_name: string
}

export type PlantForecastPoint = {
  timestamp: string
  plant_id: string
  plant_name: string
  cluster_id: string
  cluster_name: string
  asset_type: 'solar' | 'wind'
  capacity_mw: number
  cloud_cover: number
  irradiation_wm2: number
  wind_speed_ms: number
  wind_direction_deg: number
  forecast_p10_mw: number
  forecast_p50_mw: number
  forecast_p90_mw: number
  top_drivers: string[]
  top_driver_text: string
  reliability_score: number
  confidence_level: 'high' | 'medium' | 'low'
  forecast_change_reason: string
  forecast_delta_mw: number
}

export type ClusterForecastPoint = {
  timestamp: string
  cluster_id: string
  cluster_name: string
  forecast_p10_mw: number
  forecast_p50_mw: number
  forecast_p90_mw: number
  reliability_score: number
  solar_share: number
  confidence_level: 'high' | 'medium' | 'low'
}

export type ComparisonPoint = {
  timestamp: string
  plant_id: string
  plant_name: string
  cluster_id: string
  cluster_name: string
  asset_type: 'solar' | 'wind'
  actual_mw: number
  forecast_p10_mw: number
  forecast_p50_mw: number
  forecast_p90_mw: number
  curtailment_flag: number
  outage_flag: number
  data_quality_flag: number
  anomaly_hint: string
}
