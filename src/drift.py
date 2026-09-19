"""
Data drift and model-performance drift.

Live checks compare each /predict (and the running mean of this process)
to training mean ± std. No database: z = (value - train_mean) / train_std.

  python src/drift.py
  python src/drift.py --current path/to/recent.csv
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data import FEATURE_COLUMNS, load_features_target
from evaluate import ARTIFACTS, compute_metrics, make_splits
from model_io import load_model

PSI_STABLE = 0.10
PSI_SIGNIFICANT = 0.25
Z_MODERATE = 2.0
Z_SIGNIFICANT = 3.0
MIN_ROWS = 30
DEFAULT_AUC_DROP = 0.05
DEFAULT_F1_DROP = 0.05
def _default_reference_path() -> Path:
    env = os.environ.get("DIARISK_DRIFT_REFERENCE")
    if env:
        return Path(env)
    here = Path(__file__).resolve().parent
    for candidate in (
        here / "artifacts" / "drift_reference.json",  # Lambda: /var/task/artifacts
        here.parent / "artifacts" / "drift_reference.json",  # local: repo/artifacts
    ):
        if candidate.exists():
            return candidate
    return here / "artifacts" / "drift_reference.json"


BASELINE_METRICS_PATH = ARTIFACTS / "metrics_lightgbm.json"
REFERENCE_PATH = _default_reference_path()


def _safe_prop(counts: np.ndarray) -> np.ndarray:
    props = counts / max(counts.sum(), 1)
    return np.clip(props, 1e-6, 1.0)


def population_stability_index(
    reference: np.ndarray,
    current: np.ndarray,
    n_bins: int = 10,
) -> float:
    """PSI between two 1-D numeric samples. Same bins are taken from the reference."""
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    ref = ref[~np.isnan(ref)]
    cur = cur[~np.isnan(cur)]
    if len(ref) < 2 or len(cur) < 2:
        return 0.0

    edges = np.unique(np.quantile(ref, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 3:
        lo, hi = float(np.min(ref)), float(np.max(ref))
        if lo == hi:
            return 0.0
        edges = np.linspace(lo, hi, 4)
    edges[0] = -np.inf
    edges[-1] = np.inf

    expected, _ = np.histogram(ref, bins=edges)
    actual, _ = np.histogram(cur, bins=edges)
    return psi_from_counts(expected, actual)


def psi_from_counts(expected, actual) -> float:
    e = _safe_prop(np.asarray(expected, dtype=float))
    a = _safe_prop(np.asarray(actual, dtype=float))
    return float(np.sum((a - e) * np.log(a / e)))


def _bin_edges(values: np.ndarray, n_bins: int = 10) -> np.ndarray:
    ref = np.asarray(values, dtype=float)
    ref = ref[~np.isnan(ref)]
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 3:
        lo, hi = float(np.min(ref)), float(np.max(ref))
        if lo == hi:
            return np.array([-np.inf, np.inf])
        edges = np.linspace(lo, hi, 4)
    edges = edges.astype(float)
    edges[0] = -np.inf
    edges[-1] = np.inf
    return edges


def _edges_to_json(edges: np.ndarray) -> list[float | None]:
    out: list[float | None] = []
    for e in edges:
        if np.isneginf(e) or np.isposinf(e):
            out.append(None)
        else:
            out.append(float(e))
    return out


def _edges_from_json(raw: list[float | None]) -> np.ndarray:
    vals = []
    for i, e in enumerate(raw):
        if e is None:
            vals.append(-np.inf if i == 0 else np.inf)
        else:
            vals.append(float(e))
    return np.array(vals, dtype=float)


def zscore(value: float, mean: float, std: float) -> float:
    if std is None or float(std) == 0.0:
        return 0.0
    return float((value - mean) / std)


def z_status(z: float) -> str:
    a = abs(z)
    if a < Z_MODERATE:
        return "stable"
    if a < Z_SIGNIFICANT:
        return "moderate"
    return "significant"


def psi_label(psi: float) -> str:
    if psi < PSI_STABLE:
        return "stable"
    if psi < PSI_SIGNIFICANT:
        return "moderate"
    return "significant"


def feature_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    columns: list[str] | None = None,
    min_rows: int = MIN_ROWS,
) -> dict[str, Any]:
    """Per-feature PSI vs a reference (usually the training table)."""
    columns = columns or FEATURE_COLUMNS
    n = int(len(current))
    report: dict[str, Any] = {
        "n_reference": int(len(reference)),
        "n_current": n,
        "insufficient_sample": n < min_rows,
        "features": {},
        "max_psi": 0.0,
        "drifted_features": [],
        "data_drift": False,
    }
    if n == 0:
        return report

    max_psi = 0.0
    drifted: list[str] = []
    features: dict[str, Any] = {}
    for col in columns:
        if col not in reference.columns or col not in current.columns:
            continue
        psi = round(population_stability_index(reference[col].to_numpy(), current[col].to_numpy()), 4)
        status = psi_label(psi)
        features[col] = {"psi": psi, "status": status}
        max_psi = max(max_psi, psi)
        if status == "significant":
            drifted.append(col)

    report["features"] = features
    report["max_psi"] = round(max_psi, 4)
    report["drifted_features"] = drifted
    report["data_drift"] = bool(drifted) and not report["insufficient_sample"]
    return report


def performance_drift(
    y_true,
    y_pred,
    y_prob,
    baseline: dict[str, Any] | None = None,
    auc_drop: float = DEFAULT_AUC_DROP,
    f1_drop: float = DEFAULT_F1_DROP,
    min_rows: int = MIN_ROWS,
) -> dict[str, Any]:
    """Flag model drift when ROC-AUC or F1 falls by more than the allowed drop."""
    baseline = baseline or load_baseline_metrics()
    y_true = np.asarray(y_true)
    n = int(len(y_true))
    current = compute_metrics(
        str(baseline.get("model", "current")),
        y_true,
        y_pred,
        y_prob,
        n_train=int(baseline.get("n_train", 0)),
        n_test=n,
    )
    drops = {
        "roc_auc": round(float(baseline["roc_auc"]) - float(current["roc_auc"]), 4),
        "f1": round(float(baseline["f1"]) - float(current["f1"]), 4),
        "accuracy": round(float(baseline["accuracy"]) - float(current["accuracy"]), 4),
    }
    insufficient = n < min_rows
    model_drift = (not insufficient) and (
        drops["roc_auc"] >= auc_drop or drops["f1"] >= f1_drop
    )
    return {
        "n_current": n,
        "insufficient_sample": insufficient,
        "baseline": {k: baseline[k] for k in ("model", "accuracy", "f1", "roc_auc") if k in baseline},
        "current": {k: current[k] for k in ("accuracy", "f1", "roc_auc")},
        "drop": drops,
        "thresholds": {"roc_auc": auc_drop, "f1": f1_drop},
        "model_drift": model_drift,
    }


def load_baseline_metrics(path: Path = BASELINE_METRICS_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No baseline metrics at {path}. Train the model first.")
    return json.loads(path.read_text())


def evaluate_drift(
    current: pd.DataFrame,
    reference: pd.DataFrame | None = None,
    model=None,
    baseline: dict[str, Any] | None = None,
    target_column: str = "outcome",
) -> dict[str, Any]:
    """Data drift always; model drift only if `outcome` is present on `current`."""
    if reference is None:
        X_ref, _ = load_features_target()
        reference = X_ref

    data = feature_drift(reference[FEATURE_COLUMNS], current[FEATURE_COLUMNS])
    out: dict[str, Any] = {"data": data, "performance": None}

    if target_column in current.columns:
        if model is None:
            model = load_model()
        X = current[FEATURE_COLUMNS]
        y = current[target_column]
        y_pred = model.predict(X)
        y_prob = model.predict_proba(X)[:, 1]
        out["performance"] = performance_drift(y, y_pred, y_prob, baseline=baseline)
    return out


def load_live_reference(path: Path = REFERENCE_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No drift reference at {path}")
    return json.loads(path.read_text())


def save_live_reference(path: Path = REFERENCE_PATH) -> Path:
    """Save training mean and std for live z-score checks."""
    X_train, X_test, _, _ = make_splits()
    scores = load_model().predict_proba(X_test)[:, 1]
    features = {}
    for col in FEATURE_COLUMNS:
        series = X_train[col].to_numpy(dtype=float)
        series = series[~np.isnan(series)]
        features[col] = {
            "mean": round(float(np.mean(series)), 4),
            "std": round(float(np.std(series, ddof=0)), 4),
        }
    payload = {
        "n_reference": int(len(X_train)),
        "features": features,
        "score": {
            "mean": round(float(np.mean(scores)), 4),
            "std": round(float(np.std(scores, ddof=0)), 4),
            "positive_rate": round(float(np.mean(scores >= 0.5)), 4),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    return path


def live_report(
    snapshot: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare live feature/score means to training mean ± std."""
    reference = reference or load_live_reference()
    if snapshot is None:
        snapshot = _snapshot_from_rows(rows or [])
    n = int(snapshot.get("n") or 0)
    live_features = snapshot.get("features") or {}
    features_out: dict[str, Any] = {}
    drifted: list[str] = []
    max_abs_z = 0.0
    for col, spec in (reference.get("features") or {}).items():
        if col not in live_features or "mean" not in spec:
            continue
        z = round(zscore(float(live_features[col]), spec["mean"], spec["std"]), 4)
        status = z_status(z)
        features_out[col] = {
            "live_mean": round(float(live_features[col]), 4),
            "train_mean": spec["mean"],
            "train_std": spec["std"],
            "z": z,
            "status": status,
        }
        max_abs_z = max(max_abs_z, abs(z))
        if status == "significant":
            drifted.append(col)

    score_spec = reference.get("score") or {}
    live_score = snapshot.get("score_mean")
    score_z = 0.0
    if live_score is not None and score_spec.get("std"):
        score_z = round(zscore(float(live_score), score_spec["mean"], score_spec["std"]), 4)
    score_status = z_status(score_z) if live_score is not None else "stable"
    return {
        "n_current": n,
        "insufficient_sample": n == 0,
        "data": {
            "n_reference": reference.get("n_reference"),
            "features": features_out,
            "max_abs_z": round(max_abs_z, 4),
            "drifted_features": drifted,
            "data_drift": bool(drifted) and n > 0,
        },
        "score": {
            "z": score_z,
            "status": score_status,
            "mean": None if live_score is None else round(float(live_score), 4),
            "baseline_mean": score_spec.get("mean"),
            "positive_rate": snapshot.get("positive_rate"),
            "baseline_positive_rate": score_spec.get("positive_rate"),
            "score_drift": (score_status == "significant") and n > 0,
            "note": "z = (live mean − train mean) / train std. |z|≥3 is flagged. Score drift is not labeled accuracy.",
        },
    }


