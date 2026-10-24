#!/usr/bin/env bash
# Start PRAMAAN-AI with persistence enabled. Open http://127.0.0.1:8000
cd "$(dirname "$0")/backend" && pip install -q -r requirements.txt && PRAMAAN_DATA_DIR="${PRAMAAN_DATA_DIR:-data}" python -m uvicorn app.main:app --port 8000
