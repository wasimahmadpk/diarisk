"""Running means of /predict inputs. In-process only — no database."""

from __future__ import annotations

import threading
from typing import Any

from data import FEATURE_COLUMNS

_lock = threading.Lock()
_n = 0
_sums: dict[str, float] = {c: 0.0 for c in FEATURE_COLUMNS}
_score_sum = 0.0
_pred_sum = 0.0


def reset_memory() -> None:
    global _n, _score_sum, _pred_sum, _sums
    with _lock:
        _n = 0
        _score_sum = 0.0
        _pred_sum = 0.0
        _sums = {c: 0.0 for c in FEATURE_COLUMNS}


def record_observation(features: dict[str, Any], prediction: int, probability: float) -> None:
    global _n, _score_sum, _pred_sum
    try:
        with _lock:
            _n += 1
            for col in FEATURE_COLUMNS:
                if col in features:
                    _sums[col] += float(features[col])
            _score_sum += float(probability)
            _pred_sum += int(prediction)
    except Exception:
        return


def live_snapshot() -> dict[str, Any]:
    with _lock:
        n = _n
        if n == 0:
            return {"n": 0, "features": {}, "score_mean": None, "positive_rate": None}
        return {
            "n": n,
            "features": {c: _sums[c] / n for c in FEATURE_COLUMNS},
            "score_mean": _score_sum / n,
            "positive_rate": _pred_sum / n,
        }
