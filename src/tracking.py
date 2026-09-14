"""
MLflow helpers for DiaRisk training runs.

Tracking URI defaults to ./mlruns (local folder).
"""

from __future__ import annotations

import os
from typing import Any

import mlflow
from mlflow.models import infer_signature

from evaluate import ROOT

EXPERIMENT_NAME = "diarisk"
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", str(ROOT / "mlruns"))

_METRIC_KEYS = ("accuracy", "precision", "recall", "f1", "roc_auc")


def _init() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)


def log_training_run(
    *,
    run_name: str,
    params: dict[str, Any],
    metrics: dict[str, Any],
    model=None,
    X_example=None,
) -> str:
    """Log params + metrics (+ optional sklearn pipeline). Returns run_id."""
    _init()
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params({k: str(v) for k, v in params.items()})
        for key in _METRIC_KEYS:
            if key in metrics:
                mlflow.log_metric(key, float(metrics[key]))
        mlflow.log_param("n_train", metrics.get("n_train", ""))
        mlflow.log_param("n_test", metrics.get("n_test", ""))

        if model is not None and X_example is not None:
            signature = infer_signature(X_example, model.predict_proba(X_example))
            mlflow.sklearn.log_model(model, artifact_path="model", signature=signature)

        return run.info.run_id
