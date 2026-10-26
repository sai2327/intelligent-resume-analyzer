"""
Parses job description text (uploaded or pasted) into structured
requirements: required skills, preferred skills, experience/education
requirements, responsibilities, and technologies.

Uses the SAME centralized skill database (services/skill_matcher.py) as
resume parsing, so skill names are normalized identically on both sides.
"""

import re
from copy import deepcopy
from functools import lru_cache

from services.information_extractor import extract_years_of_experience
from services.section_extractor import extract_section, split_into_items
from services.skill_matcher import find_skills_in_text

# section_name -> recognized header phrases (matched against a whole, short line).
# NOTE: find_section_headers strips punctuation before comparing, so phrases
# with apostrophes are registered in their normalized form ("What You'll
# Bring" -> "what youll bring").
JD_SECTION_HEADERS = {
    "required": ["requirements", "required skills", "required qualifications",
                 "minimum qualifications", "must have", "qualifications",
                 "what you will bring", "what youll bring", "who you are",
                 "about you", "your profile", "what we are looking for",
                 "what were looking for", "skills and experience", "skills required",
                 "capabilities", "requirements and skills"],
    "preferred": ["preferred skills", "preferred qualifications", "nice to have",
                  "good to have", "bonus points", "bonus skills",
                  "bonus qualifications", "additional skills"],
    "responsibilities": ["responsibilities", "key responsibilities", "role",
                          "what you will do", "duties", "your role", "the role",
                          "key duties", "your responsibilities"],
}

# Header phrases that introduce benefits/compensation/EEO boilerplate. Words
# harvested from these sections ("401k", "insurance", "PTO"...) would be
# unfair "missing keywords" - no candidate lists perks on a resume.
JD_BENEFIT_HEADERS = {
    "benefits": ["benefits", "perks", "what we offer", "compensation",
                 "compensation and benefits", "salary", "salary and benefits",
                 "why join us", "why work with us", "why us", "our offer",
                 "our benefits", "equal opportunity", "equal opportunity employer",
                 "eeo", "diversity and inclusion", "how to apply"],
}

EDUCATION_KEYWORDS = [
    "b.tech", "btech", "b.e.", "be ", "bachelor", "b.sc", "bsc",
    "m.tech", "mtech", "m.e.", "master", "msc", "m.sc", "mca", "mba",
    "phd", "ph.d", "doctorate", "degree",
]

