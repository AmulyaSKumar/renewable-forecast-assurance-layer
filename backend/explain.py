from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def summarize_top_drivers(row: pd.Series) -> list[str]:
    if row["asset_type"] == "solar":
        ranked = [
            ("Cloud cover", float(row["cloud_cover"])),
            ("Irradiation", float(row["irradiation_wm2"]) / 1000),
            ("Temperature stress", float(max(row["temperature_c"] - 34, 0)) / 10),
            ("Seasonality", abs(float(row["doy_sin"]))),
        ]
    else:
        direction_alignment = 1 - abs(((float(row["wind_direction_deg"]) - 225 + 180) % 360) - 180) / 180
        ranked = [
            ("Wind speed", float(row["wind_speed_ms"]) / 14),
            ("Wind direction", float(direction_alignment)),
            ("Gust ratio", float(row["gust_speed_ms"]) / max(float(row["wind_speed_ms"]), 0.5) / 2),
            ("Seasonality", abs(float(row["doy_sin"]))),
        ]
    return [name for name, _ in sorted(ranked, key=lambda item: item[1], reverse=True)[:3]]


def driver_text(drivers: Iterable[str]) -> str:
    return ", ".join(drivers)


def reliability_score(
    p10: float,
    p50: float,
    p90: float,
    capacity_mw: float,
    quality_rolling_24h: float,
    availability_rolling_24h: float,
) -> float:
    spread = max(p90 - p10, 0.0) / max(capacity_mw, 1.0)
    spread_penalty = min(spread * 75, 50)
    quality_penalty = min(max(quality_rolling_24h, 0.0), 1.0) * 22
    availability_penalty = (1 - min(max(availability_rolling_24h, 0.0), 1.0)) * 18
    score = 100 - spread_penalty - quality_penalty - availability_penalty - (8 if p50 < 0 else 0)
    return round(float(np.clip(score, 22, 99)), 1)


def classify_confidence(score: float) -> str:
    if score >= 78:
        return "high"
    if score >= 58:
        return "medium"
    return "low"


def forecast_change_reason(current: pd.Series, previous: pd.Series) -> str:
    delta = float(current["forecast_p50_mw"] - previous["forecast_p50_mw"])
    if current["asset_type"] == "solar":
        if float(current["cloud_cover"]) > float(previous["cloud_cover"]) + 0.08:
            return "Higher cloud cover reduced expected solar generation."
        if float(current["irradiation_wm2"]) > float(previous["irradiation_wm2"]) + 40:
            return "Improved irradiation increased the solar forecast."
    else:
        if float(current["wind_speed_ms"]) > float(previous["wind_speed_ms"]) + 0.7:
            return "Stronger wind speeds lifted expected wind generation."
        if float(current["wind_speed_ms"]) < float(previous["wind_speed_ms"]) - 0.7:
            return "Weaker wind speeds lowered the wind forecast."
    if abs(delta) < 0.75:
        return "Forecast remains broadly stable versus the previous run."
    return "Updated weather and recent output trends increased the forecast." if delta > 0 else "Updated weather and recent output trends reduced the forecast."


def anomaly_hint(row: pd.Series) -> str:
    if pd.isna(row["actual_mw"]):
        return "Telemetry gap"
    if int(row.get("outage_flag", 0)) == 1:
        return "Likely outage or severe derating"
    if int(row.get("curtailment_flag", 0)) == 1:
        return "Likely curtailment event"
    if int(row.get("data_quality_flag", 0)) == 1:
        return "Potential data-quality issue"
    inside = row["actual_mw"] >= row["forecast_p10_mw"] and row["actual_mw"] <= row["forecast_p90_mw"]
    if inside:
        return "Within expected range"
    if row["asset_type"] == "solar" and float(row["actual_mw"] - row["forecast_p50_mw"]) < 0:
        return "Cloud volatility stronger than forecast"
    if row["asset_type"] == "wind" and float(row["actual_mw"] - row["forecast_p50_mw"]) < 0:
        return "Observed wind underperformed forecast"
    return "Observed output exceeded forecast envelope"
