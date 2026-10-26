"""Tests for the advanced features: potential score, radar chart, multi-JD
ranking, and the JSON API endpoints."""

import io

from services.analysis_service import rank_job_descriptions, split_jd_list
from services.ats_scorer import score_resume_standalone, score_resume_vs_jd
from services.information_extractor import extract_all
from services.job_description_parser import parse_job_description
from tests.conftest import SAMPLE_JD_TEXT, SAMPLE_RESUME_TEXT_LINES

RESUME = "\n".join(SAMPLE_RESUME_TEXT_LINES)

JD_ANALYST = ("Job Title: Data Analyst\n\nREQUIREMENTS\n3+ years of experience.\n"
              "Bachelor's degree required.\nExperience with Python and SQL.\n\n"
              "RESPONSIBILITIES\nAnalyze data and build dashboards.\n")
JD_DEVOPS = ("Job Title: DevOps Engineer\n\nREQUIREMENTS\n5+ years of experience.\n"
             "Bachelor's degree required.\nExperience with Terraform, Kubernetes and AWS.\n\n"
             "RESPONSIBILITIES\nAutomate infrastructure and deployments.\n")


# ---------------------------------------------------------------- potential

def test_potential_is_upper_bound_and_never_below_actual():
    rdata, jdata = extract_all(RESUME), parse_job_description(JD_ANALYST)
    ats = score_resume_vs_jd(RESUME, JD_ANALYST, rdata, jdata)
    if ats["potential"]:
        assert ats["potential"]["total"] >= ats["total"]
        assert ats["potential"]["total"] <= 100.0
        # Potential only exists when there is something real to gain.
        assert ats["potential"]["total"] > ats["potential"]["current"] + 0.05


def test_potential_skipped_when_already_maxed():
    rdata, jdata = extract_all(RESUME), parse_job_description(JD_ANALYST)
    ats = score_resume_vs_jd(RESUME, JD_ANALYST, rdata, jdata)
    # If the honest ceiling equals the current score, no potential is shown.
    if ats["potential"] is None:
        assert ats["total"] >= 99.95


def test_potential_fixable_factors_capped_not_invented():
    """Non-fixable factors (experience, education, content) must keep their
    real score inside the potential estimate."""
    rdata, jdata = extract_all(RESUME), parse_job_description(JD_ANALYST)
    ats = score_resume_vs_jd(RESUME, JD_ANALYST, rdata, jdata)
    real = {f["key"]: f["score"] for f in ats["factors"] if f["available"]}
    for key in ("experience", "education", "content"):
        if key in real and ats["potential"]:
            # The potential can never exceed 100, and a weak non-fixable
            # factor caps it below 100 no matter what else is fixed.
            if real[key] < 60:
                assert ats["potential"]["total"] < 95.0


def test_standalone_potential():
    data = extract_all(RESUME)
    ats = score_resume_standalone(RESUME, data)
    if ats["potential"]:
        assert ats["potential"]["total"] >= ats["total"]


# ---------------------------------------------------------------- radar

def test_radar_geometry_for_seven_factors():
    rdata, jdata = extract_all(RESUME), parse_job_description(JD_ANALYST)
    ats = score_resume_vs_jd(RESUME, JD_ANALYST, rdata, jdata)
    radar = ats["radar"]
    assert radar is not None
    axes = radar["axes"]
    assert len(axes) == len([f for f in ats["factors"] if f["available"]])
    for axis in axes:
        # All axis endpoints lie within the 200x200 viewBox.
        assert 0 <= axis["x"] <= 200 and 0 <= axis["y"] <= 200
    # The score polygon has one vertex per axis.
    assert len(radar["score_polygon"].split()) == len(axes)
    # Four grid rings (25/50/75/100), each with n vertices.
    assert len(radar["rings"]) == 4
    for ring in radar["rings"]:
        assert len(ring.split()) == len(axes)


def test_radar_skipped_when_too_few_factors():
    # A degenerate JD excludes most factors -> radar needs >= 3 axes.
    resume_data = extract_all(RESUME)
    jd_garbage = "!!! ???"
    ats = score_resume_vs_jd(RESUME, jd_garbage, resume_data, parse_job_description(jd_garbage))
    available = [f for f in ats["factors"] if f["available"]]
    if len(available) < 3:
        assert ats["radar"] is None


# ---------------------------------------------------------------- ranking

def test_split_jd_list_on_separators():
    raw = JD_ANALYST + "\n---\n" + JD_DEVOPS + "\n---\n   \n---\nshort"
    jds = split_jd_list(raw)
    assert len(jds) == 2  # empty and too-short fragments dropped


def test_ranking_orders_best_fit_first():
    result = rank_job_descriptions(RESUME, [JD_ANALYST, JD_DEVOPS])
    ranking = result["ranking"]
    assert len(ranking) == 2
    scores = [r["ats_total"] for r in ranking]
    assert scores == sorted(scores, reverse=True)
    # The analyst JD must beat DevOps for this software-developer resume.
    assert ranking[0]["job_title"] == "Data Analyst"
    assert ranking[0]["grade"] in {"Excellent", "Strong", "Fair"}


