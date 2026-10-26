"""
Loads the raw resume dataset, cleans it (missing values, duplicates), applies
the shared NLP preprocessing pipeline, and saves a processed CSV ready for
TF-IDF vectorization in training/train_model.py.

Usage:
    .venv\\Scripts\\python.exe -m training.prepare_dataset
"""

import pandas as pd
from pathlib import Path

from config import config
from services.text_preprocessor import preprocess_text


def load_raw_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"resume_text", "category"}
    if not required.issubset(df.columns):
        raise ValueError(f"Dataset must contain columns: {required}")
    return df


def load_real_dataset(path: str) -> pd.DataFrame | None:
    """Merge the real labeled resumes (downloaded public dataset, mapped to
    the 9 project categories) into training when the file exists. Real data
    is the single biggest accuracy lever for real-world performance."""
    p = Path(path)
    if not p.exists():
        return None
    real = pd.read_csv(p)
    if not {"resume_text", "category"}.issubset(real.columns):
        return None
    print(f"Merging real labeled resumes: {len(real)} rows from {path}")
    return real


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values, blank rows, and duplicate resume texts."""
    before = len(df)

    df = df.dropna(subset=["resume_text", "category"]).copy()
    df["resume_text"] = df["resume_text"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df = df[(df["resume_text"] != "") & (df["category"] != "")]

    df = df.drop_duplicates(subset=["resume_text"])

    after = len(df)
    print(f"Cleaned dataset: {before} -> {after} rows (removed {before - after} empty/duplicate rows).")
    return df.reset_index(drop=True)


def preprocess_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the shared NLP pipeline (clean -> tokenize -> stopwords -> lemmatize)."""
    df["processed_text"] = df["resume_text"].apply(preprocess_text)

    empty_mask = df["processed_text"].str.strip() == ""
    if empty_mask.any():
        print(f"WARNING: {empty_mask.sum()} rows became empty after preprocessing and will be dropped.")
        df = df[~empty_mask]
    return df.reset_index(drop=True)


def main() -> None:
    df = load_raw_dataset(config.RAW_DATASET_PATH)
    df = clean_dataset(df)
    real = load_real_dataset(config.REAL_DATASET_PATH)
    if real is not None:
        real = clean_dataset(real)
        df = pd.concat([df, real], ignore_index=True)
        df = df.drop_duplicates(subset=["resume_text"])
    df = preprocess_dataset(df)

    print("\nCategory distribution:")
    print(df["category"].value_counts())

    df[["resume_text", "processed_text", "category"]].to_csv(config.PROCESSED_DATASET_PATH, index=False)
    print(f"\nSaved processed dataset ({len(df)} rows) to: {config.PROCESSED_DATASET_PATH}")


if __name__ == "__main__":
    main()
