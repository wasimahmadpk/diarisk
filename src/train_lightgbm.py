"""
DiaRisk — train LightGBM classifier.

Same train/test split as logistic regression (seed=42) so metrics are comparable.

Run:
  python src/train_lightgbm.py
"""

from __future__ import annotations

from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from data import FEATURE_COLUMNS
from evaluate import (
    RANDOM_STATE,
    TEST_SIZE,
    compute_metrics,
    make_splits,
    print_metrics,
    save_metrics,
)


def build_pipeline() -> Pipeline:
    # Trees don't need scaling; median impute keeps preprocessing consistent.
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                LGBMClassifier(
                    n_estimators=200,
                    learning_rate=0.05,
                    max_depth=4,
                    num_leaves=15,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    random_state=RANDOM_STATE,
                    verbose=-1,
                ),
            ),
        ]
    )


def main() -> None:
    print("=== DiaRisk: LightGBM ===\n")
    print(f"Features: {FEATURE_COLUMNS}")
    print(f"Train/test: {1 - TEST_SIZE:.0%} / {TEST_SIZE:.0%} (seed={RANDOM_STATE})\n")

    X_train, X_test, y_train, y_test = make_splits()
    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    y_prob = pipe.predict_proba(X_test)[:, 1]

    metrics = compute_metrics(
        "lightgbm",
        y_test,
        y_pred,
        y_prob,
        n_train=len(X_train),
        n_test=len(X_test),
    )
    print_metrics(metrics, y_test, y_pred)

    path = save_metrics(metrics, "metrics_lightgbm.json")
    print(f"Saved metrics → {path}")


if __name__ == "__main__":
    main()
