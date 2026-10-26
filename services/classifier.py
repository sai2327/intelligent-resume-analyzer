"""
Loads the trained TF-IDF vectorizer + calibrated multi-model classifier ensemble
and exposes resume category prediction to the rest of the application.
The model is loaded once and cached in memory (never retrained on each request/startup).
Predictions are memoized per resume text: the tracker workflow re-analyzes
the same files repeatedly.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from config import config
from services.text_preprocessor import preprocess_text

logger = logging.getLogger(__name__)

_classifier = None
_vectorizer = None
_labels = None
_mlp = None
_scaler = None
_logreg = None
_load_attempted = False


class ModelNotAvailableError(Exception):
    """Raised when the classifier/vectorizer artifacts have not been trained yet."""


def load_model() -> None:
    """Load the classifier, vectorizer, and ensemble heads from disk once, caching in memory."""
    global _classifier, _vectorizer, _labels, _mlp, _scaler, _logreg, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True
    try:
        _classifier = joblib.load(config.CLASSIFIER_PATH)
        _vectorizer = joblib.load(config.VECTORIZER_PATH)
        with open(config.LABEL_LIST_PATH, "r", encoding="utf-8") as f:
            _labels = json.load(f)

        meta_path = Path(config.MODEL_DIR) / "model_metadata.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            mlp_file = Path(config.MODEL_DIR) / "resume_mlp.pkl"
            scaler_file = Path(config.MODEL_DIR) / "feature_scaler.pkl"
            logreg_file = Path(config.MODEL_DIR) / "resume_logreg.pkl"

            if meta.get("use_ensemble") and mlp_file.exists() and scaler_file.exists():
                _mlp = joblib.load(mlp_file)
                _scaler = joblib.load(scaler_file)
                if logreg_file.exists():
                    _logreg = joblib.load(logreg_file)
                logger.info(
                    "Multi-model ensemble selected (accuracy %.4f) - predictions use calibrated soft-vote.",
                    meta.get("ensemble_accuracy", 0),
                )
            else:
                _mlp = None
                _scaler = None
                _logreg = None
                logger.info(
                    "Calibrated LinearSVC selected (holdout %.4f).",
                    meta.get("svm_accuracy", 0),
                )
        else:
            _mlp = None
            _scaler = None
            _logreg = None
    except FileNotFoundError as exc:
        logger.warning(
            "Classifier artifacts not found (%s). Run training/train_model.py first.", exc
        )
        _classifier = None
        _vectorizer = None
        _labels = None
        _mlp = None
        _scaler = None
        _logreg = None


def is_model_available() -> bool:
    load_model()
    return _classifier is not None and _vectorizer is not None


@lru_cache(maxsize=256)
def _predict_cached(resume_text: str) -> tuple:
    """Memoized calibrated probabilities for one resume text. Returns a tuple
    of (category, confidence) pairs, highest confidence first - immutable, so
    the cache can never be mutated by callers."""
    load_model()
    if not is_model_available():
        raise ModelNotAvailableError(
            "The resume classifier has not been trained yet. Run "
            "'python -m training.train_model' first."
        )
    processed = preprocess_text(resume_text)
    vector = _vectorizer.transform([processed])
    probabilities = _classifier.predict_proba(vector)
    classes = list(_classifier.classes_)

    # Calibrated Soft-Voting Ensemble: blend predictions when ensemble heads are active
    if _mlp is not None and _scaler is not None:
        scaled_vec = _scaler.transform(vector)
        mlp_proba = _mlp.predict_proba(scaled_vec)
        if list(_mlp.classes_) == classes:
            if _logreg is not None and list(_logreg.classes_) == classes:
                lr_proba = _logreg.predict_proba(vector)
                probabilities = (probabilities * 0.45) + (mlp_proba * 0.35) + (lr_proba * 0.20)
            else:
                probabilities = (probabilities + mlp_proba) / 2.0

    ranked = sorted(zip(classes, probabilities[0]), key=lambda pair: pair[1], reverse=True)
    return tuple((category, round(float(prob), 4)) for category, prob in ranked)


def predict_category(resume_text: str) -> str:
    """Predict the single most likely job category for a resume."""
    return _predict_cached(resume_text)[0][0]


def predict_with_confidence(resume_text: str, top_n: int = 3) -> list:
    """
    Predict the top-N most likely categories with calibrated confidence
    scores (0-1). These come from CalibratedClassifierCV's predict_proba
    (sigmoid calibration over LinearSVC) - an approximate calibrated
    estimate, never a fabricated probability.
    """
    return [
        {"category": category, "confidence": confidence}
        for category, confidence in _predict_cached(resume_text)[:top_n]
    ]
