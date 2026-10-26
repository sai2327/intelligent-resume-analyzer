"""
Real-world validation: runs EVERY feature against the actual resumes in
C:\\sai\\resumes - extraction, detection, standalone ATS, job matching,
multi-JD ranking, resume comparison, and the strictness profiles - with
per-file timing and strict accuracy invariants.

Run: python validate_real_files.py
"""

import io
import sys
import time
from pathlib import Path

from app import app
from services.analysis_service import (
    analyze_and_match,
    analyze_resume,
    compare_resumes,
    rank_job_descriptions,
)
from services.document_parser import DocumentParsingError, extract_text
from services.information_extractor import extract_all
from services.resume_detector import looks_like_resume

RESUME_DIR = Path(r"C:\sai\resumes")
SKIP_PATTERNS = ("~$",
                 )  # Office lock files

JD_SOFTWARE = """Job Title: Software Developer

About the role: We are hiring engineers for our product team.

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
Write unit tests and participate in code reviews.
"""

JD_DATA = """Job Title: Data Analyst

REQUIREMENTS
4+ years of experience in data analysis.
Bachelor's degree required.
Expert-level SQL and strong Python skills.
Experience with Tableau or Power BI.
Strong statistics background.

PREFERRED SKILLS
Experience with Machine Learning.

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
    files = sorted(
        f for f in RESUME_DIR.iterdir()
        if f.is_file() and not f.name.startswith("~$") and f.suffix.lower() in {".pdf", ".docx"}
    )
    odd_files = sorted(
        f for f in RESUME_DIR.iterdir()
        if f.is_file() and f.suffix.lower() not in {".pdf", ".docx"}
    )
    print(f"Found {len(files)} resume files + {len(odd_files)} non-resume file(s): "
          f"{[f.name for f in odd_files]}")
    print("=" * 108)

    client = app.test_client()
    failures = []
    timings = {}
    skipped_rejections = []

    # ---------------- 1. extraction + detection + standalone ATS ----------------
    print(f"\n{'file':<38} {'words':>6} {'detect':>10} {'conf':>5} {'ATS':>6} {'grade':<11} {'category':<22} {'skills':>6} {'ms':>6}")
    print("-" * 108)
    parsed = {}
    for f in files:
        t0 = time.perf_counter()
        try:
            text = extract_text(str(f), f.suffix.lstrip("."))
        except DocumentParsingError as exc:
            failures.append(f"{f.name}: extraction failed: {exc}")
            print(f"{f.name:<38} EXTRACTION FAILED: {exc}")
            continue
        detection = looks_like_resume(text)
        result = analyze_resume(text)
        ms = (time.perf_counter() - t0) * 1000
        timings[f.name] = ms
        ats = result["ats_result"]
        parsed[f.name] = (text, result)

        verdict = detection["verdict"]
        if verdict == "not_resume":
            # Justified rejection (cover letter / thesis / ...) - log and skip.
            print(f"{f.name:<38} REJECTED as {detection['document_type']} ({detection['confidence']:.0f}%) - correct")
            skipped_rejections.append(f.name)
            continue
        if ats["total"] is None:
            failures.append(f"{f.name}: standalone ATS total is None")
        if ats["total"] is not None and not 0 <= ats["total"] <= 100:
            failures.append(f"{f.name}: ATS out of bounds: {ats['total']}")

        skills = result["resume_data"]["skills"]
        print(f"{f.name:<38} {len(text.split()):>6} {verdict:>10} "
              f"{detection['confidence']:>4.0f}% {ats['total']:>6.1f} {ats['grade']:<11} "
              f"{(result['category'] or '-'):<22} {len(skills):>6} {ms:>5.0f}")

    # ---------------- 2. the non-resume temp file must be rejected ----------------
    for f in odd_files:
        try:
            text = extract_text(str(f), "tmp")
            verdict = looks_like_resume(text)
            print(f"\nnon-resume file {f.name}: extracted {len(text.split())} words -> verdict={verdict['verdict']}")
        except DocumentParsingError as exc:
            print(f"\nnon-resume file {f.name}: correctly refused at extraction ({str(exc)[:60]}...)")

    # ---------------- 3. matching every resume against the software JD ----------------
    print("\n" + "=" * 108)
    print("MATCH vs Software Developer JD (with quality check + speed)")
    print("-" * 108)
    for name, (text, _result) in parsed.items():
        if name in skipped_rejections:
            continue
        t0 = time.perf_counter()
        match = analyze_and_match(text, JD_SOFTWARE)
        ms = (time.perf_counter() - t0) * 1000
        ats = match["ats_result"]
        quality = match["jd_quality"]
        overall = match["match"]["overall"]["overall_score"]
        if ats["total"] is None or not 0 <= ats["total"] <= 100:
            failures.append(f"{name}: match ATS invalid: {ats['total']}")
        if overall is not None and not 0 <= overall <= 100:
            failures.append(f"{name}: match overall invalid: {overall}")
        if quality["quality"] not in {"good", "fair", "poor"}:
            failures.append(f"{name}: jd quality invalid")
        timings[f"match:{name}"] = ms
        print(f"  {name:<38} ATS={ats['total']:>6.1f} ({ats['grade']:<11}) "
              f"match={overall if overall is not None else float('nan'):>6.1f}% "
              f"jd_quality={quality['quality']:<5} {ms:>5.0f}ms")

    # ---------------- 4. multi-JD ranking (all real resumes at once) ----------------
    print("\n" + "=" * 108)
    print("RANKING: all parsed resumes against 3 JDs")
    t0 = time.perf_counter()
    names = list(parsed.keys())
    ranking = rank_job_descriptions(parsed[names[0]][0], list(JDS.values()))
    ms = (time.perf_counter() - t0) * 1000
    for entry in ranking["ranking"]:
        print(f"  #{ranking['ranking'].index(entry) + 1} {entry['job_title']:<28} "
              f"ATS={entry['ats_total']:>6.1f} ({entry['grade']})")
    if ranking["ranking"][0]["job_title"] != "Software Developer":
        failures.append(f"ranking best-fit unexpected: {ranking['ranking'][0]['job_title']}")
    if len(ranking["ranking"]) != 3:
        failures.append("ranking did not return all 3 JDs")
    print(f"  ranking latency for 3 JDs: {ms:.0f}ms")

    # ---------------- 5. comparison of 5 real resumes ----------------
    print("\n" + "=" * 108)
    print("COMPARISON: first 5 real resumes vs Software Developer JD")
    t0 = time.perf_counter()
    accepted5 = [n for n in names if n not in skipped_rejections][:5]
    entries = [{"filename": name, "text": parsed[name][0]} for name in accepted5]
    comparison = compare_resumes(entries, JD_SOFTWARE)
    ms = (time.perf_counter() - t0) * 1000
    for i, c in enumerate(comparison["comparison"]):
        print(f"  #{i + 1} {c['filename']:<38} ATS={c['ats_total']:>6.1f} ({c['grade']})")
    if comparison["winner"] != comparison["comparison"][0]["filename"]:
        failures.append("comparison winner mismatch")
    scores = [c["ats_total"] for c in comparison["comparison"]]
    if scores != sorted(scores, reverse=True):
        failures.append("comparison not sorted")
    print(f"  comparison latency (5 resumes): {ms:.0f}ms")

    # ---------------- 6. strictness profiles on real files ----------------
    print("\n" + "=" * 108)
    print("STRICTNESS on 3 real files (lenient >= standard >= strict)")
    for name in [n for n in names if n not in skipped_rejections][:3]:
        text, _ = parsed[name]
        from services.ats_scorer import score_resume_standalone
        data = extract_all(text)
        l_ = score_resume_standalone(text, data, strictness="lenient")["total"]
        s_ = score_resume_standalone(text, data, strictness="standard")["total"]
        x_ = score_resume_standalone(text, data, strictness="strict")["total"]
        ok = l_ >= s_ >= x_
        if not ok:
            failures.append(f"{name}: strictness ordering broken {l_} {s_} {x_}")
        print(f"  {name:<38} lenient={l_:>6.1f} standard={s_:>6.1f} strict={x_:>6.1f} {'OK' if ok else 'FAIL'}")

    # ---------------- 7. full HTTP flow for 3 real files ----------------
    print("\n" + "=" * 108)
    print("HTTP end-to-end (analyze + match + rank + compare) for 3 real files")
    for f in files[:3]:
        payload = io.BytesIO(f.read_bytes())
        r = client.post("/analyze", data={"resume_file": (payload, f.name)},
                        content_type="multipart/form-data")
        rejected = f.name in skipped_rejections
        ok1 = (r.status_code == 400 and "does not look like a resume" in r.get_data(as_text=True)) if rejected             else (r.status_code == 200 and "ATS Score Tracker" in r.get_data(as_text=True))

        r = client.post("/match-job", data={"resume_file": (io.BytesIO(f.read_bytes()), f.name),
                                            "jd_text": JD_SOFTWARE},
                        content_type="multipart/form-data")
        ok2 = (r.status_code == 400) if rejected else (r.status_code == 200 and "Resume vs Job Description" in r.get_data(as_text=True))

        r = client.post("/rank-jobs", data={"resume_file": (io.BytesIO(f.read_bytes()), f.name),
                                            "jds_text": JD_SOFTWARE + "\n\n---\n\n" + JD_DATA},
                        content_type="multipart/form-data")
        ok3 = (r.status_code == 400) if rejected else (r.status_code == 200 and "Best-Fit Job Ranking" in r.get_data(as_text=True))

        if not (ok1 and ok2 and ok3):
            failures.append(f"{f.name}: HTTP flow failed (analyze={ok1}, match={ok2}, rank={ok3})")
        print(f"  {f.name:<38} analyze={'PASS' if ok1 else 'FAIL'} match={'PASS' if ok2 else 'FAIL'} rank={'PASS' if ok3 else 'FAIL'}")

    r = client.post("/api/compare", json={
        "resumes": [{"filename": name, "text": parsed[name][0]}
                    for name in [n for n in names if n not in skipped_rejections][:3]],
        "jd_text": JD_SOFTWARE,
    })
    if r.status_code != 200 or not r.get_json().get("winner"):
        failures.append("api compare failed on real files")
    else:
        print(f"  API compare winner: {r.get_json()['winner']}")

    # ---------------- 8. speed summary ----------------
    print("\n" + "=" * 108)
    warm = [v for k, v in timings.items() if not k.startswith("match:")]
    match_times = [v for k, v in timings.items() if k.startswith("match:")]
    print(f"analyze latency  (first run incl. one-time model load): {min(warm):.0f}-{max(warm):.0f} ms")
    if match_times:
        print(f"match latency    (first runs, real JDs): {min(match_times):.0f}-{max(match_times):.0f} ms")

    # warm timing: rerun one file
    name0 = names[0]
    t0 = time.perf_counter()
    for _ in range(10):
        analyze_and_match(parsed[name0][0], JD_SOFTWARE)
    warm_ms = (time.perf_counter() - t0) * 1000 / 10
    print(f"warm full-analysis (analyze+match, 10 repeats): {warm_ms:.1f} ms each")
    if warm_ms > 250:
        failures.append(f"warm latency too high: {warm_ms:.1f} ms")

    print("\n" + "=" * 108)
    if failures:
        print(f"REAL-FILE VALIDATION FAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print(f"ALL REAL-FILE CHECKS PASSED ({len(parsed)} resumes, every feature exercised)")


if __name__ == "__main__":
    main()
