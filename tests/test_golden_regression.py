"""Golden regression tests: pin the canonical scores for the shared fixture
resume/JD. Any code change that shifts these numbers must consciously update
this file - that is the point. Tolerance absorbs float noise, not logic drift."""

import pytest

from tests.conftest import SAMPLE_JD_TEXT, SAMPLE_RESUME_TEXT_LINES
from services.analysis_service import analyze_and_match, analyze_resume
from services.matching_engine import compare_resume_to_job
from services.job_description_parser import parse_job_description
from services.information_extractor import extract_all

TOL = 0.5
RESUME = "\n".join(SAMPLE_RESUME_TEXT_LINES)
JD = SAMPLE_JD_TEXT


def test_standalone_ats_golden():
    ats = analyze_resume(RESUME)["ats_result"]
    assert ats["mode"] == "standalone"
    assert ats["total"] == pytest.approx(77.58, abs=TOL)
    scores = {f["key"]: f["score"] for f in ats["factors"]}
    assert scores["format"] == pytest.approx(75, abs=TOL)
    assert scores["content"] == pytest.approx(70.0, abs=TOL)
    assert scores["skills"] == pytest.approx(76.67, abs=TOL)
    assert scores["education"] == pytest.approx(100.0, abs=TOL)


def test_job_match_ats_golden():
    result = analyze_and_match(RESUME, JD)
    ats = result["ats_result"]
    assert ats["total"] == pytest.approx(74.67, abs=TOL)
    scores = {f["key"]: f["score"] for f in ats["factors"]}
    assert scores["keywords"] == pytest.approx(45.68, abs=TOL)
    assert scores["skills"] == pytest.approx(75.0, abs=TOL)
    assert scores["title"] == pytest.approx(100.0, abs=TOL)
    assert scores["experience"] == pytest.approx(100.0, abs=TOL)
    assert scores["education"] == pytest.approx(100.0, abs=TOL)
    assert scores["format"] == pytest.approx(75, abs=TOL)
    assert scores["content"] == pytest.approx(70.0, abs=TOL)


def test_match_engine_golden():
    result = analyze_and_match(RESUME, JD)
    assert result["match"]["overall"]["overall_score"] == pytest.approx(79.11, abs=TOL)
    assert result["match"]["text_similarity"] == pytest.approx(16.42, abs=TOL)
    assert result["match"]["skill_match"]["required_skill_score"] == pytest.approx(100.0, abs=TOL)
    assert result["category"] == "Software Developer"


def test_extraction_golden():
    resume_data = extract_all(RESUME)
    assert resume_data["email"] == "john.doe@example.com"
    assert "Python" in resume_data["skills"]
    assert "React" in resume_data["skills"]
    assert resume_data["years_of_experience"] == pytest.approx(3.0, abs=0.01)

    jd_data = parse_job_description(JD)
    assert jd_data["job_title"] == "Software Developer"
    assert jd_data["experience_requirement"] == pytest.approx(3.0, abs=0.01)
    assert "Python" in jd_data["required_skills"]
    assert "AWS" in jd_data["preferred_skills"]


def test_consistency_between_factors_and_match_engine():
    """The match engine and ATS scorer must agree on skill overlap - they use
    the same canonical skill database."""
    resume_data = extract_all(RESUME)
    jd_data = parse_job_description(JD)
    match_result = compare_resume_to_job(resume_data, jd_data, RESUME, JD)
    ats = analyze_and_match(RESUME, JD)["ats_result"]
    match_skills = match_result["skill_match"]["required_skill_score"]
    ats_skills = next(f["score"] for f in ats["factors"] if f["key"] == "skills")
    # ATS blends required (100) at 75% and preferred (0 - AWS/Kubernetes are
    # missing) at 25%.
    expected = 0.75 * match_skills + 0.25 * match_result["skill_match"]["preferred_skill_score"]
    assert ats_skills == pytest.approx(expected, abs=TOL)
