import pytest

from predict import prepare_features, predict_one, risk_level


def test_risk_level_thresholds():
    assert risk_level(0.1) == "low"
    assert risk_level(0.45) == "moderate"
    assert risk_level(0.9) == "high"


def test_prepare_features_requires_all_fields():
    with pytest.raises(ValueError, match="Missing fields"):
        prepare_features({"glucose": 120})


def test_prepare_features_zeros_become_nan(sample_patient):
    payload = dict(sample_patient)
    payload["insulin"] = 0
    X = prepare_features(payload)
    assert X.shape == (1, 8)
    assert X["insulin"].isna().iloc[0]


def test_predict_one_returns_expected_keys(sample_patient):
    result = predict_one(sample_patient)
    assert set(result) == {
        "diabetes_prediction",
        "diabetes_probability",
        "risk_level",
    }
    assert result["diabetes_prediction"] in (0, 1)
    assert 0.0 <= result["diabetes_probability"] <= 1.0
    assert result["risk_level"] in {"low", "moderate", "high"}
