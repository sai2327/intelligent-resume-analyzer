"""Tests for resume comparison, per-file progress tracking, adjacent-skill
suggestions, and the JD quality checker."""

import io

from docx import Document as DocxDocument

from database import database
from services.analysis_service import assess_jd_quality, compare_resumes
from services.information_extractor import extract_all
from services.job_description_parser import parse_job_description
from services.recommendation_engine import generate_recommendations
from services.matching_engine import compare_resume_to_job
from tests.conftest import SAMPLE_RESUME_TEXT_LINES

RESUME_STRONG = "\n".join(SAMPLE_RESUME_TEXT_LINES)
RESUME_WEAK = """Bob Brown
bob@x.com
555-999-8888
Worked as a cashier at Store X for 2 years.
High school diploma, 2015.
"""
JD = ("Job Title: Software Developer\n\nREQUIREMENTS\n3+ years of experience.\n"
      "Bachelor's degree required.\nStrong Python and JavaScript skills.\n"
      "Experience with React and Node.js.\n\nRESPONSIBILITIES\nBuild web applications.\n")


def _entries(*texts):
    return [{"filename": f"resume{i + 1}.pdf", "text": t} for i, t in enumerate(texts)]


# ---------------------------------------------------------------- compare

def test_compare_ranks_stronger_resume_first():
    result = compare_resumes(_entries(RESUME_WEAK, RESUME_STRONG), JD)
    assert result["mode"] == "job_match"
    assert result["winner"] == "resume2.pdf"
    assert result["comparison"][0]["ats_total"] >= result["comparison"][1]["ats_total"]
    assert result["rejected"] == []


def test_compare_deltas_are_zero_for_winner_and_negative_for_loser():
    result = compare_resumes(_entries(RESUME_STRONG, RESUME_WEAK), JD)
    winner, loser = result["comparison"]
    assert all(delta == 0 for delta in winner["factor_deltas"].values())
    assert any(delta < 0 for delta in loser["factor_deltas"].values())


def test_compare_standalone_mode_without_jd():
    result = compare_resumes(_entries(RESUME_STRONG, RESUME_WEAK), None)
    assert result["mode"] == "standalone"
    assert result["winner"] == "resume1.pdf"
    assert all(c["match_overall"] is None for c in result["comparison"])


def test_compare_is_deterministic():
    a = compare_resumes(_entries(RESUME_WEAK, RESUME_STRONG), JD)
    b = compare_resumes(_entries(RESUME_WEAK, RESUME_STRONG), JD)
    assert [c["ats_total"] for c in a["comparison"]] == [c["ats_total"] for c in b["comparison"]]


def test_compare_requires_two_resumes():
    assert len(compare_resumes(_entries(RESUME_STRONG), JD)["comparison"]) == 1


