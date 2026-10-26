"""
Flask backend for the Intelligent Resume Analysis and Job Matching System.

Routes only handle HTTP concerns (validation, orchestration calls, template
rendering); all business logic lives in services/ and database/.
"""

import csv
import gzip
import io
import json
import logging
import time

from flask import Flask, Response, jsonify, render_template, request

from config import config
from database import database
from services import analysis_service, ats_scorer
from services.classifier import is_model_available
from services.document_parser import DocumentParsingError, extract_text
from services.charts import charts
from services import shortlist_service
from services.information_extractor import _get_spacy_model
from services.resume_detector import looks_like_resume, rejection_message
from utils.file_utils import get_extension
from utils.validators import ValidationError, validate_text_input, validate_upload_file

VALID_STRICTNESS = ("lenient", "standard", "strict")

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    # Repeat visits: static assets (css/js) are re-fetched far less often.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600

    database.init_db()
    logger.info("Application starting. Model available: %s", is_model_available())

    # ---- request telemetry ----
    @app.before_request
    def _start_timer():
        from flask import g
        g.start_time = time.perf_counter()

    # ---- error handlers ----

    def _wants_json() -> bool:
        """API-style paths must never receive an HTML error page - programmatic
        callers need a machine-readable body."""
        return request.path.startswith(("/api/", "/results/", "/report/", "/history/export"))

    @app.errorhandler(413)
    def handle_file_too_large(_error):
        max_mb = config.MAX_CONTENT_LENGTH_MB
        message = f"The uploaded file exceeds the {max_mb:.0f} MB limit."
        if _wants_json():
            return jsonify({"error": message}), 413
        return render_template("error.html", message=message), 413

    @app.errorhandler(404)
    def handle_not_found(_error):
        if _wants_json():
            return jsonify({"error": "Not found."}), 404
        return render_template("error.html", message="Page not found."), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_error):
        if _wants_json():
            return jsonify({"error": "Method not allowed."}), 405
        return render_template("error.html", message="Method not allowed."), 405

    @app.errorhandler(500)
    def handle_server_error(error):
        logger.exception("Unhandled server error: %s", error)
        if _wants_json():
            return jsonify({"error": "An unexpected internal error occurred."}), 500
        return render_template("error.html", message="An unexpected error occurred. Please try again."), 500

    @app.after_request
    def add_process_time(response):
        from flask import g
        start = getattr(g, "start_time", None)
        if start is not None:
            response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
        return response

    @app.after_request
    def compress_response(response):
        """Gzip text responses above 500 bytes: pages now carry several inline
        SVG charts, so this cuts transfer size roughly 3-4x with no extra
        dependencies. Streamed responses are skipped (none exist today)."""
        accept = request.headers.get("Accept-Encoding", "")
        content_type = response.headers.get("Content-Type", "")
        compressible = content_type.startswith(
            ("text/html", "application/json", "text/plain", "text/css", "image/svg")
        )
        if (response.status_code < 300
                and response.direct_passthrough is False
                and "gzip" in accept.lower()
                and compressible
                and (response.calculate_content_length() or 0) > 500):
            response.headers["Content-Encoding"] = "gzip"
            response.set_data(gzip.compress(response.get_data(), compresslevel=6))
        response.headers.setdefault("Vary", "Accept-Encoding")
        return response

    # ---- helpers ----

    def _read_resume_text():
        """Extract resume text from the required uploaded file. Never writes to disk."""
        file_storage = request.files.get("resume_file")
        validate_upload_file(file_storage, config.ALLOWED_EXTENSIONS, config.MAX_CONTENT_LENGTH)
        extension = get_extension(file_storage.filename)
        text = extract_text(file_storage.stream, extension)
        return text, file_storage.filename

    def _read_jd_text():
        """Extract JD text from an uploaded file OR pasted text (either is accepted)."""
        file_storage = request.files.get("jd_file")
        if file_storage and file_storage.filename:
            validate_upload_file(file_storage, config.ALLOWED_EXTENSIONS, config.MAX_CONTENT_LENGTH)
            extension = get_extension(file_storage.filename)
            return extract_text(file_storage.stream, extension)

        pasted_text = request.form.get("jd_text", "")
        return validate_text_input(pasted_text, "Job description", min_length=30)

    def _gate_resume(text):
        """Run the resume detector once. Returns (detection, error_response);
        error_response is a rendered 400 response when the upload is not a resume."""
        detection = looks_like_resume(text)
        if detection["verdict"] == "not_resume":
            return detection, (render_template(
                "error.html", message=rejection_message(detection)
            ), 400)
        return detection, None

    def _form_strictness() -> str:
        value = (request.form.get("strictness") or "standard").strip().lower()
        return value if value in VALID_STRICTNESS else "standard"

    # ---- pages ----

    app.jinja_env.globals["donut"] = charts.donut
    app.jinja_env.globals["stacked_bar"] = charts.stacked_bar

    @app.route("/")
    def index():
        return render_template("index.html", model_available=is_model_available())

    @app.route("/health")
    def health():
        database_ok = True
        try:
            from database import database as db_module
            with db_module.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
        except Exception as exc:
            database_ok = False
            logger.warning("health check: database unreachable: %s", exc)
        return jsonify(
            {
                "status": "ok" if database_ok and is_model_available() else "degraded",
                "model_available": is_model_available(),
                            "database": "ok" if database_ok else "unreachable",
                "nlp": "ok" if _get_spacy_model() is not None else "regex-fallback",
                "server": "waitress" if not config.DEBUG else "flask-dev",
            }
        )

    @app.route("/analyze", methods=["POST"])
    @app.route("/analyze-resume", methods=["POST"])
    def analyze():
        try:
            resume_text, filename = _read_resume_text()
        except (ValidationError, DocumentParsingError) as exc:
            return render_template("error.html", message=str(exc)), 400

        detection, error = _gate_resume(resume_text)
        if error:
            return error

        strictness = _form_strictness()
        result = analysis_service.analyze_resume(resume_text, strictness=strictness, detection=detection)
        analysis_id = database.save_analysis(
            filename, result.get("category"), None, gemini_used=False,
            ats_result=result.get("ats_result"),
        )

        ats_result = result.get("ats_result")
        category_counts = {}
        for skill in result["resume_data"].get("skills", []):
            cat = ats_scorer.skill_categories().get(skill, "Other")
            category_counts[cat] = category_counts.get(cat, 0) + 1
        skill_bars = charts.score_bars(
            [{"label": cat, "score": count * 100.0 / max(category_counts.values())}
             for cat, count in sorted(category_counts.items(), key=lambda kv: -kv[1])],
            color="#10b981",
        ) if category_counts else None
        return render_template(
            "results.html",
            mode="analyze",
            filename=filename,
            analysis_id=analysis_id,
            resume_data=result["resume_data"],
            category=result["category"],
            top_predictions=result["top_predictions"],
            ats_result=ats_result,
            ats_changes=ats_scorer.get_change_suggestions(ats_result) if ats_result else [],
            detection=result.get("detection"),
            skill_bars=skill_bars,
            skill_total=len(result["resume_data"].get("skills", [])),
            strictness=strictness,
        )

    @app.route("/match-job", methods=["POST"])
    def match_job():
        try:
            resume_text, filename = _read_resume_text()
            jd_text = _read_jd_text()
        except (ValidationError, DocumentParsingError) as exc:
            return render_template("error.html", message=str(exc)), 400

        detection, error = _gate_resume(resume_text)
        if error:
            return error

        strictness = _form_strictness()
        target_title = (request.form.get("target_title") or "").strip()[:80] or None
        result = analysis_service.analyze_and_match(
            resume_text, jd_text,
            strictness=strictness, target_title=target_title, detection=detection,
        )

        analysis_id = database.save_analysis(
            filename,
            result.get("category"),
            result.get("match"),
            gemini_used=False,
            ats_result=result.get("ats_result"),
        )

        return render_template(
            "results.html",
            mode="match",
            filename=filename,
            analysis_id=analysis_id,
            resume_data=result["resume_data"],
            category=result["category"],
            top_predictions=result["top_predictions"],
            job_description=result["job_description"],
            match=result["match"],
            ats_result=result["ats_result"],
            ats_changes=ats_scorer.get_change_suggestions(result["ats_result"]),
            recommendations=result["recommendations"],
            detection=result.get("detection"),
            jd_quality=result.get("jd_quality"),
            strictness=strictness,
        )

    @app.route("/results/<int:analysis_id>")
    def view_result(analysis_id):
        record = database.get_analysis(analysis_id)
        if record is None:
            return jsonify({"error": "Analysis record not found."}), 404
        # The breakdown is stored as a JSON string; return it as a real object
        # so the downloaded report is properly structured.
        if record.get("ats_breakdown"):
            try:
                record["ats_breakdown"] = json.loads(record["ats_breakdown"])
            except (TypeError, json.JSONDecodeError):
                pass
        response = jsonify(record)
        # A stored analysis is immutable: safe to cache briefly client-side.
        response.headers["Cache-Control"] = "private, max-age=300"
        return response

    @app.route("/history/export.csv")
    def export_history_csv():
        """Download the ATS tracker history as CSV for spreadsheet analysis."""
        rows = database.list_recent_analyses(limit=500)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "id", "created_at", "resume_filename", "type",
            "ats_score", "ats_grade", "overall_match",
            "skill_score", "similarity_score", "experience_score", "education_score",
            "matched_required_count", "missing_required_count", "gemini_used",
        ])
        for row in rows:
            writer.writerow([
                row["id"], row["created_at"], row["resume_filename"],
                row.get("ats_mode") or "",
                row.get("ats_score"), row.get("ats_grade"), row.get("overall_score"),
                row.get("skill_score"), row.get("similarity_score"),
                row.get("experience_score"), row.get("education_score"),
                row.get("matched_required_count"), row.get("missing_required_count"),
                bool(row.get("gemini_used")),
            ])
        output = Response(buffer.getvalue(), mimetype="text/csv")
        output.headers["Content-Disposition"] = "attachment; filename=ats_history.csv"
        return output

    @app.route("/report/<int:analysis_id>.txt")
    def report_txt(analysis_id):
        """Human-readable plain-text ATS report for any past run."""
        record = database.get_analysis(analysis_id)
        if record is None:
            return render_template("error.html", message="Analysis record not found."), 404

        lines = [
            "ATS SCORE REPORT",
            "=" * 60,
            f"Generated:  {record['created_at']}",
            f"File:       {record.get('resume_filename') or 'unknown'}",
            f"Mode:       {(record.get('ats_mode') or 'n/a').replace('_', ' ')}",
            "",
        ]
        breakdown = record.get("ats_breakdown")
        if breakdown:
            try:
                ats = json.loads(breakdown) if isinstance(breakdown, str) else breakdown
            except (TypeError, json.JSONDecodeError):
                ats = None
            if ats:
                lines += [
                    f"ATS SCORE:  {ats.get('total')} / 100  ({ats.get('grade')})",
                    ats.get("grade_detail") or "",
                    "-" * 60,
                    "FACTOR BREAKDOWN",
                ]
                for factor in ats.get("factors", []):
                    score = f"{factor['score']:.1f}" if factor.get("score") is not None else "N/A"
                    lines.append(
                        f"  {factor['label']:<24s} {score:>6s}   (weight {factor['weight'] * 100:.0f}%)"
                    )
                    lines.append(f"    {factor.get('detail', '')}")
                if ats.get("excluded_factors"):
                    lines.append(f"  Excluded (insufficient info): {', '.join(ats['excluded_factors'])}")
                lines += ["", "TOP SUGGESTIONS", "-" * 60]
                for i, item in enumerate(ats.get("top_suggestions", []), 1):
                    lines.append(f"  {i}. [{item['priority'].upper()}] ({item['factor']}) {item['text']}")
        else:
            lines.append("No ATS breakdown stored for this analysis.")

        lines += [
            "",
            "-" * 60,
            "SCORE HISTORY SUMMARY",
            f"  Overall job match: {record.get('overall_score') if record.get('overall_score') is not None else 'n/a'}%",
            f"  Skill score:       {record.get('skill_score') if record.get('skill_score') is not None else 'n/a'}%",
            f"  Text similarity:   {record.get('similarity_score') if record.get('similarity_score') is not None else 'n/a'}%",
            f"  Experience match:  {record.get('experience_score') if record.get('experience_score') is not None else 'n/a'}%",
            f"  Education match:   {record.get('education_score') if record.get('education_score') is not None else 'n/a'}%",
            "",
            "Generated by Intelligent Resume Analyzer - scores are heuristic",
            "estimates of ATS behaviour, not guarantees of any employer's decision.",
        ]

        output = Response("\n".join(lines), mimetype="text/plain")
        output.headers["Content-Disposition"] = f"attachment; filename=ats_report_{analysis_id}.txt"
        output.headers["Cache-Control"] = "private, max-age=300"
        return output

    @app.route("/history")
    def history():
        """ATS score tracker: every past run with scores, aggregate stats, a
        score-trend chart, and per-file progress for resumes analyzed more
        than once."""
        analyses = database.list_recent_analyses(limit=50)
        stats = database.get_tracker_stats()
        progress = database.get_file_progress(limit=100)
        for row in progress:
            row["sparkline"] = charts.trend_chart(
                [{"label": f"run {i + 1}", "score": s}
                 for i, s in enumerate(row["scores"])],
                width=110, height=30, padding=4,
            )
        chronological = list(reversed(analyses))
        trend = charts.trend_chart(
            [
                {"label": f"{row['resume_filename'] or 'run ' + str(row['id'])}",
                 "score": row["ats_score"]}
                for row in chronological
                if row["ats_score"] is not None
            ][:50]
        )
        return render_template(
            "history.html", analyses=analyses, stats=stats,
            progress=progress, trend=trend,
        )

    # ---- recruiter mode: bulk shortlisting ----

    @app.route("/shortlist", methods=["POST"])
    def shortlist():
        """Recruiter mode: screen many resumes against one job description.
        Kicks off a background job and redirects to a live progress page."""
        files = [f for f in request.files.getlist("resume_files") if f and f.filename]
        if not files:
            return render_template("error.html",
                                   message="Please select at least one resume file."), 400
        if len(files) > config.SHORTLIST_MAX_FILES:
            return render_template(
                "error.html",
                message=f"At most {config.SHORTLIST_MAX_FILES} resumes can be screened per batch.",
            ), 400

        entries = []
        try:
            for file_storage in files:
                validate_upload_file(file_storage, config.ALLOWED_EXTENSIONS, config.MAX_CONTENT_LENGTH)
                entries.append((file_storage.filename, file_storage.read()))
        except (ValidationError, DocumentParsingError) as exc:
            return render_template("error.html", message=str(exc)), 400

        try:
            jd_file = request.files.get("jd_file")
            if jd_file and jd_file.filename:
                validate_upload_file(jd_file, config.ALLOWED_EXTENSIONS, config.MAX_CONTENT_LENGTH)
                jd_text = extract_text(jd_file.stream, get_extension(jd_file.filename))
            else:
                jd_text = validate_text_input(request.form.get("jd_text", ""),
                                              "Job description", min_length=30)
        except (ValidationError, DocumentParsingError) as exc:
            return render_template("error.html", message=str(exc)), 400

        threshold_raw = request.form.get("threshold", "").strip()
        try:
            threshold = float(threshold_raw) if threshold_raw else None
        except ValueError:
            return render_template("error.html", message="Shortlist threshold must be a number."), 400

        job_id = shortlist_service.create_job(
            entries, jd_text, strictness=_form_strictness(),
            target_title=(request.form.get("target_title") or "").strip()[:80] or None,
            threshold=threshold,
        )
        from flask import redirect, url_for
        return redirect(url_for("shortlist_view", job_id=job_id))

    @app.route("/shortlist/<job_id>")
    def shortlist_view(job_id):
        """Live progress while the job runs; the ranked shortlist when done.
        Auto-refreshes (meta refresh) - no JavaScript needed."""
        job = shortlist_service.get_job(job_id)
        if job is None:
            return render_template("error.html",
                                   message="Shortlist job not found (it may have expired)."), 404
        if job["state"] != "done":
            return render_template("shortlist_progress.html", job=job)
        from services.charts import charts as chart_lib
        job["score_bars"] = chart_lib.score_bars(
            [{"label": r["filename"], "score": r["ats_total"]} for r in job["results"]],
            color="#16a34a",
        )
        return render_template("shortlist_results.html", job=job)

    @app.route("/shortlist/<job_id>/progress")
    def shortlist_progress(job_id):
        job = shortlist_service.get_job(job_id)
        if job is None:
            return jsonify({"error": "Shortlist job not found."}), 404
        percent = round(job["processed"] / job["total"] * 100) if job["total"] else 0
        return jsonify({
            "id": job["id"], "state": job["state"],
            "processed": job["processed"], "total": job["total"], "percent": percent,
            "skipped": len(job["skipped"]), "errors": len(job["errors"]),
        })

    @app.route("/api/shortlist/<job_id>")
    def api_shortlist(job_id):
        job = shortlist_service.get_job(job_id)
        if job is None:
            return jsonify({"error": "Shortlist job not found."}), 404
        job["score_bars"] = None
        return jsonify(job)

    # ---- advanced: multi-JD ranking + resume comparison + JSON API ----

    @app.route("/compare", methods=["POST"])
    def compare():
        """Compare 2-5 resumes against each other (with an optional JD)."""
        files = [f for f in request.files.getlist("resume_files") if f and f.filename]
        if len(files) < 2:
            return render_template(
                "error.html",
                message="Please select at least 2 resume files to compare (up to 5).",
            ), 400
        if len(files) > analysis_service.MAX_COMPARE_RESUMES:
            return render_template(
                "error.html",
                message=f"At most {analysis_service.MAX_COMPARE_RESUMES} resumes can be compared at once.",
            ), 400

        entries = []
        try:
            for file_storage in files:
                validate_upload_file(file_storage, config.ALLOWED_EXTENSIONS, config.MAX_CONTENT_LENGTH)
                entries.append({
                    "filename": file_storage.filename,
                    "text": extract_text(file_storage.stream, get_extension(file_storage.filename)),
                })
        except (ValidationError, DocumentParsingError) as exc:
            return render_template("error.html", message=str(exc)), 400

        jd_text = None
        try:
            jd_file = request.files.get("jd_file")
            if jd_file and jd_file.filename:
                validate_upload_file(jd_file, config.ALLOWED_EXTENSIONS, config.MAX_CONTENT_LENGTH)
                jd_text = extract_text(jd_file.stream, get_extension(jd_file.filename))
            else:
                pasted = request.form.get("jd_text", "")
                if pasted.strip():
                    jd_text = validate_text_input(pasted, "Job description", min_length=30)
        except (ValidationError, DocumentParsingError) as exc:
            return render_template("error.html", message=str(exc)), 400

        for entry in entries:
            detection = looks_like_resume(entry["text"])
            if detection["verdict"] == "not_resume":
                return render_template(
                    "error.html",
                    message=f"{entry['filename']}: {rejection_message(detection)}",
                ), 400

        result = analysis_service.compare_resumes(
            entries, jd_text, strictness=_form_strictness(),
            target_title=(request.form.get("target_title") or "").strip()[:80] or None,
        )
        factor_labels = {
            "keywords": "Keyword coverage", "skills": "Skills match",
            "title": "Job title match", "experience": "Experience match",
            "education": "Education match", "format": "Format & parseability",
            "content": "Content quality",
        }
        colors = ["#4f46e5", "#f59e0b", "#10b981", "#ef4444", "#0ea5e9"]
        factor_bars = charts.grouped_bars(
            [{"key": k, "label": label} for k, label in factor_labels.items()],
            result["comparison"], colors,
        )
        return render_template("compare.html", strictness=_form_strictness(),
                               factor_bars=factor_bars, **result)

    @app.route("/api/compare", methods=["POST"])
    def api_compare():
        """JSON API: compare 2-5 resumes. JSON body {"resumes": [{"filename",
        "text"}...], "jd_text": optional} or multipart resume_files[] + jd_text."""
        if request.is_json:
            data = request.get_json(silent=True) or {}
            entries = [
                {"filename": r.get("filename") or f"resume{i + 1}", "text": (r.get("text") or "")}
                for i, r in enumerate(data.get("resumes") or [])
                if isinstance(r, dict) and (r.get("text") or "").strip()
            ]
            jd_text = (data.get("jd_text") or "").strip() or None
        else:
            files = [f for f in request.files.getlist("resume_files") if f and f.filename]
            entries = []
            try:
                for file_storage in files:
                    validate_upload_file(file_storage, config.ALLOWED_EXTENSIONS, config.MAX_CONTENT_LENGTH)
                    entries.append({
                        "filename": file_storage.filename,
                        "text": extract_text(file_storage.stream, get_extension(file_storage.filename)),
                    })
            except (ValidationError, DocumentParsingError) as exc:
                return _json_error(str(exc))
            jd_text = request.form.get("jd_text", "").strip() or None

        if len(entries) < 2:
            return _json_error("At least 2 resumes are required to compare.")
        if len(entries) > analysis_service.MAX_COMPARE_RESUMES:
            return _json_error(f"At most {analysis_service.MAX_COMPARE_RESUMES} resumes can be compared.")

        for entry in entries:
            detection = looks_like_resume(entry["text"])
            if detection["verdict"] == "not_resume":
                return _json_error(f"{entry['filename']}: {rejection_message(detection)}",
                                   detection=detection)

        result = analysis_service.compare_resumes(
            entries, jd_text, strictness=_form_strictness(),
            target_title=(request.form.get("target_title") or "").strip()[:80] or None,
        )
        return jsonify(result)

    @app.route("/rank-jobs", methods=["POST"])
    def rank_jobs():
        """Rank one resume against multiple pasted job descriptions."""
        try:
            resume_text, filename = _read_resume_text()
        except (ValidationError, DocumentParsingError) as exc:
            return render_template("error.html", message=str(exc)), 400

        detection, error = _gate_resume(resume_text)
        if error:
            return error

        jd_texts = analysis_service.split_jd_list(request.form.get("jds_text", ""))
        if not jd_texts:
            return render_template(
                "error.html",
                message="No usable job descriptions were found. Separate each job "
                        "description with a line of --- and make sure each one has "
                        "at least 30 characters.",
            ), 400

        strictness = _form_strictness()
        target_title = (request.form.get("target_title") or "").strip()[:80] or None
        ranked = analysis_service.rank_job_descriptions(
            resume_text, jd_texts, strictness=strictness, target_title=target_title
        )
        ranked["score_bars"] = charts.score_bars(
            [{"label": entry["job_title"], "score": entry["ats_total"]}
             for entry in ranked["ranking"]]
        )
        return render_template(
            "ranking.html", filename=filename, strictness=strictness, **ranked
        )

    def _json_error(message, status=400, **extra):
        payload = {"error": message}
        payload.update(extra)
        return jsonify(payload), status

    @app.route("/api/analyze", methods=["POST"])
    def api_analyze():
        """JSON API: multipart resume upload -> full analysis as JSON."""
        try:
            resume_text, filename = _read_resume_text()
        except (ValidationError, DocumentParsingError) as exc:
            return _json_error(str(exc))

        detection = looks_like_resume(resume_text)
        if detection["verdict"] == "not_resume":
            return _json_error(rejection_message(detection), detection=detection)

        result = analysis_service.analyze_resume(
            resume_text, strictness=_form_strictness(), detection=detection
        )
        ats = result["ats_result"]
        return jsonify({
            "filename": filename,
            "category": result["category"],
            "top_predictions": result["top_predictions"],
            "resume_data": result["resume_data"],
            "detection": detection,
            "ats": {k: ats[k] for k in (
                "mode", "total", "grade", "grade_detail", "factors",
                "excluded_factors", "top_suggestions", "potential", "radar",
            )},
            "change_suggestions": ats_scorer.get_change_suggestions(ats),
        })

    @app.route("/api/match", methods=["POST"])
    def api_match():
        """JSON API: multipart resume + JD -> match analysis as JSON."""
        try:
            resume_text, filename = _read_resume_text()
            jd_text = _read_jd_text()
        except (ValidationError, DocumentParsingError) as exc:
            return _json_error(str(exc))

        detection = looks_like_resume(resume_text)
        if detection["verdict"] == "not_resume":
            return _json_error(rejection_message(detection), detection=detection)

        target_title = (request.form.get("target_title") or "").strip()[:80] or None
        result = analysis_service.analyze_and_match(
            resume_text, jd_text,
            strictness=_form_strictness(), target_title=target_title, detection=detection,
        )
        ats = result["ats_result"]
        return jsonify({
            "filename": filename,
            "category": result["category"],
            "top_predictions": result["top_predictions"],
            "resume_data": result["resume_data"],
            "job_description": result["job_description"],
            "match": result["match"],
            "detection": detection,
            "jd_quality": result.get("jd_quality"),
            "ats": {k: ats[k] for k in (
                "mode", "total", "grade", "grade_detail", "factors",
                "excluded_factors", "top_suggestions", "potential", "radar",
            )},
            "change_suggestions": ats_scorer.get_change_suggestions(ats),
            "recommendations": result["recommendations"]["offline"],
        })

    @app.route("/api/rank-jds", methods=["POST"])
    def api_rank_jds():
        """JSON API: rank one resume against multiple job descriptions.
        Accepts JSON {"resume_text": ..., "jds": [...]} or multipart with a
        resume file and a jds_text field (--- separators)."""
        if request.is_json:
            data = request.get_json(silent=True) or {}
            resume_text = (data.get("resume_text") or "").strip()
            jd_texts = [jd for jd in (data.get("jds") or [])
                        if isinstance(jd, str) and len(jd.strip()) >= analysis_service.MIN_JD_CHARS]
            filename = "resume.txt"
        else:
            try:
                resume_text, filename = _read_resume_text()
            except (ValidationError, DocumentParsingError) as exc:
                return _json_error(str(exc))
            jd_texts = analysis_service.split_jd_list(request.form.get("jds_text", ""))

        if not resume_text:
            return _json_error("No resume text was provided.")
        if not jd_texts:
            return _json_error(
                "No usable job descriptions were provided (each needs at least 30 characters; "
                "max 10)."
            )

        detection = looks_like_resume(resume_text)
        if detection["verdict"] == "not_resume":
            return _json_error(rejection_message(detection), detection=detection)

        strictness = _form_strictness()
        target_title = (
            (request.form.get("target_title") or
             (request.get_json(silent=True) or {}).get("target_title") or "")
            .strip()[:80] or None
        )
        ranked = analysis_service.rank_job_descriptions(
            resume_text, jd_texts, strictness=strictness, target_title=target_title
        )
        ranked["filename"] = filename
        return jsonify(ranked)

    return app


app = create_app()

def run_server() -> None:
    """Serve with waitress (production-grade, multi-threaded) whenever it is
    installed; the Flask dev server remains the fallback and the debugger
    path. Host/port come from SERVER_HOST/SERVER_PORT in .env."""
    if config.DEBUG:
        app.run(debug=True, host=config.SERVER_HOST, port=config.SERVER_PORT)
        return
    try:
        from waitress import serve
    except ImportError:
        logger.warning("waitress not installed - falling back to the Flask dev server. "
                       "Install it with: pip install waitress")
        app.run(host=config.SERVER_HOST, port=config.SERVER_PORT)
        return
    logger.info("Serving on http://%s:%s with waitress (%s worker threads)",
                config.SERVER_HOST, config.SERVER_PORT, 8)
    serve(app, host=config.SERVER_HOST, port=config.SERVER_PORT, threads=8)


if __name__ == "__main__":
    run_server()
