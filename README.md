# DiaRisk

Predict diabetes risk from standard clinical measurements (glucose, BMI, blood pressure, insulin, age, and related features).

Data: [Pima Indians Diabetes](https://archive.ics.uci.edu/dataset/34/diabetes) (UCI), 768 samples.

**Live API** (`eu-north-1`):

- Health: https://b2je1touwh.execute-api.eu-north-1.amazonaws.com/health
- Docs: https://b2je1touwh.execute-api.eu-north-1.amazonaws.com/docs
- Predict: `POST` https://b2je1touwh.execute-api.eu-north-1.amazonaws.com/predict

## Stack

- Training: scikit-learn logistic regression (baseline) and LightGBM, compared on a shared split
- Tracking: MLflow
- Serving: FastAPI, packaged as a container
- Production: AWS Lambda (container image on ECR) behind Amazon API Gateway
- CI: GitHub Actions (`pytest`, image build, GHCR)

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

Zeros in glucose, blood pressure, skin thickness, insulin, and BMI are treated as missing.

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

- Logistic regression: impute → scale → classifier → `artifacts/metrics_logistic.json`
- LightGBM: impute → classifier → `artifacts/metrics_lightgbm.json` and `models/diarisk_lightgbm.joblib`

On macOS, LightGBM needs OpenMP: `brew install libomp`

## Predict

```bash
python src/predict.py --json samples/example_patient.json
```

```json
{
  "diabetes_prediction": 1,
  "diabetes_probability": 0.72,
  "risk_level": "high"
}
```

## API (local)

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

Training logs parameters, metrics, and the model artifact under experiment `diarisk`.

```bash
python src/train_logistic.py
python src/train_lightgbm.py
mlflow ui --backend-store-uri ./mlruns --port 5001
```

http://127.0.0.1:5001 (port 5000 is often taken by AirPlay on macOS.)

## Tests

```bash
pytest -q
```

## Docker

Runtime image (API only; see `requirements-api.txt`):

```bash
docker build -t diarisk .
docker run --rm -p 8000:8000 diarisk
```

Lambda image: `Dockerfile.lambda`.

## CI

On every push or pull request to `main`, GitHub Actions installs dependencies, runs `pytest`, and builds the Docker images. Pushes to `main` also publish `ghcr.io/wasimahmadpk/diarisk`. Optional AWS rollout (ECR + Lambda) is gated by the repository variable `AWS_DEPLOY`.

## AWS

The production service is a Lambda function running the container image, exposed through an HTTP API in `eu-north-1`. Infrastructure is defined in `terraform-aws/`.

Deploy and operations: [docs/AWS_SETUP.md](docs/AWS_SETUP.md).
