"""Tests for date-range experience computation, job-title extraction, and the
new JD parser fields (title + seniority)."""

from datetime import date

from services.information_extractor import (
    extract_experience_years,
    extract_job_titles,
    extract_years_from_date_ranges,
    extract_years_of_experience,
)
from services.job_description_parser import (
    detect_seniority,
    extract_job_title,
    extract_years_requirement,
    parse_job_description,
)

REF = date(2024, 6, 15)


def test_simple_range():
    text = "Software Developer\nJan 2020 - Mar 2022\n- Did things"
    assert extract_years_from_date_ranges(text, REF) == 2.2  # 26 months


def test_overlapping_ranges_are_merged_not_double_counted():
    text = "Role A\nJan 2020 - Dec 2021\nRole B\nJul 2021 - Jun 2022\n"
    # Overlap Jul-Dec 2021 must count once: union Jan 2020 -> Jun 2022 = 29 months.
    assert extract_years_from_date_ranges(text, REF) == 2.4


def test_present_resolves_against_reference_date():
    text = "Engineer\nJun 2022 - Present\n"
    assert extract_years_from_date_ranges(text, REF) == 2.0


def test_month_variants_and_numeric_format():
    assert extract_years_from_date_ranges("01/2020 - 01/2021", REF) == 1.0
    assert extract_years_from_date_ranges("September 2019 - October 2019", REF) == round(1 / 12, 1)


def test_no_dates_returns_none():
    assert extract_years_from_date_ranges("no dates here", REF) is None
    assert extract_years_from_date_ranges("", REF) is None


def test_invalid_range_ignored():
    assert extract_years_from_date_ranges("Mar 2022 - Jan 2020", REF) is None  # reversed


def test_experience_years_prefers_higher_of_claim_vs_dates():
    text = """SUMMARY
9 years of experience.

EXPERIENCE
Engineer
Jan 2020 - Present
- Built systems
"""
    result = extract_experience_years(text, REF)
    assert result["reported"] == 9.0
    assert result["from_dates"] == 4.4  # Jan 2020 -> Jun 2024 = 53 months
    assert result["years"] == 9.0  # claim covers earlier, undated roles


def test_experience_years_uses_dates_when_claim_absent():
    text = "EXPERIENCE\nEngineer\nJan 2020 - Jan 2023\n- Built systems\n"
    result = extract_experience_years(text, REF)
    assert result["reported"] is None
    assert result["years"] == 3.0


def test_experience_years_none_when_no_evidence():
    text = "EXPERIENCE\nEngineer\n- Built systems\n"
    assert extract_experience_years(text, REF)["years"] is None


def test_linkedin_style_years_and_months():
    assert extract_years_of_experience("3 yrs 6 mos of experience") == 3.5
    assert extract_years_of_experience("1 year and 8 months in the role") == 1 + 8 / 12
    assert extract_years_of_experience("4+ years of experience") == 4.0
    assert extract_years_of_experience("6 months internship") is None  # months alone never count
    # Largest claim wins, including composite ones.
    assert extract_years_of_experience("2 years of tutoring and 5 yrs 3 mos of engineering") == 5.25


def test_job_titles_extracted():
    text = """EXPERIENCE
Data Analyst, Acme Corp
Jan 2020 - Mar 2022
- Built dashboards

Worked as a Senior Software Engineer at Globex
Jun 2022 - Present
- Led migration
"""
    titles = extract_job_titles(text)
    lowered = [t.lower() for t in titles]
    assert "data analyst" in lowered
    assert "senior software engineer" in lowered


def test_jd_title_and_seniority():
    jd = "Job Title: Senior Data Analyst\n\nREQUIREMENTS\n5+ years of experience.\n"
    assert extract_job_title(jd) == "Senior Data Analyst"
    assert detect_seniority(jd) == "senior"

    jd2 = "We are hiring a Junior Web Developer to join our team.\n"
    assert detect_seniority(jd2) == "junior"

    assert detect_seniority("No level words in this text at all.") is None


def test_jd_experience_range_uses_lower_bound():
    # Meeting the minimum is what satisfies a "2-4 years" requirement.
    assert extract_years_requirement("We need 2-4 years of experience.") == 2.0
    assert extract_years_requirement("Requires 5 to 7 years in a similar role.") == 5.0
    # Non-range phrasings keep their existing behaviour.
    assert extract_years_requirement("3+ years of experience required.") == 3.0
    assert extract_years_requirement("At least 4 years in the field.") == 4.0
    assert extract_years_requirement("No experience mention here.") is None


def test_jd_range_requirement_feeds_experience_match():
    jd_data = parse_job_description(
        "Job Title: Developer\n\nREQUIREMENTS\n2-4 years of experience.\nExperience with Python.\n"
    )
    assert jd_data["experience_requirement"] == 2.0
