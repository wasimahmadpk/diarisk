"""
DiaRisk — train Logistic Regression baseline.

Run:
  python src/train_logistic.py
"""

from __future__ import annotations

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from data import FEATURE_COLUMNS
from evaluate import (
    RANDOM_STATE,
    TEST_SIZE,
    compute_metrics,
    make_splits,
    print_metrics,
    save_metrics,
)
from tracking import log_training_run


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
            ),
        ]
    )


def main() -> None:
    print("=== DiaRisk: Logistic Regression ===\n")
    print(f"Features: {FEATURE_COLUMNS}")
    print(f"Train/test: {1 - TEST_SIZE:.0%} / {TEST_SIZE:.0%} (seed={RANDOM_STATE})\n")

    X_train, X_test, y_train, y_test = make_splits()
    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    y_prob = pipe.predict_proba(X_test)[:, 1]

    metrics = compute_metrics(
        "logistic_regression",
        y_test,
        y_pred,
        y_prob,
        n_train=len(X_train),
        n_test=len(X_test),
    )
    print_metrics(metrics, y_test, y_pred)

    path = save_metrics(metrics, "metrics_logistic.json")
    run_id = log_training_run(
        run_name="logistic_regression",
        params={
            "model_type": "logistic_regression",
            "max_iter": 1000,
            "scaler": "StandardScaler",
            "imputer": "median",
            "test_size": TEST_SIZE,
            "random_state": RANDOM_STATE,
        },
        metrics=metrics,
        model=pipe,
        X_example=X_test.head(5),
    )
    print(f"Saved metrics → {path}")
    print(f"MLflow run_id → {run_id}")


if __name__ == "__main__":
    main()
