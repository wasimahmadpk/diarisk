# DiaRisk

Predict whether a patient is likely diabetic from standard clinical measurements
(glucose, BMI, blood pressure, insulin, age, etc.).

Data: [Pima Indians Diabetes](https://archive.ics.uci.edu/dataset/34/diabetes) (UCI), 768 samples.

## Status

- [x] data + EDA notebook
- [x] logistic regression baseline
- [x] LightGBM + comparison
- [x] model export / JSON inference
- [x] FastAPI
- [x] MLflow
- [x] tests
- [x] Docker + CI
- [x] cloud deploy (AWS Lambda + HTTP API, eu-north-1)

## Setup

```bash
git clone https://github.com/wasimahmadpk/diarisk.git
cd diarisk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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

Zeros in glucose / BP / skin / insulin / BMI are treated as missing.

EDA:

```bash
jupyter notebook notebooks/01_basic_data_analysis.ipynb
# or
python src/explore_data.py
```

## Train

Same split for both models (`seed=42`, 80/20, stratified).

```bash
python src/train_logistic.py
python src/train_lightgbm.py
python src/compare_models.py
```

- Logistic: impute → scale → logistic regression → `artifacts/metrics_logistic.json`
- LightGBM: impute → LightGBM → `artifacts/metrics_lightgbm.json` + `models/diarisk_lightgbm.joblib`

On macOS, LightGBM needs OpenMP: `brew install libomp`

## Predict

```bash
python src/train_lightgbm.py   # once, saves the model
python src/predict.py --json samples/example_patient.json
```

Example output:

```json
{
  "diabetes_prediction": 1,
  "diabetes_probability": 0.72,
  "risk_level": "high"
}
```

## API

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

Training logs params + metrics (+ model artifact) under experiment `diarisk`.

```bash
python src/train_logistic.py
python src/train_lightgbm.py
mlflow ui --backend-store-uri ./mlruns --port 5001
```

Open http://127.0.0.1:5001 and compare the two runs.
(On macOS, port 5000 is often taken by AirPlay.)

## Tests

```bash
pytest -q
```

## Docker

```bash
docker build -t diarisk .
docker run --rm -p 8000:8000 diarisk
```

Then: http://localhost:8000/docs

The image installs `requirements-api.txt` only (no notebooks, plotting or
MLflow). `Dockerfile.lambda` packages the same app for AWS Lambda.

## CI

GitHub Actions (`.github/workflows/ci.yml`) on every push/PR to `main`:

1. install deps + `pytest`
2. build Docker image
3. on push to `main`, push image to `ghcr.io/wasimahmadpk/diarisk`
4. on push to `main`, build + push to ECR and update the Lambda function
   (only when the repository variable `AWS_DEPLOY` is `true`)

## Cloud deploy (AWS)

Live API (Stockholm, `eu-north-1`):

- Health: https://b2je1touwh.execute-api.eu-north-1.amazonaws.com/health
- Docs: https://b2je1touwh.execute-api.eu-north-1.amazonaws.com/docs

The function runs as a container on Lambda. On the new AWS Free plan the
Function URL stays Forbidden, so a cheap HTTP API sits in front. Idle cost is
still zero. Use `eu-north-1` — Frankfurt is blocked by the account's home-Region
SCP. Details: [docs/AWS_SETUP.md](docs/AWS_SETUP.md)
