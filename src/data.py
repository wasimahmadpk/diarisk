"""
Shared data loading for DiaRisk.

Zeros in some medical columns are treated as missing (common for Pima).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "pima-indians-diabetes.csv"

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

# In Pima, 0 is often "missing" for these fields (not for pregnancies).
ZERO_AS_MISSING = [
    "glucose",
    "blood_pressure",
    "skin_thickness",
    "insulin",
    "bmi",
]

FEATURE_COLUMNS = [c for c in COLUMNS if c != "outcome"]
TARGET_COLUMN = "outcome"


def load_raw() -> pd.DataFrame:
    return pd.read_csv(RAW_PATH, header=None, names=COLUMNS)


def load_features_target() -> tuple[pd.DataFrame, pd.Series]:
    """Return X, y with impossible zeros turned into NaN (imputed later in the pipeline)."""
    df = load_raw()
    X = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy()

    for col in ZERO_AS_MISSING:
        X.loc[X[col] == 0, col] = np.nan

    return X, y
