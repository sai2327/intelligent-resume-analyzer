"""
Comprehensive ATS validation harness.

Runs a matrix of 8 domain-matched resumes against 8 job descriptions and
verifies the score behaves like a correct ATS ranker:

  1. DIAGONAL DOMINANCE: every tailored resume scores highest against its own
     domain's JD (8x8 cross-matrix).
  2. ORDERING: matched > partial > weak per domain.
  3. CAUSALITY: following the tool's own suggestions (adding the missing
     skills/keywords it flags) must RAISE the score; removing contact info or
     quantified metrics must LOWER it.
  4. ROBUSTNESS: odd JD formats (CRLF, unicode bullets, no sections, very
     long) never crash and stay in [0, 100].
  5. SPEED: warm full-analysis latency.

Run: python validate_ats_matrix.py
"""

import time

from services.analysis_service import analyze_and_match
from services.ats_scorer import score_resume_standalone
from services.information_extractor import extract_all
from services.job_description_parser import parse_job_description


def make_resume(title, skills, bullets, years, contact=True, dates=True, education="B.Tech in Computer Science, Tech University, 2020"):
    parts = []
    if contact:
        parts += ["Alex Kumar", "Email: alex.kumar@example.com | Phone: +1-555-010-2030"]
    parts += ["SUMMARY", f"{title} with {years} years of professional experience."]
    parts += ["SKILLS", ", ".join(skills)]
    parts += ["EXPERIENCE", f"{title} at TechCorp"]
    if dates:
        parts += ["Jan 2021 - Present"]
    parts += [f"- {b}" for b in bullets]
    parts += ["EDUCATION", education]
    return "\n".join(p for p in parts if p)


JDS = {
    "data_analyst": """Job Title: Senior Data Analyst

REQUIREMENTS
4+ years of experience in data analysis.
Bachelor's degree required.
Expert SQL and strong Python skills.
Experience with Tableau.
Experience with Airflow.

PREFERRED SKILLS
Experience with Spark.
Experience with Snowflake.

RESPONSIBILITIES
Analyze large datasets and build dashboards for stakeholders.
""",

    "backend_engineer": """Job Title: Backend Software Engineer

REQUIREMENTS
3+ years of backend development experience.
Bachelor's degree in Computer Science.
Strong Python and FastAPI skills.
Experience with Docker and Kubernetes.
Experience with PostgreSQL.

PREFERRED SKILLS
Experience with RabbitMQ.
Experience with Redis.

RESPONSIBILITIES
Design and implement scalable REST API services.
""",

    "frontend_developer": """Job Title: Frontend Developer

REQUIREMENTS
3+ years of frontend development experience.
Bachelor's degree required.
Expert JavaScript and TypeScript.
Experience with React and Redux.
Experience with Tailwind CSS.

PREFERRED SKILLS
Experience with Next.js.
Experience with Jest or testing tools.

RESPONSIBILITIES
Build responsive web interfaces and design systems.
""",

    "devops_engineer": """Job Title: DevOps Engineer

REQUIREMENTS
4+ years of DevOps or infrastructure experience.
Bachelor's degree required.
Strong Terraform and Kubernetes skills.
Experience with AWS and CI/CD pipelines.
Experience with Jenkins and GitHub Actions.

PREFERRED SKILLS
Experience with Prometheus and Grafana.
Experience with Ansible.

RESPONSIBILITIES
Automate infrastructure and manage cloud deployments.
""",

    "ml_engineer": """Job Title: Machine Learning Engineer

REQUIREMENTS
3+ years of machine learning experience.
Master's degree or Bachelor's in a technical field.
Strong Python, PyTorch, and TensorFlow skills.
Experience with Large Language Models.
Experience with Hugging Face.

PREFERRED SKILLS
Experience with MLOps tools.
Experience with Docker.

RESPONSIBILITIES
Train, evaluate, and deploy machine learning models to production.
""",

    "qa_engineer": """Job Title: QA Automation Engineer

REQUIREMENTS
3+ years of test automation experience.
Bachelor's degree required.
Strong Selenium and Python skills.
Experience with Pytest and API testing with Postman.
Experience with CI/CD pipelines.

PREFERRED SKILLS
Experience with Playwright.
Experience with Cypress.

RESPONSIBILITIES
Build and maintain automated test suites and report quality metrics.
""",

    "business_analyst": """Job Title: Business Analyst

REQUIREMENTS
4+ years of business analysis experience.
Bachelor's degree required.
Strong SQL and Excel skills.
Experience with Power BI and PowerPoint reporting.
Experience with Agile and Jira.

PREFERRED SKILLS
Experience with Tableau.
Stakeholder management experience.

RESPONSIBILITIES
Gather requirements and translate business needs into specifications.
""",

    "mobile_developer": """Job Title: Mobile App Developer

REQUIREMENTS
3+ years of mobile development experience.
Bachelor's degree required.
Strong Flutter and Dart skills.
Experience with Kotlin for Android Development.
Experience with Firebase.

PREFERRED SKILLS
Experience with Swift for iOS Development.
Experience with REST API integration.

RESPONSIBILITIES
Build and ship cross-platform mobile applications.
""",

}

