"""Shared train/eval helpers for fair model comparison."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from data import load_features_target

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

RANDOM_STATE = 42
TEST_SIZE = 0.2


def make_splits():
    """Same split for every model (seed=42, stratified)."""
    X, y = load_features_target()
    return train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )


def compute_metrics(model_name: str, y_true, y_pred, y_prob, n_train: int, n_test: int) -> dict[str, Any]:
    return {
        "model": model_name,
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred)), 4),
        "recall": round(float(recall_score(y_true, y_pred)), 4),
        "f1": round(float(f1_score(y_true, y_pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "n_train": int(n_train),
        "n_test": int(n_test),
    }


def print_metrics(metrics: dict[str, Any], y_true, y_pred) -> None:
    print("--- Test metrics ---")
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        print(f"  {key:10s}: {metrics[key]:.4f}")
    print("\n--- Classification report ---")
    print(classification_report(y_true, y_pred, target_names=["no diabetes", "diabetes"]))


def save_metrics(metrics: dict[str, Any], filename: str) -> Path:
    ARTIFACTS.mkdir(exist_ok=True)
    path = ARTIFACTS / filename
    path.write_text(json.dumps(metrics, indent=2))
    return path
