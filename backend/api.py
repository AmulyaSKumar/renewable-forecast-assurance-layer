from __future__ import annotations

import json

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .explain import anomaly_hint
from .features import build_training_features
from .generate_data import generate_synthetic_data
from .ingest import build_hourly_frame, split_history_and_future
from .predict import cluster_forecast_view, plant_forecast_view
from .train import EVAL_PATH, train_model_bundle


app = FastAPI(title="Renewable Forecast Assurance Layer", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_STATE: dict[str, object] = {}


def build_actual_vs_forecast() -> pd.DataFrame:
    frame = build_hourly_frame()
    history, _future = split_history_and_future(frame)
    feature_bundle = build_training_features(history)
    bundle = train_model_bundle(force=False)
    models = bundle["models"]  # type: ignore[assignment]
    holdout = feature_bundle.frame.groupby("plant_id").tail(24).copy()
    x = holdout[feature_bundle.feature_columns].fillna(feature_bundle.fill_values)
    holdout["forecast_p10_mw"] = models["p10"].predict(x).clip(0, holdout["capacity_mw"])  # type: ignore[index]
    holdout["forecast_p50_mw"] = models["p50"].predict(x).clip(0, holdout["capacity_mw"])  # type: ignore[index]
    holdout["forecast_p90_mw"] = models["p90"].predict(x).clip(0, holdout["capacity_mw"])  # type: ignore[index]
    holdout["anomaly_hint"] = holdout.apply(anomaly_hint, axis=1)
    return holdout[
        [
            "timestamp",
            "plant_id",
            "plant_name",
            "cluster_id",
            "cluster_name",
            "asset_type",
            "actual_mw",
            "forecast_p10_mw",
            "forecast_p50_mw",
            "forecast_p90_mw",
            "curtailment_flag",
            "outage_flag",
            "data_quality_flag",
            "anomaly_hint",
        ]
    ].copy()


def build_health_view(frame: pd.DataFrame) -> dict[str, object]:
    latest_actual = frame.loc[frame["actual_mw"].notna(), "timestamp"].max()
    return {
        "data_quality_issue_rate": round(float(frame["data_quality_flag"].mean()), 3),
        "telemetry_availability_rate": round(float(frame["availability_flag"].mean()), 3),
        "latest_actual_timestamp": latest_actual.isoformat(),
        "plant_count": int(frame["plant_id"].nunique()),
        "cluster_count": int(frame["cluster_id"].nunique()),
    }


def refresh_state() -> None:
    generate_synthetic_data(force=False)
    train_model_bundle(force=False)
    frame = build_hourly_frame()
    plant_forecast = plant_forecast_view()
    cluster_forecast = cluster_forecast_view(plant_forecast)
    actual_vs_forecast = build_actual_vs_forecast()
    evaluation = json.loads(EVAL_PATH.read_text()) if EVAL_PATH.exists() else {}
    plants = frame[["plant_id", "plant_name", "cluster_id", "cluster_name", "asset_type", "capacity_mw", "lat", "lon"]].drop_duplicates().sort_values(["asset_type", "plant_id"])
    clusters = plants[["cluster_id", "cluster_name"]].drop_duplicates().sort_values("cluster_id")

    APP_STATE.clear()
    APP_STATE.update(
        {
            "health": build_health_view(frame),
            "evaluation": evaluation,
            "plant_forecast": plant_forecast,
            "cluster_forecast": cluster_forecast,
            "actual_vs_forecast": actual_vs_forecast,
            "plants": plants,
            "clusters": clusters,
        }
    )


@app.on_event("startup")
def startup() -> None:
    refresh_state()


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "renewable-forecast-assurance-layer"}


@app.get("/summary")
def summary() -> dict[str, object]:
    return {
        "health": APP_STATE["health"],
        "evaluation": APP_STATE["evaluation"],
        "cluster_count": len(APP_STATE["clusters"]),
        "plant_count": len(APP_STATE["plants"]),
    }


@app.get("/plants")
def plants() -> list[dict[str, object]]:
    frame: pd.DataFrame = APP_STATE["plants"]  # type: ignore[assignment]
    return frame.to_dict(orient="records")


@app.get("/clusters")
def clusters() -> list[dict[str, object]]:
    frame: pd.DataFrame = APP_STATE["clusters"]  # type: ignore[assignment]
    return frame.to_dict(orient="records")


@app.get("/forecast/plant/{plant_id}")
def forecast_plant(plant_id: str) -> list[dict[str, object]]:
    frame: pd.DataFrame = APP_STATE["plant_forecast"]  # type: ignore[assignment]
    subset = frame[frame["plant_id"] == plant_id].copy()
    if subset.empty:
        raise HTTPException(status_code=404, detail="Plant not found")
    subset["timestamp"] = subset["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return subset.to_dict(orient="records")


@app.get("/forecast/cluster/{cluster_id}")
def forecast_cluster(cluster_id: str) -> list[dict[str, object]]:
    frame: pd.DataFrame = APP_STATE["cluster_forecast"]  # type: ignore[assignment]
    subset = frame[frame["cluster_id"] == cluster_id].copy()
    if subset.empty:
        raise HTTPException(status_code=404, detail="Cluster not found")
    subset["timestamp"] = subset["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return subset.to_dict(orient="records")


@app.get("/drivers/{plant_id}")
def drivers(plant_id: str) -> list[dict[str, object]]:
    frame: pd.DataFrame = APP_STATE["plant_forecast"]  # type: ignore[assignment]
    subset = frame[frame["plant_id"] == plant_id][["timestamp", "top_drivers", "top_driver_text", "forecast_change_reason", "reliability_score", "confidence_level"]].copy()
    if subset.empty:
        raise HTTPException(status_code=404, detail="Plant not found")
    subset["timestamp"] = subset["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return subset.to_dict(orient="records")


@app.get("/compare/actual-vs-forecast")
def compare_actual_vs_forecast() -> list[dict[str, object]]:
    frame: pd.DataFrame = APP_STATE["actual_vs_forecast"]  # type: ignore[assignment]
    result = frame.copy()
    result["timestamp"] = result["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return result.to_dict(orient="records")


@app.get("/health/data-quality")
def health_data_quality() -> dict[str, object]:
    return APP_STATE["health"]  # type: ignore[return-value]


@app.post("/refresh")
def refresh() -> dict[str, str]:
    refresh_state()
    return {"status": "refreshed"}
