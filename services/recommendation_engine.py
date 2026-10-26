"""
Generates offline, prioritized recommendations from resume-job matching
results (and optionally the ATS score breakdown and ML statistical models).

The input is the dict produced by services/matching_engine.py
compare_resume_to_job(): {"skill_match": {...}, "text_similarity": ...,
"experience_match": {...}, "education_match": {...}, "overall": {...}}.

Deepened with Machine Learning attribution, action-verb semantic scoring,
and quantification diagnostics via services/ml_suggester.py.
"""

import logging
import re

from services import ml_suggester
from services.skill_matcher import skill_categories

logger = logging.getLogger(__name__)

# (priority, order) so high-impact fixes bubble to the top of the rendered list.
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _rec(text, priority="medium"):
    return {"text": text, "priority": priority}


def _adjacent_skill_recommendations(resume_skills: list, missing_skills: list, limit: int = 2) -> list:
    """For missing skills the candidate is CLOSE to (another skill from the
    same category is already on the resume), add encouragement-style advice:
    'you already know X from that area, so learning Y is a small step'."""
    if not resume_skills or not missing_skills:
        return []
    categories = skill_categories()
    user_by_category = {}
    for skill in resume_skills:
        category = categories.get(skill)
        if category:
            user_by_category.setdefault(category, []).append(skill)

    suggestions = []
    for missing in missing_skills:
        category = categories.get(missing)
        if not category or category not in user_by_category:
            continue
        example = sorted(user_by_category[category])[0]
        suggestions.append(_rec(
            f"You already work with {example} in the same area ({category}) - "
            f"picking up {missing} should be a small step, not a new field.",
            "low",
        ))
        if len(suggestions) >= limit:
            break
    return suggestions


def generate_recommendations(
    match_result: dict,
    ats_result: dict | None = None,
    resume_skills: list | None = None,
    resume_text: str | None = None,
    jd_text: str | None = None,
    target_category: str | None = None,
) -> list:
    """
    Generate specific, prioritized recommendations based on matching analysis
    and deep machine learning diagnostics. Every recommendation names concrete
    skills, numbers, or ML attribution scores.
    """
    recommendations = []
    seen_texts = set()

    def add_rec(rec_item):
        dedupe_key = re.sub(r"[^a-z0-9]+", " ", rec_item["text"].lower()).strip()
        if dedupe_key not in seen_texts:
            seen_texts.add(dedupe_key)
            recommendations.append(rec_item)

    # --- 1. ATS quick wins first (highest overall ATS score impact) ---
    if ats_result:
        for item in ats_result.get("top_suggestions", []):
            add_rec(_rec(f"[ATS - {item['factor']}] {item['text']}", item["priority"]))

    # --- 2. Deep Machine Learning attribution & optimization suggestions ---
    if resume_text:
        try:
            ml_recs = ml_suggester.generate_deep_ml_suggestions(
                resume_text=resume_text,
                target_category=target_category,
                jd_text=jd_text,
                resume_skills=resume_skills,
            )
            for m in ml_recs:
                add_rec(_rec(m["text"], m["priority"]))
        except Exception as exc:
            logger.debug("ML suggester skipped: %s", exc)

    # --- 3. Overall match framing ---
    overall_score = (match_result.get("overall") or {}).get("overall_score")
    if overall_score is not None:
        if overall_score < 40:
            add_rec(_rec(
                f"Overall match is only {overall_score:.0f}% - tailor this resume heavily "
                f"for this job before applying.", "high",
            ))
        elif overall_score < 60:
            add_rec(_rec(
                f"Overall match is {overall_score:.0f}% (moderate). Focus on the highest-weight "
                f"gaps below.", "medium",
            ))
        else:
            add_rec(_rec(
                f"Strong overall match ({overall_score:.0f}%). Emphasize the matched "
                f"qualifications in your cover letter, and close any remaining gaps below.", "low",
            ))

    # --- 4. Concrete Skills Gaps ---
    skill_match = match_result.get("skill_match") or {}
    missing_required = skill_match.get("missing_required", [])
    missing_preferred = skill_match.get("missing_preferred", [])
    matched_required = skill_match.get("matched_required", [])

    if missing_required:
        top = missing_required[:5]
        add_rec(_rec(
            f"Missing required skills ({', '.join(top)}). If you have them under a different name, "
            f"use the job posting's exact wording; otherwise consider upskilling - these are "
            f"hard filters for many ATS.", "high",
        ))
        for adj in _adjacent_skill_recommendations(resume_skills or [], missing_required):
            add_rec(adj)

    if missing_preferred:
        top = missing_preferred[:4]
        add_rec(_rec(
            f"Preferred skills you could highlight if you have them: {', '.join(top)}.", "medium",
        ))

    if matched_required:
        add_rec(_rec(
            f"Matched required skills ({', '.join(matched_required[:6])}) - make sure each one "
            f"appears in a concrete achievement bullet, not just the skills list.", "low",
        ))

    # --- 5. Experience alignment ---
    experience_match = match_result.get("experience_match") or {}
    exp_score = experience_match.get("score")
    if exp_score is not None and exp_score < 100:
        add_rec(_rec(
            "Your evidenced experience is below the job's requirement. Emphasize relevant "
            "accomplishments, internships, and freelance/project work to close the gap.", "high",
        ))

    # --- 6. Education alignment ---
    education_match = match_result.get("education_match") or {}
    edu_score = education_match.get("score")
    if edu_score is not None and edu_score < 100:
        add_rec(_rec(
            "Highlight relevant coursework, certifications, or equivalent practical experience "
            "to offset the education gap.", "medium",
        ))

    # --- 7. Keyword similarity ---
    similarity = match_result.get("text_similarity")
    if similarity is not None and similarity < 25:
        add_rec(_rec(
            f"Resume/job wording overlap is low ({similarity:.0f}%). Mirror the job posting's "
            f"terminology where truthful - ATS keyword matching is largely literal.", "medium",
        ))

    if not recommendations:
        add_rec(_rec(
            "Review the job description carefully and customize your resume for it.", "low",
        ))
        add_rec(_rec(
            "Quantify your achievements with specific metrics wherever possible.", "low",
        ))

    recommendations.sort(key=lambda r: _PRIORITY_ORDER.get(r["priority"], 3))
    return recommendations
