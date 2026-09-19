import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("DIARISK_DRIFT_BACKEND", "memory")
os.environ.pop("DIARISK_DRIFT_TABLE", None)


@pytest.fixture(autouse=True)
def clear_observations():
    from observations import reset_memory

    reset_memory()
    yield
    reset_memory()

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "example_patient.json"


@pytest.fixture
def sample_patient() -> dict:
    return json.loads(SAMPLE.read_text())
