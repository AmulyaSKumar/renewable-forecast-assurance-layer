from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"


@dataclass(frozen=True)
class ClusterSpec:
    cluster_id: str
    label: str
    lat: float
    lon: float


CLUSTERS = [
    ClusterSpec("CL-BLR-SOLAR", "Bengaluru Rural Solar Belt", 13.10, 77.55),
    ClusterSpec("CL-KLB-SOLAR", "Kalyana Karnataka Solar Belt", 17.32, 76.83),
    ClusterSpec("CL-CKM-WIND", "Chitradurga Wind Corridor", 14.22, 76.40),
    ClusterSpec("CL-BTM-WIND", "Ballari-Tumakuru Wind Corridor", 15.18, 76.95),
]


def _season_factor(day_of_year: np.ndarray) -> np.ndarray:
    return 0.5 + 0.5 * np.sin((day_of_year - 80) * 2 * np.pi / 365.25)


def _solar_profile(hour: np.ndarray, day_of_year: np.ndarray) -> np.ndarray:
    daylight = np.clip(np.sin((hour - 6) * np.pi / 12), 0, None)
    seasonal = 0.78 + 0.18 * _season_factor(day_of_year)
    return daylight * seasonal


def _wind_curve(speed: np.ndarray) -> np.ndarray:
    cut_in = np.clip((speed - 3.0) / 9.0, 0, 1)
    rated = np.clip(speed / 12.0, 0, 1)
    return np.where(speed < 12.0, cut_in**1.8, np.clip(1.08 - (speed - 12.0) * 0.04, 0.25, 1.0)) * rated


def _make_plants() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rng = np.random.default_rng(42)
    for idx in range(10):
        cluster = CLUSTERS[idx % 2]
        rows.append(
            {
                "plant_id": f"SOLAR-{idx + 1:02d}",
                "plant_name": f"Solar Plant {idx + 1:02d}",
                "cluster_id": cluster.cluster_id,
                "cluster_name": cluster.label,
                "asset_type": "solar",
                "capacity_mw": int(rng.integers(45, 125)),
                "lat": cluster.lat + rng.normal(0, 0.12),
                "lon": cluster.lon + rng.normal(0, 0.12),
            }
        )
    for idx in range(10):
        cluster = CLUSTERS[2 + idx % 2]
        rows.append(
            {
                "plant_id": f"WIND-{idx + 1:02d}",
                "plant_name": f"Wind Plant {idx + 1:02d}",
                "cluster_id": cluster.cluster_id,
                "cluster_name": cluster.label,
                "asset_type": "wind",
                "capacity_mw": int(rng.integers(60, 180)),
                "lat": cluster.lat + rng.normal(0, 0.18),
                "lon": cluster.lon + rng.normal(0, 0.18),
            }
        )
    return pd.DataFrame(rows)


