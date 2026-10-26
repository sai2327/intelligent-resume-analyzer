"""
Orchestrates the full analysis pipeline: resume parsing + classification + ATS
scoring, and (optionally) job description parsing + matching + recommendations.
Flask routes call into this module rather than containing business logic
directly.
"""

import logging
import re

from services import ats_scorer, classifier, matching_engine, ml_suggester, recommendation_engine
from services.classifier import ModelNotAvailableError
from services.information_extractor import extract_all
from services.job_description_parser import parse_job_description
from services.resume_detector import looks_like_resume, rejection_message

logger = logging.getLogger(__name__)

VALID_STRICTNESS = set(ats_scorer.STRICTNESS_PROFILES)
MAX_RANKING_JDS = 10
MIN_JD_CHARS = 30


def split_jd_list(raw_text: str) -> list:
    """Split a multi-JD paste into individual job descriptions. Separators:
    a line of ---, === or *** between descriptions. Whitespace-only and
    too-short fragments are dropped; at most MAX_RANKING_JDS are kept."""
    fragments = re.split(r"\n[ \t]*(?:-{3,}|={3,}|\*{3,})[ \t]*\n", raw_text or "")
    jds = []
    for fragment in fragments:
        cleaned = fragment.strip()
        if len(cleaned) >= MIN_JD_CHARS:
            jds.append(cleaned)
        if len(jds) >= MAX_RANKING_JDS:
            break
    return jds


def analyze_resume(resume_text: str, include_standalone_ats: bool = True,
                   strictness: str = "standard", detection: dict | None = None) -> dict:
    """Parse a resume, classify its job category, and (by default) run the
    standalone ATS audit. Match mode passes include_standalone_ats=False -
    it scores against the JD instead. `detection` may be precomputed by the
    caller (the routes run the resume detector before analysis)."""
    resume_data = extract_all(resume_text)

    try:
        # One calibrated predict_proba call serves both the top category and
        # the confidence list (calling predict_category separately would
        # duplicate the vectorizer transform + prediction).
        top_predictions = classifier.predict_with_confidence(resume_text)
        category = top_predictions[0]["category"] if top_predictions else None
    except ModelNotAvailableError as exc:
        logger.warning("Classifier unavailable: %s", exc)
        category = None
        top_predictions = []

    ats_result = (
        ats_scorer.score_resume_standalone(resume_text, resume_data, strictness=strictness)
        if include_standalone_ats
        else None
    )
    if ats_result:
        ats_result["ml_suggestions"] = ml_suggester.generate_deep_ml_suggestions(
            resume_text=resume_text,
            target_category=category,
            resume_skills=resume_data.get("skills", []),
        )

    return {
        "resume_data": resume_data,
        "category": category,
        "top_predictions": top_predictions,
        "ats_result": ats_result,
        "detection": detection if detection is not None else looks_like_resume(resume_text),
    }


def analyze_and_match(resume_text: str, jd_text: str,
                      strictness: str = "standard", target_title: str | None = None,
                      detection: dict | None = None) -> dict:
    """Full pipeline: resume analysis + JD parsing + matching + ATS scoring + recommendations."""
    resume_analysis = analyze_resume(
        resume_text, include_standalone_ats=False, detection=detection
    )
    resume_data = resume_analysis["resume_data"]
    jd_data = parse_job_description(jd_text)
    if target_title:
        # The user's explicitly stated target title outranks extraction.
        jd_data["job_title"] = target_title

    match_result = matching_engine.compare_resume_to_job(resume_data, jd_data, resume_text, jd_text)

    ats_result = ats_scorer.score_resume_vs_jd(
        resume_text, jd_text, resume_data, jd_data, match_result=match_result,
        strictness=strictness,
    )

    if ats_result:
        ats_result["ml_suggestions"] = ml_suggester.generate_deep_ml_suggestions(
            resume_text=resume_text,
            target_category=resume_analysis.get("category"),
            jd_text=jd_text,
            resume_skills=resume_data.get("skills", []),
        )

    recommendations = {
        "offline": recommendation_engine.generate_recommendations(
            match_result,
            ats_result,
            resume_skills=resume_data.get("skills", []),
            resume_text=resume_text,
            jd_text=jd_text,
            target_category=resume_analysis.get("category"),
        )
    }

    return {
        "resume_data": resume_data,
        "category": resume_analysis["category"],
        "top_predictions": resume_analysis["top_predictions"],
        "job_description": jd_data,
        "match": match_result,
        "ats_result": ats_result,
        "detection": resume_analysis["detection"],
        "jd_quality": assess_jd_quality(jd_text, jd_data),
        "recommendations": recommendations,
    }


