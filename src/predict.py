"""
Predict diabetes risk from a JSON object / file.

Example:
  python src/predict.py --json samples/example_patient.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from data import FEATURE_COLUMNS, ZERO_AS_MISSING
from model_io import load_model


def risk_level(probability: float) -> str:
    if probability < 0.3:
        return "low"
    if probability < 0.6:
        return "moderate"
    return "high"


def prepare_features(payload: dict[str, Any]) -> pd.DataFrame:
    missing = [c for c in FEATURE_COLUMNS if c not in payload]
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    row = {col: float(payload[col]) for col in FEATURE_COLUMNS}
    X = pd.DataFrame([row], columns=FEATURE_COLUMNS)

    for col in ZERO_AS_MISSING:
        if X.at[0, col] == 0:
            X.at[0, col] = float("nan")

    return X


def predict_one(payload: dict[str, Any], model=None) -> dict[str, Any]:
    if model is None:
        model = load_model()
    X = prepare_features(payload)
    proba = float(model.predict_proba(X)[0, 1])
    label = int(model.predict(X)[0])
    return {
        "diabetes_prediction": label,
        "diabetes_probability": round(proba, 4),
        "risk_level": risk_level(proba),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="DiaRisk inference")
    parser.add_argument(
        "--json",
        type=Path,
        required=True,
        help="JSON file with the 8 clinical feature fields",
    )
    args = parser.parse_args()

    if not args.json.exists():
        print(f"File not found: {args.json}", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(args.json.read_text())
    result = predict_one(payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
