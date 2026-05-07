from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from backend.features import build_training_features
    from backend.generate_data import generate_synthetic_data
    from backend.ingest import build_hourly_frame, split_history_and_future
else:
    from .features import build_training_features
    from .generate_data import generate_synthetic_data
    from .ingest import build_hourly_frame, split_history_and_future


ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
MODEL_BUNDLE_PATH = MODELS_DIR / "forecast_bundle.joblib"
EVAL_PATH = MODELS_DIR / "evaluation.json"


def pinball_loss(y_true: pd.Series, y_pred: np.ndarray, alpha: float) -> float:
    delta = y_true.to_numpy() - y_pred
    return float(np.mean(np.maximum(alpha * delta, (alpha - 1) * delta)))


def _baseline_predictions(valid: pd.DataFrame, train: pd.DataFrame) -> dict[str, np.ndarray]:
    persistence = valid["lag_24h"].to_numpy()
    seasonal_lookup = train.groupby(["plant_id", "hour"])["actual_mw"].mean().rename("seasonal_mean").reset_index()
    seasonal = valid[["plant_id", "hour"]].merge(seasonal_lookup, on=["plant_id", "hour"], how="left")["seasonal_mean"].fillna(train["actual_mw"].mean())
    reg_columns = ["asset_type_code", "cloud_cover", "irradiation_wm2", "temperature_c", "wind_speed_ms", "gust_speed_ms", "hour_sin", "hour_cos"]
    reg_model = LinearRegression()
    reg_model.fit(train[reg_columns], train["actual_mw"])
    return {
        "persistence": persistence,
        "seasonal_hourly_mean": seasonal.to_numpy(),
        "weather_regression": reg_model.predict(valid[reg_columns]),
    }


def _evaluate(y_true: pd.Series, baseline_predictions: dict[str, np.ndarray], p10: np.ndarray, p50: np.ndarray, p90: np.ndarray) -> dict[str, object]:
    baselines = {}
    for name, prediction in baseline_predictions.items():
        baselines[name] = {
            "mae": round(float(mean_absolute_error(y_true, prediction)), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(y_true, prediction))), 3),
        }
    interval_hit = ((y_true >= p10) & (y_true <= p90)).mean()
    model = {
        "mae": round(float(mean_absolute_error(y_true, p50)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, p50))), 3),
        "pinball_p10": round(pinball_loss(y_true, p10, 0.1), 3),
        "pinball_p50": round(pinball_loss(y_true, p50, 0.5), 3),
        "pinball_p90": round(pinball_loss(y_true, p90, 0.9), 3),
        "coverage_p10_p90": round(float(interval_hit), 3),
    }
    return {"baselines": baselines, "model": model}


def train_model_bundle(force: bool = False) -> dict[str, object]:
    MODELS_DIR.mkdir(exist_ok=True)
    if not force and MODEL_BUNDLE_PATH.exists() and EVAL_PATH.exists():
        try:
            return joblib.load(MODEL_BUNDLE_PATH)
        except Exception:
            # Rebuild the model bundle when the saved artifact was created by a
            # different scikit-learn / Python environment and cannot be unpickled.
            pass

    generate_synthetic_data(force=False)
    frame = build_hourly_frame()
    history, _future = split_history_and_future(frame)
    feature_bundle = build_training_features(history)
    dataset = feature_bundle.frame.copy()
    validation_cutoff = dataset["timestamp"].max() - pd.Timedelta(days=14)
    train = dataset[dataset["timestamp"] < validation_cutoff].copy()
    valid = dataset[dataset["timestamp"] >= validation_cutoff].copy()

    x_train = train[feature_bundle.feature_columns]
    y_train = train["actual_mw"]
    x_valid = valid[feature_bundle.feature_columns]
    y_valid = valid["actual_mw"]

    models = {
        "p10": HistGradientBoostingRegressor(loss="quantile", quantile=0.1, random_state=42, max_iter=160, max_depth=6, learning_rate=0.06),
        "p50": HistGradientBoostingRegressor(loss="quantile", quantile=0.5, random_state=42, max_iter=180, max_depth=6, learning_rate=0.06),
        "p90": HistGradientBoostingRegressor(loss="quantile", quantile=0.9, random_state=42, max_iter=160, max_depth=6, learning_rate=0.06),
    }
    for model in models.values():
        model.fit(x_train, y_train)

    valid_predictions = {name: np.clip(model.predict(x_valid), 0, None) for name, model in models.items()}
    evaluation = _evaluate(y_valid, _baseline_predictions(valid, train), valid_predictions["p10"], valid_predictions["p50"], valid_predictions["p90"])
    bundle = {
        "models": models,
        "feature_columns": feature_bundle.feature_columns,
        "fill_values": feature_bundle.fill_values,
        "evaluation": evaluation,
    }
    joblib.dump(bundle, MODEL_BUNDLE_PATH)
    EVAL_PATH.write_text(json.dumps(evaluation, indent=2))
    return bundle


if __name__ == "__main__":
    train_model_bundle(force=True)
