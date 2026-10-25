# PRAMAAN-AI Fresh Environment Setup & Execution Guide

**SIH Problem Statement:** SIH26261 — Evidence-First Validation Copilot for AICTE Approvals  
**System Architecture:** FastAPI Modular Monolith + Pure ES6 Frontend + File-Backed Protected Storage

---

## 1. Prerequisites

- **Python**: Version 3.11, 3.12, or 3.13.
- **Node.js** (Optional): Version 22+ for local JavaScript syntax checks; GitHub Actions performs this check automatically.
- **Tesseract OCR** (Optional): For optical character recognition on scanned raster images. If absent, the system honestly abstains (`status = MANUAL_REVIEW_REQUIRED`) without fabricating claims.
- **Operating System**: Linux, macOS, or Windows (PowerShell/CMD).

---

## 2. Fresh Environment Installation

### Step A: Clone / Navigate to Repository
```bash
git clone <repository_url> pramaan-ai
cd pramaan-ai
```

### Step B: Create and Activate Virtual Environment
**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step C: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step D: Configure Environment Variables
```bash
# On Linux / macOS
cp .env.example .env

# On Windows (PowerShell)
Copy-Item .env.example .env
```

---

## 3. Running Automated Tests & Verification

### Run the current backend test suite

Run from the repository root:

```bash
# Linux / macOS
PYTHONPATH=backend python -m pytest backend/tests -q

# Windows PowerShell
$env:PYTHONPATH="$PWD\backend"
python -m pytest backend/tests -q
```

Do not use a fixed expected test count; new regression tests are added over time. GitHub Actions runs the suite on Python 3.11 and 3.13 and compiles the Python modules.

### Check frontend syntax

The frontend is composed of browser ES modules, not a Node.js package. The [Quality Gates workflow](https://github.com/vyshnavi421/PRAMAAN-AI/actions/workflows/ci.yml) checks all JavaScript modules as ES modules using Node.js 22.

### Run the 15-bundle synthetic benchmark

From the repository root:

```bash
python backend/run_benchmark.py
```

The benchmark uses synthetic fixtures and writes measurements to `docs/EVALUATION_REPORT.md`. Rerun it before quoting any latency or accuracy figure.

---

## 4. Starting the Application Server

From the repository root:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
```

Open `http://127.0.0.1:8000/` in a browser. The server also exposes:
- **Swagger API docs:** `http://127.0.0.1:8000/api/v1/docs`
- **Health probe:** `http://127.0.0.1:8000/health`

---

## 5. Browser Demo Smoke Check and Walkthrough

With `PYTHONPATH=backend` set (PowerShell: `$env:PYTHONPATH="$PWD\backend"`), run the checked-in smoke tests:

```bash
python -m pytest backend/tests/test_demo_smoke.py -q
```

These tests confirm that the health endpoint responds, the UI includes the synthetic-data disclosure, and the browser entry modules and stylesheet are served. They do not replace testing every interaction in a real browser.

For the 3–5 minute reviewer walkthrough, follow [`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md).

> **Reproducibility note:** Some older internal notes refer to `scratch/verify_flow.py`. That local-only script is not included in this repository. Use the checked-in pytest suite and the browser walkthrough instead.
