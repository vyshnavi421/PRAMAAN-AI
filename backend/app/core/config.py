"""
PRAMAAN-AI Core Configuration
"""
from pydantic import BaseModel
import os

class Settings(BaseModel):
    PROJECT_NAME: str = "PRAMAAN-AI"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    IS_DEMO_MODE: bool = os.getenv("IS_DEMO_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}
    DEMO_BANNER_TEXT: str = "DEMO DATA — NOT CONNECTED TO LIVE AICTE SYSTEMS"
    STORAGE_DIR: str = os.getenv("PRAMAAN_STORAGE_DIR", "storage/uploads")
    MIN_OCR_CONFIDENCE_THRESHOLD: float = 0.65
    # Empty = in-memory only (tests). Set PRAMAAN_DATA_DIR to persist applications, reviews and audit ledger.
    DATA_DIR: str = os.getenv("PRAMAAN_DATA_DIR", "")

settings = Settings()
