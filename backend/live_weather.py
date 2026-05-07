from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "live_cache"
OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
INDIA_TZ_OFFSET = timedelta(hours=5, minutes=30)


@dataclass(frozen=True)
class LiveWeatherResult:
    frame: pd.DataFrame
    source: str
    status: str


def _build_request_url(lat: float, lon: float, forecast_hours: int) -> str:
    query = {
        "latitude": round(lat, 5),
        "longitude": round(lon, 5),
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "cloud_cover",
                "shortwave_radiation",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ]
        ),
        "timezone": "Asia/Kolkata",
        "forecast_hours": forecast_hours,
        "wind_speed_unit": "ms",
    }
    return f"{OPEN_METEO_ENDPOINT}?{urlencode(query)}"


def _fetch_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _cluster_points(plants: pd.DataFrame) -> Iterable[tuple[str, str, float, float, pd.DataFrame]]:
    for (cluster_id, cluster_name), group in plants.groupby(["cluster_id", "cluster_name"]):
        yield str(cluster_id), str(cluster_name), float(group["lat"].mean()), float(group["lon"].mean()), group


def _normalize_hourly(payload: dict[str, object], cluster_name: str) -> pd.DataFrame:
    hourly = payload["hourly"]  # type: ignore[index]
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(hourly["time"]),  # type: ignore[index]
            "cluster_name": cluster_name,
            "temperature_c": hourly["temperature_2m"],  # type: ignore[index]
            "humidity_pct": hourly["relative_humidity_2m"],  # type: ignore[index]
            "cloud_cover": pd.Series(hourly["cloud_cover"], dtype="float64") / 100.0,  # type: ignore[index]
            "irradiation_wm2": hourly["shortwave_radiation"],  # type: ignore[index]
            "wind_speed_ms": hourly["wind_speed_10m"],  # type: ignore[index]
            "wind_direction_deg": hourly["wind_direction_10m"],  # type: ignore[index]
            "gust_speed_ms": hourly["wind_gusts_10m"],  # type: ignore[index]
        }
    )


def _expand_to_plants(hourly_cluster: pd.DataFrame, plants: pd.DataFrame, cluster_id: str, cluster_name: str) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for _, plant in plants.iterrows():
        expanded = hourly_cluster.copy()
        expanded["plant_id"] = plant["plant_id"]
        expanded["plant_name"] = plant["plant_name"]
        expanded["cluster_id"] = cluster_id
        expanded["cluster_name"] = cluster_name
        expanded["asset_type"] = plant["asset_type"]
        expanded["capacity_mw"] = plant["capacity_mw"]
        expanded["lat"] = plant["lat"]
        expanded["lon"] = plant["lon"]
        rows.append(expanded)
    return pd.concat(rows, ignore_index=True)


def _trim_to_next_24h(frame: pd.DataFrame) -> pd.DataFrame:
    now_india = datetime.now(timezone.utc) + INDIA_TZ_OFFSET
    next_hour = now_india.replace(minute=0, second=0, microsecond=0)
    if now_india.minute or now_india.second or now_india.microsecond:
        next_hour = next_hour + timedelta(hours=1)
    end = next_hour + timedelta(hours=23)
    trimmed = frame[(frame["timestamp"] >= pd.Timestamp(next_hour.replace(tzinfo=None))) & (frame["timestamp"] <= pd.Timestamp(end.replace(tzinfo=None)))].copy()
    return trimmed.sort_values(["plant_id", "timestamp"]).reset_index(drop=True)


def fetch_live_weather_frame(plants: pd.DataFrame, forecast_hours: int = 30) -> LiveWeatherResult:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cluster_frames: list[pd.DataFrame] = []
    for cluster_id, cluster_name, lat, lon, cluster_plants in _cluster_points(plants):
        url = _build_request_url(lat, lon, forecast_hours)
        payload = _fetch_json(url)
        hourly_cluster = _normalize_hourly(payload, cluster_name)
        cluster_frames.append(_expand_to_plants(hourly_cluster, cluster_plants, cluster_id, cluster_name))

    frame = _trim_to_next_24h(pd.concat(cluster_frames, ignore_index=True))
    cache_path = CACHE_DIR / "open_meteo_latest.csv"
    frame.to_csv(cache_path, index=False)
    return LiveWeatherResult(frame=frame, source="Open-Meteo live forecast", status="live")


def get_future_weather(plants: pd.DataFrame) -> LiveWeatherResult | None:
    mode = os.getenv("LIVE_WEATHER_MODE", "auto").strip().lower()
    if mode == "off":
        return None
    try:
        return fetch_live_weather_frame(plants)
    except Exception:
        if mode == "force":
            raise
        return None