def rank_job_descriptions(resume_text: str, jd_texts: list,
                          strictness: str = "standard",
                          target_title: str | None = None) -> dict:
    """Score one resume against several job descriptions and rank them best
    first. Lightweight: no recommendations or AI calls per JD."""
    resume_data = extract_all(resume_text)

    try:
        top_predictions = classifier.predict_with_confidence(resume_text)
        category = top_predictions[0]["category"] if top_predictions else None
    except ModelNotAvailableError:
        category = None

    ranked = []
    for index, jd_text in enumerate(jd_texts[:MAX_RANKING_JDS]):
        jd_data = parse_job_description(jd_text)
        if target_title:
            jd_data["job_title"] = target_title
        match_result = matching_engine.compare_resume_to_job(resume_data, jd_data, resume_text, jd_text)
        ats = ats_scorer.score_resume_vs_jd(
            resume_text, jd_text, resume_data, jd_data,
            match_result=match_result, strictness=strictness,
        )
        excerpt = re.sub(r"\s+", " ", jd_text)[:110].strip()
        ranked.append({
            "index": index,
            "job_title": jd_data.get("job_title") or f"Job description #{index + 1}",
            "seniority": jd_data.get("seniority"),
            "ats_total": ats.get("total"),
            "grade": ats.get("grade"),
            "match_overall": match_result.get("overall", {}).get("overall_score"),
            "required_skills": jd_data.get("required_skills", [])[:8],
            "missing_required_count": len(match_result.get("skill_match", {}).get("missing_required", [])),
            "top_suggestions": ats.get("top_suggestions", [])[:3],
            "excerpt": excerpt,
        })

    ranked.sort(key=lambda r: r["ats_total"] if r["ats_total"] is not None else -1.0, reverse=True)
    return {
        "ranking": ranked,
        "category": category,
        "resume_skills_count": len(resume_data.get("skills", [])),
        "detection": looks_like_resume(resume_text),
    }


def assess_jd_quality(jd_text: str, jd_data: dict) -> dict:
    """Flag weak job descriptions early: a JD with few skills, no title, or no
    requirements produces unreliable match numbers, and users deserve to know."""
    warnings = []
    word_count = len(jd_text.split())
    skill_count = len(jd_data.get("required_skills", [])) + len(jd_data.get("preferred_skills", []))

    if word_count < 80:
        warnings.append("The job description is very short; matching will be shallow.")
    if skill_count < 3:
        warnings.append("Fewer than 3 recognizable skills were found in the job description.")
    if jd_data.get("experience_requirement") is None:
        warnings.append("No years-of-experience requirement was detected (experience factor skipped).")
    if not jd_data.get("job_title"):
        warnings.append("No job title was detected (title matching skipped - use the target title option).")
    if not jd_data.get("education_requirement"):
        warnings.append("No education requirement was detected (education factor skipped).")

    quality = "good" if not warnings else ("fair" if len(warnings) <= 2 else "poor")
    return {"quality": quality, "warnings": warnings,
            "word_count": word_count, "skill_count": skill_count}


MAX_COMPARE_RESUMES = 5


def compare_resumes(entries: list, jd_text: str | None = None,
                    strictness: str = "standard",
                    target_title: str | None = None) -> dict:
    """Compare 2-5 resumes against each other - against one job description
    when given, otherwise on standalone ATS quality. Non-resume uploads are
    excluded from the ranking and reported separately."""
    jd_data = parse_job_description(jd_text) if jd_text else None
    if jd_data and target_title:
        jd_data["job_title"] = target_title
    match_overall = None

    candidates, rejected = [], []
    for entry in entries:
        detection = looks_like_resume(entry["text"])
        if detection["verdict"] == "not_resume":
            rejected.append({"filename": entry["filename"],
                             "reason": rejection_message(detection)})
            continue
        resume_data = extract_all(entry["text"])
        if jd_data:
            match_result = matching_engine.compare_resume_to_job(resume_data, jd_data, entry["text"], jd_text)
            ats = ats_scorer.score_resume_vs_jd(
                entry["text"], jd_text, resume_data, jd_data,
                match_result=match_result, strictness=strictness,
            )
            match_overall = match_result.get("overall", {}).get("overall_score")
        else:
            ats = ats_scorer.score_resume_standalone(entry["text"], resume_data, strictness=strictness)
            match_result = None
            match_overall = None

        candidates.append({
            "filename": entry["filename"],
            "ats_total": ats.get("total"),
            "grade": ats.get("grade"),
            "match_overall": match_overall,
            "factors": {f["key"]: f["score"] for f in ats.get("factors", [])},
            "skills": resume_data.get("skills", []),
            "years": resume_data.get("years_of_experience"),
            "top_suggestions": ats.get("top_suggestions", [])[:3],
            "potential": (ats.get("potential") or {}).get("total"),
        })

    ranked = sorted(candidates,
                    key=lambda c: c["ats_total"] if c["ats_total"] is not None else -1.0,
                    reverse=True)
    winner = ranked[0] if ranked else None
    for candidate in ranked:
        candidate["factor_deltas"] = {
            key: round((candidate["factors"].get(key) or 0) - (winner["factors"].get(key) or 0), 1)
            for key in winner["factors"]
        } if winner else {}

    return {
        "comparison": ranked,
        "rejected": rejected,
        "winner": winner["filename"] if winner else None,
        "jd_title": (jd_data or {}).get("job_title"),
        "mode": "job_match" if jd_data else "standalone",
        "match_overall": match_overall,
    }
