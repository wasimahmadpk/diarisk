# DiaRisk

Predict whether a patient is likely diabetic from standard clinical measurements
(glucose, BMI, blood pressure, insulin, age, etc.).

Data: [Pima Indians Diabetes](https://archive.ics.uci.edu/dataset/34/diabetes) (UCI), 768 samples.

## Status

- [x] data + EDA notebook
- [x] logistic regression baseline
- [x] LightGBM + comparison
- [x] model export / JSON inference
- [ ] FastAPI
- [ ] MLflow
- [ ] tests
- [ ] Docker + CI
- [ ] cloud deploy

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
