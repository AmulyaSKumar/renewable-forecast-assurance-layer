from __future__ import annotations

from collections import deque

import joblib
import numpy as np
import pandas as pd

from .explain import classify_confidence, driver_text, forecast_change_reason, reliability_score, summarize_top_drivers
from .features import add_time_features, add_weather_features
from .generate_data import generate_synthetic_data
from .ingest import build_hourly_frame, split_history_and_future
from .train import MODEL_BUNDLE_PATH, train_model_bundle


def _load_bundle() -> dict[str, object]:
    if not MODEL_BUNDLE_PATH.exists():
        return train_model_bundle(force=False)
    return joblib.load(MODEL_BUNDLE_PATH)


def _prepare_runtime_rows(history: pd.DataFrame, future: pd.DataFrame) -> pd.DataFrame:
    history = history.sort_values(["plant_id", "timestamp"]).copy()
    future = add_weather_features(add_time_features(future.copy()))
    cluster_codes = {cluster_id: idx for idx, cluster_id in enumerate(sorted(history["cluster_id"].dropna().unique()))}
    rows: list[pd.DataFrame] = []

    for plant_id, plant_future in future.groupby("plant_id"):
        plant_history = history[history["plant_id"] == plant_id].tail(48).copy()
        output_state = deque(plant_history["actual_mw_filled"].tail(24).tolist(), maxlen=24)
        quality_state = deque(plant_history["data_quality_flag"].tail(24).tolist(), maxlen=24)
        availability_state = deque(plant_history["availability_flag"].tail(24).tolist(), maxlen=24)
        prepared_rows: list[dict[str, object]] = []

        for _, row in plant_future.iterrows():
            prepared_rows.append(
                {
                    **row.to_dict(),
                    "cluster_code": cluster_codes.get(str(row["cluster_id"]), -1),
                    "lag_1h": output_state[-1],
                    "lag_24h": output_state[-24],
                    "rolling_6h": float(np.mean(list(output_state)[-6:])),
                    "rolling_24h": float(np.mean(output_state)),
                    "ramp_prev": output_state[-1] - output_state[-2],
                    "capacity_factor_lag_1h": output_state[-1] / row["capacity_mw"],
                    "capacity_factor_24h": float(np.mean(output_state)) / row["capacity_mw"],
                    "availability_rolling_24h": float(np.mean(availability_state)),
                    "quality_rolling_24h": float(np.mean(quality_state)),
                    "curtailment_flag": 0,
                    "outage_flag": 0,
                    "telemetry_missing_flag": 0,
                    "data_quality_flag": 0,
                }
            )
            output_state.append(output_state[-1])
            quality_state.append(0)
            availability_state.append(1)
        rows.append(pd.DataFrame(prepared_rows))
    return pd.concat(rows, ignore_index=True)


def _predict_runtime(rows: pd.DataFrame, bundle: dict[str, object]) -> pd.DataFrame:
    models = bundle["models"]  # type: ignore[assignment]
    feature_columns: list[str] = bundle["feature_columns"]  # type: ignore[assignment]
    fill_values: dict[str, float] = bundle["fill_values"]  # type: ignore[assignment]

    results: list[pd.DataFrame] = []
    for plant_id, plant_rows in rows.groupby("plant_id"):
        output_state = deque(plant_rows["lag_24h"].head(24).tolist(), maxlen=24)
        quality_state = deque([0] * 24, maxlen=24)
        availability_state = deque([1] * 24, maxlen=24)
        rows_out: list[dict[str, object]] = []

        for _, row in plant_rows.iterrows():
            runtime = row.copy()
            runtime["lag_1h"] = output_state[-1]
            runtime["lag_24h"] = output_state[-24]
            runtime["rolling_6h"] = float(np.mean(list(output_state)[-6:]))
            runtime["rolling_24h"] = float(np.mean(output_state))
            runtime["ramp_prev"] = output_state[-1] - output_state[-2]
            runtime["capacity_factor_lag_1h"] = runtime["lag_1h"] / runtime["capacity_mw"]
            runtime["capacity_factor_24h"] = runtime["rolling_24h"] / runtime["capacity_mw"]
            runtime["availability_rolling_24h"] = float(np.mean(availability_state))
            runtime["quality_rolling_24h"] = float(np.mean(quality_state))

            x = pd.DataFrame([{column: runtime.get(column, fill_values[column]) for column in feature_columns}]).fillna(fill_values)
            p10 = float(np.clip(models["p10"].predict(x)[0], 0, runtime["capacity_mw"]))  # type: ignore[index]
            p50 = float(np.clip(models["p50"].predict(x)[0], 0, runtime["capacity_mw"]))  # type: ignore[index]
            p90 = float(np.clip(models["p90"].predict(x)[0], 0, runtime["capacity_mw"]))  # type: ignore[index]
            p10, p50, p90 = sorted([p10, p50, p90])
            drivers = summarize_top_drivers(runtime)
            score = reliability_score(p10, p50, p90, float(runtime["capacity_mw"]), float(runtime["quality_rolling_24h"]), float(runtime["availability_rolling_24h"]))
            rows_out.append(
                {
                    **runtime[["timestamp", "plant_id", "plant_name", "cluster_id", "cluster_name", "asset_type", "capacity_mw", "cloud_cover", "irradiation_wm2", "wind_speed_ms", "wind_direction_deg"]].to_dict(),
                    "forecast_p10_mw": round(p10, 3),
                    "forecast_p50_mw": round(p50, 3),
                    "forecast_p90_mw": round(p90, 3),
                    "top_drivers": drivers,
                    "top_driver_text": driver_text(drivers),
                    "reliability_score": score,
                    "confidence_level": classify_confidence(score),
                }
            )
            output_state.append(p50)
            quality_state.append(0)
            availability_state.append(1)

        results.append(pd.DataFrame(rows_out))
    return pd.concat(results, ignore_index=True)


