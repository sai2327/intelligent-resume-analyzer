"""End-to-end route tests: ATS score tracker wiring through the Flask app."""

import gzip
import io

from tests.conftest import SAMPLE_JD_TEXT

from database import database


def _upload(client, resume_bytes, filename, **extra_form):
    data = {"resume_file": (io.BytesIO(resume_bytes), filename)}
    data.update(extra_form)
    return data


def test_analyze_page_contains_ats_panel(client, sample_resume_pdf_bytes):
    response = client.post(
        "/analyze",
        data=_upload(client, sample_resume_pdf_bytes, "resume.pdf"),
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ATS Score Tracker" in html
    assert "Standalone Resume Audit" in html
    assert "What to change" in html


def test_match_page_contains_ats_panel_and_changes(client, sample_resume_docx_bytes):
    # Missing JD text must be rejected by validation.
    response = client.post(
        "/match-job",
        data=_upload(client, sample_resume_docx_bytes, "resume.docx", jd_text=""),
        content_type="multipart/form-data",
    )
    assert response.status_code == 400

    jd = (
        "Job Title: Software Developer\n\n"
        "REQUIREMENTS\n"
        "3+ years of experience in software development.\n"
        "Bachelor's degree in Computer Science or related field.\n"
        "Strong proficiency in Python and JavaScript.\n"
        "Experience with React and Node.js.\n"
        "Experience with MySQL.\n\n"
        "PREFERRED SKILLS\n"
        "Experience with AWS.\n\n"
        "RESPONSIBILITIES\n"
        "Design and implement scalable backend services.\n"
    )
    response = client.post(
        "/match-job",
        data=_upload(client, sample_resume_docx_bytes, "resume.docx", jd_text=jd),
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ATS Score Tracker" in html
    assert "Resume vs Job Description" in html
    assert "What to change" in html


def test_history_page_lists_tracked_scores(client):
    # Ensure at least one record exists, then render the tracker page.
    database.save_analysis("tracker-test.pdf", None, None, gemini_used=False, ats_result={
        "mode": "standalone", "total": 77.5, "grade": "Strong",
        "grade_detail": "", "factors": [], "excluded_factors": [], "top_suggestions": [],
    })
    response = client.get("/history")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ATS Score Tracker" in html
    assert "tracker-test.pdf" in html
    assert "77.5" in html


def test_history_csv_export(client):
    database.save_analysis("csv-test.pdf", "Data Analyst", {"overall": {"overall_score": 60.0}},
                           gemini_used=False, ats_result={
        "mode": "job_match", "total": 66.6, "grade": "Fair",
        "grade_detail": "", "factors": [], "excluded_factors": [], "top_suggestions": [],
    })
    response = client.get("/history/export.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    body = response.get_data(as_text=True)
    assert "ats_score" in body and "csv-test.pdf" in body and "66.6" in body


def test_json_detail_returns_breakdown_as_object(client):
    database.save_analysis("json-test.pdf", None, None, gemini_used=False, ats_result={
        "mode": "standalone", "total": 80.0, "grade": "Strong",
        "grade_detail": "d", "factors": [{"key": "format"}],
        "excluded_factors": [], "top_suggestions": [],
    })
    record_id = database.list_recent_analyses(limit=1)[0]["id"]
    response = client.get(f"/results/{record_id}")
    data = response.get_json()
    assert response.status_code == 200
    assert isinstance(data["ats_breakdown"], dict)
    assert data["ats_breakdown"]["total"] == 80.0


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_api_paths_return_json_errors_not_html(client):
    """Programmatic callers must get machine-readable errors from API-style
    paths - never an HTML page."""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    assert "error" in response.get_json()

    response = client.post("/results/999999")
    assert response.status_code == 405
    assert "error" in response.get_json()

    response = client.get("/report/999999.txt")
    assert response.status_code == 404  # report route handles its own 404

    # A JSON-shaped body for an oversized request is env-dependent (413 handler);
    # just assert the API 404 shape above covers the handler wiring.


def test_charts_render_on_real_pages(client, sample_resume_pdf_bytes):
    """The server-rendered graphs must appear: keyword donut on results,
    score-trend line on the tracker page."""
    from database import database
    response = client.post(
        "/match-job",
        data={"resume_file": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf"),
              "jd_text": SAMPLE_JD_TEXT},
        content_type="multipart/form-data",
    )
    html = response.get_data(as_text=True)
    assert "chart-donut-label" in html  # keyword coverage donut (match mode)

    database.save_analysis("chart-test.pdf", None, None, False, ats_result={
        "mode": "standalone", "total": 60.0, "grade": "Fair", "grade_detail": "",
        "factors": [], "excluded_factors": [], "top_suggestions": [],
    })
    database.save_analysis("chart-test.pdf", None, None, False, ats_result={
        "mode": "standalone", "total": 75.0, "grade": "Strong", "grade_detail": "",
        "factors": [], "excluded_factors": [], "top_suggestions": [],
    })
    response = client.get("/history")
    html = response.get_data(as_text=True)
    assert "chart-line" in html and "chart-dot" in html  # trend chart


def test_chart_builders_geometry():
    from services.charts import charts

    trend = charts.trend_chart([{"label": f"r{i}", "score": s}
                                for i, s in enumerate([10, 45, 70, 90])])
    assert trend is not None
    for dot in trend["dots"]:
        assert trend["padding"] <= dot["x"] <= trend["width"] - trend["padding"]
        assert trend["padding"] <= dot["y"] <= trend["height"] - trend["padding"]

    assert charts.trend_chart([{"label": "a", "score": 50}]) is None  # too few points

    bars = charts.grouped_bars(
        [{"key": "format", "label": "Format"}],
        [{"filename": "a", "factors": {"format": 80}},
         {"filename": "b", "factors": {"format": 40}}],
        ["#111", "#222"],
    )
    assert bars is not None
    assert len(bars["rows"][0]["bars"]) == 2
    assert bars["rows"][0]["bars"][0]["width"] == bars["rows"][0]["bars"][1]["width"] * 2

    assert charts.donut([{"label": "x", "value": 0, "color": "#000"}]) is None


def test_gzip_compression_on_large_pages(client, sample_resume_pdf_bytes):
    """Large text responses must be gzipped when the client accepts it - the
    results page carries inline SVG charts and benefits most."""
    client.post("/match-job",
                data={"resume_file": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf"),
                      "jd_text": SAMPLE_JD_TEXT},
                content_type="multipart/form-data")
    # Small JSON responses stay under the 500-byte threshold - use /history.
    response = client.get("/history", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("Content-Encoding") == "gzip"
    assert response.headers.get("Vary", "").find("Accept-Encoding") != -1
    # Decompressed body is valid HTML with the tracker content.
    decompressed = gzip.decompress(response.get_data()).decode("utf-8")
    assert "ATS Score Tracker" in decompressed


def test_small_responses_are_not_gzipped(client):
    response = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert response.headers.get("Content-Encoding") != "gzip"


def test_report_endpoints_send_cache_headers(client, sample_resume_pdf_bytes):
    """Stored analyses are immutable - the JSON and TXT report endpoints may be
    cached briefly by the client."""
    client.post("/analyze",
                data={"resume_file": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf")},
                content_type="multipart/form-data")
    from database import database
    row_id = database.list_recent_analyses(limit=1)[0]["id"]

    json_resp = client.get(f"/results/{row_id}")
    assert "max-age" in json_resp.headers.get("Cache-Control", "")

    txt_resp = client.get(f"/report/{row_id}.txt")
    assert "max-age" in txt_resp.headers.get("Cache-Control", "")


def test_factor_bars_use_per_factor_colors(client, sample_resume_docx_bytes):
    """A weak factor must render red even when the overall grade is strong -
    bars reflect the factor's own score, never the overall grade."""
    response = client.post(
        "/match-job",
        data={"resume_file": (io.BytesIO(sample_resume_docx_bytes), "resume.docx"),
              "jd_text": SAMPLE_JD_TEXT},
        content_type="multipart/form-data",
    )
    html = response.get_data(as_text=True)
    # The fixture resume has weak keyword coverage (<55) while overall is Strong:
    # both a red factor bar and a primary-grade badge must coexist.
    assert "bg-danger" in html
    assert "bg-primary" in html
