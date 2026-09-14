import json

from fastapi.testclient import TestClient

from api import app


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["service"] == "diarisk"
        assert body["model_loaded"] is True


def test_predict_ok(sample_patient):
    with TestClient(app) as client:
        r = client.post("/predict", json=sample_patient)
        assert r.status_code == 200
        body = r.json()
        assert body["diabetes_prediction"] in (0, 1)
        assert 0.0 <= body["diabetes_probability"] <= 1.0
        assert body["risk_level"] in {"low", "moderate", "high"}


def test_predict_rejects_negative_glucose(sample_patient):
    payload = dict(sample_patient)
    payload["glucose"] = -1
    with TestClient(app) as client:
        r = client.post("/predict", json=payload)
        assert r.status_code == 422


def test_predict_rejects_missing_field(sample_patient):
    payload = dict(sample_patient)
    del payload["age"]
    with TestClient(app) as client:
        r = client.post("/predict", json=payload)
        assert r.status_code == 422


def test_lambda_handler_serves_health():
    """The Lambda entrypoint must handle a Function URL event."""
    from lambda_handler import handler

    event = {
        "version": "2.0",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {"host": "localhost"},
        "requestContext": {
            "http": {"method": "GET", "path": "/health", "sourceIp": "127.0.0.1"}
        },
        "isBase64Encoded": False,
    }
    response = handler(event, None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["status"] == "ok"
