# DiaRisk

Predict diabetes risk from standard clinical measurements (glucose, BMI, blood pressure, insulin, age, and related features).

Data: [Pima Indians Diabetes](https://archive.ics.uci.edu/dataset/34/diabetes) (UCI), 768 samples.

This is a decision-support model, not a medical diagnosis.

## Live API

Region: `eu-north-1`. Interactive docs: [Swagger UI](https://b2je1touwh.execute-api.eu-north-1.amazonaws.com/docs).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service and model status |
| `/stats` | GET | CloudWatch traffic, latency, errors (last 24h) |
| `/predict` | POST | Risk score from eight clinical fields |
| `/docs` | GET | OpenAPI UI |

```bash
curl -s https://b2je1touwh.execute-api.eu-north-1.amazonaws.com/health

curl -s https://b2je1touwh.execute-api.eu-north-1.amazonaws.com/predict \
  -H 'Content-Type: application/json' \
  -d @samples/example_patient.json
```

Example response:

```json
{
  "diabetes_prediction": 1,
  "diabetes_probability": 0.8702,
  "risk_level": "high"
}
```

`risk_level` is `low` (< 0.3), `moderate` (< 0.6), or `high`.

## Demo UI

A single static page in `web/` posts to the live API. On Vercel, set **Root Directory** to `web` and leave install/build empty. Do not install `requirements.txt` — that is only for the AWS API.

## Architecture

```
train → joblib → FastAPI container → ECR → Lambda → API Gateway
```

- Training: logistic regression baseline and LightGBM on the same 80/20 stratified split (`seed=42`)
- Tracking: MLflow experiment `diarisk`
- Serving: FastAPI in a container (`Dockerfile` locally, `Dockerfile.lambda` on AWS)
- Production: Lambda + HTTP API; infrastructure in `terraform-aws/`
- CI: GitHub Actions (`pytest`, image build, publish to GHCR)

## Setup

```bash
git clone https://github.com/wasimahmadpk/diarisk.git
cd diarisk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On macOS, LightGBM needs OpenMP: `brew install libomp`

## Data

Raw file: `data/raw/pima-indians-diabetes.csv`

| column | description |
|--------|-------------|
| pregnancies | number of pregnancies |
| glucose | plasma glucose |
| blood_pressure | diastolic BP |
| skin_thickness | triceps skin fold |
| insulin | 2-hour serum insulin |
| bmi | body mass index |
| diabetes_pedigree | diabetes pedigree function |
| age | age in years |
| outcome | 1 = diabetes, 0 = not |

Zeros in glucose, blood pressure, skin thickness, insulin, and BMI are treated as missing.

```bash
jupyter notebook notebooks/01_basic_data_analysis.ipynb
python src/explore_data.py
```

## Train

```bash
python src/train_logistic.py
python src/train_lightgbm.py
python src/compare_models.py
```

| Model | Pipeline | Output |
|-------|----------|--------|
| Logistic regression | impute → scale → classifier | `artifacts/metrics_logistic.json` |
| LightGBM | impute → classifier | `artifacts/metrics_lightgbm.json`, `models/diarisk_lightgbm.joblib` |

## Predict (local)

```bash
python src/predict.py --json samples/example_patient.json
```

```bash
uvicorn api:app --app-dir src --reload --port 8000
```

- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

```bash
curl -s http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d @samples/example_patient.json
```

## MLflow

```bash
python src/train_logistic.py
python src/train_lightgbm.py
mlflow ui --backend-store-uri ./mlruns --port 5001
```

Open http://127.0.0.1:5001 (port 5000 is often used by AirPlay on macOS).

## Tests

```bash
pytest -q
```

## Docker

Runtime image (API dependencies only: `requirements-api.txt`):

```bash
docker build -t diarisk .
docker run --rm -p 8000:8000 diarisk
```

Lambda image: `Dockerfile.lambda`.

## CI

On each push or pull request to `main`, GitHub Actions installs dependencies, runs `pytest`, and builds both images. Pushes to `main` also publish `ghcr.io/wasimahmadpk/diarisk`. Updating Lambda from CI is optional (`AWS_DEPLOY` repository variable).

## Operations

Terraform and deploy steps: [docs/AWS_SETUP.md](docs/AWS_SETUP.md).

Lambda metrics (invocations, errors, duration): [diarisk-api Monitor](https://eu-north-1.console.aws.amazon.com/lambda/home?region=eu-north-1#/functions/diarisk-api?tab=monitoring).
