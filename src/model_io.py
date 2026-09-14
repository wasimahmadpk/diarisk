"""Load/save the trained DiaRisk pipeline."""

from __future__ import annotations

import os
from pathlib import Path

import joblib
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
# DIARISK_MODEL_PATH lets deployments (e.g. Lambda) point at another location.
DEFAULT_MODEL_PATH = Path(
    os.environ.get("DIARISK_MODEL_PATH", MODELS_DIR / "diarisk_lightgbm.joblib")
)


def save_model(pipeline: Pipeline, path: Path = DEFAULT_MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, path)
    return path


def load_model(path: Path = DEFAULT_MODEL_PATH) -> Pipeline:
    if not path.exists():
        raise FileNotFoundError(
            f"No model at {path}. Run: python src/train_lightgbm.py"
        )
    return joblib.load(path)