def _snapshot_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n": 0, "features": {}, "score_mean": None, "positive_rate": None}
    features = {}
    for col in FEATURE_COLUMNS:
        vals = [row.get("features", {}).get(col) for row in rows]
        vals = [float(v) for v in vals if v is not None]
        if vals:
            features[col] = sum(vals) / len(vals)
    probs = [float(row["probability"]) for row in rows if row.get("probability") is not None]
    preds = [int(row["prediction"]) for row in rows if row.get("prediction") is not None]
    return {
        "n": n,
        "features": features,
        "score_mean": (sum(probs) / len(probs)) if probs else None,
        "positive_rate": (sum(preds) / len(preds)) if preds else None,
    }


def _shifted_copy(X: pd.DataFrame) -> pd.DataFrame:
    shifted = X.copy()
    shifted["glucose"] = shifted["glucose"] + 80
    shifted["bmi"] = shifted["bmi"] * 1.6
    return shifted


def main() -> None:
    parser = argparse.ArgumentParser(description="DiaRisk data / model drift")
    parser.add_argument("--current", type=Path, help="CSV of recent rows (optional outcome column)")
    args = parser.parse_args()

    X, y = load_features_target()
    _, X_test, _, y_test = make_splits()

    if args.current:
        current = pd.read_csv(args.current)
        report = evaluate_drift(current, reference=X)
    else:
        matched = X_test.copy()
        matched["outcome"] = y_test.to_numpy()
        shifted = _shifted_copy(X_test)
        print("No --current file. Showing train-vs-test (should be stable) then a shifted copy.\n")
        report = {
            "test_split": evaluate_drift(matched, reference=X),
            "shifted_demo": evaluate_drift(shifted, reference=X),
        }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
