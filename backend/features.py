from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


TARGET = "actual_mw"


@dataclass
class FeatureBundle:
    frame: pd.DataFrame
    feature_columns: list[str]
    fill_values: dict[str, float]


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["hour"] = enriched["timestamp"].dt.hour
    enriched["day_of_week"] = enriched["timestamp"].dt.dayofweek
    enriched["month"] = enriched["timestamp"].dt.month
    enriched["day_of_year"] = enriched["timestamp"].dt.dayofyear
    enriched["hour_sin"] = np.sin(2 * np.pi * enriched["hour"] / 24)
    enriched["hour_cos"] = np.cos(2 * np.pi * enriched["hour"] / 24)
    enriched["doy_sin"] = np.sin(2 * np.pi * enriched["day_of_year"] / 365.25)
    enriched["doy_cos"] = np.cos(2 * np.pi * enriched["day_of_year"] / 365.25)
    enriched["is_monsoon"] = enriched["month"].isin([6, 7, 8, 9]).astype(int)
    enriched["asset_type_code"] = (enriched["asset_type"] == "wind").astype(int)
    cluster_codes = {cluster_id: idx for idx, cluster_id in enumerate(sorted(enriched["cluster_id"].dropna().unique()))}
    enriched["cluster_code"] = enriched["cluster_id"].map(cluster_codes).fillna(-1).astype(int)
    return enriched


def add_weather_features(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    radians = np.deg2rad(enriched["wind_direction_deg"])
    enriched["wind_u"] = enriched["wind_speed_ms"] * np.cos(radians)
    enriched["wind_v"] = enriched["wind_speed_ms"] * np.sin(radians)
    enriched["cloud_irradiance_interaction"] = enriched["cloud_cover"] * enriched["irradiation_wm2"]
    enriched["thermal_stress"] = np.clip(enriched["temperature_c"] - 34, 0, None)
    enriched["gust_ratio"] = enriched["gust_speed_ms"] / np.clip(enriched["wind_speed_ms"], 0.5, None)
    return enriched


def add_generation_history_features(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    group = enriched.groupby("plant_id", group_keys=False)
    enriched["lag_1h"] = group["actual_mw_filled"].shift(1)
    enriched["lag_2h"] = group["actual_mw_filled"].shift(2)
    enriched["lag_24h"] = group["actual_mw_filled"].shift(24)
    enriched["rolling_6h"] = group["actual_mw_filled"].shift(1).rolling(6, min_periods=1).mean().reset_index(level=0, drop=True)
    enriched["rolling_24h"] = group["actual_mw_filled"].shift(1).rolling(24, min_periods=1).mean().reset_index(level=0, drop=True)
    enriched["ramp_prev"] = enriched["lag_1h"] - enriched["lag_2h"]
    enriched["capacity_factor_lag_1h"] = enriched["lag_1h"] / enriched["capacity_mw"]
    enriched["capacity_factor_24h"] = enriched["rolling_24h"] / enriched["capacity_mw"]
    enriched["availability_rolling_24h"] = group["availability_flag"].shift(1).rolling(24, min_periods=1).mean().reset_index(level=0, drop=True)
    enriched["quality_rolling_24h"] = group["data_quality_flag"].shift(1).rolling(24, min_periods=1).mean().reset_index(level=0, drop=True)
    return enriched


def build_training_features(frame: pd.DataFrame) -> FeatureBundle:
    enriched = add_generation_history_features(add_weather_features(add_time_features(frame)))
    feature_columns = [
        "capacity_mw",
        "lat",
        "lon",
        "asset_type_code",
        "cluster_code",
        "hour",
        "day_of_week",
        "month",
        "day_of_year",
        "hour_sin",
        "hour_cos",
        "doy_sin",
        "doy_cos",
        "is_monsoon",
        "cloud_cover",
        "irradiation_wm2",
        "temperature_c",
        "humidity_pct",
        "wind_speed_ms",
        "wind_direction_deg",
        "gust_speed_ms",
        "wind_u",
        "wind_v",
        "cloud_irradiance_interaction",
        "thermal_stress",
        "gust_ratio",
        "lag_1h",
        "lag_24h",
        "rolling_6h",
        "rolling_24h",
        "ramp_prev",
        "capacity_factor_lag_1h",
        "capacity_factor_24h",
        "availability_rolling_24h",
        "quality_rolling_24h",
        "curtailment_flag",
        "outage_flag",
        "telemetry_missing_flag",
        "data_quality_flag",
    ]
    trainable = enriched.dropna(subset=["lag_1h", "lag_24h", "actual_mw"]).copy()
    fill_values = {column: float(trainable[column].median()) for column in feature_columns}
    trainable[feature_columns] = trainable[feature_columns].fillna(fill_values)
    return FeatureBundle(frame=trainable, feature_columns=feature_columns, fill_values=fill_values)