def test_compare_route_with_two_files(client):
    def docx_bytes(text):
        buf = io.BytesIO()
        d = DocxDocument()
        for line in text.splitlines():
            d.add_paragraph(line)
        d.save(buf)
        return buf.getvalue()

    response = client.post(
        "/compare",
        data={
            "resume_files": [
                (io.BytesIO(docx_bytes(RESUME_STRONG)), "strong.docx"),
                (io.BytesIO(docx_bytes(RESUME_WEAK)), "weak.docx"),
            ],
            "jd_text": JD,
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Resume Comparison" in html and "WINNER" in html
    assert "strong.docx" in html and "weak.docx" in html


def test_compare_route_requires_two_files(client, sample_resume_pdf_bytes):
    response = client.post(
        "/compare",
        data={"resume_files": [(io.BytesIO(sample_resume_pdf_bytes), "one.pdf")],
              "jd_text": JD},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_api_compare_json_body(client):
    response = client.post(
        "/api/compare",
        json={"resumes": [{"filename": "a.pdf", "text": RESUME_STRONG},
                          {"filename": "b.pdf", "text": RESUME_WEAK}],
              "jd_text": JD},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["winner"] == "a.pdf"
    assert data["comparison"][0]["filename"] == "a.pdf"


def test_api_compare_rejects_single_resume(client):
    response = client.post("/api/compare", json={"resumes": [{"filename": "a.pdf", "text": RESUME_STRONG}]})
    assert response.status_code == 400


# ---------------------------------------------------------------- progress

def test_file_progress_math(tmp_path, monkeypatch):
    from config import config
    monkeypatch.setattr(config, "DATABASE_PATH", str(tmp_path / "t.db"))
    database.init_db()

    ats = {"mode": "standalone", "total": 50.0, "grade": "Fair", "grade_detail": "",
           "factors": [], "excluded_factors": [], "top_suggestions": []}
    database.save_analysis("my_cv.pdf", None, None, False, ats_result=ats)
    ats2 = {**ats, "total": 61.2, "grade": "Strong"}
    database.save_analysis("my_cv.pdf", None, None, False, ats_result=ats2)
    ats3 = {**ats, "total": 58.0}
    database.save_analysis("my_cv.pdf", None, None, False, ats_result=ats3)
    database.save_analysis("one_off.pdf", None, None, False, ats_result=ats)  # only once

    progress = database.get_file_progress()
    assert len(progress) == 1
    p = progress[0]
    assert p["filename"] == "my_cv.pdf"
    assert p["runs"] == 3
    assert p["first_score"] == 50.0
    assert p["last_score"] == 58.0
    assert p["delta"] == 8.0
    assert p["best_score"] == 61.2
    assert p["direction"] == "up"


def test_history_page_renders_progress(client, tmp_path, monkeypatch):
    from config import config
    monkeypatch.setattr(config, "DATABASE_PATH", str(tmp_path / "h.db"))
    database.init_db()
    ats = {"mode": "standalone", "total": 55.0, "grade": "Fair", "grade_detail": "",
           "factors": [], "excluded_factors": [], "top_suggestions": []}
    database.save_analysis("cv.docx", None, None, False, ats_result=ats)
    database.save_analysis("cv.docx", None, None, False, ats_result={**ats, "total": 70.0})
    response = client.get("/history")
    html = response.get_data(as_text=True)
    assert "Resume progress" in html and "cv.docx" in html


# ---------------------------------------------------------------- adjacent skills

def test_adjacent_skill_suggestion_for_related_missing_skill():
    resume_text = RESUME_STRONG.replace(
        "Python, JavaScript, React, Node.js, REST API, Git, MySQL, Docker",
        "Python, JavaScript, React, Node.js, REST API, Git, MySQL, Docker, Pandas, NumPy",
    )
    resume_data = extract_all(resume_text)
    # Machine Learning shares the "AI & Machine Learning" category with the
    # Pandas/NumPy the resume already lists.
    jd_data = parse_job_description(
        "Job Title: Data Engineer\n\nREQUIREMENTS\nExperience with Pandas, NumPy and Machine Learning.\n"
    )
    match = compare_resume_to_job(resume_data, jd_data, resume_text, "")
    assert "Machine Learning" in jd_data["required_skills"]
    assert "Machine Learning" not in resume_data["skills"]
    recs = generate_recommendations(match, resume_skills=resume_data["skills"])
    joined = " ".join(r["text"] for r in recs)
    assert "small step" in joined


def test_no_adjacent_suggestion_without_resume_skills():
    jd_data = parse_job_description("Job Title: X\n\nREQUIREMENTS\nExperience with Pandas.\n")
    resume_data = extract_all(RESUME_STRONG)
    match = compare_resume_to_job(resume_data, jd_data, RESUME_STRONG, "")
    recs = generate_recommendations(match, resume_skills=None)
    assert all("small step" not in r["text"] for r in recs)


# ---------------------------------------------------------------- jd quality

def test_good_jd_scores_good():
    jd_data = parse_job_description(SAMPLE_JD := (
        "Job Title: Software Developer\n\nREQUIREMENTS\n3+ years of experience in software development.\n"
        "Bachelor's degree in Computer Science or a related field is required for this position.\n"
        "Strong proficiency in Python and JavaScript is essential for this role.\n"
        "Experience with React and Node.js for frontend integration work.\n"
        "Experience with MySQL databases and REST API design.\n"
        "Familiarity with Docker and CI/CD pipelines is a plus.\n\n"
        "RESPONSIBILITIES\nDesign and implement scalable backend services for our products.\n"
        "Write unit tests and participate in daily code reviews with the team.\n"
        "Collaborate with frontend developers to integrate user facing features.\n"
        "Participate in Agile ceremonies and sprint planning every week.\n"
    ))
    quality = assess_jd_quality(SAMPLE_JD, jd_data)
    assert quality["quality"] == "good"
    assert quality["warnings"] == []


def test_short_jd_flagged_poor():
    jd = "We need a dev who knows Python."
    jd_data = parse_job_description(jd)
    quality = assess_jd_quality(jd, jd_data)
    assert quality["quality"] in {"fair", "poor"}
    assert quality["warnings"]


def test_jd_quality_exposed_via_api(client, sample_resume_docx_bytes):
    response = client.post(
        "/api/match",
        data={"resume_file": (io.BytesIO(sample_resume_docx_bytes), "resume.docx"),
              "jd_text": "We need a dev who knows Python."},
        content_type="multipart/form-data",
    )
    data = response.get_json()
    assert data["jd_quality"]["quality"] in {"fair", "poor"}
    assert data["jd_quality"]["warnings"]


def test_jd_quality_shown_on_results_page(client, sample_resume_docx_bytes):
    response = client.post(
        "/match-job",
        data={"resume_file": (io.BytesIO(sample_resume_docx_bytes), "resume.docx"),
              "jd_text": "We need a dev who knows Python."},
        content_type="multipart/form-data",
    )
    html = response.get_data(as_text=True)
    assert "Job description check" in html
