# Renewable Forecast Assurance Layer

GitHub repository: [AmulyaSKumar/renewable-forecast-assurance-layer](https://github.com/AmulyaSKumar/renewable-forecast-assurance-layer)

## Overview

**Renewable Forecast Assurance Layer for Karnataka Grid Operations** is a decision-support prototype built for **Theme 10: AI for Renewable Generation Forecasting**.

The core idea is simple:

> A forecast alone does not tell operators what action to take.

This system predicts solar and wind generation at both **plant level** and **cluster level**, then converts those forecasts into:

- uncertainty-aware planning signals
- risk labels
- reserve recommendations
- critical risk windows
- operator-facing consequence estimates

So instead of only saying:

- "Expected generation is 320 MW"

the system can say:

- "High ramp risk between 11:00 and 12:00"
- "Recommended reserve: 50.86 MW"
- "Primary cause: wide uncertainty spread"
- "If ignored: balancing exposure increases"

That is why this project is positioned as a **forecast assurance and operator recommendation layer**, not just an ML dashboard.

---

## Problem Statement

Karnataka has high renewable penetration across different geographies and asset types. Solar output changes with:

- cloud cover
- irradiation
- temperature

Wind output changes with:

- wind speed
- wind direction
- local operating conditions

This creates a planning problem for grid operators:

- reserve commitments must be made before uncertainty fully resolves
- inaccurate forecasts lead to reserve stress
- operators may need late thermal ramp-up
- balancing exposure and curtailment pressure increase

The real problem is not only forecasting generation. The real problem is helping operators decide:

- **when the grid is entering a risky renewable window**
- **how much reserve to commit**
- **what happens if that recommendation is ignored**

---

## What the System Does

This prototype provides:

- hourly **day-ahead** renewable forecasts
- **intra-day update** logic
- **P10 / P50 / P90** uncertainty bands
- plant-level and cluster-level visibility
- **critical window detection**
- **reserve recommendation**
- **spinning reserve recommendation**
- **risk reason explanation**
- **what changed** summaries
- **if ignored** consequence simulation
- a frontend decision console for judges and operators

---

## Why This Approach

### Why quantile forecasting?
Because operators need uncertainty awareness, not only a point estimate.

### Why one generalized model framework?
Because the theme requires generalization across:

- solar and wind assets
- different geographies

without a separate custom model per plant.

### Why a read-only sidecar?
Because existing systems should not be replaced. This prototype is designed to sit above them as a forecasting and decision-support layer.

### Why deterministic recommendation logic?
Because reserve guidance must be explainable, reviewable, and easy to justify in operational settings.

### Why live weather integration?
Because it improves real-world credibility. The current prototype supports live weather at inference time while keeping historical generation synthetic for sandbox evaluation.

---

## Current System Architecture

The system is organized into five layers:

1. **Data layer**
2. **Forecasting backend**
3. **Forecast assurance layer**
4. **Operator recommendation layer**
5. **Planner dashboard**

### Input data

The backend uses:

- plant metadata
- historical generation
- weather variables

### Forecasting pipeline

The internal flow is:

`live + historical weather`
-> `renewable generation forecasting`
-> `uncertainty estimation`
-> `risk detection`
-> `reserve recommendation`
-> `consequence simulation`
-> `operator decision support`

---

## Live Weather vs Model Training

This is important:

- The **model is trained on historical data** available in the project dataset pipeline.
- The **live weather API is used at inference time**, not as the training source.

So:

- training = historical weather + historical generation
- prediction = trained model + latest forecast weather

This means the system can say:

> live weather inputs are integrated into the forecasting pipeline

while still remaining a sandbox prototype.

---

## Frontend: What Reviewers Will See

The frontend is a **decision console**, not a notebook UI.

### 1. Critical Operations Panel
This is the main first screen. It shows:

- critical risk window
- recommended reserve
- spinning reserve
- primary causes
- estimated impact if ignored

### 2. Operator Summary Cards
Quick KPI cards show:

- reserve to commit
- spinning reserve
- peak risk trigger
- if ignored exposure

### 3. What Changed
Shows:

- forecast delta
- reserve delta
- reason for change

### 4. Karnataka Risk Map
A simplified statewide cluster map that shows:

- cluster risk colors
- reserve stress per cluster

### 5. Peak Risk Timeline
An hourly timeline that shows:

- stable hours
- moderate volatility
- high-risk windows
- reserve action
- consequence of inaction

### 6. Cluster Forecast Chart
Displays the uncertainty band:

- `P10`
- `P50`
- `P90`

### 7. Plant Drilldown
Reviewers can click into specific plants to see:

- plant forecast
- reserve contribution
- top drivers
- risk explanation
- anomaly interpretation

---

## Repository Structure

```text
renewable-forecast-assurance-layer/
  backend/
  dashboard/
  submission/
  data/
  models/
  README.md
  DEPLOYMENT.md
  requirements.txt
  run_demo.ps1
```

### Folder meanings

- `backend/`  
  Forecasting logic, feature engineering, live weather integration, API, operator recommendation engine

- `dashboard/`  
  Vite + React frontend decision console

- `submission/`  
  Final submission documents, deck, and reviewer-facing materials

- `data/`  
  Generated sandbox data and live weather cache

- `models/`  
  Trained model artifacts and evaluation outputs

---

## Is the `models/` Folder Necessary in GitHub?

**Short answer: no, the trained model artifacts should not be pushed to GitHub.**

### What is in `models/`?
Usually:

- `forecast_bundle.joblib`
- `evaluation.json`

### What should be committed?

- `evaluation.json` is okay to keep if you want to preserve benchmark numbers for reviewers.

### What should NOT be committed?

- `forecast_bundle.joblib`
- any large generated binary artifact

### Why?

Because model artifacts are:

- generated outputs, not source code
- environment-sensitive
- often large
- sometimes incompatible across Python / scikit-learn versions

This project is designed so the model can be rebuilt locally or during deployment if needed.

### Practical recommendation

- keep the **`models/` folder conceptually** in the project
- do **not** push generated `.joblib` model files
- optionally keep only evaluation summaries if needed

---

## Is the `data/` Folder Necessary in GitHub?

For a clean hackathon repo:

- source code should be pushed
- generated CSV data generally should **not** be pushed if it can be recreated

This repo is already configured to ignore generated CSV files and model bundles through `.gitignore`.

---

## What Should Go To GitHub

Push these:

- `backend/`
- `dashboard/`
- `submission/`
- `README.md`
- `DEPLOYMENT.md`
- `requirements.txt`
- `.gitignore`
- `run_demo.ps1`

Do **not** push:

- `.venv/`
- `dashboard/node_modules/`
- `dashboard/dist/`
- generated logs
- generated CSVs
- generated model bundles

---

## How To Run Locally

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

### Frontend

Open a second terminal:

```powershell
cd dashboard
npm install
$env:VITE_API_BASE="http://127.0.0.1:8001"
npx vite --host 127.0.0.1 --port 5174
```

### URLs

- Frontend: `http://127.0.0.1:5174`
- Backend API: `http://127.0.0.1:8001`
- API docs: `http://127.0.0.1:8001/docs`

---

## Deployment Recommendation

Recommended split:

- **Frontend on Vercel**
- **Backend on Render or Railway**

Why:

- Vercel is ideal for the Vite frontend
- the Python backend is heavier and better suited to a persistent app host than a serverless-first runtime

Detailed deployment notes are in [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Submission Assets

Start with:

- [submission/SUBMISSION_BRIEF.md](submission/SUBMISSION_BRIEF.md)
- [submission/ARCHITECTURE.md](submission/ARCHITECTURE.md)
- [submission/DEMO_NOTES.md](submission/DEMO_NOTES.md)
- [submission/REPO_STRUCTURE.md](submission/REPO_STRUCTURE.md)
- [submission/Renewable_Forecast_Assurance_Layer_White_Theme_v2.pptx](submission/Renewable_Forecast_Assurance_Layer_White_Theme_v2.pptx)

---

## Final Positioning

This project should be described as:

> a read-only operational support layer for renewable instability

not as:

> just an AI forecasting dashboard

That distinction is important, because the product’s value comes from turning:

- forecast
- uncertainty
- risk
- reserve action
- operational consequence

into something grid operators can actually use.
