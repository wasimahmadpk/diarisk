"""
DiaRisk — Step 2a: train a Logistic Regression baseline.

Why Logistic Regression first?
- Simple and interpretable
- Gives probability scores
- Good baseline before LightGBM / stronger models

Run:
  source .venv/bin/activate
  python src/train_logistic.py
"""

from __future__ import annotations

import json
from pathlib import Path

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from data import FEATURE_COLUMNS, load_features_target

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
RANDOM_STATE = 42
TEST_SIZE = 0.2


def build_pipeline() -> Pipeline:
    """Impute → scale → logistic regression."""
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


def main() -> None:
    print("=== DiaRisk Step 2a: Logistic Regression baseline ===\n")

    X, y = load_features_target()
    print(f"Features: {FEATURE_COLUMNS}")
    print(f"Samples: {len(X)}")
    print(f"Train/test split: {1 - TEST_SIZE:.0%} / {TEST_SIZE:.0%} (seed={RANDOM_STATE})\n")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,  # keep similar class balance in train and test
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    y_prob = pipe.predict_proba(X_test)[:, 1]

    metrics = {
        "model": "logistic_regression",
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred)), 4),
        "recall": round(float(recall_score(y_test, y_pred)), 4),
        "f1": round(float(f1_score(y_test, y_pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }

    print("--- Test metrics ---")
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        print(f"  {key:10s}: {metrics[key]:.4f}")

    print("\n--- Classification report ---")
    print(classification_report(y_test, y_pred, target_names=["no diabetes", "diabetes"]))

    ARTIFACTS.mkdir(exist_ok=True)
    metrics_path = ARTIFACTS / "metrics_logistic.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"Saved metrics → {metrics_path.relative_to(ROOT)}")
    print("\nNext later: train LightGBM and compare these numbers.")


if __name__ == "__main__":
    main()