# Resume "ingredient" banks per domain: skills and bullets covering the JD.
RESUME_INGREDIENTS = {
    "data_analyst": {
        "title": "Senior Data Analyst",
        "skills": ["SQL", "Python", "Tableau", "Apache Airflow", "Apache Spark", "Snowflake", "Statistics"],
        "bullets": [
            "Analyzed large datasets with SQL and Python to build 12 Tableau dashboards",
            "Automated reporting pipelines using Airflow, cutting delivery time by 45%",
            "Migrated 8 dashboards to Snowflake and improved query speed by 60%",
            "Led A/B testing analysis that increased conversion by 12%",
        ],
        "years": 5,
    },
    "backend_engineer": {
        "title": "Backend Software Engineer",
        "skills": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL", "RabbitMQ", "Redis", "REST API"],
        "bullets": [
            "Designed REST API services in FastAPI handling 10k requests per minute",
            "Containerized 14 services with Docker and deployed on Kubernetes",
            "Modeled PostgreSQL schemas and cut p99 latency by 35%",
            "Introduced RabbitMQ queues and Redis caching to scale order flow by 3x",
        ],
        "years": 4,
    },
    "frontend_developer": {
        "title": "Frontend Developer",
        "skills": ["JavaScript", "TypeScript", "React", "Redux", "Tailwind CSS", "Next.js", "HTML", "CSS"],
        "bullets": [
            "Built responsive React interfaces used by 200k monthly users",
            "Migrated a legacy app to TypeScript and Next.js, reducing load time by 40%",
            "Implemented a Redux state architecture across 30 screens",
            "Created a Tailwind CSS design system adopted by 3 teams",
        ],
        "years": 4,
    },
    "devops_engineer": {
        "title": "DevOps Engineer",
        "skills": ["Terraform", "Kubernetes", "AWS", "CI/CD", "Jenkins", "GitHub Actions", "Prometheus", "Grafana", "Ansible"],
        "bullets": [
            "Managed AWS infrastructure with Terraform across 40+ environments",
            "Cut deployment time by 70% with GitHub Actions CI/CD pipelines",
            "Set up Prometheus and Grafana monitoring covering 200 services",
            "Automated configuration with Ansible, eliminating 15 hours of manual work weekly",
        ],
        "years": 5,
    },
    "ml_engineer": {
        "title": "Machine Learning Engineer",
        "skills": ["Python", "PyTorch", "TensorFlow", "Large Language Models", "Hugging Face", "Docker", "Machine Learning"],
        "bullets": [
            "Fine-tuned Large Language Models with Hugging Face, improving accuracy by 18%",
            "Trained and deployed PyTorch models serving 1M predictions daily",
            "Built TensorFlow training pipelines that cut experiment time in half",
            "Containerized inference services with Docker for production deployment",
        ],
        "years": 4,
    },
    "qa_engineer": {
        "title": "QA Automation Engineer",
        "skills": ["Selenium", "Python", "Pytest", "Postman", "CI/CD", "Playwright", "Test Automation"],
        "bullets": [
            "Built Selenium and Pytest suites covering 500+ test cases",
            "Integrated automated tests into CI/CD pipelines, catching 90% of regressions",
            "Performed API testing with Postman across 60 endpoints",
            "Added Playwright end-to-end coverage that reduced escaped bugs by 50%",
        ],
        "years": 4,
    },
    "business_analyst": {
        "title": "Business Analyst",
        "skills": ["SQL", "Excel", "Power BI", "PowerPoint", "Agile", "Jira", "Stakeholder Management", "Tableau"],
        "bullets": [
            "Gathered requirements from 20+ stakeholders and shipped 12 Agile releases",
            "Built Power BI dashboards tracked by executives across 5 departments",
            "Wrote SQL queries against a 3TB warehouse to answer business questions",
            "Delivered PowerPoint presentations that secured $2M in project funding",
        ],
        "years": 5,
    },
    "mobile_developer": {
        "title": "Mobile App Developer",
        "skills": ["Flutter", "Dart", "Kotlin", "Android Development", "Firebase", "Swift", "iOS Development", "REST API"],
        "bullets": [
            "Shipped 3 cross-platform Flutter apps with 100k+ combined downloads",
            "Built Kotlin Android modules and migrated 10 screens to Material 3",
            "Integrated Firebase auth, analytics, and push notifications",
            "Consumed REST API backends with offline-first caching in Dart",
        ],
        "years": 4,
    },
}


