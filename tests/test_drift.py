import numpy as np

from data import FEATURE_COLUMNS, load_features_target
from drift import (
    evaluate_drift,
    feature_drift,
    performance_drift,
    population_stability_index,
    psi_label,
)
from evaluate import make_splits
from model_io import load_model


def test_psi_near_zero_on_same_sample():
    rng = np.random.default_rng(0)
    x = rng.normal(size=400)
    assert population_stability_index(x, x) < 0.05
    assert psi_label(0.02) == "stable"
    assert psi_label(0.4) == "significant"


def test_feature_drift_flags_shifted_glucose():
    X, _ = load_features_target()
    same = feature_drift(X, X.sample(120, random_state=1))
    assert same["data_drift"] is False

    shifted = X.sample(120, random_state=1).copy()
    shifted["glucose"] = shifted["glucose"] + 90
    drifted = feature_drift(X, shifted)
    assert drifted["data_drift"] is True
    assert "glucose" in drifted["drifted_features"]


def test_feature_drift_marks_small_batches():
    X, _ = load_features_target()
    tiny = feature_drift(X, X.head(5), min_rows=30)
    assert tiny["insufficient_sample"] is True
    assert tiny["data_drift"] is False


def test_performance_drift_flags_random_labels():
    y_true = np.array([0, 1] * 40)
    y_good = y_true.copy()
    y_prob_good = np.where(y_true == 1, 0.9, 0.1)
    baseline = {"model": "toy", "accuracy": 1.0, "f1": 1.0, "roc_auc": 1.0, "n_train": 80}
    ok = performance_drift(y_true, y_good, y_prob_good, baseline=baseline)
    assert ok["model_drift"] is False

    rng = np.random.default_rng(2)
    y_bad = rng.integers(0, 2, size=len(y_true))
    y_prob_bad = rng.random(len(y_true))
    bad = performance_drift(y_true, y_bad, y_prob_bad, baseline=baseline)
    assert bad["model_drift"] is True
    assert bad["drop"]["roc_auc"] >= 0.05


def test_live_report_flags_shifted_inputs():
    from drift import live_report, save_live_reference

    save_live_reference()
    X, _ = load_features_target()
    sample = X.head(40)
    rows = []
    for _, rec in sample.iterrows():
        feats = {c: float(rec[c]) if rec[c] == rec[c] else 0.0 for c in FEATURE_COLUMNS}
        feats["glucose"] = feats["glucose"] + 90
        rows.append({"features": feats, "probability": 0.95, "prediction": 1})
    report = live_report(rows)
    assert report["n_current"] == 40
    assert report["data"]["data_drift"] is True
    assert "glucose" in report["data"]["drifted_features"]
    assert report["score"]["score_drift"] is True


def test_evaluate_drift_test_split_is_stable():
    X, y = load_features_target()
    _, X_test, _, y_test = make_splits()
    current = X_test.copy()
    current["outcome"] = y_test.to_numpy()
    report = evaluate_drift(
        current,
        reference=X,
        model=load_model(),
        baseline={
            "model": "lightgbm",
            "accuracy": 0.7532,
            "precision": 0.66,
            "recall": 0.6111,
            "f1": 0.6346,
            "roc_auc": 0.8157,
            "n_train": 614,
        },
    )
    assert report["data"]["data_drift"] is False
    assert report["performance"] is not None
    assert report["performance"]["model_drift"] is False
    assert set(report["data"]["features"]) == set(FEATURE_COLUMNS)
