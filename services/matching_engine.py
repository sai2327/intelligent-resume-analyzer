"""
Compares a parsed resume against a parsed job description: skill overlap,
TF-IDF cosine similarity, experience match, education match, and a
transparent weighted overall score.
"""

from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import config
from services.text_preprocessor import preprocess_text

EDUCATION_LEVELS = {
    "phd": 4, "ph.d": 4, "doctorate": 4,
    "master": 3, "m.tech": 3, "mtech": 3, "m.e.": 3, "msc": 3, "m.sc": 3, "mca": 3, "mba": 3,
    "bachelor": 2, "b.tech": 2, "btech": 2, "b.e.": 2, "bsc": 2, "b.sc": 2,
    "diploma": 1,
}


@lru_cache(maxsize=256)
def compute_text_similarity(resume_text: str, jd_text: str) -> float:
    """
    Cosine similarity between TF-IDF vectors of the resume and JD, expressed
    as a 0-100 percentage. Uses unigrams + bigrams and sublinear term
    frequency: bigrams capture multi-word concepts ("machine learning",
    "data analysis") that unigrams miss, and sublinear TF stops a single
    repeated word from dominating the vector. Cached per (resume, JD) pair -
    the tracker workflow re-scores the same pairs repeatedly. This is a
    general TEXT similarity metric and is intentionally kept distinct from
    the job-specific 'skill match' metric.
    """
    processed_resume = preprocess_text(resume_text)
    processed_jd = preprocess_text(jd_text)

    if not processed_resume.strip() or not processed_jd.strip():
        return 0.0

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    try:
        vectors = vectorizer.fit_transform([processed_resume, processed_jd])
    except ValueError:
        return 0.0  # empty vocabulary after preprocessing

    similarity = cosine_similarity(vectors[0], vectors[1])[0][0]
    return round(float(similarity) * 100, 2)


def compute_skill_match(resume_skills: list, required_skills: list, preferred_skills: list) -> dict:
    """Compare skill sets and compute required/preferred match percentages.
    Returns None for a percentage when its denominator (total skills of that
    kind in the JD) is zero, rather than a misleading 0% or 100%."""
    resume_set = set(resume_skills)
    required_set = set(required_skills)
    preferred_set = set(preferred_skills)

    matched_required = sorted(resume_set & required_set)
    missing_required = sorted(required_set - resume_set)
    matched_preferred = sorted(resume_set & preferred_set)
    missing_preferred = sorted(preferred_set - resume_set)
    additional_skills = sorted(resume_set - required_set - preferred_set)

    required_score = (
        round(len(matched_required) / len(required_set) * 100, 2) if required_set else None
    )
    preferred_score = (
        round(len(matched_preferred) / len(preferred_set) * 100, 2) if preferred_set else None
    )

    return {
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_preferred": matched_preferred,
        "missing_preferred": missing_preferred,
        "additional_skills": additional_skills,
        "required_skill_score": required_score,
        "preferred_skill_score": preferred_score,
    }


def _education_rank(text: str) -> int | None:
    """Return the highest recognized education level rank mentioned in text, or None."""
    if not text:
        return None
    lowered = text.lower()
    best_rank = None
    for keyword, rank in EDUCATION_LEVELS.items():
        if keyword in lowered and (best_rank is None or rank > best_rank):
            best_rank = rank
    return best_rank


def compute_experience_match(resume_years, required_years) -> dict:
    """Compare extracted years of experience. Never invents a number when one is missing."""
    if resume_years is None or required_years is None:
        return {
            "score": None,
            "detail": "Not enough information to compare experience.",
            "resume_years": resume_years,
            "required_years": required_years,
        }

    score = 100.0 if required_years <= 0 else min(resume_years / required_years, 1.0) * 100
    detail = (
        f"Resume shows about {resume_years:g} year(s) of experience; "
        f"the job requires about {required_years:g} year(s)."
    )
    return {
        "score": round(score, 2),
        "detail": detail,
        "resume_years": resume_years,
        "required_years": required_years,
    }


def compute_education_match(resume_education: list, education_requirement) -> dict:
    """Compare education levels where possible. Returns score=None (not a
    guessed value) whenever either side's level cannot be determined."""
    if not education_requirement:
        return {"score": None, "detail": "The job description does not specify an education requirement."}

    required_rank = _education_rank(education_requirement)
    if required_rank is None:
        return {"score": None, "detail": "Could not determine a specific education level from the job description."}

    resume_rank = _education_rank(" ".join(resume_education))
    if resume_rank is None:
        return {"score": None, "detail": "Not enough information to compare education level."}

    if resume_rank >= required_rank:
        return {"score": 100.0, "detail": "Resume education level meets or exceeds the job requirement."}
    return {"score": 50.0, "detail": "Resume education level is below the job's stated requirement."}


def compute_overall_score(skill_score, similarity_score, experience_score, education_score, weights=None) -> dict:
    """
    Transparent weighted overall score. If a component is unavailable
    (None), its weight is proportionally redistributed across the remaining
    available components instead of silently assigning an arbitrary value.
    """
    weights = weights or config.SCORE_WEIGHTS
    components = {
        "skills": skill_score,
        "similarity": similarity_score,
        "experience": experience_score,
        "education": education_score,
    }

    available = {name: value for name, value in components.items() if value is not None}
    excluded = [name for name in components if name not in available]

    if not available:
        return {
            "overall_score": None,
            "excluded_components": excluded,
            "note": "Not enough information was available to compute an overall score.",
        }

    total_weight = sum(weights[name] for name in available)
    if total_weight == 0:
        normalized_weights = {name: 1 / len(available) for name in available}
    else:
        normalized_weights = {name: weights[name] / total_weight for name in available}

    overall = sum(available[name] * normalized_weights[name] for name in available)

    note = None
    if excluded:
        note = (
            f"Components excluded due to insufficient information: {', '.join(excluded)}. "
            "Remaining weights were proportionally redistributed so the score stays on a 0-100 scale."
        )

    return {"overall_score": round(overall, 2), "excluded_components": excluded, "note": note}


def compare_resume_to_job(resume_data: dict, jd_data: dict, resume_text: str, jd_text: str) -> dict:
    """Full resume-vs-job-description comparison producing every metric the UI needs."""
    skill_match = compute_skill_match(
        resume_data.get("skills", []),
        jd_data.get("required_skills", []),
        jd_data.get("preferred_skills", []),
    )
    similarity_score = compute_text_similarity(resume_text, jd_text)
    experience_match = compute_experience_match(
        resume_data.get("years_of_experience"), jd_data.get("experience_requirement")
    )
    education_match = compute_education_match(
        resume_data.get("education", []), jd_data.get("education_requirement")
    )

    overall = compute_overall_score(
        skill_match["required_skill_score"],
        similarity_score,
        experience_match["score"],
        education_match["score"],
    )

    return {
        "skill_match": skill_match,
        "text_similarity": similarity_score,
        "experience_match": experience_match,
        "education_match": education_match,
        "overall": overall,
    }
