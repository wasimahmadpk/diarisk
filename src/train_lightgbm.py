"""
DiaRisk — train LightGBM and save the pipeline for inference.

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
from model_io import save_model
from tracking import log_training_run

LGBM_PARAMS = {
    "n_estimators": 200,
    "learning_rate": 0.05,
    "max_depth": 4,
    "num_leaves": 15,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
}


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                LGBMClassifier(
                    **LGBM_PARAMS,
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

    metrics_path = save_metrics(metrics, "metrics_lightgbm.json")
    model_path = save_model(pipe)
    run_id = log_training_run(
        run_name="lightgbm",
        params={
            "model_type": "lightgbm",
            "imputer": "median",
            "test_size": TEST_SIZE,
            "random_state": RANDOM_STATE,
            **LGBM_PARAMS,
        },
        metrics=metrics,
        model=pipe,
        X_example=X_test.head(5),
    )
    print(f"Saved metrics → {metrics_path}")
    print(f"Saved model   → {model_path}")
    print(f"MLflow run_id → {run_id}")


if __name__ == "__main__":
    main()