def plant_forecast_view() -> pd.DataFrame:
    generate_synthetic_data(force=False)
    bundle = _load_bundle()
    frame = build_hourly_frame()
    history, future = split_history_and_future(frame)
    horizon = future.groupby("plant_id").head(24).copy()
    current_rows = _prepare_runtime_rows(history, horizon)
    current = _predict_runtime(current_rows, bundle)

    previous_horizon = horizon.copy()
    previous_horizon["cloud_cover"] = np.clip(previous_horizon["cloud_cover"] * 0.9 + 0.04, 0, 1)
    previous_horizon["wind_speed_ms"] = np.clip(previous_horizon["wind_speed_ms"] * 0.94, 0.2, None)
    previous_horizon["irradiation_wm2"] = np.clip(previous_horizon["irradiation_wm2"] * 0.96, 0, None)
    previous = _predict_runtime(_prepare_runtime_rows(history, previous_horizon), bundle).rename(
        columns={
            "forecast_p10_mw": "previous_p10",
            "forecast_p50_mw": "previous_p50",
            "forecast_p90_mw": "previous_p90",
            "cloud_cover": "previous_cloud_cover",
            "irradiation_wm2": "previous_irradiation_wm2",
            "wind_speed_ms": "previous_wind_speed_ms",
            "wind_direction_deg": "previous_wind_direction_deg",
        }
    )
    merged = current.merge(
        previous[
            [
                "timestamp",
                "plant_id",
                "previous_p10",
                "previous_p50",
                "previous_p90",
                "previous_cloud_cover",
                "previous_irradiation_wm2",
                "previous_wind_speed_ms",
                "previous_wind_direction_deg",
            ]
        ],
        on=["timestamp", "plant_id"],
        how="left",
    )
    merged["forecast_delta_mw"] = (merged["forecast_p50_mw"] - merged["previous_p50"]).round(3)
    merged["forecast_change_reason"] = merged.apply(
        lambda row: forecast_change_reason(
            row,
            pd.Series(
                {
                    "forecast_p50_mw": row["previous_p50"],
                    "cloud_cover": row["previous_cloud_cover"],
                    "irradiation_wm2": row["previous_irradiation_wm2"],
                    "wind_speed_ms": row["previous_wind_speed_ms"],
                    "wind_direction_deg": row["previous_wind_direction_deg"],
                }
            ),
        ),
        axis=1,
    )
    return merged


def cluster_forecast_view(plant_forecast: pd.DataFrame | None = None) -> pd.DataFrame:
    forecast = plant_forecast if plant_forecast is not None else plant_forecast_view()
    aggregated = (
        forecast.groupby(["timestamp", "cluster_id", "cluster_name"], as_index=False)
        .agg(
            forecast_p10_mw=("forecast_p10_mw", "sum"),
            forecast_p50_mw=("forecast_p50_mw", "sum"),
            forecast_p90_mw=("forecast_p90_mw", "sum"),
            reliability_score=("reliability_score", "mean"),
            solar_share=("asset_type", lambda values: float((pd.Series(values) == "solar").mean())),
        )
    )
    aggregated["confidence_level"] = aggregated["reliability_score"].map(classify_confidence)
    return aggregated
