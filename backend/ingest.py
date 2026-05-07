from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def _read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, parse_dates=["timestamp"] if name != "plants.csv" else None)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    plants = _read_csv("plants.csv")
    weather = _read_csv("weather.csv")
    generation = _read_csv("generation.csv")
    return plants, weather, generation


def build_hourly_frame() -> pd.DataFrame:
    plants, weather, generation = load_inputs()
    frame = weather.merge(plants, on="plant_id", how="left").merge(generation, on=["timestamp", "plant_id"], how="left")
    frame["data_quality_flag"] = (
        frame["actual_mw"].isna()
        | frame["cloud_cover"].isna()
        | frame["irradiation_wm2"].isna()
        | frame["wind_speed_ms"].isna()
    ).astype(int)
    frame["actual_mw_filled"] = frame["actual_mw"].fillna(0.0)
    frame["availability_flag"] = frame["actual_mw"].notna().astype(int)
    return frame.sort_values(["plant_id", "timestamp"]).reset_index(drop=True)


def split_history_and_future(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    generation_max = frame.loc[frame["actual_mw"].notna(), "timestamp"].max()
    history = frame[frame["timestamp"] <= generation_max].copy()
    future = frame[frame["timestamp"] > generation_max].copy()
    return history, future
