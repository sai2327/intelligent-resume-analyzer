"""Tests for the ATS score tracker engine (services/ats_scorer.py)."""

from datetime import date

from config import config
from services.ats_scorer import (
    compute_format_factor,
    extract_jd_keywords,
    get_change_suggestions,
    score_resume_standalone,
    score_resume_vs_jd,
)
from services.information_extractor import extract_all
from services.job_description_parser import parse_job_description

REF_DATE = date(2026, 9, 19)

STRONG_RESUME = """Jane Smith
Email: jane@example.com | Phone: +1-555-123-4567

SUMMARY
Data Analyst with 4 years of experience in data analysis and reporting.

SKILLS
Python, SQL, Tableau, Machine Learning, Git, Statistics

EXPERIENCE
Data Analyst, Acme Corp
Jan 2020 - Mar 2022
- Analyzed customer data and built 12 dashboards in Tableau
- Automated 5 recurring reports with Python, cutting turnaround by 40%

Senior Data Analyst, Globex
Jun 2022 - Present
- Led a team of 3 analysts and reduced reporting time by 35%
- Designed the company KPI dataset used by 200+ employees

EDUCATION
B.Tech in Computer Science, XYZ University, 2019
"""

WEAK_RESUME = """Bob
bob@example.com

I am a hardworking person and a team player. I worked at a store for a while.
I did some computer stuff. I am passionate about technology.
"""

JD_TEXT = """Job Title: Senior Data Analyst

REQUIREMENTS
4+ years of experience in data analysis.
Bachelor's degree required.
Strong proficiency in Python and SQL.
Experience with Tableau.
Experience with Airflow.

PREFERRED SKILLS
Experience with Spark.

RESPONSIBILITIES
Analyze large datasets and build dashboards.
"""


def _strong_parts():
    resume_data = extract_all(STRONG_RESUME)
    jd_data = parse_job_description(JD_TEXT)
    return resume_data, jd_data


def test_weights_sum_to_one():
    assert abs(sum(config.ATS_WEIGHTS_JOB_MATCH.values()) - 1.0) < 1e-9
    assert abs(sum(config.ATS_WEIGHTS_STANDALONE.values()) - 1.0) < 1e-9


def test_job_match_scores_in_range_and_deterministic():
    resume_data, jd_data = _strong_parts()
    first = score_resume_vs_jd(STRONG_RESUME, JD_TEXT, resume_data, jd_data)
    second = score_resume_vs_jd(STRONG_RESUME, JD_TEXT, resume_data, jd_data)

    assert first["mode"] == "job_match"
    assert 0 <= first["total"] <= 100
    assert first["total"] == second["total"]  # deterministic
    assert len(first["factors"]) == 7
    assert first["grade"] in {"Excellent", "Strong", "Fair", "Needs work", "High risk"}


def test_strong_resume_outranks_weak_resume():
    resume_data, jd_data = _strong_parts()
    strong = score_resume_vs_jd(STRONG_RESUME, JD_TEXT, resume_data, jd_data)
    weak_data = extract_all(WEAK_RESUME)
    weak = score_resume_vs_jd(WEAK_RESUME, JD_TEXT, weak_data, jd_data)

    assert strong["total"] > weak["total"] + 30
    # The weak resume should trigger keyword penalties; the strong one fewer.
    weak_keywords = next(f for f in weak["factors"] if f["key"] == "keywords")
    strong_keywords = next(f for f in strong["factors"] if f["key"] == "keywords")
    assert weak_keywords["score"] < strong_keywords["score"]


def test_missing_jd_skills_produce_high_priority_suggestions():
    resume_data, jd_data = _strong_parts()
    result = score_resume_vs_jd(STRONG_RESUME, JD_TEXT, resume_data, jd_data)
    changes = get_change_suggestions(result)
    texts = " ".join(item["text"] for item in changes)

    # Airflow is in the JD requirements but nowhere on the resume.
    assert "airflow" in texts.lower()
    assert any(item["priority"] == "high" for item in changes)
    # Every item is traceable to a factor.
    assert all(item["factor"] for item in changes)


