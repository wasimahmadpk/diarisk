# DiaRisk

Educational MLOps project: **diabetes risk prediction** from simple health features  
(Pima Indians Diabetes dataset).

> **Disclaimer:** Demo only — not medical advice. Not for clinical use.

---

## Learning path (Schritt für Schritt)

| Step | What we do | Status |
|------|------------|--------|
| **1** | Project + download & understand data | ✅ current |
| **2** | Train a first model | next |
| **3** | Evaluate (accuracy is not enough) | pending |
| **4** | Save model + predict from JSON | pending |
| **5** | FastAPI serving | pending |
| **6** | MLflow tracking | pending |
| **7** | Tests | pending |
| **8** | Docker | pending |
| **9** | GitHub Actions CI | pending |
| **10** | Deploy (e.g. Cloud Run) | pending |

We finish one step before starting the next.

---

## Step 1 — Data

**Dataset:** Pima Indians Diabetes (UCI / public mirrors)  
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

```bash
cd /Users/wasim/diarisk
source .venv/bin/activate
python src/explore_data.py
```
