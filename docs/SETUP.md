# PRAMAAN-AI Fresh Environment Setup & Execution Guide

**SIH Problem Statement:** SIH26261 — Evidence-First Validation Copilot for AICTE Approvals  
**System Architecture:** FastAPI Modular Monolith + Pure ES6 Frontend + File-Backed Protected Storage

---

## 1. Prerequisites

- **Python**: Version 3.11, 3.12, or 3.13.
- **Node.js** (Optional): Version 18+ (only required if running `node --check` static syntax verification).
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

### Run Full Test Suite (107 Tests)
```bash
python -m pytest backend/tests -v
```
*Expected Result:* `107 passed in ~18s (100% green)`

### Run Static JavaScript Syntax Validation
```bash
node --check backend/static/js/api.js backend/static/js/app.js
```

### Run Labelled 15-Bundle Benchmark
```bash
python backend/run_benchmark.py
```
*Expected Result:* Evaluates 15 synthetic application bundles across all edge cases (clean, expired, cross-document mismatch, duplicate reuse, timeout, etc.).

---

## 4. Starting the Application Server

Start the FastAPI application with live hot-reloading:

```bash
# From workspace root
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
```
*(Or navigate to `cd backend` and run `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`)*

---

## 5. Accessing the System

Once Uvicorn is running:
- **Interactive Reviewer Studio (Web UI):** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger Interactive API Documentation:** [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **ReDoc API Documentation:** [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)
- **System Health Probe:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 6. End-to-End Programmatic Flow Verification

With the server running, execute the automated 13-step verification script:
```bash
python scratch/verify_flow.py
```

The script verifies:
1. Health & readiness probe.
2. Server-validated demo session creation.
3. Secure document intake & SHA-256 byte persistence.
4. Real PDF visitor text stream coordinate extraction.
5. Complete Pre-Scrutiny execution.
6. 100% Coverage audit reconciliation.
7. Finding navigation & handbook citations.
8. Evidence graph link traceability.
9. Cross-application duplicate and change-aware historical review.
10. Honest uncertainty and source-unavailable timeouts.
11. Human review decision modal and audit logging.
12. Report reopening from persistence.
13. Cryptographic hash-chain integrity & tamper simulation.
