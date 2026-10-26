"""
Deep real-world battery: the COMPLETE feature set against every resume in
C:\\sai\\resumes.

  1. Cross-matrix: every resume x every JD (bounds + timing on all 54 matches)
  2. Causal accuracy: injecting the missing JD skills into real resumes must
     RAISE their ATS score (the tool's advice actually works on real data)
  3. Typo tolerance: misspelling a real skill must lower the strict-mode
     keyword score vs standard (strict = literal parser)
  4. DOCX/PDF consistency: same-content pairs must score within tolerance
  5. Progress tracking, CSV/JSON/TXT exports (against an isolated temp DB)
  6. Full HTTP + API battery with real files (strictness, target title)
  7. Warm-speed profile across all files

Run: python validate_real_files_full.py
"""

import io
import re
import sys
import time
from pathlib import Path

from app import app
from config import config
from services.analysis_service import analyze_and_match, analyze_resume
from services.document_parser import extract_text
from services.information_extractor import extract_all
from services.job_description_parser import parse_job_description
from services.ats_scorer import (
    compute_keyword_match,
    score_resume_standalone,
    score_resume_vs_jd,
)
from services.resume_detector import looks_like_resume

RESUME_DIR = Path(r"C:\sai\resumes")

JD_SOFTWARE = """Job Title: Software Developer

REQUIREMENTS
3+ years of experience in software development.
Bachelor's degree in Computer Science or related field.
Strong proficiency in Python and JavaScript.
Experience with React and Node.js.
Experience with MySQL and REST API design.
Familiarity with Docker and CI/CD pipelines.

PREFERRED SKILLS
Experience with AWS and Kubernetes.
Knowledge of TypeScript.

RESPONSIBILITIES
Design and implement scalable backend services.
Collaborate with frontend developers to integrate APIs.
"""

JD_DATA = """Job Title: Data Analyst

REQUIREMENTS
4+ years of experience in data analysis.
Bachelor's degree required.
Expert-level SQL and strong Python skills.
Experience with Tableau or Power BI.
Strong statistics background.

RESPONSIBILITIES
Analyze large datasets and build dashboards for stakeholders.
"""

JD_DEVOPS = """Job Title: DevOps Engineer

REQUIREMENTS
4+ years of DevOps or infrastructure experience.
Bachelor's degree required.
Strong Terraform and Kubernetes skills.
Experience with AWS and CI/CD pipelines.

RESPONSIBILITIES
Automate infrastructure and manage cloud deployments.
"""

JDS = {"Software Developer": JD_SOFTWARE, "Data Analyst": JD_DATA, "DevOps Engineer": JD_DEVOPS}