def test_ranking_deterministic():
    a = rank_job_descriptions(RESUME, [JD_ANALYST, JD_DEVOPS])
    b = rank_job_descriptions(RESUME, [JD_ANALYST, JD_DEVOPS])
    assert [r["ats_total"] for r in a["ranking"]] == [r["ats_total"] for r in b["ranking"]]


# ---------------------------------------------------------------- API

def test_api_analyze_returns_full_json(client, sample_resume_pdf_bytes):
    response = client.post(
        "/api/analyze",
        data={"resume_file": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["ats"]["mode"] == "standalone"
    assert isinstance(data["ats"]["total"], float)
    assert len(data["ats"]["factors"]) == 4
    assert "change_suggestions" in data
    assert data["detection"]["verdict"] in {"resume", "likely_resume", "uncertain"}
    assert "Python" in data["resume_data"]["skills"] or data["resume_data"]["skills"]


def test_api_analyze_rejects_non_resume_as_json(client, academic_pdf_bytes):
    response = client.post(
        "/api/analyze",
        data={"resume_file": (io.BytesIO(academic_pdf_bytes), "thesis.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "does not look like a resume" in data["error"]
    assert data["detection"]["verdict"] == "not_resume"


def test_api_analyze_rejects_bad_file_type_as_json(client):
    response = client.post(
        "/api/analyze",
        data={"resume_file": (io.BytesIO(b"not a pdf"), "resume.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_api_match_returns_match_and_ats(client, sample_resume_docx_bytes):
    response = client.post(
        "/api/match",
        data={
            "resume_file": (io.BytesIO(sample_resume_docx_bytes), "resume.docx"),
            "jd_text": SAMPLE_JD_TEXT,
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["ats"]["mode"] == "job_match"
    assert data["job_description"]["job_title"] == "Software Developer"
    assert data["match"]["overall"]["overall_score"] is not None
    assert data["recommendations"]


def test_api_match_requires_jd(client, sample_resume_docx_bytes):
    response = client.post(
        "/api/match",
        data={"resume_file": (io.BytesIO(sample_resume_docx_bytes), "resume.docx"),
              "jd_text": ""},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_api_rank_jds_json_body(client):
    response = client.post(
        "/api/rank-jds",
        json={"resume_text": RESUME, "jds": [JD_ANALYST, JD_DEVOPS]},
    )
    assert response.status_code == 200
    data = response.get_json()
    scores = [r["ats_total"] for r in data["ranking"]]
    assert scores == sorted(scores, reverse=True)
    assert data["ranking"][0]["job_title"] == "Data Analyst"
    # Best fit carries actionable suggestions.
    assert data["ranking"][0]["top_suggestions"]


def test_api_rank_jds_multipart(client, sample_resume_docx_bytes):
    response = client.post(
        "/api/rank-jds",
        data={"resume_file": (io.BytesIO(sample_resume_docx_bytes), "resume.docx"),
              "jds_text": JD_ANALYST + "\n---\n" + JD_DEVOPS},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert len(response.get_json()["ranking"]) == 2


def test_api_rank_jds_rejects_empty_jd_list(client):
    response = client.post("/api/rank-jds", json={"resume_text": RESUME, "jds": []})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_api_rank_jds_caps_at_ten(client):
    many = [JD_ANALYST] * 15
    response = client.post("/api/rank-jds", json={"resume_text": RESUME, "jds": many})
    data = response.get_json()
    assert response.status_code == 200
    assert len(data["ranking"]) <= 10


def test_results_page_shows_potential_and_radar(client, sample_resume_pdf_bytes):
    response = client.post(
        "/analyze",
        data={"resume_file": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf")},
        content_type="multipart/form-data",
    )
    html = response.get_data(as_text=True)
    assert "Potential score" in html or "up to" in html
    assert "ats-radar" in html
    assert "ats-radar__score" in html


def test_ranking_page_renders(client, sample_resume_docx_bytes):
    response = client.post(
        "/rank-jobs",
        data={"resume_file": (io.BytesIO(sample_resume_docx_bytes), "resume.docx"),
              "jds_text": JD_ANALYST + "\n---\n" + JD_DEVOPS},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Best-Fit Job Ranking" in html
    assert "BEST FIT" in html
    assert "Data Analyst" in html
    assert "DevOps Engineer" in html


def test_ranking_page_requires_jds(client, sample_resume_docx_bytes):
    response = client.post(
        "/rank-jobs",
        data={"resume_file": (io.BytesIO(sample_resume_docx_bytes), "resume.docx"),
              "jds_text": "too short"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "No usable job descriptions" in response.get_data(as_text=True)
