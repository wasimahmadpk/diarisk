"""
DiaRisk FastAPI app.

Run:
  uvicorn api:app --app-dir src --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from drift import live_report
from model_io import load_model
from observations import live_snapshot, record_observation
from predict import predict_one
from stats import collect_stats

_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model
    _model = load_model()
    yield


app = FastAPI(
    title="DiaRisk",
    description="Diabetes risk prediction from clinical measurements",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PatientFeatures(BaseModel):
    pregnancies: float = Field(..., ge=0)
    glucose: float = Field(..., ge=0)
    blood_pressure: float = Field(..., ge=0)
    skin_thickness: float = Field(..., ge=0)
    insulin: float = Field(..., ge=0)
    bmi: float = Field(..., ge=0)
    diabetes_pedigree: float = Field(..., ge=0)
    age: float = Field(..., ge=0)


class PredictionResponse(BaseModel):
    diabetes_prediction: int
    diabetes_probability: float
    risk_level: Literal["low", "moderate", "high"]


@app.get("/health")
def health():
    return {"status": "ok", "service": "diarisk", "model_loaded": _model is not None}


@app.get("/stats")
def stats(hours: int = 24):
    """Operational metrics from CloudWatch (Lambda + HTTP API)."""
    try:
        return collect_stats(hours=hours)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Metrics unavailable: {exc}") from exc


@app.options("/{full_path:path}")
def cors_preflight(full_path: str):
    return Response(status_code=204)


@app.get("/drift")
def drift():
    """Live data/score drift vs training mean and std (no database)."""
    try:
        return live_report(snapshot=live_snapshot())
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Drift unavailable: {exc}") from exc


@app.post("/predict", response_model=PredictionResponse)
def predict(features: PatientFeatures):
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        result = predict_one(features.model_dump(), model=_model)
        record_observation(
            features.model_dump(),
            result["diabetes_prediction"],
            result["diabetes_probability"],
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
