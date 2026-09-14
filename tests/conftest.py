import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "example_patient.json"


@pytest.fixture
def sample_patient() -> dict:
    return json.loads(SAMPLE.read_text())
