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
from pydantic import BaseModel, Field

from model_io import load_model
from predict import predict_one

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


@app.post("/predict", response_model=PredictionResponse)
def predict(features: PatientFeatures):
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        return predict_one(features.model_dump(), model=_model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