# Ordered low -> high; the LAST matching level wins (e.g. "senior" beats "junior"
# when a JD mentions both). Used to compare career-level expectations.
SENIORITY_LEVELS = [
    ("intern", 0), ("internship", 0), ("trainee", 0), ("entry-level", 0), ("entry level", 0),
    ("graduate", 1), ("junior", 1), ("associate", 1), ("fresher", 1),
    ("mid-level", 2), ("mid level", 2),
    ("senior", 3), ("lead", 3),
    ("staff", 4), ("principal", 4), ("manager", 4),
    ("senior manager", 5), ("director", 5), ("head of", 5),
    ("vp", 6), ("vice president", 6), ("chief", 6),
]
_SENIORITY_PATTERNS = [
    (term, re.compile(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", re.IGNORECASE), rank)
    for term, rank in SENIORITY_LEVELS
]

# "Job Title: X" / "Title: X" / "Position: X" / "Role: X"
_LABELED_TITLE = re.compile(
    r"^\s*(?:job\s*title|title|position|role)\s*[:\-]\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_HIRING_TITLE = re.compile(
    r"\b(?:hiring|seeking|looking for|recruiting)\s+(?:an?\s+)?"
    r"((?:[a-z]+[\w./#-]*\s+){0,3}?(?:engineer|developer|analyst|scientist|architect|"
    r"consultant|manager|administrator|designer|specialist|coordinator|"
    r"associate|intern|director|officer|executive|lead))\b",
    re.IGNORECASE,
)
_TITLE_HINT = re.compile(
    r"(engineer|developer|analyst|scientist|architect|consultant|manager|"
    r"administrator|designer|specialist|coordinator|associate|intern|"
    r"officer|executive|lead)",
    re.IGNORECASE,
)


def extract_job_title(text: str) -> str | None:
    """Best-effort JD job title: labeled 'Job Title:' line, a 'hiring a X'
    sentence, or a short first line that names a role. Never guesses when
    none of these are present."""
    labeled = _LABELED_TITLE.search(text)
    if labeled:
        title = labeled.group(1).strip()
        if 2 <= len(title) <= 80:
            return title

    hiring = _HIRING_TITLE.search(text)
    if hiring:
        return hiring.group(1).strip()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) > 60 or len(stripped) < 4:
            continue
        if _TITLE_HINT.search(stripped) and not stripped.endswith((".", "!", "?")):
            return stripped
    return None


def detect_seniority(text: str) -> str | None:
    """Return the highest seniority keyword found in text ('intern'... 'chief'),
    or None when no level keyword appears."""
    best_term = None
    best_rank = -1
    for term, pattern, rank in _SENIORITY_PATTERNS:
        if rank > best_rank and pattern.search(text):
            best_rank = rank
            best_term = term
    return best_term


def _extract_jd_section(text: str, section_name: str) -> str:
    return extract_section(text, section_name, JD_SECTION_HEADERS)


def extract_required_and_preferred_skills(text: str) -> tuple:
    """
    Split skills into required vs preferred using detected section headers.
    If no required/preferred sections are found at all, every detected skill
    in the document is treated as required (the common case for short JDs
    that don't separate the two).
    """
    required_section = _extract_jd_section(text, "required")
    preferred_section = _extract_jd_section(text, "preferred")

    if not required_section and not preferred_section:
        required_skills = find_skills_in_text(text)
        return required_skills, []

    required_skills = find_skills_in_text(required_section) if required_section else []
    preferred_skills = find_skills_in_text(preferred_section) if preferred_section else []

    # Anything mentioned elsewhere in the JD but not already categorized is
    # still relevant context; treat it as required so it isn't silently lost.
    all_skills = set(find_skills_in_text(text))
    already_categorized = set(required_skills) | set(preferred_skills)
    leftover = sorted(all_skills - already_categorized)
    required_skills = sorted(set(required_skills) | set(leftover))

    return required_skills, preferred_skills


def extract_education_requirement(text: str) -> str | None:
    """Return the first sentence/line mentioning a recognizable degree keyword, if any."""
    lines = re.split(r"[\n.]", text)
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in EDUCATION_KEYWORDS):
            cleaned = line.strip()
            if cleaned:
                return cleaned
    return None


def extract_responsibilities(text: str) -> list:
    return split_into_items(_extract_jd_section(text, "responsibilities"))


def extract_technologies(required_skills: list, preferred_skills: list) -> list:
    """Return the union of all detected skills, used for a flat 'technologies' view."""
    return sorted(set(required_skills) | set(preferred_skills))


@lru_cache(maxsize=32)
def _parse_job_description_cached(text: str) -> dict:
    """Pure function of the JD text (the skill database is process-cached),
    so results are memoized: analyzing N resumes against the same JD parses
    it once. Callers receive a defensive copy they may freely mutate."""
    required_skills, preferred_skills = extract_required_and_preferred_skills(text)

    return {
        "job_title": extract_job_title(text),
        "seniority": detect_seniority(text),
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "experience_requirement": extract_years_requirement(text),
        "education_requirement": extract_education_requirement(text),
        "responsibilities": extract_responsibilities(text),
        "technologies": extract_technologies(required_skills, preferred_skills),
    }


# "2-4 years", "five to seven years" style ranges: meeting the LOWER bound
# already satisfies the requirement, so the requirement is the minimum.
JD_YEARS_RANGE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


def extract_years_requirement(text: str) -> float | None:
    """Years-of-experience requirement for a JD. Range phrasing ("2-4 years")
    resolves to the lower bound - meeting the minimum is what satisfies the
    requirement - while "N+ years" and bare "N years" keep their existing
    handling. Falls back to the single-figure extractor. Never invents a number."""
    for match in JD_YEARS_RANGE_PATTERN.finditer(text):
        return float(match.group(1))
    return extract_years_of_experience(text)


def parse_job_description(text: str) -> dict:
    """Parse raw job description text into a structured requirements dict."""
    return deepcopy(_parse_job_description_cached(text))