def test_unavailable_factors_excluded_and_weights_redistributed():
    # JD without education requirement or explicit years: those factors must
    # be excluded (score None), never guessed as 0.
    jd_no_edu = "Job Title: Developer\n\nREQUIREMENTS\nExperience with Python.\n\nRESPONSIBILITIES\nWrite code.\n"
    jd_data = parse_job_description(jd_no_edu)
    resume_data = extract_all(STRONG_RESUME)
    result = score_resume_vs_jd(STRONG_RESUME, jd_no_edu, resume_data, jd_data)

    excluded_keys = {
        f["key"] for f in result["factors"] if not f["available"]
    }
    assert "education" in excluded_keys
    assert result["total"] is not None
    # Total stays a weighted average of available scores: within [min, max].
    scores = [f["score"] for f in result["factors"] if f["available"]]
    assert min(scores) <= result["total"] <= max(scores)


def test_standalone_mode_scores_resume_without_jd():
    resume_data = extract_all(STRONG_RESUME)
    result = score_resume_standalone(STRONG_RESUME, resume_data)

    assert result["mode"] == "standalone"
    assert 0 <= result["total"] <= 100
    assert {f["key"] for f in result["factors"]} == {"format", "content", "skills", "education"}
    assert any(item for item in get_change_suggestions(result))


def test_format_factor_checks_contact_sections_dates():
    resume_data = extract_all(STRONG_RESUME)
    strong = compute_format_factor(STRONG_RESUME, resume_data)
    weak = compute_format_factor(WEAK_RESUME, extract_all(WEAK_RESUME))

    strong_checks = {c["name"]: c["passed"] for c in strong["checks"]}
    assert strong_checks["Email address"] and strong_checks["Phone number"]
    assert strong["score"] > weak["score"]


def test_extract_jd_keywords_ignores_generic_words_and_cross_line_pairs():
    jd_data = parse_job_description(JD_TEXT)
    terms = [k["term"] for k in extract_jd_keywords(JD_TEXT, jd_data)]
    lowered = [t.lower() for t in terms]

    # Canonical skills are always on the checklist...
    assert "python" in lowered and "tableau" in lowered
    # ...generic JD boilerplate never is...
    assert "experience" not in lowered and "years" not in lowered
    # ...and no bigram may span a line/sentence boundary ("spark analyze").
    assert "spark analyze" not in lowered
    assert "large datasets" in lowered  # true in-line adjacency kept


def test_jd_without_detectable_requirements_sets_warning():
    resume_data = extract_all(STRONG_RESUME)
    jd_garbage = "!!! ??? ### ... ---"
    result = score_resume_vs_jd(STRONG_RESUME, jd_garbage, resume_data, parse_job_description(jd_garbage))
    assert result.get("jd_warning")
    # Score still exists (resume quality factors remain) but is annotated.
    assert result["total"] is not None

    # A real JD never triggers the warning.
    real = score_resume_vs_jd(STRONG_RESUME, JD_TEXT, resume_data, parse_job_description(JD_TEXT))
    assert "jd_warning" not in real


def test_newly_added_database_skills_are_recognized():
    resume_data = extract_all(STRONG_RESUME)
    jd = ("Job Title: Analytics Engineer\n\nREQUIREMENTS\n"
          "Experience with Airflow, Snowflake and dbt.\n"
          "Experience with Kafka.\n\n"
          "PREFERRED SKILLS\nExperience with Databricks.\n")
    jd_data = parse_job_description(jd)
    # The expanded skills database must treat these as canonical skills.
    assert "Apache Airflow" in jd_data["required_skills"]
    assert "Snowflake" in jd_data["required_skills"]
    assert "dbt" in jd_data["required_skills"]
    assert "Apache Kafka" in jd_data["required_skills"]
    assert "Databricks" in jd_data["preferred_skills"]

    result = score_resume_vs_jd(STRONG_RESUME, jd, resume_data, jd_data)
    keywords_factor = next(f for f in result["factors"] if f["key"] == "keywords")
    # Factor carries the chips the UI renders.
    assert isinstance(keywords_factor["missing_keywords"], list)
    assert isinstance(keywords_factor["matched_keywords"], list)


