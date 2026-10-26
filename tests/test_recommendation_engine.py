"""Tests for the rewritten recommendation engine, which must consume the REAL
match-result structure produced by services/matching_engine.py."""

from services.information_extractor import extract_all
from services.job_description_parser import parse_job_description
from services.matching_engine import compare_resume_to_job
from services.recommendation_engine import generate_recommendations

SAMPLE_RESUME = """Jane Smith
Email: jane@example.com | Phone: +1-555-123-4567

SUMMARY
Software Developer with 3 years of experience.

SKILLS
Python, JavaScript, React, Node.js, Git

EXPERIENCE
Software Developer at TechNova
Jan 2021 - Present
- Built REST APIs in Node.js serving 10k daily requests
- Reduced page load time by 35% with React code splitting

EDUCATION
B.Tech in Computer Science, XYZ University, 2020
"""

SAMPLE_JD = """Job Title: Software Developer

REQUIREMENTS
3+ years of experience.
Bachelor's degree in Computer Science.
Proficiency in Python and Docker.
Experience with MySQL.

RESPONSIBILITIES
Design and implement backend services.
"""


def _build_match_result():
    resume_data = extract_all(SAMPLE_RESUME)
    jd_data = parse_job_description(SAMPLE_JD)
    return compare_resume_to_job(resume_data, jd_data, SAMPLE_RESUME, SAMPLE_JD)


def test_recommendations_generated_from_real_match_result():
    recs = generate_recommendations(_build_match_result())
    assert recs, "recommendations must never be empty"
    assert all({"text", "priority"} <= set(r) for r in recs)
    assert all(r["priority"] in {"high", "medium", "low"} for r in recs)


def test_missing_skills_named_concretely():
    recs = generate_recommendations(_build_match_result())
    joined = " ".join(r["text"] for r in recs)
    # Docker and MySQL are required by the JD but absent from the resume.
    assert "Docker" in joined or "docker" in joined
    assert "MySQL" in joined or "mysql" in joined


def test_priorities_sorted_high_first():
    recs = generate_recommendations(_build_match_result())
    order = {"high": 0, "medium": 1, "low": 2}
    priorities = [order[r["priority"]] for r in recs]
    assert priorities == sorted(priorities)


def test_empty_result_does_not_crash():
    recs = generate_recommendations({})
    assert recs  # falls back to generic advice instead of raising
