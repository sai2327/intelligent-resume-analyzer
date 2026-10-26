"""
Extracts structured information from raw resume text using a hybrid of
regex, section-header detection, the centralized skill database, and
optional spaCy NER for name detection.

This is heuristic, not perfect: resumes come in too many formats for 100%
reliable extraction. Fields that cannot be confidently found are returned as
None / empty rather than guessed.
"""

import logging
import re
from datetime import date
from functools import lru_cache

from services.section_extractor import extract_section as _extract_section
from services.section_extractor import split_into_items
from services.skill_matcher import find_skills_in_text

logger = logging.getLogger(__name__)

_NLP_MODEL = None
_NLP_LOAD_ATTEMPTED = False


def _get_spacy_model():
    """Lazily load the spaCy English model once. Only tok2vec + NER stay
    enabled - tagger/parser/lemmatizer are dead weight for name extraction
    and roughly 40% of the runtime. Returns None if unavailable, in which
    case name extraction falls back to a regex/heuristic-only mode."""
    global _NLP_MODEL, _NLP_LOAD_ATTEMPTED
    if not _NLP_LOAD_ATTEMPTED:
        _NLP_LOAD_ATTEMPTED = True
        try:
            import spacy

            _NLP_MODEL = spacy.load(
                "en_core_web_sm",
                exclude=["tagger", "parser", "lemmatizer", "attribute_ruler"],
            )
        except Exception as exc:  # model missing, spaCy not installed, etc.
            logger.warning(
                "spaCy model 'en_core_web_sm' unavailable (%s). "
                "Falling back to regex-only name extraction. "
                "Run setup_nlp.py to install it.",
                exc,
            )
            _NLP_MODEL = None
    return _NLP_MODEL


EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Professional profile links (modern resumes carry them near the contact line).
LINKEDIN_PATTERN = re.compile(
    r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|pub)/[A-Za-z0-9._%-]{2,60}",
    re.IGNORECASE,
)
GITHUB_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9._-]{2,39}(?!/[A-Za-z0-9._-])",
    re.IGNORECASE,
)


def extract_profiles(text: str) -> dict:
    """Extract LinkedIn / GitHub profile URLs. Returns None per field when the
    document does not carry one."""
    linkedin = LINKEDIN_PATTERN.search(text or "")
    github = GITHUB_PATTERN.search(text or "")
    return {
        "linkedin": linkedin.group(0).rstrip(".,;") if linkedin else None,
        "github": github.group(0).rstrip(".,;") if github else None,
    }

PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
)

# "4+ years of experience", "3 yrs 6 mos" (LinkedIn style), "1 year and 8 months"
YEARS_EXPERIENCE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\b(?:\s*of\s*experience)?"
    r"(?:\s*(?:and\s+)?(\d+(?:\.\d+)?)\s*(?:months?|mos?|mths?|mts?)\b)?",
    re.IGNORECASE,
)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_RE = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\w*\.?"

