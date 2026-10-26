"""Tests for the advanced options: strictness profiles, target job title
override, resume-detector gating at the routes, and the text report."""

import io

from services.ats_scorer import score_resume_standalone
from services.information_extractor import extract_all
from tests.conftest import SAMPLE_JD_TEXT, SAMPLE_RESUME_TEXT_LINES

RESUME = "\n".join(SAMPLE_RESUME_TEXT_LINES)




# ---------------------------------------------------------------- strictness

def test_strictness_ordering_lenient_ge_standard_ge_strict():
    data = extract_all(RESUME)
    lenient = score_resume_standalone(RESUME, data, strictness="lenient")["total"]
    standard = score_resume_standalone(RESUME, data, strictness="standard")["total"]
    strict = score_resume_standalone(RESUME, data, strictness="strict")["total"]
    assert lenient >= standard >= strict


def test_strict_mode_disables_typo_forgiveness():
    jd = "Job Title: Data Analyst\n\nREQUIREMENTS\nExperience with Python and SQL.\n"
    from services.job_description_parser import parse_job_description
    from services.ats_scorer import compute_keyword_match

    jd_data = parse_job_description(jd)
    typo_resume = RESUME.replace("Python", "Pyhton")
    resume_data = extract_all(typo_resume)

    standard = compute_keyword_match(typo_resume, jd, jd_data, resume_data)["score"]
    strict = compute_keyword_match(typo_resume, jd, jd_data, resume_data,
                                   profile={"typo_matching": False,
                                            "partial_credit_multiplier": 1.0})["score"]
    assert standard > strict  # standard forgives the typo, strict does not


def test_invalid_strictness_falls_back_to_standard():
    data = extract_all(RESUME)
    assert (score_resume_standalone(RESUME, data, strictness="bogus")["total"]
            == score_resume_standalone(RESUME, data, strictness="standard")["total"])


# ---------------------------------------------------------------- routes

def test_non_resume_upload_rejected_with_explanation(client, academic_pdf_bytes):
    response = client.post(
        "/analyze",
        data={"resume_file": (io.BytesIO(academic_pdf_bytes), "thesis.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "does not look like a resume" in html


def test_resume_upload_shows_detection_badge(client, sample_resume_pdf_bytes):
    response = client.post(
        "/analyze",
        data={"resume_file": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert "Resume detected" in response.get_data(as_text=True)


def test_target_title_override(client, sample_resume_docx_bytes):
    # The fixture resume's experience says "Software Developer"; a matching
    # target title must yield a perfect title factor.
    response = client.post(
        "/match-job",
        data={
            "resume_file": (io.BytesIO(sample_resume_docx_bytes), "resume.docx"),
            "jd_text": SAMPLE_JD_TEXT,
            "target_title": "Software Developer",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Job title match" in html


def test_text_report_download(client, sample_resume_pdf_bytes):
    response = client.post(
        "/analyze",
        data={"resume_file": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200

    from database import database
    report_id = database.list_recent_analyses(limit=1)[0]["id"]
    report = client.get(f"/report/{report_id}.txt")
    assert report.status_code == 200
    assert report.mimetype == "text/plain"
    text = report.get_data(as_text=True)
    assert "ATS SCORE REPORT" in text
    assert "FACTOR BREAKDOWN" in text
    assert "TOP SUGGESTIONS" in text


def test_report_for_missing_id(client):
    assert client.get("/report/99999.txt").status_code == 404
