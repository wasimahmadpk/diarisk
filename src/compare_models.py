"""
Compare logistic regression vs LightGBM using saved metric files.

Run both trainers first:
  python src/train_logistic.py
  python src/train_lightgbm.py
  python src/compare_models.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

METRIC_KEYS = ("accuracy", "precision", "recall", "f1", "roc_auc")
FILES = {
    "logistic_regression": ARTIFACTS / "metrics_logistic.json",
    "lightgbm": ARTIFACTS / "metrics_lightgbm.json",
}


def main() -> None:
    missing = [name for name, path in FILES.items() if not path.exists()]
    if missing:
        print("Missing metrics for:", ", ".join(missing))
        print("Run train_logistic.py and train_lightgbm.py first.")
        sys.exit(1)

    rows = {name: json.loads(path.read_text()) for name, path in FILES.items()}

    print("=== DiaRisk model comparison (same test split) ===\n")
    header = f"{'metric':12s}  {'logistic':>10s}  {'lightgbm':>10s}  {'winner':>10s}"
    print(header)
    print("-" * len(header))

    for key in METRIC_KEYS:
        a = rows["logistic_regression"][key]
        b = rows["lightgbm"][key]
        if a > b:
            winner = "logistic"
        elif b > a:
            winner = "lightgbm"
        else:
            winner = "tie"
        print(f"{key:12s}  {a:10.4f}  {b:10.4f}  {winner:>10s}")

    print()


if __name__ == "__main__":
    main()