def matched_resume(domain):
    ing = RESUME_INGREDIENTS[domain]
    return make_resume(ing["title"], ing["skills"], ing["bullets"], ing["years"])


def partial_resume(domain):
    ing = RESUME_INGREDIENTS[domain]
    half_skills = ing["skills"][: max(1, len(ing["skills"]) // 2)]
    half_bullets = ing["bullets"][:2]
    return make_resume(ing["title"], half_skills, half_bullets, max(1, ing["years"] - 2))


def weak_resume():
    return (
        "Sam Sample\n"
        "sam@example.com\n\n"
        "I am a hardworking person and a team player. I did some computer stuff.\n"
        "I am passionate and a quick learner. I worked at places for a while.\n"
    )


def ats_of(resume, jd):
    result = analyze_and_match(resume, jd)
    return result["ats_result"]["total"], result


def main():
    domains = list(JDS.keys())
    failures = []

    # ---------------------------------------------------------------- 8x8 matrix
    print("Building 8x8 cross-domain matrix (matched resume i vs JD j)...")
    start = time.perf_counter()
    matrix = {}
    for i in domains:
        resume = matched_resume(i)
        for j in domains:
            matrix[(i, j)], _ = ats_of(resume, JDS[j])
    cold_ms = (time.perf_counter() - start) * 1000

    warm_start = time.perf_counter()
    for i in domains:
        ats_of(matched_resume(i), JDS[i])
    warm_ms = (time.perf_counter() - warm_start) * 1000 / len(domains)

    print(f"\n{'resume \\ JD':22s}" + "".join(f"{d[:9]:>10s}" for d in domains))
    for i in domains:
        row = "".join(f"{matrix[(i, j)]:10.1f}" for j in domains)
        print(f"{i:22s}{row}")

    print("\n[1] DIAGONAL DOMINANCE (each tailored resume ranks its own JD first):")
    for i in domains:
        home = matrix[(i, i)]
        best_other = max(matrix[(i, j)] for j in domains if j != i)
        status = "OK" if home > best_other else "FAIL"
        if status == "FAIL":
            failures.append(f"{i}: home {home:.1f} <= best other {best_other:.1f}")
        print(f"  {i:22s} home={home:5.1f} best-other={best_other:5.1f}  {status}")

    # ---------------------------------------------------------------- ordering
    print("\n[2] ORDERING matched > partial > weak, per domain:")
    for i in domains:
        strong, _ = ats_of(matched_resume(i), JDS[i])
        mid, _ = ats_of(partial_resume(i), JDS[i])
        low, _ = ats_of(weak_resume(), JDS[i])
        ok = strong > mid > low
        if not ok:
            failures.append(f"{i}: ordering broken {strong:.1f} > {mid:.1f} > {low:.1f}")
        print(f"  {i:22s} {strong:5.1f} > {mid:5.1f} > {low:5.1f}  {'OK' if ok else 'FAIL'}")

    # ---------------------------------------------------------------- causality
    print("\n[3] CAUSALITY: following the tool's suggestions must raise the score:")
    for i in domains:
        jd_data = parse_job_description(JDS[i])
        base_resume = partial_resume(i)
        base_data = extract_all(base_resume)
        base_ats, _ = ats_of(base_resume, JDS[i])

        # Add every missing canonical skill the tool would flag.
        from services.ats_scorer import compute_keyword_match, compute_skill_match

        kw = compute_keyword_match(base_resume, JDS[i], jd_data, base_data)
        skill_match = compute_skill_match(base_data.get("skills", []), jd_data["required_skills"], jd_data["preferred_skills"])
        additions = set()
        for k in kw["missing"][:10]:
            additions.add(k["term"])
        additions.update(skill_match["missing_required"])
        # Only inject terms that are real words for a resume skills section.
        injected_skills = sorted(base_data["skills"] + [a for a in additions])
        improved = make_resume(
            RESUME_INGREDIENTS[i]["title"], injected_skills,
            RESUME_INGREDIENTS[i]["bullets"][:2], max(1, RESUME_INGREDIENTS[i]["years"] - 2),
        )
        improved_ats, _ = ats_of(improved, JDS[i])
        ok = improved_ats > base_ats
        if not ok:
            failures.append(f"{i}: injecting flagged skills did not raise score ({base_ats:.1f} -> {improved_ats:.1f})")
        print(f"  {i:22s} base={base_ats:5.1f} -> after-inject={improved_ats:5.1f}  {'OK' if ok else 'FAIL'}")

    print("\n[4] CAUSALITY: removing quality signals must lower the score:")
    strong = matched_resume("data_analyst")
    base_total, _ = ats_of(strong, JDS["data_analyst"])
    no_contact = make_resume(
        RESUME_INGREDIENTS["data_analyst"]["title"], RESUME_INGREDIENTS["data_analyst"]["skills"],
        RESUME_INGREDIENTS["data_analyst"]["bullets"], RESUME_INGREDIENTS["data_analyst"]["years"], contact=False,
    )
    no_contact_total, res = ats_of(no_contact, JDS["data_analyst"])
    fmt_base = next(f["score"] for f in res["ats_result"]["factors"] if f["key"] == "format")

    _, res2 = ats_of(strong, JDS["data_analyst"])
    fmt_contact = next(f["score"] for f in res2["ats_result"]["factors"] if f["key"] == "format")
    ok = no_contact_total < base_total and fmt_contact > fmt_base
    if not ok:
        failures.append(f"contact removal did not lower format score ({fmt_contact} -> {fmt_base})")
    print(f"  remove contact info : total {base_total:.1f} -> {no_contact_total:.1f}, format {fmt_contact} -> {fmt_base}  {'OK' if ok else 'FAIL'}")

    unquantified = make_resume(
        RESUME_INGREDIENTS["data_analyst"]["title"], RESUME_INGREDIENTS["data_analyst"]["skills"],
        ["Analyzed datasets and built dashboards for the team",
         "Automated reporting pipelines to save time",
         "Presented insights to stakeholders regularly",
         "Worked with engineers on data quality"],
        RESUME_INGREDIENTS["data_analyst"]["years"],
    )
    unq_total, res3 = ats_of(unquantified, JDS["data_analyst"])
    content_full = next(f["score"] for f in res2["ats_result"]["factors"] if f["key"] == "content")
    content_unq = next(f["score"] for f in res3["ats_result"]["factors"] if f["key"] == "content")
    ok = content_unq < content_full
    if not ok:
        failures.append(f"removing metrics did not lower content score ({content_full} -> {content_unq})")
    print(f"  remove metrics      : content {content_full:.1f} -> {content_unq:.1f}  {'OK' if ok else 'FAIL'}")

    # ---------------------------------------------------------------- robustness
    print("\n[5] ROBUSTNESS: odd JD formats must parse without crashing:")
    odd_jds = [
        ("CRLF + tabs", "Job Title: Analyst\r\n\r\nREQUIREMENTS\r\n\tSQL experience required.\r\n\tPython skills.\r\nExperience with Excel.\r\n"),
        ("unicode bullets", "Job Title: Developer\n\nREQUIREMENTS\n• Python experience\n• Docker knowledge\n• 3 years of experience\n\nRESPONSIBILITIES\n• Write code\n"),
        ("no sections", "We are looking for a great developer who knows Python, Docker and Kubernetes. 5 years experience required. Bachelor degree needed. Email us."),
        ("very long", ("RESPONSIBILITIES\nAnalyze data and build reports.\n" + "Support stakeholders with ad-hoc analysis.\n" * 120) + "\nREQUIREMENTS\nSQL, Python, Tableau. 3 years of experience.\n"),
        ("only punctuation", "!!! ??? ### ... --- ||| \\\\\\ ~~~ ^^^"),
        ("jd is a resume", "EXPERIENCE\nEngineer at X\nJan 2020 - Present\n- Built things\n\nSKILLS\nPython, SQL\n"),
    ]
    for name, jd in odd_jds:
        total, _ = ats_of(matched_resume("data_analyst"), jd)
        ok = total is None or 0 <= total <= 100
        if not ok:
            failures.append(f"odd JD '{name}' out of range: {total}")
        print(f"  {name:18s} total={total!s:6s}  {'OK' if ok else 'FAIL'}")

    # ---------------------------------------------------------------- precision
    print("\n[5b] PRECISION: real-world JD with benefits/EEO boilerplate:")
    real_jd = """Job Title: Senior Data Analyst

About us: We are a fast-growing company on an amazing journey.

What You'll Bring
4+ years of experience in data analysis.
Expert SQL and Python skills.
Experience with Tableau and Airflow.

Responsibilities
Analyze datasets and build dashboards.

Benefits
We offer 401k with company match, health insurance, dental and vision
coverage, PTO, parental leave, gym membership, and free snacks.

Equal Opportunity Employer: We celebrate diversity and are committed to an
inclusive environment for all employees.
"""
    from services.ats_scorer import compute_keyword_match

    result = analyze_and_match(matched_resume("data_analyst"), real_jd)
    keywords_factor = next(f for f in result["ats_result"]["factors"] if f["key"] == "keywords")
    missing_terms = [t.lower() for t in keywords_factor["missing_keywords"]]
    leaked = [t for t in missing_terms if t in
              {"401k", "insurance", "dental", "vision", "snacks", "pto", "gym",
               "parental", "leave", "diversity", "inclusive", "match", "benefits"}]
    airflow_ok = "Apache Airflow" in keywords_factor["matched_keywords"]
    ok = not leaked and airflow_ok
    if not ok:
        failures.append(f"precision check failed: leaked={leaked}, airflow matched={airflow_ok}")
    print(f"  benefit words leaked: {leaked or 'none'}  | Apache Airflow matched: {airflow_ok}"
          f"  {'OK' if ok else 'FAIL'}")

    # ---------------------------------------------------------------- determinism
    print("\n[6] DETERMINISM:")
    r1, _ = ats_of(matched_resume("backend_engineer"), JDS["backend_engineer"])
    r2, _ = ats_of(matched_resume("backend_engineer"), JDS["backend_engineer"])
    ok = r1 == r2
    if not ok:
        failures.append(f"non-deterministic: {r1} vs {r2}")
    print(f"  backend run twice: {r1:.2f} == {r2:.2f}  {'OK' if ok else 'FAIL'}")

    # ---------------------------------------------------------------- standalone
    print("\n[7] STANDALONE audit ordering:")
    strong_sa = score_resume_standalone(matched_resume("data_analyst"), extract_all(matched_resume("data_analyst")))["total"]
    weak_sa = score_resume_standalone(weak_resume(), extract_all(weak_resume()))["total"]
    ok = strong_sa > weak_sa
    if not ok:
        failures.append(f"standalone ordering broken: {strong_sa} vs {weak_sa}")
    print(f"  strong={strong_sa:.1f} > weak={weak_sa:.1f}  {'OK' if ok else 'FAIL'}")

    # ---------------------------------------------------------------- speed
    print(f"\n[8] SPEED: cold matrix (64 full analyses incl. imports/models): {cold_ms:.0f} ms total, "
          f"warm per-analysis: {warm_ms:.1f} ms")
    if warm_ms > 250:
        failures.append(f"warm latency too high: {warm_ms:.1f} ms")

    print("\n" + "=" * 70)
    if failures:
        print(f"VALIDATION FAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print("ALL VALIDATION CHECKS PASSED")


if __name__ == "__main__":
    main()
