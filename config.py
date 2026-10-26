"""
Central configuration for the Resume Analyzer application.

All settings are loaded from environment variables (via a local .env file)
so that no secrets or machine-specific paths are hardcoded in source code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a .env file in the project root (if present).
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


class Config:
    """Application-wide configuration, populated from environment variables."""

    BASE_DIR = BASE_DIR

    # --- Flask ---
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")
    DEBUG = _get_bool("FLASK_DEBUG", False)
    SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "5000"))

    # --- Bulk shortlisting (recruiter mode) ---
    SHORTLIST_MAX_FILES = int(os.getenv("SHORTLIST_MAX_FILES", "600"))
    SHORTLIST_DEFAULT_THRESHOLD = float(os.getenv("SHORTLIST_DEFAULT_THRESHOLD", "60"))
    SHORTLIST_MAYBE_BAND = float(os.getenv("SHORTLIST_MAYBE_BAND", "15"))  # points below threshold
    
    # --- GPU Optimization ---
    USE_GPU = _get_bool("USE_GPU", True)  # Auto-detect and use GPU if available
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))  # Batch processing for GPU efficiency
    NUM_WORKERS = int(os.getenv("NUM_WORKERS", "4"))  # Parallel processing workers

    # --- File uploads ---
    # Uploaded resumes/JDs are parsed entirely in memory and never written to
    # disk (see services/document_parser.py), so there is no UPLOAD_FOLDER.
    ALLOWED_EXTENSIONS = {"pdf", "docx"}
    MAX_CONTENT_LENGTH_MB = _get_float("MAX_CONTENT_LENGTH_MB", 10)
    MAX_CONTENT_LENGTH = int(MAX_CONTENT_LENGTH_MB * 1024 * 1024)

    # --- Database ---
    DATABASE_PATH = str(BASE_DIR / os.getenv("DATABASE_PATH", "database/app.db"))

    # --- Models ---
    MODEL_DIR = str(BASE_DIR / os.getenv("MODEL_DIR", "models"))
    CLASSIFIER_PATH = str(Path(MODEL_DIR) / "resume_classifier.pkl")
    VECTORIZER_PATH = str(Path(MODEL_DIR) / "tfidf_vectorizer.pkl")
    LABEL_LIST_PATH = str(Path(MODEL_DIR) / "labels.json")
    TRAINING_REPORT_PATH = str(Path(MODEL_DIR) / "training_report.txt")

    # --- Data ---
    DATA_DIR = str(BASE_DIR / "data")
    SKILLS_PATH = str(BASE_DIR / "data" / "skills.json")
    RAW_DATASET_PATH = str(BASE_DIR / "data" / "raw" / "resume_dataset.csv")
    REAL_DATASET_PATH = str(BASE_DIR / "data" / "external" / "real_resumes_mapped.csv")
    PROCESSED_DATASET_PATH = str(BASE_DIR / "data" / "processed" / "resume_dataset_processed.csv")


    # --- Scoring weights (must sum to ~1.0) ---
    SCORE_WEIGHTS = {
        "skills": _get_float("SCORE_WEIGHT_SKILLS", 0.50),
        "similarity": _get_float("SCORE_WEIGHT_SIMILARITY", 0.25),
        "experience": _get_float("SCORE_WEIGHT_EXPERIENCE", 0.15),
        "education": _get_float("SCORE_WEIGHT_EDUCATION", 0.10),
    }

    # --- ATS score tracker weights (each dict must sum to ~1.0) ---
    # Factors that cannot be computed for a given resume/JD pair are excluded
    # and their weight is redistributed proportionally across the rest, so a
    # missing component never silently drags the score down.
    ATS_WEIGHTS_JOB_MATCH = {
        "keywords": 0.25,    # JD keyword coverage (what keyword-parsing ATS rank first)
        "skills": 0.25,      # required/preferred skill overlap
        "title": 0.10,       # job-title similarity
        "experience": 0.15,  # years-of-experience vs requirement
        "education": 0.05,
        "format": 0.10,      # parser-friendliness (contact info, sections, dates, length)
        "content": 0.10,     # quantified achievements, action verbs, style
    }
    ATS_WEIGHTS_STANDALONE = {
        "format": 0.35,
        "content": 0.30,
        "skills": 0.20,      # breadth + diversity of detected skills
        "education": 0.15,   # education section present with a recognizable degree
    }

    # --- Logging ---
    LOG_DIR = str(BASE_DIR / "logs")
    LOG_FILE = str(Path(LOG_DIR) / "app.log")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


config = Config()
