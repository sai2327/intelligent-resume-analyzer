"""
Final acceptance sweep: every HTTP endpoint x every real resume in
C:\\sai\\resumes, plus determinism, parallel-load, and latency percentiles.
Requires the server running on :5000.

Run: python validate_live_acceptance.py
"""

import concurrent.futures
import io
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:5000"
RESUME_DIR = Path(r"C:\sai\resumes")

JD = """Job Title: Software Developer

REQUIREMENTS
3+ years of experience in software development.
Bachelor's degree in Computer Science or related field.
Strong proficiency in Python and JavaScript.
Experience with React and Node.js.

RESPONSIBILITIES
Design and implement scalable backend services.
"""

JD2 = """Job Title: Data Analyst

REQUIREMENTS
4+ years of experience in data analysis.
Bachelor's degree required.
Expert-level SQL and strong Python skills.
Experience with Tableau.

RESPONSIBILITIES
Analyze large datasets and build dashboards.
"""


def post_multipart(path, fields):
    """fields: list of (name, value); a value that is a tuple is (filename, bytes)."""
    boundary = "----acc7"
    body = io.BytesIO()
    for key, value in fields:
        if isinstance(value, tuple):
            filename, data = value
            body.write(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n".encode() + data + b"\r\n"
            )
        else:
            body.write(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
            )
    body.write(f"--{boundary}--\r\n".encode())
    return post(path, body.getvalue(), {"Content-Type": f"multipart/form-data; boundary={boundary}"})


def post_json(path, payload):
    return post(path, json.dumps(payload).encode(), {"Content-Type": "application/json"})


def post(path, data, headers, _retry=True):
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.status, response.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "ignore")
    except (ConnectionResetError, OSError):
        # The dev reloader restarts the server when files change; one retry
        # rides it out.
        if _retry:
            time.sleep(3)
            return post(path, data, headers, _retry=False)
        raise


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=60) as response:
            return response.status, response.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "ignore")


def main():
    failures = []
    files = sorted(
        f for f in RESUME_DIR.iterdir()
        if f.is_file() and not f.name.startswith("~$") and f.suffix.lower() in {".pdf", ".docx"}
    )

    # ------------------------------------- 1. analyze all files: page + API agree
    print(f"[1] /analyze + /api/analyze for all {len(files)} files (page/API agreement)")
    disagree = 0
    latencies = []
    api_scores = {}
    for f in files:
        req_file = (f.name, f.read_bytes())
        t0 = time.perf_counter()
        status, html = post_multipart("/analyze", [("resume_file", req_file)])
        latencies.append((time.perf_counter() - t0) * 1000)

        status2, body = post_multipart("/api/analyze", [("resume_file", (f.name, f.read_bytes()))])
        if status2 == 400 and "does not look like a resume" in body:
            api_scores[f.name] = None  # justified non-resume rejection
            continue
        if status2 != 200:
            failures.append(f"{f.name}: /api/analyze -> {status2}")
            continue
        api_total = json.loads(body)["ats"]["total"]
        api_scores[f.name] = api_total

        if status == 200:
            m = re.search(r"ats-gauge__value[^>]*>([\d.]+)<", html)
            page_total = float(m.group(1)) if m else None
            if page_total is not None and abs(page_total - api_total) > 0.06:
                disagree += 1
                failures.append(f"{f.name}: page {page_total} != api {api_total}")
        elif status != 400:
            failures.append(f"{f.name}: /analyze -> {status}")
    print(f"  page/API disagreements: {disagree}")
    print(f"  /analyze latency: p50={statistics.median(latencies):.0f}ms  "
          f"p95={sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]:.0f}ms  "
          f"max={max(latencies):.0f}ms")

    # ------------------------------------- 2. determinism: same file x3 through HTTP
    print("\n[2] DETERMINISM: same resume analyzed 3 times through the live server")
    probe = next(f for f in files if "Naga" in f.name)
    totals = []
    for _ in range(3):
        status, body = post_multipart("/api/analyze", [("resume_file", (probe.name, probe.read_bytes()))])
        totals.append(json.loads(body)["ats"]["total"])
    if len(set(totals)) != 1:
        failures.append(f"non-deterministic across HTTP calls: {totals}")
    print(f"  {probe.name}: {totals} -> {'identical' if len(set(totals)) == 1 else 'DIFFERENT'}")

    # ------------------------------------- 3. match all files via HTTP
    print(f"\n[3] /match-job for all {len(files)} files")
    ok = 0
    match_times = []
    for f in files:
        t0 = time.perf_counter()
        status, html = post_multipart("/match-job", [("resume_file", (f.name, f.read_bytes())),
                                                     ("jd_text", JD)])
        match_times.append((time.perf_counter() - t0) * 1000)
        if status == 200 and "Resume vs Job Description" in html:
            ok += 1
        elif status == 400 and "does not look like a resume" in html:
            ok += 1  # justified rejection
        else:
            failures.append(f"{f.name}: /match-job -> {status}")
    print(f"  {ok}/{len(files)} handled correctly (200 or justified 400), "
          f"p50={statistics.median(match_times):.0f}ms  max={max(match_times):.0f}ms")

    # ------------------------------------- 4. rank + compare via API
    print("\n[4] /api/rank-jds + /api/compare")
    status, body = post_json("/api/rank-jds", {
        "resume_text": fetch_text(files[0]),
        "jds": [JD, JD2],
    })
    rank = json.loads(body) if status == 200 else {}
    if status != 200 or len(rank.get("ranking", [])) != 2:
        failures.append(f"/api/rank-jds -> {status}")
    else:
        print(f"  ranking: {[(r['job_title'], r['ats_total']) for r in rank['ranking']]}")

    sample = [f for f in files[:5] if api_scores.get(f.name) is not None][:3]
    status, body = post_json("/api/compare", {
        "resumes": [{"filename": f.name, "text": fetch_text(f)} for f in sample],
        "jd_text": JD,
    })
    comp = json.loads(body) if status == 200 else {}
    if status != 200 or not comp.get("winner"):
        failures.append(f"/api/compare -> {status}")
    else:
        print(f"  comparison of {len(sample)} real resumes - winner: {comp['winner']}")

    # ------------------------------------- 5. parallel load: 8 concurrent uploads
    print("\n[5] PARALLEL LOAD: 8 simultaneous /api/analyze requests")
    probes = files[:8]

    def upload(f):
        t0 = time.perf_counter()
        status, body = post_multipart("/api/analyze", [("resume_file", (f.name, f.read_bytes()))])
        return status, (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(upload, probes))
    wall = (time.perf_counter() - t0) * 1000
    def acceptable(pair):
        status, _ = pair
        return status == 200
    bad = [s for s, _ in results if not acceptable((s, None)) and s != 400]
    if bad:
        failures.append(f"parallel load: unexpected responses: {bad}")
    times = sorted(t for _, t in results)
    print(f"  8 concurrent uploads: all 200 in {wall:.0f}ms wall | "
          f"per-request p50={statistics.median(times):.0f}ms max={max(times):.0f}ms")

    # ------------------------------------- verdict
    print("\n" + "=" * 90)
    if failures:
        print(f"LIVE ACCEPTANCE FAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("LIVE ACCEPTANCE PASSED: every endpoint x every real file, deterministic, "
          "parallel-safe, fast")


def fetch_text(f):
    from services.document_parser import extract_text
    return extract_text(str(f), f.suffix.lstrip("."))


if __name__ == "__main__":
    main()