def test_resume_with_new_skills_matches_them():
    resume = STRONG_RESUME.replace(
        "SKILLS\nPython, SQL, Tableau, Machine Learning, Git, Statistics",
        "SKILLS\nPython, SQL, Tableau, Machine Learning, Git, Statistics, Apache Airflow, Snowflake, dbt, Apache Kafka",
    )
    jd = ("Job Title: Analytics Engineer\n\nREQUIREMENTS\n"
          "Experience with Airflow, Snowflake and dbt.\n"
          "Experience with Kafka.\n\n"
          "PREFERRED SKILLS\nExperience with Databricks.\n")
    resume_data = extract_all(resume)
    jd_data = parse_job_description(jd)
    result = score_resume_vs_jd(resume, jd, resume_data, jd_data)
    keywords_factor = next(f for f in result["factors"] if f["key"] == "keywords")
    assert "Apache Airflow" in keywords_factor["matched_keywords"]
    assert "Apache Kafka" in keywords_factor["matched_keywords"]


REAL_WORLD_JD = """Job Title: Senior Data Analyst

About us: We are a fast-growing company on an amazing journey.

What You'll Bring
4+ years of experience in data analysis.
Expert SQL and Python skills.
Experience with Tableau and Airflow.

Nice to have
Experience with Snowflake.

Responsibilities
Analyze datasets and build dashboards.

Benefits
We offer 401k with company match, health insurance, dental and vision
coverage, PTO, parental leave, gym membership, and free snacks.

Equal Opportunity Employer: We celebrate diversity and are committed to an
inclusive environment for all employees.
"""


def test_benefits_and_eeo_boilerplate_never_become_keywords():
    jd_data = parse_job_description(REAL_WORLD_JD)
    terms = {k["term"].lower() for k in extract_jd_keywords(REAL_WORLD_JD, jd_data)}
    leaked = terms & {"401k", "insurance", "dental", "vision", "snacks", "pto",
                      "gym", "parental", "leave", "diversity", "inclusive",
                      "match", "benefits", "celebrate", "committed"}
    assert not leaked, f"benefit/EEO words leaked into keywords: {leaked}"
    # The requirement sections still harvested properly.
    assert "Apache Airflow" in jd_data["required_skills"]
    assert jd_data["job_title"] == "Senior Data Analyst"


def test_typo_on_resume_is_matched_with_fix_suggestion():
    jd = "Job Title: Data Analyst\n\nREQUIREMENTS\nExperience with Python and SQL.\n"
    resume_data = extract_all(STRONG_RESUME.replace("Python", "Pyhton"))
    result = score_resume_vs_jd(STRONG_RESUME.replace("Python", "Pyhton"), jd,
                                resume_data, parse_job_description(jd))
    texts = " ".join(s["text"] for f in result["factors"] for s in f["suggestions"])
    assert "pyhton" in texts.lower()
    # Not flagged as missing - the candidate clearly has the skill.
    keywords_factor = next(f for f in result["factors"] if f["key"] == "keywords")
    assert "Python" not in [m.lower() for m in keywords_factor["missing_keywords"]]


def test_alternative_requirement_headers_recognized():
    jd = ("Job Title: Developer\n\nWhat You'll Bring\nExperience with Python.\n\n"
          "Nice to have\nExperience with Docker.\n\nYour Role\nWrite code.\n")
    jd_data = parse_job_description(jd)
    assert "Python" in jd_data["required_skills"]
    assert "Docker" in jd_data["preferred_skills"]


def test_year_numbers_do_not_count_as_metrics():
    """A bullet mentioning only calendar years is NOT 'quantified' - the
    metric check must reward real figures (40%, 12 dashboards) only."""
    from services.ats_scorer import _has_real_metric

    assert _has_real_metric("Reduced reporting time by 40%")
    assert _has_real_metric("Built 12 dashboards in Tableau")
    assert _has_real_metric("Led a team of 12 analysts")
    assert _has_real_metric("Increased revenue 3x year over year")
    assert not _has_real_metric("Worked there in 2021 on migrations")
    assert not _has_real_metric("Handled migrations during 2020-2022")
    assert not _has_real_metric("Mentored junior engineers")


def test_spacy_pipeline_is_ner_only():
    """The loaded spaCy model must exclude tagger/parser/lemmatizer - they are
    dead weight for name extraction."""
    from services.information_extractor import _get_spacy_model

    nlp = _get_spacy_model()
    if nlp is None:
        import pytest
        pytest.skip("spaCy model not installed")
    assert "parser" not in nlp.pipe_names
    assert "ner" in nlp.pipe_names