def generate_synthetic_data(force: bool = False) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SYNTHETIC_DIR.mkdir(exist_ok=True)

    plants_path = DATA_DIR / "plants.csv"
    weather_path = DATA_DIR / "weather.csv"
    generation_path = DATA_DIR / "generation.csv"

    if not force and plants_path.exists() and weather_path.exists() and generation_path.exists():
        return

    plants = _make_plants()
    plants.to_csv(plants_path, index=False)

    timestamps = pd.date_range("2025-01-01 00:00:00", "2026-01-02 23:00:00", freq="h")
    history_end = pd.Timestamp("2025-12-31 23:00:00")
    hours = timestamps.hour.to_numpy()
    day_of_year = timestamps.dayofyear.to_numpy()
    month = timestamps.month.to_numpy()

    rng = np.random.default_rng(7)
    weather_rows: list[pd.DataFrame] = []
    generation_rows: list[pd.DataFrame] = []

    monsoon = np.isin(month, [6, 7, 8, 9]).astype(float)
    solar_profile = _solar_profile(hours, day_of_year)
    thermal_base = 24 + 8 * _season_factor(day_of_year) + 4 * np.sin((hours - 7) * 2 * np.pi / 24)

    for _, plant in plants.iterrows():
        regional_bias = np.sin((plant["lat"] + plant["lon"]) * np.pi / 90)
        cloud_cover = np.clip(
            0.18
            + 0.52 * monsoon
            + 0.12 * np.sin(day_of_year * 2 * np.pi / 11 + regional_bias)
            + 0.08 * np.cos(hours * 2 * np.pi / 24)
            + rng.normal(0, 0.09, len(timestamps)),
            0,
            1,
        )
        irradiation = np.clip(
            980 * solar_profile * (1 - 0.82 * cloud_cover) + rng.normal(0, 35, len(timestamps)),
            0,
            None,
        )
        temperature = thermal_base + rng.normal(0, 1.6, len(timestamps))
        humidity = np.clip(44 + 40 * monsoon + 25 * cloud_cover + rng.normal(0, 6, len(timestamps)), 20, 98)
        wind_direction = np.mod(
            210 + 60 * np.sin(day_of_year * 2 * np.pi / 31) + rng.normal(0, 28, len(timestamps)),
            360,
        )
        wind_speed = np.clip(
            4.5
            + 2.8 * monsoon
            + 1.4 * np.cos((hours - 14) * 2 * np.pi / 24)
            + 0.9 * np.sin(day_of_year * 2 * np.pi / 18 + regional_bias)
            + rng.normal(0, 1.1, len(timestamps)),
            0.2,
            None,
        )
        gust_speed = np.clip(wind_speed + rng.normal(1.2, 0.9, len(timestamps)), 0.2, None)

        weather_df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "plant_id": plant["plant_id"],
                "cloud_cover": np.round(cloud_cover, 4),
                "irradiation_wm2": np.round(irradiation, 2),
                "temperature_c": np.round(temperature, 2),
                "humidity_pct": np.round(humidity, 2),
                "wind_speed_ms": np.round(wind_speed, 2),
                "wind_direction_deg": np.round(wind_direction, 2),
                "gust_speed_ms": np.round(gust_speed, 2),
            }
        )

        history_mask = timestamps <= history_end
        capacity = float(plant["capacity_mw"])
        issue_sample = rng.random(history_mask.sum())
        curtailment_flag = (issue_sample < 0.02).astype(int)
        outage_flag = ((issue_sample >= 0.02) & (issue_sample < 0.03)).astype(int)
        telemetry_missing = ((issue_sample >= 0.03) & (issue_sample < 0.05)).astype(int)

        if plant["asset_type"] == "solar":
            temp_derate = np.clip(1 - np.maximum(temperature[history_mask] - 34, 0) * 0.006, 0.82, 1.0)
            base_output = capacity * np.clip(irradiation[history_mask] / 920, 0, 1.04) * temp_derate
            variability = np.clip(1 - cloud_cover[history_mask] * 0.58 + rng.normal(0, 0.03, history_mask.sum()), 0, 1.08)
            generation = base_output * variability
        else:
            direction_factor = 0.92 + 0.08 * np.cos(np.deg2rad(wind_direction[history_mask] - 225))
            base_output = capacity * _wind_curve(wind_speed[history_mask]) * direction_factor
            generation = base_output * np.clip(1 + rng.normal(0, 0.08, history_mask.sum()), 0.2, 1.25)

        generation = generation * np.where(curtailment_flag == 1, 0.76, 1.0)
        generation = generation * np.where(outage_flag == 1, 0.18, 1.0)
        generation = np.clip(generation, 0, capacity)

        generation_df = pd.DataFrame(
            {
                "timestamp": timestamps[history_mask],
                "plant_id": plant["plant_id"],
                "actual_mw": np.round(generation, 3),
                "curtailment_flag": curtailment_flag,
                "outage_flag": outage_flag,
                "telemetry_missing_flag": telemetry_missing,
            }
        )
        generation_df.loc[generation_df["telemetry_missing_flag"] == 1, "actual_mw"] = np.nan

        weather_rows.append(weather_df)
        generation_rows.append(generation_df)

    weather = pd.concat(weather_rows, ignore_index=True)
    generation = pd.concat(generation_rows, ignore_index=True)

    for frame, name in [(plants, "plants"), (weather, "weather"), (generation, "generation")]:
        frame.to_csv(SYNTHETIC_DIR / f"{name}.csv", index=False)

    weather.to_csv(weather_path, index=False)
    generation.to_csv(generation_path, index=False)


if __name__ == "__main__":
    generate_synthetic_data(force=True)