def main():
    client = app.test_client()
    failures = []

    files = sorted(
        f for f in RESUME_DIR.iterdir()
        if f.is_file() and not f.name.startswith("~$") and f.suffix.lower() in {".pdf", ".docx"}
    )

    # ---------------------------------------------------------------- load all
    parsed = {}
    rejected = {}
    t_load = time.perf_counter()
    for f in files:
        try:
            text = extract_text(str(f), f.suffix.lstrip("."))
        except Exception as exc:
            failures.append(f"{f.name}: extraction error {exc}")
            continue
        detection = looks_like_resume(text)
        if detection["verdict"] == "not_resume":
            rejected[f.name] = detection
            continue
        parsed[f.name] = {"text": text, "detection": detection, "data": extract_all(text)}
    print(f"Loaded {len(parsed)} resumes, rejected {len(rejected)}: "
          f"{[(n, d['document_type']) for n, d in rejected.items()]}")
    print(f"load+parse+extract all files: {(time.perf_counter() - t_load) * 1000:.0f} ms total")

    # ------------------------------------------------- 1. cross-matrix 18x3
    print("\n[1] CROSS-MATRIX: every resume x every JD")
    print(f"{'resume':<40}" + "".join(f"{j[:14]:>16}" for j in JDS))
    matrix_ms = []
    for name, item in parsed.items():
        row = {}
        row_ms = 0.0
        for jd_name, jd in JDS.items():
            t0 = time.perf_counter()
            ats = score_resume_vs_jd(item["text"], jd, item["data"], parse_job_description(jd))
            row_ms += (time.perf_counter() - t0) * 1000
            if ats["total"] is None or not 0 <= ats["total"] <= 100:
                failures.append(f"{name} x {jd_name}: ATS invalid {ats['total']}")
            row[jd_name] = ats["total"]
        matrix_ms.append(row_ms)
        item["row"] = row
        print(f"{name:<40}" + "".join(f"{row[j]:>16.1f}" for j in JDS))
    print(f"timing: {min(matrix_ms):.0f}-{max(matrix_ms):.0f} ms per resume for all 3 JD matches")

    # ------------------------------------------- 2. causal accuracy on real resumes
    print("\n[2] CAUSAL: injecting the JD's missing required skills must RAISE the ATS score")
    injections_tested = 0
    for name in list(parsed.keys())[:5]:
        item = parsed[name]
        jd_data = parse_job_description(JD_SOFTWARE)
        base = score_resume_vs_jd(item["text"], JD_SOFTWARE, item["data"], jd_data)
        missing = [s for s in jd_data["required_skills"] if s not in item["data"]["skills"]]
        if not missing:
            continue
        boosted_text = item["text"] + "\nSKILLS\n" + ", ".join(missing) + "\n"
        boosted_data = extract_all(boosted_text)
        boosted = score_resume_vs_jd(boosted_text, JD_SOFTWARE, boosted_data, jd_data)
        injections_tested += 1
        gain = boosted["total"] - base["total"]
        if gain <= 0.5:
            failures.append(f"{name}: skill injection did not raise ATS ({base['total']} -> {boosted['total']})")
        print(f"  {name:<40} {base['total']:>6.1f} -> {boosted['total']:>6.1f}  (+{gain:.1f})")
    if injections_tested == 0:
        failures.append("no causal injection was testable")

    # ------------------------------------------- 3. typo tolerance on real resumes
    print("\n[3] TYPO TOLERANCE: misspelling a real skill must cost the strict parser")
    typo_tested = 0
    for name in list(parsed.keys())[:6]:
        item = parsed[name]
        skills = item["data"]["skills"]
        target = next((s for s in skills if len(s) >= 6 and s.isalpha()), None)
        if not target:
            continue
        jd_text = f"Job Title: Role\n\nREQUIREMENTS\nExperience with {target}.\n"
        jd_data = parse_job_description(jd_text)
        # misspell: swap two inner characters
        mid = len(target) // 2
        typo = target[:mid] + target[mid + 1] + target[mid] + target[mid + 2:]
        typo_text = re.sub(rf"\b{re.escape(target)}\b", typo, item["text"], flags=re.IGNORECASE)
        typo_data = extract_all(typo_text)
        standard = compute_keyword_match(typo_text, jd_text, jd_data, typo_data)["score"]
        strict = compute_keyword_match(
            typo_text, jd_text, jd_data, typo_data,
            profile={"typo_matching": False, "partial_credit_multiplier": 1.0},
        )["score"]
        if standard is None or strict is None:
            continue
        typo_tested += 1
        if standard <= strict:
            failures.append(f"{name}: typo tolerance did not help ({standard} vs strict {strict})")
        print(f"  {name:<40} '{target}'->'{typo}': standard={standard:.0f} > strict={strict:.0f}")
    if typo_tested < 3:
        print(f"  (only {typo_tested} files had a testable alpha skill)")

    # ------------------------------------------- 4. DOCX/PDF consistency pairs
    print("\n[4] DOCX/PDF CONSISTENCY: same resume in both formats")
    pairs = [
        ("Sai Teja_Resume.docx", "Sai Teja_Resume.pdf"),
        ("Sai Teja Kondapalli.docx", "Sai Teja Kondapalli (1).pdf"),
        ("Sai Teja Kondapalli (1).docx", "sai_teja_resume (1) (1).pdf"),
    ]
    for docx_name, pdf_name in pairs:
        if docx_name not in parsed or pdf_name not in parsed:
            continue
        d = score_resume_standalone(parsed[docx_name]["text"], parsed[docx_name]["data"])["total"]
        p = score_resume_standalone(parsed[pdf_name]["text"], parsed[pdf_name]["data"])["total"]
        diff = abs(d - p)
        status = "OK" if diff <= 15 else "FAIL"
        if diff > 15:
            failures.append(f"{docx_name} vs {pdf_name}: scores differ by {diff:.1f}")
        print(f"  {docx_name:<38} {d:>6.1f}  |  {pdf_name:<38} {p:>6.1f}  diff={diff:.1f} {status}")

    # ------------------------------------------- 5. progress + exports (isolated DB)
    print("\n[5] PROGRESS TRACKING + EXPORTS (isolated temp DB)")
    import tempfile
    original_db_path = config.DATABASE_PATH
    config.DATABASE_PATH = str(Path(tempfile.mkdtemp()) / "real_files.db")
    from database import database as db_module
    db_module.init_db()
    names = list(parsed.keys())[:2]
    for name in names:  # analyze twice: first the raw, then a slightly edited copy
        for text in (parsed[name]["text"], parsed[name]["text"] + "\nPROJECTS\nBuilt 3 dashboards.\n"):
            result = analyze_resume(text)
            db_module.save_analysis(name, result["category"], None, False,
                                   ats_result=result["ats_result"])
    progress = db_module.get_file_progress()
    if len(progress) != 2:
        failures.append(f"expected 2 progress rows, got {len(progress)}")
    for p in progress:
        print(f"  {p['filename']:<40} runs={p['runs']} first={p['first_score']:.1f} "
              f"last={p['last_score']:.1f} ({p['direction']})")
    client = app.test_client()
    r = client.get("/history")
    if not (r.status_code == 200 and "Resume progress" in r.get_data(as_text=True)):
        failures.append("history progress section missing")
    r = client.get("/history/export.csv")
    if not (r.status_code == 200 and "ats_score" in r.get_data(as_text=True)):
        failures.append("CSV export failed")
    row_id = db_module.list_recent_analyses(limit=1)[0]["id"]
    r = client.get(f"/results/{row_id}")
    if not (r.status_code == 200 and isinstance(r.get_json().get("ats_breakdown"), dict)):
        failures.append("JSON report failed")
    r = client.get(f"/report/{row_id}.txt")
    if not (r.status_code == 200 and "FACTOR BREAKDOWN" in r.get_data(as_text=True)):
        failures.append("TXT report failed")
    print("  history page + CSV export + JSON report + TXT report: OK")

    # ------------------------------------------- 6. HTTP + API battery
    print("\n[6] HTTP + API battery with real files")
    name0 = list(parsed.keys())[0]
    f0 = next(f for f in files if f.name == name0)
    checks = {}
    checks["analyze strict"] = client.post(
        "/analyze", data={"resume_file": (io.BytesIO(f0.read_bytes()), f0.name), "strictness": "strict"},
        content_type="multipart/form-data").status_code == 200
    r = client.post("/api/analyze", data={"resume_file": (io.BytesIO(f0.read_bytes()), f0.name)},
                    content_type="multipart/form-data")
    api = r.get_json()
    checks["api analyze"] = r.status_code == 200 and "change_suggestions" in api
    r = client.post("/api/match", data={"resume_file": (io.BytesIO(f0.read_bytes()), f0.name),
                                        "jd_text": JD_SOFTWARE, "target_title": "Software Developer"},
                    content_type="multipart/form-data")
    api = r.get_json()
    checks["api match + target title"] = r.status_code == 200 and \
        api["job_description"]["job_title"] == "Software Developer"
    r = client.post("/api/rank-jds",
                    json={"resume_text": parsed[name0]["text"], "jds": list(JDS.values())})
    rank = r.get_json()
    checks["api rank-jds"] = r.status_code == 200 and len(rank["ranking"]) == 3
    r = client.post("/api/compare", json={
        "resumes": [{"filename": n, "text": parsed[n]["text"]} for n in list(parsed.keys())[:4]],
        "jd_text": JD_SOFTWARE})
    checks["api compare"] = r.status_code == 200 and r.get_json().get("winner")
    for label, ok in checks.items():
        if not ok:
            failures.append(f"HTTP/API check failed: {label}")
        print(f"  {label:<28} {'PASS' if ok else 'FAIL'}")

    config.DATABASE_PATH = original_db_path  # stop using the temp DB

    # ------------------------------------------- 7. warm speed across all files
    print("\n[7] WARM SPEED: full analyze+match for every resume")
    times = []
    for name, item in parsed.items():
        t0 = time.perf_counter()
        analyze_and_match(item["text"], JD_SOFTWARE)
        times.append(((time.perf_counter() - t0) * 1000, name))
    times.sort()
    slowest = times[-1]
    avg = sum(t for t, _ in times) / len(times)
    for ms, name in times[-3:]:
        print(f"  slowest: {name:<42} {ms:6.1f} ms")
    print(f"  average across {len(times)} real resumes: {avg:.1f} ms")
    if avg > 120:
        failures.append(f"average warm latency too high: {avg:.1f} ms")
    if slowest[0] > 300:
        failures.append(f"slowest real resume too slow: {slowest}")

    # ---------------------------------------------------------------- verdict
    print("\n" + "=" * 100)
    if failures:
        print(f"DEEP REAL-FILE BATTERY FAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print(f"DEEP REAL-FILE BATTERY PASSED: {len(parsed)} resumes x {len(JDS)} JDs, "
          f"{injections_tested} causal injections, {typo_tested} typo cases, "
          f"all exports, APIs, and speed targets")


if __name__ == "__main__":
    main()
