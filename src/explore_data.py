"""
DiaRisk — Step 1: understand the Pima diabetes dataset.

Run:
  source .venv/bin/activate
  python src/explore_data.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "pima-indians-diabetes.csv"

COLUMNS = [
    "pregnancies",
    "glucose",
    "blood_pressure",
    "skin_thickness",
    "insulin",
    "bmi",
    "diabetes_pedigree",
    "age",
    "outcome",
]


def main() -> None:
    df = pd.read_csv(RAW, header=None, names=COLUMNS)

    print("=== DiaRisk Step 1: Data overview ===\n")
    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}\n")

    print("--- First 5 rows ---")
    print(df.head().to_string(index=False))
    print()

    print("--- Target balance (outcome) ---")
    counts = df["outcome"].value_counts().sort_index()
    for label, n in counts.items():
        name = "diabetes" if label == 1 else "no diabetes"
        pct = 100 * n / len(df)
        print(f"  {label} ({name}): {n}  ({pct:.1f}%)")
    print()

    print("--- Basic stats ---")
    print(df.describe().round(2).to_string())
    print()

    # In this dataset, 0 often means "missing" for some medical fields
    zero_cols = ["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi"]
    print("--- Zeros that may mean missing ---")
    for col in zero_cols:
        n = int((df[col] == 0).sum())
        print(f"  {col}: {n} zeros")


if __name__ == "__main__":
    main()