# "Jan 2020 - Mar 2022", "June 2019 to Present", "2020 - 2023", "07/2021 - 11/2024"
DATE_RANGE_PATTERN = re.compile(
    rf"(?P<start>(?:{_MONTH_RE}\s*)?(?:\d{{1,2}}/)?(?:19|20)\d{{2}})"
    r"\s*(?:-|–|—|to|until|through)\s*"
    rf"(?P<end>(?:{_MONTH_RE}\s*)?(?:\d{{1,2}}/)?(?:19|20)\d{{2}}"
    r"|present|current|now|ongoing|today)",
    re.IGNORECASE,
)
_WORD_MM_YYYY = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s*((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_NUMERIC_MM_YYYY = re.compile(r"\b(\d{1,2})/((?:19|20)\d{2})\b")
_BARE_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")
_OPEN_ENDED = re.compile(r"present|current|now|ongoing|today", re.IGNORECASE)

# Job titles commonly found on resumes; used to pull role names out of the
# experience section for job-title matching against a job description.
TITLE_KEYWORDS = re.compile(
    r"(engineer|developer|programmer|analyst|scientist|architect|consultant|"
    r"manager|administrator|designer|specialist|coordinator|technician|"
    r"associate|intern|trainee|lead|head|director|officer|executive|"
    r"researcher|devops|qa|recruiter|accountant|marketer)",
    re.IGNORECASE,
)
# "Worked as a Data Analyst at X", "Software Engineer, X Corp", "SDE @ Acme"
TITLE_FROM_SENTENCE = re.compile(
    r"\b(?:as|promoted to)\s+(?:an?\s+)?([A-Za-z][\w./+#-]*(?:\s+[A-Za-z][\w./+#-]*){0,3})\s+"
    r"(?:at|with|for|@|in)\s",
)
TITLE_BEFORE_COMMA = re.compile(
    r"^\s*((?:[A-Z][\w./+#-]*\s+){0,3}[A-Z][\w./+#-]*)\s*[,|@]\s*[A-Z]",
)

# section_name -> recognized header phrases (matched against a whole, short line).
SECTION_HEADERS = {
    "summary": ["summary", "professional summary", "career summary", "objective",
                "career objective", "profile", "professional profile", "about me",
                "about", "professional overview"],
    "skills": ["skills", "technical skills", "core skills", "key skills",
               "skills summary", "core competencies", "competencies", "technologies",
               "technical proficiencies", "tech stack", "areas of expertise"],
    "education": ["education", "academic background", "academic qualifications",
                  "educational qualifications", "academic details"],
    "experience": ["work experience", "professional experience", "experience",
                   "employment history", "work history", "career history",
                   "relevant experience", "employment", "internship experience"],
    "projects": ["projects", "personal projects", "academic projects", "key projects",
                 "selected projects", "project work"],
    "certifications": ["certifications", "certificates", "licenses and certifications",
                       "licenses & certifications", "professional development"],
    "achievements": ["achievements", "awards", "honors", "accomplishments",
                     "awards and honors", "achievements and awards"],
    "volunteer": ["volunteer experience", "volunteering", "volunteer work",
                  "community involvement", "extracurricular activities"],
}

_HEADER_KEYWORDS_FLAT = {kw for kws in SECTION_HEADERS.values() for kw in kws}

# Words that must never appear inside an extracted name: contact/link labels,
# document boilerplate, and product names spaCy occasionally mislabels PERSON.
_NAME_BLOCKLIST = {
    "email", "phone", "mobile", "contact", "gmail", "mail", "linkedin", "github",
    "leetcode", "hackerrank", "portfolio", "resume", "curriculum", "vitae",
    "address", "location", "whatsapp", "telegram", "boiler", "summary",
    "profile", "objective", "engineering", "developer", "student",
    "programming", "achievements", "projects", "experience", "education",
    "skills", "certifications", "activities", "manager", "solved", "problems",
}

# PDF artifacts: a single uppercase letter glued to the next lowercase word
# ("Sai T eja" -> "Sai Teja").
_SPLIT_TOKEN_PAIR = re.compile(r"\b([A-Z]) (?=[a-z])")

_NAME_CANDIDATE_CHARS = re.compile(r"^[A-Za-z .'-]+$")


def _clean_name_candidate(candidate: str) -> str | None:
    """Hygiene filter for a name candidate: alphabetic words only, no digits,
    no contact-label words, reasonable length. Returns the cleaned string or
    None when the candidate is junk (e.g. 'Phone:+917330719394', 'Gmail')."""
    cleaned = candidate.strip(" .,-|_\n\r\t")
    if not (2 <= len(cleaned) <= 60):
        return None
    if not _NAME_CANDIDATE_CHARS.fullmatch(cleaned):
        return None  # contains digits/symbols (phone numbers, emails, etc.)
    words = cleaned.split()
    if not (1 <= len(words) <= 5):
        return None
    lowered = {w.rstrip(".").lower() for w in words}
    if lowered & _NAME_BLOCKLIST:
        return None
    if not any(w[0].isupper() for w in words if w[:1].isalpha()):
        return None  # no capitalization signal at all
    return re.sub(r"\s+", " ", cleaned)


def _entity_name_candidates(ent_text: str) -> list:
    """ spaCy PERSON entities frequently glue the name line to the following
    contact line ('Sai Teja Kondapalli\\nPhone'). Return line segments of the
    entity, first line first, so the true name is tried before the tail."""
    return [segment for segment in ent_text.split("\n") if segment.strip()]


def _header_lines(lines: list, count: int = 4) -> list:
    """The first `count` non-empty lines, with PDF intra-word splits repaired
    and consecutive short all-caps lines joined into one name candidate
    ('KUMARI' + 'GNANESWARI' -> 'KUMARI GNANESWARI')."""
    header = []
    for line in lines[:count]:
        repaired = _SPLIT_TOKEN_PAIR.sub(r"\1", line)
        header.append(repaired)
    joined = []
    for line in header:
        words = line.split()
        is_caps_fragment = (
            1 <= len(words) <= 3
            and all(w.isupper() and w.isalpha() for w in words)
            and not any(w.lower() in _NAME_BLOCKLIST for w in words)
        )
        if joined and is_caps_fragment and joined[-1][1]:
            joined[-1] = (joined[-1][0] + " " + line, True)
        else:
            joined.append((line, is_caps_fragment))
    return [text for text, _ in joined]


def extract_section(text: str, section_name: str) -> str:
    """Return the raw text between a named section's header and the next
    detected header (or end of document). Returns '' if the section is not found."""
    return _extract_section(text, section_name, SECTION_HEADERS)


@lru_cache(maxsize=256)
def extract_name(text: str) -> str | None:
    """Best-effort candidate name extraction.

    Pipeline: spaCy PERSON entities found in the repaired document header win
    (earliest line first), subject to a hygiene filter; otherwise the
    'looks like a name' heuristic on the same header lines. Cached per text -
    NER is the most expensive extraction step."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None

    header = _header_lines(lines)
    header_text = "\n".join(header[:5])

    nlp = _get_spacy_model()
    if nlp is not None:
        try:
            doc = nlp(header_text)
            for ent in doc.ents:
                if ent.label_ != "PERSON":
                    continue
                # Try each line segment of the entity (first line first): a
                # PERSON entity often glues the name line to the contact line.
                for segment in _entity_name_candidates(ent.text):
                    cleaned = _clean_name_candidate(segment)
                    if cleaned and 1 <= len(cleaned.split()) <= 4:
                        return cleaned
        except Exception as exc:
            logger.warning("spaCy NER failed during name extraction: %s", exc)

    for line in header[:4]:
        if "@" in line or any(ch.isdigit() for ch in line):
            continue
        if line.lower() in _HEADER_KEYWORDS_FLAT or line.lower() in {"resume", "curriculum vitae", "cv"}:
            continue
        words = line.split()
        if 1 < len(words) <= 4 and all(w[0].isupper() for w in words if w[:1].isalpha()):
            cleaned = _clean_name_candidate(line)
            if cleaned:
                return cleaned
    return None


def extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    for match in PHONE_PATTERN.finditer(text):
        candidate = match.group(0)
        digits = re.sub(r"\D", "", candidate)
        if 9 <= len(digits) <= 13:
            return candidate.strip()
    return None


def extract_years_of_experience(text: str) -> float | None:
    """Return the largest self-reported experience figure mentioned ('4+ years',
    '3 yrs 6 mos', '1 year and 8 months'), in float years, or None when no such
    figure is present. Never invents a number."""
    best = None
    for match in YEARS_EXPERIENCE_PATTERN.finditer(text):
        years = float(match.group(1))
        months = match.group(2)
        total = years + (float(months) / 12.0 if months else 0.0)
        if best is None or total > best:
            best = total
    return best


def _parse_date_side(side: str) -> tuple | None:
    """Parse one side of a date range into (year, month). Returns None when the
    side is an open-ended word (Present/Current/...) or unparseable."""
    lowered = side.strip().lower()
    if _OPEN_ENDED.fullmatch(lowered):
        return None
    match = _NUMERIC_MM_YYYY.search(lowered)
    if match:
        return int(match.group(2)), min(max(int(match.group(1)), 1), 12)
    match = _WORD_MM_YYYY.search(lowered)
    if match:
        return int(match.group(2)), _MONTHS[match.group(1)[:3]]
    match = _BARE_YEAR.search(lowered)
    if match:
        return int(match.group(1)), 1
    return None


def extract_years_from_date_ranges(text: str, reference_date=None) -> float | None:
    """Total employment time implied by every 'start - end' date range in text,
    in float years, with overlapping ranges merged (interval union) so the same
    period is never double-counted. Open-ended ends ('Present') resolve against
    reference_date (default: today). Returns None when no valid range is found."""
    if not text:
        return None
    today = reference_date or date.today()
    today_ym = (today.year, today.month)
    intervals = []
    for match in DATE_RANGE_PATTERN.finditer(text):
        start = _parse_date_side(match.group("start"))
        end_raw = match.group("end")
        if _OPEN_ENDED.fullmatch(end_raw.strip().lower()):
            end = today_ym
        else:
            end = _parse_date_side(end_raw)
        if start is None or end is None or end < start:
            continue
        intervals.append((start, end))
    if not intervals:
        return None

    intervals.sort()
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    total_months = sum(
        (ey * 12 + em) - (sy * 12 + sm) for (sy, sm), (ey, em) in merged
    )
    return round(total_months / 12, 1)


def extract_experience_years(text: str, reference_date=None) -> dict:
    """Best estimate of total professional experience, combining:
    - explicit self-reported claims ("5+ years of experience"), and
    - objective date-range math over the experience section only (so
      education dates never inflate the figure).
    The larger of the two wins: summary claims often cover earlier,
    undated roles, while date math catches inflated claims."""
    reported = extract_years_of_experience(text)
    experience_section = extract_section(text, "experience")
    from_dates = extract_years_from_date_ranges(experience_section, reference_date)

    candidates = [value for value in (reported, from_dates) if value is not None]
    best = round(max(candidates), 1) if candidates else None
    return {
        "years": best,
        "reported": reported,
        "from_dates": from_dates,
    }


def extract_job_titles(text: str) -> list:
    """Pull likely job titles out of the experience section ("as a Data Analyst
    at X", "Software Engineer, X Corp"). Used for resume-vs-JD title matching."""
    titles = []
    seen = set()
    items = extract_experience(text)
    if not items:
        return titles
    for item in items:
        candidate = None
        sentence_match = TITLE_FROM_SENTENCE.search(item)
        if sentence_match:
            candidate = sentence_match.group(1)
        else:
            comma_match = TITLE_BEFORE_COMMA.match(item)
            if comma_match:
                candidate = comma_match.group(1)
        if not candidate:
            continue
        candidate = re.sub(r"\s+", " ", candidate).strip(" .,-").strip()
        if not (2 <= len(candidate) <= 50):
            continue
        if not TITLE_KEYWORDS.search(candidate):
            continue
        lowered = candidate.lower()
        if lowered not in seen:
            seen.add(lowered)
            titles.append(candidate)
    return titles


def extract_education(text: str) -> list:
    return split_into_items(extract_section(text, "education"))


def extract_experience(text: str) -> list:
    return split_into_items(extract_section(text, "experience"))


def extract_projects(text: str) -> list:
    return split_into_items(extract_section(text, "projects"))


def extract_certifications(text: str) -> list:
    return split_into_items(extract_section(text, "certifications"))


def extract_all(text: str) -> dict:
    """Run every extractor and return a single structured dict describing the resume."""
    experience_years = extract_experience_years(text)
    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "profiles": extract_profiles(text),
        "skills": find_skills_in_text(text),
        "education": extract_education(text),
        "experience": extract_experience(text),
        "years_of_experience": experience_years["years"],
        "experience_years_reported": experience_years["reported"],
        "experience_years_from_dates": experience_years["from_dates"],
        "job_titles": extract_job_titles(text),
        "projects": extract_projects(text),
        "certifications": extract_certifications(text),
    }
