# DiaRisk

**Diabetes risk prediction** from clinical health features, using the  
[Pima Indians Diabetes](https://archive.ics.uci.edu/dataset/34/diabetes) dataset  
(UCI Machine Learning Repository — established, widely used benchmark data).

Predict diabetes likelihood from glucose, BMI, age, blood pressure, and related measurements.  
Built with a modern MLOps stack: training → evaluation → API → tracking → CI/CD → cloud.

---

## Project roadmap

| Step | What we do | Status |
|------|------------|--------|
| **1** | Project setup & data analysis | ✅ done |
| **2a** | Train Logistic Regression baseline | ✅ current |
| **2b** | Train LightGBM and compare | next |
| **3** | Deeper evaluation (confusion matrix, etc.) | pending |
| **4** | Persist model + JSON inference | pending |
| **5** | FastAPI serving | pending |
| **6** | MLflow tracking | pending |
| **7** | Tests | pending |
| **8** | Docker | pending |
| **9** | GitHub Actions CI | pending |
| **10** | Deploy (e.g. Cloud Run) | pending |

---

## Step 1 — Data

**Dataset:** Pima Indians Diabetes  
**File:** `data/raw/pima-indians-diabetes.csv`

| Column | Meaning |
|--------|---------|
| pregnancies | Number of pregnancies |
| glucose | Plasma glucose concentration |
| blood_pressure | Diastolic blood pressure |
| skin_thickness | Triceps skin fold thickness |
| insulin | 2-Hour serum insulin |
| bmi | Body mass index |
| diabetes_pedigree | Diabetes pedigree function |
| age | Age in years |
| outcome | 1 = diabetes, 0 = no diabetes |

### Explore the data

**Notebook:** `notebooks/01_basic_data_analysis.ipynb`

```bash
cd /Users/wasim/diarisk
source .venv/bin/activate
jupyter notebook notebooks/01_basic_data_analysis.ipynb
```

Or the CLI script:

```bash
python src/explore_data.py
```

---

## Step 2a — Logistic Regression baseline

Train a baseline first, then compare against stronger models (e.g. LightGBM).

```bash
cd /Users/wasim/diarisk
source .venv/bin/activate
python src/train_logistic.py
```

Pipeline: **median impute** (zeros→missing) → **StandardScaler** → **LogisticRegression**  
Metrics: `artifacts/metrics_logistic.json`
