"""
SQLite persistence for analysis history. Stores only non-sensitive summary
data (scores, category, filename) - never raw resume text, names, emails, or
phone numbers - to avoid unnecessarily persisting personal data. All queries
use parameterized placeholders (never string-formatted SQL).
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    resume_filename TEXT,
    predicted_category TEXT,
    overall_score REAL,
    skill_score REAL,
    similarity_score REAL,
    experience_score REAL,
    education_score REAL,
    matched_required_count INTEGER,
    missing_required_count INTEGER,
    gemini_used INTEGER NOT NULL DEFAULT 0,
    ats_score REAL,
    ats_mode TEXT,
    ats_grade TEXT,
    ats_breakdown TEXT
);
"""

# Column additions for databases created before the ATS tracker existed.
# Each statement is applied once; "duplicate column name" errors mean the
# migration already ran and are ignored.
MIGRATIONS = [
    "ALTER TABLE analyses ADD COLUMN ats_score REAL",
    "ALTER TABLE analyses ADD COLUMN ats_mode TEXT",
    "ALTER TABLE analyses ADD COLUMN ats_grade TEXT",
    "ALTER TABLE analyses ADD COLUMN ats_breakdown TEXT",
]


@contextmanager
def get_connection():
    Path(config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    # timeout + busy_timeout keep concurrent uploads from failing with
    # "database is locked" when several analyses finish at once; WAL journal
    # mode lets readers and writers proceed in parallel.
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the database schema if it does not already exist, then apply
    any pending column migrations (idempotent)."""
    with get_connection() as conn:
        conn.execute(SCHEMA)
        for statement in MIGRATIONS:
            try:
                conn.execute(statement)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise


def save_analysis(
    resume_filename,
    predicted_category,
    match_result,
    gemini_used: bool,
    ats_result: dict | None = None,
) -> int:
    """Persist a summary record of one analysis run. Returns the new row id."""
    overall_score = skill_score = similarity_score = experience_score = education_score = None
    matched_required_count = missing_required_count = None

    if match_result:
        overall_score = match_result.get("overall", {}).get("overall_score")
        skill_score = match_result.get("skill_match", {}).get("required_skill_score")
        similarity_score = match_result.get("text_similarity")
        experience_score = match_result.get("experience_match", {}).get("score")
        education_score = match_result.get("education_match", {}).get("score")
        matched_required_count = len(match_result.get("skill_match", {}).get("matched_required", []))
        missing_required_count = len(match_result.get("skill_match", {}).get("missing_required", []))

    ats_score = ats_mode = ats_grade = ats_breakdown = None
    if ats_result:
        ats_score = ats_result.get("total")
        ats_mode = ats_result.get("mode")
        ats_grade = ats_result.get("grade")
        # Persist the full breakdown so the tracker can show what changed
        # over time without recomputing old analyses.
        ats_breakdown = json.dumps(ats_result, ensure_ascii=False)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO analyses (
                created_at, resume_filename, predicted_category, overall_score,
                skill_score, similarity_score, experience_score, education_score,
                matched_required_count, missing_required_count, gemini_used,
                ats_score, ats_mode, ats_grade, ats_breakdown
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                resume_filename,
                predicted_category,
                overall_score,
                skill_score,
                similarity_score,
                experience_score,
                education_score,
                matched_required_count,
                missing_required_count,
                int(gemini_used),
                ats_score,
                ats_mode,
                ats_grade,
                ats_breakdown,
            ),
        )
        return cursor.lastrowid


def get_analysis(analysis_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return dict(row) if row else None


# Columns for list views: ats_breakdown is a multi-KB JSON blob that history
# tables and progress math never need - excluding it keeps the tracker page
# light and fast no matter how many runs are stored.
_LIST_COLUMNS = (
    "id, created_at, resume_filename, predicted_category, overall_score, "
    "skill_score, similarity_score, experience_score, education_score, "
    "matched_required_count, missing_required_count, gemini_used, "
    "ats_score, ats_mode, ats_grade"
)


def list_recent_analyses(limit: int = 20) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {_LIST_COLUMNS} FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_tracker_stats() -> dict:
    """Aggregate ATS-tracker statistics across all recorded analyses."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_runs,
                COUNT(ats_score) AS scored_runs,
                AVG(ats_score) AS avg_ats,
                MAX(ats_score) AS best_ats,
                MIN(ats_score) AS worst_ats,
                AVG(overall_score) AS avg_match
            FROM analyses
            """
        ).fetchone()
        return dict(row)


def get_file_progress(limit: int = 500) -> list:
    """Per-resume score progress across repeated analyses: for every filename
    analyzed at least twice, first -> last ATS score, delta, and direction.
    This is the 'track my improvements' view of the tracker."""
    rows = list_recent_analyses(limit=limit)
    by_file = {}
    for row in rows:  # newest first; reverse to chronological
        if not row.get("resume_filename") or row.get("ats_score") is None:
            continue
        by_file.setdefault(row["resume_filename"], []).append(row)

    progress = []
    for filename, runs in by_file.items():
        if len(runs) < 2:
            continue
        runs = list(reversed(runs))
        first, last = runs[0], runs[-1]
        delta = round(last["ats_score"] - first["ats_score"], 1)
        progress.append({
            "filename": filename,
            "runs": len(runs),
            "first_score": first["ats_score"],
            "last_score": last["ats_score"],
            "delta": delta,
            "best_score": max(r["ats_score"] for r in runs),
            "direction": "up" if delta > 0.05 else ("down" if delta < -0.05 else "flat"),
            # Chronological scores for the per-row sparkline.
            "scores": [r["ats_score"] for r in runs],
        })
    progress.sort(key=lambda p: abs(p["delta"]), reverse=True)
    return progress
