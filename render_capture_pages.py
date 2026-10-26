"""Render real app pages via the Flask test client and serve them (plus /static)
for screenshot capture. One-off helper for the presentation build."""
import io
import threading
import time
from pathlib import Path

from app import app
from database import database
from services import shortlist_service

ASSETS = Path(__file__).parent / "ppt_assets"
(ASSETS / "site").mkdir(parents=True, exist_ok=True)

RESUME = Path(r"C:\sai\resumes\Sai_Teja_Resume(updated) .docx").read_bytes()
JD = ("Job Title: Software Developer\n\nREQUIREMENTS\n"
      "3+ years of experience in software development.\n"
      "Bachelor's degree in Computer Science.\n"
      "Strong proficiency in Python and JavaScript.\n"
      "Experience with React and Node.js.\n\n"
      "RESPONSIBILITIES\nDesign and implement scalable backend services.\n")

client = app.test_client()

# 1. analyze results (the 90.3 run)
resp = client.post("/analyze", data={"resume_file": (io.BytesIO(RESUME), "Sai_Teja_Resume.docx")},
                   content_type="multipart/form-data")
(ASSETS / "site" / "results_analyze.html").write_bytes(resp.data)
print("results_analyze:", resp.status_code)

# 2. match results
resp = client.post("/match-job", data={"resume_file": (io.BytesIO(RESUME), "Sai_Teja_Resume.docx"),
                                       "jd_text": JD},
                   content_type="multipart/form-data")
(ASSETS / "site" / "results_match.html").write_bytes(resp.data)
print("results_match:", resp.status_code)

# 3. history (for a static copy too; live page also captured)
resp = client.get("/history")
(ASSETS / "site" / "history.html").write_bytes(resp.data)
print("history:", resp.status_code)

# 4. run a real 4-resume shortlist job and render its results page
R = Path(r"C:\sai\resumes")
jd_short = ("Job Title: Software Developer\n\nREQUIREMENTS\n"
            "3+ years of experience in software development.\n"
            "Bachelor's degree in Computer Science.\n"
            "Strong proficiency in Python and JavaScript.\n\n"
            "RESPONSIBILITIES\nDesign and implement scalable backend services.\n")
files = [("Divya_Resume.pdf", (R / "Divya_Resume.pdf").read_bytes()),
         ("Sai_Teja_Resume.docx", RESUME),
         ("resume_hari.pdf", (R / "resume_hari (3).pdf").read_bytes()),
         ("KKV_letter.docx", (R / "KKV -CV (3).docx").read_bytes())]
job_id = shortlist_service.create_job(files, jd_short)
deadline = time.time() + 60
while time.time() < deadline:
    job = shortlist_service.get_job(job_id)
    if job and job["state"] == "done":
        break
    time.sleep(0.2)
resp = client.get(f"/shortlist/{job_id}")
(ASSETS / "site" / "shortlist_results.html").write_bytes(resp.data)
print("shortlist_results:", resp.status_code)


import shutil
import subprocess

# Serve rendered pages with the app's static assets copied alongside, so the
# absolute /static/... references resolve. Plain http.server is enough.
static_dest = ASSETS / "site" / "static"
if static_dest.exists():
    shutil.rmtree(static_dest)
shutil.copytree(Path(__file__).parent / "static", static_dest)
print("static copied")
