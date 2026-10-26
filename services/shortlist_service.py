"""
Bulk shortlisting (recruiter mode): screen many resumes against ONE job
description and rank the candidates.

A job runs on a background thread so the browser is never blocked: the
recruiter uploads a batch, gets a job id immediately, and polls progress.
Per-resume processing budget is 7 seconds (config.SHORTLIST_*) - in practice
the pipeline finishes in well under a second per resume.

Verdicts per candidate, relative to the shortlist threshold (default 60):
    ats >= threshold            -> "Shortlisted"
    ats >= threshold - band     -> "Maybe"      (band default 15)
    otherwise                   -> "Rejected"
Files that are not resumes (cover letters, theses...) are skipped with a
reason instead of polluting the ranking.
"""

import io
import logging
import threading
import time
import uuid

from config import config
from services.classifier import ModelNotAvailableError, predict_with_confidence
from services.document_parser import extract_text
from services.information_extractor import extract_all
from services.job_description_parser import parse_job_description
from services.matching_engine import compare_resume_to_job
from services.ats_scorer import score_resume_vs_jd
from services.resume_detector import looks_like_resume, rejection_message

RESUME_BUDGET_SECONDS = 7.0

logger = logging.getLogger(__name__)

_JOBS: dict = {}
_LOCK = threading.Lock()
MAX_JOBS_KEPT = 20


def _prune_locked() -> None:
    """Keep only the most recent MAX_JOBS_KEPT jobs (by creation time)."""
    if len(_JOBS) <= MAX_JOBS_KEPT:
        return
    oldest = sorted(_JOBS.values(), key=lambda j: j["created"])[: len(_JOBS) - MAX_JOBS_KEPT]
    for job in oldest:
        _JOBS.pop(job["id"], None)


def create_job(files: list, jd_text: str, strictness: str = "standard",
               target_title: str | None = None,
               threshold: float | None = None) -> str:
    """Create a shortlist job from (filename, raw_bytes) pairs and start it on
    a background thread. Returns the job id."""
    threshold = float(threshold) if threshold is not None else config.SHORTLIST_DEFAULT_THRESHOLD
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "state": "queued",
        "created": time.time(),
        "total": len(files),
        "processed": 0,
        "results": [],
        "skipped": [],
        "errors": [],
        "per_resume_ms": [],
        "threshold": threshold,
        "maybe_band": config.SHORTLIST_MAYBE_BAND,
        "strictness": strictness,
        "jd_text": jd_text,
        "target_title": target_title,
        "files": [(filename, data) for filename, data in files],
        "started": None,
        "finished": None,
    }
    with _LOCK:
        _JOBS[job_id] = job
        _prune_locked()
    threading.Thread(target=_run_job, args=(job,), daemon=True, name=f"shortlist-{job_id}").start()
    return job_id


def get_job(job_id: str) -> dict | None:
    """A snapshot of the job without the heavy fields (files, full JD text)."""
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        return {k: v for k, v in job.items() if k not in {"files", "jd_text"}}


def wait_for_job(job_id: str, timeout: float = 120.0) -> dict | None:
    """Blocking helper for tests and scripts: waits until the job leaves the
    queued/running states."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = get_job(job_id)
        if job is None or job["state"] in {"done", "error"}:
            return job
        time.sleep(0.1)
    return get_job(job_id)


def _verdict(score: float | None, threshold: float, band: float) -> str:
    if score is None:
        return "Rejected"
    if score >= threshold:
        return "Shortlisted"
    if score >= threshold - band:
        return "Maybe"
    return "Rejected"


def _run_job(job: dict) -> None:
    job["state"] = "running"
    job["started"] = time.time()
    jd_data = parse_job_description(job["jd_text"])
    if job["target_title"]:
        jd_data["job_title"] = job["target_title"]

    for filename, raw in job["files"]:
        started = time.perf_counter()
        try:
            text = extract_text(io.BytesIO(raw), filename.rsplit(".", 1)[-1].lower())
            detection = looks_like_resume(text)
            if detection["verdict"] == "not_resume":
                job["skipped"].append({
                    "filename": filename,
                    "reason": rejection_message(detection),
                })
                continue

            resume_data = extract_all(text)
            match_result = compare_resume_to_job(resume_data, jd_data, text, job["jd_text"])
            ats = score_resume_vs_jd(
                text, job["jd_text"], resume_data, jd_data,
                match_result=match_result, strictness=job["strictness"],
            )
            total = ats.get("total")

            try:
                category = predict_with_confidence(text)[0]["category"]
            except ModelNotAvailableError:
                category = None

            # Persist to the ATS tracker so screened candidates appear in the
            # score history (private, max-age-cached views are per-id anyway).
            try:
                from database import database as db_module
                db_module.save_analysis(
                    filename, category, match_result, False, ats_result=ats,
                )
            except Exception as exc:
                logger.warning("shortlist: could not persist %s: %s", filename, exc)

            job["results"].append({
                "filename": filename,
                "ats_total": total,
                "grade": ats.get("grade"),
                "match_overall": (match_result.get("overall") or {}).get("overall_score"),
                "verdict": _verdict(total, job["threshold"], job["maybe_band"]),
                "years": resume_data.get("years_of_experience"),
                "skills_count": len(resume_data.get("skills", [])),
                "category": category,
                "top_suggestion": (ats.get("top_suggestions") or [{}])[0].get("text", ""),
                "potential": (ats.get("potential") or {}).get("total"),
            })
        except Exception as exc:  # one bad file must never kill the batch
            job["errors"].append({"filename": filename, "error": str(exc)})
        finally:
            job["per_resume_ms"].append((time.perf_counter() - started) * 1000)
            job["processed"] += 1

    job["results"].sort(
        key=lambda r: r["ats_total"] if r["ats_total"] is not None else -1.0, reverse=True
    )
    job["shortlisted_count"] = sum(1 for r in job["results"] if r["verdict"] == "Shortlisted")
    job["maybe_count"] = sum(1 for r in job["results"] if r["verdict"] == "Maybe")
    job["rejected_count"] = sum(1 for r in job["results"] if r["verdict"] == "Rejected")
    job["state"] = "done"
    job["finished"] = time.time()
