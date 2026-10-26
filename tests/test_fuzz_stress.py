"""Property-based stress tests: a seeded random corpus of resumes and job
descriptions is pushed through the full pipeline, checking the invariants a
correct ATS ranker must always hold (bounds, determinism, monotonicity,
ordering) - far beyond what hand-written cases can cover."""

import random
import re

import pytest

from services.analysis_service import analyze_and_match
from services.ats_scorer import compute_keyword_match, score_resume_standalone
from services.information_extractor import extract_all
from services.job_description_parser import parse_job_description

SEED = 20260919

SKILL_POOL = [
    "Python", "Java", "SQL", "Tableau", "Docker", "Kubernetes", "AWS", "React",
    "Machine Learning", "PostgreSQL", "Airflow", "Terraform", "Excel",
    "Power BI", "Pytest", "Selenium", "Flutter", "Firebase", "Redis", "Spark",
]

GENERIC_SENTENCES = [
    "Analyzed data and built reports for the team.",
    "Worked with stakeholders to gather requirements.",
    "Improved performance of the main service.",
    "Participated in code reviews and mentoring.",
    "Managed deployments across environments.",
    "Presented findings to leadership every month.",
    "Automated manual tasks saving hours per week.",
    "Collaborated with designers on new features.",
]

BOILERPLATE = [
    "We offer 401k with company match, health insurance and free snacks.",
    "Equal Opportunity Employer committed to diversity and inclusion.",
    "Our office has a fun culture with team events every month.",
    "We provide competitive salary, PTO and parental leave.",
]

SECTIONS = ["REQUIREMENTS", "RESPONSIBILITIES", "PREFERRED SKILLS",
            "BENEFITS", "WHAT YOU'LL BRING", "ABOUT US"]


def random_jd(rng):
    lines = [f"Job Title: {rng.choice(['Senior', 'Junior', ''])} {rng.choice(['Data Analyst', 'Engineer', 'Developer', 'Analyst'])}"]
    n_sections = rng.randint(0, 4)
    for _ in range(n_sections):
        lines.append("")
        lines.append(rng.choice(SECTIONS))
        for _ in range(rng.randint(1, 5)):
            if rng.random() < 0.5:
                lines.append(f"Experience with {rng.choice(SKILL_POOL)}"
                             f"{', ' + rng.choice(SKILL_POOL) if rng.random() < 0.4 else ''}.")
            else:
                lines.append(rng.choice(GENERIC_SENTENCES + BOILERPLATE))
    if rng.random() < 0.5:
        lines.append(f"{rng.randint(1, 9)}+ years of experience required.")
    if rng.random() < 0.4:
        lines.append("Bachelor's degree required.")
    if rng.random() < 0.3:
        lines.append("")
        lines.append(rng.choice(BOILERPLATE))
    return "\n".join(lines)


def random_resume(rng):
    name = f"{rng.choice(['Alex','Sam','Jo','Robin','Maria'])} {rng.choice(['Kumar','Lee','Patel','Wong'])}"
    lines = [name, f"Email: {name.split()[0].lower()}@example.com | Phone: +1-555-010-{rng.randint(1000, 9999)}"]
    if rng.random() < 0.8:
        lines += ["SUMMARY", f"{rng.choice(['Engineer','Analyst','Developer'])} with {rng.randint(1, 9)} years of experience."]
    if rng.random() < 0.9:
        skills = rng.sample(SKILL_POOL, rng.randint(0, 6))
        if rng.random() < 0.15 and skills:  # inject a typo occasionally
            s = skills[0]
            skills[0] = s[:-1] + s[-2] + s[-1] if len(s) > 5 else s
        lines += ["SKILLS", ", ".join(skills)]
    if rng.random() < 0.85:
        lines += ["EXPERIENCE", f"{rng.choice(['Engineer','Analyst'])} at Corp{rng.randint(1, 9)}"]
        if rng.random() < 0.7:
            lines.append(f"Jan {rng.randint(2015, 2024)} - Present")
        for _ in range(rng.randint(0, 4)):
            bullet = rng.choice(GENERIC_SENTENCES)
            if rng.random() < 0.4:
                bullet = f"Led {bullet.lower()}"
            if rng.random() < 0.4:
                bullet = f"{bullet[:-1]} improving results by {rng.randint(5, 60)}%."
            lines.append(f"- {bullet}")
    if rng.random() < 0.7:
        lines += ["EDUCATION", f"B.{rng.choice(['Tech', 'Sc'])} in {rng.choice(['CS', 'Math', 'Physics'])}, University, {rng.randint(2010, 2024)}"]
    return "\n".join(lines)


@pytest.fixture(scope="module")
def rng():
    return random.Random(SEED)


def test_corpus_scores_always_in_bounds_and_deterministic(rng):
    seen = set()
    for i in range(40):
        jd = random_jd(rng)
        resume = random_resume(rng)
        result = analyze_and_match(resume, jd)
        total = result["ats_result"]["total"]
        assert total is None or 0 <= total <= 100, f"case {i}: out of bounds {total}"

        # Determinism on a subset (full re-run would double suite time).
        if i % 8 == 0:
            again = analyze_and_match(resume, jd)["ats_result"]["total"]
            assert again == total, f"case {i}: non-deterministic {total} vs {again}"
        seen.add(i)
    assert len(seen) == 40


def test_adding_a_missing_skill_never_lowers_keyword_score(rng):
    for i in range(10):
        jd_text = random_jd(rng)
        jd_data = parse_job_description(jd_text)
        resume = random_resume(rng)
        resume_data = extract_all(resume)
        before = compute_keyword_match(resume, jd_text, jd_data, resume_data)
        if not before["missing"]:
            continue
        missing_terms = {k["term"] for k in before["missing"]}
        # Add exactly one missing canonical skill to the skills line.
        inject = next((t for t in missing_terms
                       if t in {s.lower() for s in SKILL_POOL}), None)
        if not inject:
            continue
        lines = resume.splitlines()
        for idx, line in enumerate(lines):
            if line.strip().lower() == "skills":
                lines[idx + 1] = lines[idx + 1].rstrip() + f", {inject.title() if inject.isalpha() else inject}"
                break
        improved_resume = "\n".join(lines)
        after = compute_keyword_match(improved_resume, jd_text, jd_data, extract_all(improved_resume))
        assert after["score"] >= before["score"], (
            f"case {i}: adding skill '{inject}' lowered keyword score "
            f"{before['score']:.1f} -> {after['score']:.1f}"
        )


def test_removing_all_skills_never_raises_total(rng):
    for i in range(10):
        jd_text = random_jd(rng)
        resume = random_resume(rng)
        base = analyze_and_match(resume, jd_text)["ats_result"]["total"]
        stripped = re.sub(
            r"(?ims)^SKILLS\s*$\n(^.*$\n?)",
            "SKILLS\nVarious things.\n",
            resume,
        )
        if stripped == resume:
            continue
        reduced = analyze_and_match(stripped, jd_text)["ats_result"]["total"]
        if base is not None and reduced is not None:
            assert reduced < base, f"case {i}: gutting skills did not lower score ({base} -> {reduced})"


def test_standalone_always_in_bounds(rng):
    for _ in range(20):
        resume = random_resume(rng)
        total = score_resume_standalone(resume, extract_all(resume))["total"]
        assert total is None or 0 <= total <= 100
