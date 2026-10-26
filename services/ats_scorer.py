"""
ATS (Applicant Tracking System) score tracker.

Models how keyword-parsing ATS platforms (Taleo, Workday, iCIMS, Greenhouse,
...) evaluate a resume: exact/normalized keyword coverage first, structured
sections and parseability second, content quality third. The score is a
transparent weighted checklist, never a black box:

- every factor returns a 0-100 subscore, its weight, a plain-English detail,
  and prioritized, specific suggestions;
- a factor that cannot be computed (e.g. the JD states no education
  requirement) is EXCLUDED and its weight is redistributed proportionally,
  so missing information never silently drags the score toward 0 or 100;
- ``get_change_suggestions`` flattens every factor's suggestions into one
  prioritized "what to change" list ordered by potential score gain.

Two modes:
- job_match:   resume vs a specific job description (7 factors)
- standalone:  resume alone - parseability/quality audit (4 factors)
"""

import logging
import math
import re
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache

from config import config
from services.matching_engine import (
    compute_education_match,
    compute_experience_match,
    compute_skill_match,
)
from services.information_extractor import (
    DATE_RANGE_PATTERN,
    TITLE_BEFORE_COMMA,
    extract_section,
)
from services.job_description_parser import (
    JD_BENEFIT_HEADERS,
    JD_SECTION_HEADERS,
    parse_job_description,
)
from services.section_extractor import extract_section as _extract_jd_section_by
from services.section_extractor import find_section_headers
from services.skill_matcher import (
    all_canonical_skills,
    normalize_skill,
    skill_categories,
)
from services.text_preprocessor import clean_text, load_stopwords, preprocess_text

logger = logging.getLogger(__name__)

# Strictness profiles. "strict" models a rigid keyword-parsing ATS: no typo
# forgiveness, half partial credit, tighter length band, higher quality bars.
# "lenient" models a modern parser that forgives more.
STRICTNESS_PROFILES = {
    "lenient": {
        "typo_matching": True,
        "partial_credit_multiplier": 1.0,
        "length_band": (250, 1400),
        "length_partial_band": (150, 1800),
        "quantified_target": 0.30,
        "action_verb_target": 0.50,
    },
    "standard": {
        "typo_matching": True,
        "partial_credit_multiplier": 1.0,
        "length_band": (350, 1200),
        "length_partial_band": (200, 1600),
        "quantified_target": 0.40,
        "action_verb_target": 0.60,
    },
    "strict": {
        "typo_matching": False,
        "partial_credit_multiplier": 0.5,
        "length_band": (350, 1100),
        "length_partial_band": (250, 1400),
        "quantified_target": 0.50,
        "action_verb_target": 0.70,
    },
}


def _normalize_strictness(strictness: str | None) -> str:
    value = (strictness or "standard").strip().lower()
    return value if value in STRICTNESS_PROFILES else "standard"

# Words so generic in job descriptions that counting them as "keywords" would
# drown the signal (every JD says "experience" several times). Canonical
# skills are matched separately and always count.
_GENERIC_TERMS = frozenset({
    "ability", "able", "across", "also", "always", "apply", "application", "apply",
    "based", "benefit", "benefits", "best", "candidate", "candidates", "career",
    "client", "clients", "company", "compensation", "customer", "customers",
    "day", "description", "duty", "duties", "employee", "employees", "employer",
    "environment", "etc", "excellent", "field", "fresher", "full", "general",
    "good", "great", "help", "ideal", "including", "join", "job", "least",
    "looking", "minimum", "must", "need", "needed", "new", "nice", "office",
    "opportunity", "others", "part", "plus", "position", "preferred", "provide",
    "quality", "related", "requirement", "requirements", "required", "role",
    "roles", "salary", "seeking", "seniority", "skill", "skills", "strong",
    "successful", "support", "team", "teams", "time", "title", "understanding", "well",
    "within", "work", "working", "works", "year", "years", "you", "your",
    "responsibility", "responsibilities", "responsible", "experience",
    "knowledge", "proficiency", "proficient", "familiarity", "familiar",
    "expertise", "equivalent", "bachelor", "bachelors", "master", "masters",
    "degree", "phd", "duty", "ensuring", "ensure", "using", "used", "usage",
    # Fluff/buzzwords that appear in JDs but are never matchable keywords -
    # suggesting "add snacks to your resume" would be nonsense.
    "amazing", "awesome", "culture", "dynamic", "energetic", "enthusiastic",
    "free", "fun", "hardworking", "journey", "love", "motivated", "ninja",
    "guru", "rockstar", "wizard", "passionate", "people", "perks", "snacks",
    "vibrant", "everyday", "perk", "lounge", "spirit", "vibe",
    "resume", "cv", "send", "send us", "every", "apply now", "click",
    "us", "we", "our", "they", "their", "here",
    # Benefits / compensation / EEO boilerplate (candidates never list these
    # on a resume, so counting them as missing keywords would be unfair).
    "insurance", "401k", "k", "dental", "vision", "medical", "health",
    "life", "disability", "retirement", "vacation", "pto", "sick", "leave",
    "parental", "match", "retirement plan", "gym", "membership", "stipend",
    "wellness", "tuition", "reimbursement", "accommodation", "equal",
    "opportunity", "employer", "diversity", "inclusion", "eeo", "meal",
    "lunch", "dinner", "relocation", "bonus compensation", "flexible",
})

MAX_GENERAL_KEYWORDS = 50

ACTION_VERBS = frozenset({
    "accelerated", "achieved", "administered", "advanced", "advised", "analyzed",
    "architected", "automated", "built", "chaired", "collaborated", "compiled",
    "completed", "conducted", "configured", "consolidated", "constructed",
    "coordinated", "created", "cut", "debugged", "decreased", "defined",
    "delivered", "deployed", "designed", "developed", "diagnosed", "directed",
    "documented", "doubled", "drove", "earned", "eliminated", "enabled",
    "engineered", "enhanced", "established", "evaluated", "exceeded",
    "executed", "expanded", "expedited", "forecasted", "founded", "generated",
    "grew", "guided", "handled", "headed", "identified", "implemented",
    "improved", "increased", "influenced", "initiated", "innovated",
    "integrated", "introduced", "invented", "launched", "led", "maintained",
    "managed", "mapped", "marketed", "measured", "mentored", "migrated",
    "modeled", "modernized", "monitored", "motivated", "negotiated",
    "optimized", "organized", "overhauled", "owned", "partnered", "performed",
    "pioneered", "planned", "presented", "prioritized", "produced",
    "programmed", "prototyped", "published", "recommended", "reduced",
    "refactored", "reengineered", "resolved", "restructured", "revamped",
    "saved", "scaled", "secured", "shipped", "simplified", "solved",
    "spearheaded", "standardized", "streamlined", "strengthened",
    "structured", "supervised", "tested", "tracked", "trained", "transformed",
    "translated", "trimmed", "troubleshot", "unified", "upgraded", "validated",
    "verified", "won", "wrote",
})

FIRST_PERSON_PATTERN = re.compile(r"\b(?:i|me|my|mine|myself)\b", re.IGNORECASE)
DIGIT_PATTERN = re.compile(r"\d")

# A bullet counts as "quantified" only when it contains a real metric: a
# suffixed figure (40%, 3x, $2M, 12 hours, 5 dashboards...) or a plain number
# that is not a calendar year ("team of 12" yes; "in 2021" no).
_METRIC_SUFFIX = re.compile(
    r"\d(?:\.\d+)?\s*(?:%|percent|x\b|\$|\₹|\€|k\b|m\b|bn\b|million|billion|"
    r"hours?|hrs?|days?|weeks?|months?|minutes?|seconds?|users?|customers?|"
    r"clients?|people|students?|employees?|requests?|queries?|records?|rows?|"
    r"tickets?|problems?|projects?|dashboards?|reports?|apps?|services?|"
    r"servers?|machines?|countries?|teams?|engineers?|analysts?|downloads?|"
    r"installs?|reviews?|orders?|transactions?|stars?|points?)",
    re.IGNORECASE,
)
_PLAIN_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
_YEAR_LIKE = re.compile(r"\b(?:19|20)\d{2}\b")


def _has_real_metric(text: str) -> bool:
    if _METRIC_SUFFIX.search(text):
        return True
    for match in _PLAIN_NUMBER.finditer(text):
        if not _YEAR_LIKE.fullmatch(match.group(0)):
            return True
    return False
BULLET_PREFIX_PATTERN = re.compile(r"^[•▪◦‣·\-\*–]\s*")
_SUSPICIOUS_CHARS = re.compile(r"[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f]")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _factor(key, label, score, weight, detail, suggestions=None, checks=None):
    available = score is not None
    return {
        "key": key,
        "label": label,
        "score": round(score, 2) if available else None,
        "weight": weight,
        "available": available,
        "detail": detail,
        "checks": checks or [],
        "suggestions": suggestions or [],
    }


def _suggestion(priority, text):
    return {"priority": priority, "text": text}


def _weighted_total(factors, weights):
    """Weighted 0-100 total. Unavailable factors are excluded and their weight
    is redistributed proportionally; returns None when nothing is computable."""
    available = {f["key"]: f["score"] for f in factors if f["available"]}
    if not available:
        return None, sorted(set(weights) - set(available))

    used_weights = {k: weights[k] for k in available}
    total_weight = sum(used_weights.values())
    total = sum(available[k] * (w / total_weight) for k, w in used_weights.items())
    excluded = sorted(set(weights) - set(available))
    return round(total, 2), excluded


def _grade(total):
    if total is None:
        return "Unknown", "Not enough information was available to score this resume."
    if total >= 85:
        return "Excellent", "Ready to submit - the ATS should parse and rank this resume well."
    if total >= 70:
        return "Strong", "Solid score. A few targeted fixes could push it into the top band."
    if total >= 55:
        return "Fair", "The resume will parse, but it will likely be outranked by closer matches."
    if total >= 40:
        return "Needs work", "Meaningful ATS penalties. Work through the high-priority fixes below."
    return "High risk", "This resume is likely to be filtered out by keyword-parsing ATS platforms."


# --------------------------------------------------------------------------
# factor 1: keyword coverage (job-match mode only)
# --------------------------------------------------------------------------

def _recognized_terms_lower() -> set:
    recognized = {s.lower() for s in all_canonical_skills()}
    return recognized


def _strip_benefit_sections(jd_text: str) -> str:
    """Cut benefits/compensation/EEO sections out of the JD text. Their words
    ("401k", "insurance", "PTO"...) would otherwise become unfair missing
    keywords - no candidate is expected to list perks on a resume. Section
    spans are bounded by any recognized header of either map."""
    lines = jd_text.splitlines()
    combined = {**JD_SECTION_HEADERS, **JD_BENEFIT_HEADERS}
    headers = find_section_headers(lines, combined)
    drop = []
    for idx, (line_no, name) in enumerate(headers):
        if name != "benefits":
            continue
        end = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        drop.append((line_no, end))
    if not drop:
        return jd_text
    kept = [line for i, line in enumerate(lines) if not any(s <= i < e for s, e in drop)]
    return "\n".join(kept)


def _keyword_harvest_text(jd_text: str) -> str:
    """Harvest general keywords from requirement/responsibility/preferred
    sections when they exist (real keyword optimizers ignore marketing
    boilerplate); otherwise fall back to the benefit-stripped full text."""
    stripped = _strip_benefit_sections(jd_text)
    present = {
        name for _, name in find_section_headers(jd_text.splitlines(), JD_SECTION_HEADERS)
    }
    if present & {"required", "responsibilities", "preferred"}:
        parts = [
            _extract_jd_section_by(stripped, name, JD_SECTION_HEADERS)
            for name in ("required", "responsibilities", "preferred")
        ]
        joined = "\n".join(p for p in parts if p.strip())
        if joined.strip():
            return joined
    return stripped


def extract_jd_keywords(jd_text: str, jd_data: dict) -> list:
    """
    Build the weighted keyword checklist a keyword-parsing ATS would derive
    from this job description. Canonical skills always count (high weight,
    matched by name/alias); remaining frequent unigrams and bigrams add
    coverage for domain terms outside the skills database ("data pipelines",
    "stakeholder", ...).

    Terms are harvested line by line so a phrase is only counted when the two
    words genuinely sit next to each other in the JD ("large datasets" yes;
    "spark analyze" across a line break no). Deterministic output.
    """
    recognized = _recognized_terms_lower()
    stopwords = load_stopwords()
    keywords = {}

    # 1. canonical skills from the JD, heaviest weight
    for skill in jd_data.get("required_skills", []) + jd_data.get("preferred_skills", []):
        keywords.setdefault(skill.lower(), {"term": skill, "weight": 2.5, "is_skill": True, "count": 1})

    def harvestable(token: str) -> bool:
        return (
            len(token) > 1
            and token not in _GENERIC_TERMS
            and token not in stopwords
            and not token.startswith("skillterm_")
            and token.lower() not in recognized
            and normalize_skill(token) == token
        )

    # 2. frequency-based unigrams + bigrams; bigrams require true adjacency
    #    in the original text ("datasets and build" must not yield "datasets build")
    counts = Counter()
    for line in _keyword_harvest_text(jd_text).splitlines():
        tokens = clean_text(line).split()
        good = [t for t in tokens if harvestable(t)]
        counts.update(good)
        for first, second in zip(tokens, tokens[1:]):
            if harvestable(first) and harvestable(second):
                counts.update((f"{first} {second}",))

    for term, count in counts.most_common():
        lowered = term.lower()
        if lowered in keywords:
            continue
        if len(keywords) >= MAX_GENERAL_KEYWORDS:
            break
        weight = min(1.0 + 0.5 * (count - 1), 2.0)
        keywords[lowered] = {"term": term, "weight": weight, "is_skill": False, "count": count}

    return sorted(keywords.values(), key=lambda k: (-k["weight"], k["term"]))


# Common irregular resume verbs. Regular stemming ("build" -> "builded") is
# wrong for these, so each family is matched as an explicit alternation.
_IRREGULAR_FAMILIES = [
    ("build", ["build", "builds", "building", "built"]),
    ("lead", ["lead", "leads", "leading", "led"]),
    ("run", ["run", "runs", "running", "ran"]),
    ("make", ["make", "makes", "making", "made"]),
    ("grow", ["grow", "grows", "growing", "grew", "grown"]),
    ("drive", ["drive", "drives", "driving", "drove", "driven"]),
    ("write", ["write", "writes", "writing", "wrote", "written"]),
    ("win", ["win", "wins", "winning", "won"]),
    ("sell", ["sell", "sells", "selling", "sold"]),
    ("teach", ["teach", "teaches", "teaching", "taught"]),
    ("bring", ["bring", "brings", "bringing", "brought"]),
    ("hold", ["hold", "holds", "holding", "held"]),
    ("keep", ["keep", "keeps", "keeping", "kept"]),
    ("meet", ["meet", "meets", "meeting", "met"]),
    ("pay", ["pay", "pays", "paying", "paid"]),
    ("spend", ["spend", "spends", "spending", "spent"]),
    ("take", ["take", "takes", "taking", "took", "taken"]),
    ("give", ["give", "gives", "giving", "gave", "given"]),
    ("speak", ["speak", "speaks", "speaking", "spoke", "spoken"]),
    ("cut", ["cut", "cuts", "cutting"]),
    ("set", ["set", "sets", "setting"]),
    ("oversee", ["oversee", "oversees", "overseeing", "oversaw", "overseen"]),
    ("forecast", ["forecast", "forecasts", "forecasting"]),
]
_IRREGULAR_BY_STEM = {stem: forms for stem, forms in _IRREGULAR_FAMILIES}
_IRREGULAR_LOOKUP = {}
for _stem, _forms in _IRREGULAR_FAMILIES:
    for _form in _forms:
        _IRREGULAR_LOOKUP.setdefault(_form.lower(), _stem)


def _irregular_alternation(term: str) -> str | None:
    """Regex alternation of an irregular verb family ('build|builds|building|built'),
    or None when the term is not part of a known family."""
    stem_key = _IRREGULAR_LOOKUP.get(term.lower())
    if stem_key is None:
        return None
    return "|".join(re.escape(form) for form in _IRREGULAR_BY_STEM[stem_key])


def _inflection_pattern_str(term: str) -> str:
    """Regex body (without boundaries) that accepts inflections of one term.
    Phrases inflect each word separately, so 'analyzing datasets' matches
    'analyzed datasets' - the most common resume/JD wording mismatch."""
    if " " in term:
        parts = []
        for token in term.split():
            single = _inflection_pattern_str(token)
            # single-word bodies are already boundary-free alternations
            parts.append(single)
        return r"[\s]+".join(parts)
    alternation = _irregular_alternation(term)
    if alternation:
        return f"(?:{alternation})"
    if len(term) < 5:
        return re.escape(term)
    stem = term
    for suffix in ("ing", "ed", "es", "s"):
        if stem.endswith(suffix) and len(stem) - len(suffix) >= 4:
            stem = stem[: -len(suffix)]
            break
    base = f"{re.escape(stem)}(?:e?(?:s|d)?|ing)?"
    if stem.endswith("e"):
        # e-drop before -ing: "automate" -> "automating", "manage" -> "managing"
        return f"(?:{base}|{re.escape(stem[:-1])}ing)"
    return base


def _inflection_regex(term: str) -> re.Pattern:
    """Word-boundary matcher that accepts regular inflections of the term
    ('datasets' <-> 'dataset', 'automated' <-> 'automate/automating'), plus
    irregular verb families ('build' <-> 'built', 'lead' <-> 'led'), mirroring
    the stem matching real keyword parsers perform. Phrases inflect each word."""
    return re.compile(
        rf"(?<![A-Za-z0-9]){ _inflection_pattern_str(term) }(?![A-Za-z0-9])",
        re.IGNORECASE,
    )


def _keyword_in_resume(term: str, processed_resume: str, raw_resume_lower: str) -> bool:
    """Word-boundary match against both the lemmatized text and the raw text."""
    regex = re.compile(
        rf"(?<![A-Za-z0-9]){ _inflection_pattern_str(term) }(?![A-Za-z0-9])",
        re.IGNORECASE,
    )
    return bool(regex.search(processed_resume) or regex.search(raw_resume_lower))


def _token_set_present(term: str, processed_resume: str) -> bool:
    """True when every word of a multi-word term appears somewhere in the
    resume, in any order (e.g. 'analysis of data' vs the phrase 'data analysis')."""
    tokens = term.split()
    if len(tokens) < 2:
        return False
    return all(
        re.search(rf"(?<![A-Za-z0-9]){re.escape(t)}(?![A-Za-z0-9])", processed_resume, re.IGNORECASE)
        for t in tokens
    )


def _is_single_edit(a: str, b: str) -> bool:
    """True when b can be turned into a with exactly one edit: substitution,
    insertion, deletion, or adjacent transposition ("pyhton" -> "python") -
    transpositions being the most common real-world typo."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    for i, ch in enumerate(a):
        if ch != b[i]:
            if len(a) == len(b):
                if a[i + 1:] == b[i + 1:]:
                    return True  # substitution
                # adjacent transposition
                return (
                    i + 1 < len(a)
                    and a[i] == b[i + 1]
                    and a[i + 1] == b[i]
                    and a[i + 2:] == b[i + 2:]
                )
            return a[i:] == b[i + 1:]  # insertion in b
    return len(b) - len(a) == 1  # trailing insertion


def _find_typo_match(term: str, words_by_first_letter: dict) -> str | None:
    """Return the resume word that looks like a single-typo variant of term
    ('pyhton' for 'python'), or None. Conservative: single words of 6+
    characters, same first letter, length within 1."""
    if " " in term or len(term) < 6:
        return None
    for word in words_by_first_letter.get(term[0], ()):
        if word != term and abs(len(word) - len(term)) <= 1 and _is_single_edit(term, word):
            return word
    return None


@lru_cache(maxsize=32)
def _extract_jd_keywords_cached(jd_text: str) -> tuple:
    """Memoized variant keyed on the JD text alone: in production jd_data is
    always derived from the same text, and the classic workflow analyzes many
    resumes against one JD."""
    return tuple(extract_jd_keywords(jd_text, parse_job_description(jd_text)))


def compute_keyword_match(resume_text: str, jd_text: str, jd_data: dict, resume_data: dict,
                          profile: dict | None = None) -> dict:
    profile = profile or STRICTNESS_PROFILES["standard"]
    keywords = list(_extract_jd_keywords_cached(jd_text))
    if not keywords:
        return {"score": None, "detail": "No meaningful keywords could be extracted from the job description.",
                "matched": [], "missing": [], "partial": [], "typo_matches": []}

    processed_resume = preprocess_text(resume_text)
    raw_lower = resume_text.lower()
    resume_skills = {s.lower() for s in resume_data.get("skills", [])}

    words_by_first_letter = {}
    if profile["typo_matching"]:
        for word in set(re.findall(r"[a-z0-9]+", raw_lower)) | set(processed_resume.split()):
            words_by_first_letter.setdefault(word[0], []).append(word)

    matched, missing, partial, typo_matches = [], [], [], []
    for keyword in keywords:
        term = keyword["term"]
        if keyword["is_skill"] and term.lower() in resume_skills:
            matched.append(keyword)
            continue
        if _keyword_in_resume(term, processed_resume, raw_lower):
            matched.append(keyword)
            continue
        if _token_set_present(term, processed_resume):
            keyword = {**keyword, "weight": keyword["weight"] * profile["partial_credit_multiplier"]}
            partial.append(keyword)
            continue
        if profile["typo_matching"]:
            typo = _find_typo_match(term.lower(), words_by_first_letter)
            if typo:
                typo_matches.append({"term": term, "found_as": typo, "weight": keyword["weight"]})
                continue
        missing.append(keyword)

    total_weight = sum(k["weight"] for k in keywords)
    earned_weight = (
        sum(k["weight"] for k in matched)
        + sum(k["weight"] for k in partial)
        + sum(t["weight"] for t in typo_matches)
    )
    score = earned_weight / total_weight * 100 if total_weight else None

    detail_bits = [f"{len(matched)} of {len(keywords)} weighted keywords from the job description were found on the resume."]
    if partial:
        detail_bits.append(f"{len(partial)} more appear only in a different word form.")
    if typo_matches:
        detail_bits.append(f"{len(typo_matches)} matched despite a misspelling on the resume.")
    return {
        "score": score,
        "detail": " ".join(detail_bits),
        "matched": sorted(k["term"] for k in matched),
        "missing": sorted(missing, key=lambda k: -k["weight"]),
        "partial": sorted(partial, key=lambda k: -k["weight"]),
        "typo_matches": sorted(typo_matches, key=lambda t: -t["weight"]),
    }


# --------------------------------------------------------------------------
# factor 2: skills match
# --------------------------------------------------------------------------

def compute_skills_factor(match_result: dict | None, resume_data: dict, jd_data: dict) -> dict:
    skill_match = (match_result or {}).get("skill_match") or compute_skill_match(
        resume_data.get("skills", []),
        jd_data.get("required_skills", []),
        jd_data.get("preferred_skills", []),
    )
    required_score = skill_match.get("required_skill_score")
    preferred_score = skill_match.get("preferred_skill_score")

    if required_score is None and preferred_score is None:
        score = None
    elif required_score is None:
        score = preferred_score
    elif preferred_score is None:
        score = required_score
    else:
        score = 0.75 * required_score + 0.25 * preferred_score

    missing_required = skill_match.get("missing_required", [])
    missing_preferred = skill_match.get("missing_preferred", [])
    matched_required = skill_match.get("matched_required", [])

    suggestions = []
    if missing_required:
        top = missing_required[:6]
        suggestions.append(_suggestion(
            "high",
            f"Add these required skills to your Skills section (and evidence them in your experience bullets): "
            f"{', '.join(top)}.",
        ))
    if missing_preferred:
        top = missing_preferred[:4]
        suggestions.append(_suggestion(
            "medium",
            f"Nice-to-have skills worth adding if you have them: {', '.join(top)}.",
        ))

    detail = (
        f"{len(matched_required)} required skill(s) matched. "
        f"Required: {required_score if required_score is not None else 'n/a'}%, "
        f"Preferred: {preferred_score if preferred_score is not None else 'n/a'}%."
    )
    return {"score": score, "detail": detail, "suggestions": suggestions}


# --------------------------------------------------------------------------
# factor 3: job title match
# --------------------------------------------------------------------------

_TITLE_TOKENS_TO_DROP = {"a", "an", "the", "of", "and", "in", "for", "to"}


def _title_score(jd_title: str, candidate: str) -> float:
    jd_lower, cand_lower = jd_title.lower(), candidate.lower()
    ratio = SequenceMatcher(None, jd_lower, cand_lower).ratio() * 100
    jd_tokens = {t for t in re.split(r"[\s/,&+]+", jd_lower) if t not in _TITLE_TOKENS_TO_DROP}
    cand_tokens = {t for t in re.split(r"[\s/,&+]+", cand_lower) if t not in _TITLE_TOKENS_TO_DROP}
    overlap = (len(jd_tokens & cand_tokens) / len(jd_tokens) * 100) if jd_tokens else 0.0
    return max(ratio, overlap)


def compute_title_factor(resume_text: str, resume_data: dict, jd_data: dict) -> dict:
    jd_title = jd_data.get("job_title")
    resume_titles = resume_data.get("job_titles", [])

    if not jd_title or (not resume_titles and not resume_text):
        return {"score": None, "detail": "Could not compare job titles.", "suggestions": []}

    # The headline (first two lines) also counts: many resumes state a target title there.
    headline = " ".join(resume_text.splitlines()[:2])
    candidates = resume_titles + ([headline] if headline.strip() else [])
    jd_lower = jd_title.lower()

    best = 0.0
    for candidate in candidates:
        best = max(best, _title_score(jd_title, candidate))
    if re.search(r"(?<![a-z0-9])" + re.escape(jd_lower) + r"(?![a-z0-9])", resume_text.lower()):
        best = max(best, 95.0)

    suggestions = []
    if best < 60:
        suggestions.append(_suggestion(
            "high",
            f'Mirror the exact job title "{jd_title}" in your resume headline or most recent role title '
            f"(only if it honestly describes what you do).",
        ))
    elif best < 85:
        suggestions.append(_suggestion(
            "medium",
            f'Consider aligning your current role title with the posting\'s "{jd_title}" where truthful.',
        ))

    return {
        "score": best,
        "detail": f'Job title from the posting: "{jd_title}". Closest title on the resume scored {best:.0f}% similarity.',
        "suggestions": suggestions,
    }


# --------------------------------------------------------------------------
# factor 4: experience match
# --------------------------------------------------------------------------

def compute_experience_factor(resume_data: dict, jd_data: dict) -> dict:
    resume_years = resume_data.get("years_of_experience")
    required_years = jd_data.get("experience_requirement")

    if resume_years is None or required_years is None:
        detail_bits = []
        if resume_years is not None:
            detail_bits.append(f"Resume evidences ~{resume_years:g} year(s) of experience.")
        if required_years is not None:
            detail_bits.append(f"The job states ~{required_years:g} year(s).")
        return {
            "score": None,
            "detail": "Not enough information to compare experience. " + " ".join(detail_bits),
            "suggestions": [],
        }

    match = compute_experience_match(resume_years, required_years)
    score = match["score"]
    suggestions = []
    if score is not None and score < 80:
        suggestions.append(_suggestion(
            "high",
            f"The job asks for ~{required_years:g} year(s) of experience while your resume evidences ~{resume_years:g}. "
            f"Lead with your most relevant roles and quantify their impact.",
        ))

    from_dates = resume_data.get("experience_years_from_dates")
    reported = resume_data.get("experience_years_reported")
    if from_dates is not None and reported is not None and abs(from_dates - reported) > 1:
        detail = (
            f"{match['detail']} (Self-reported: ~{reported:g} yr(s); "
            f"computed from employment dates: ~{from_dates:g} yr(s).)"
        )
    else:
        detail = match["detail"]
    return {"score": score, "detail": detail, "suggestions": suggestions}


# --------------------------------------------------------------------------
# factor 5: education match
# --------------------------------------------------------------------------

def compute_education_factor(resume_data: dict, jd_data: dict) -> dict:
    match = compute_education_match(resume_data.get("education", []), jd_data.get("education_requirement"))
    suggestions = []
    if match["score"] is not None and match["score"] < 100:
        suggestions.append(_suggestion(
            "medium",
            "The job states an education requirement your resume does not clearly meet - "
            "make sure your Education section names the degree explicitly, and consider "
            "listing relevant coursework or certifications.",
        ))
    return {"score": match["score"], "detail": match["detail"], "suggestions": suggestions}


# --------------------------------------------------------------------------
# factor 6: format & parseability
# --------------------------------------------------------------------------

def compute_format_factor(resume_text: str, resume_data: dict, profile: dict | None = None) -> dict:
    profile = profile or STRICTNESS_PROFILES["standard"]
    checks = []
    suggestions = []

    def add_check(name, passed, points, suggestion=None, priority="high"):
        checks.append({"name": name, "passed": passed, "points": points if passed else 0})
        if not passed and suggestion:
            suggestions.append(_suggestion(priority, suggestion))

    add_check(
        "Email address", resume_data.get("email"), 10,
        "Add a plain-text email address near the top of the resume - ATS parsers key contact data off it.",
    )
    add_check(
        "Phone number", resume_data.get("phone"), 10,
        "Add a phone number in plain text (not inside a header, image, or table).",
    )
    add_check(
        "Name detected", bool(resume_data.get("name")), 10,
        "Put your full name as the first line of the document, as plain text.",
    )
    add_check(
        "Experience section", bool(resume_data.get("experience")) or bool(resume_data.get("experience_years_from_dates")), 15,
        'Add an experience section headed with a standard title like "Work Experience" or "Professional Experience".',
    )
    add_check(
        "Education section", bool(resume_data.get("education")), 10,
        'Add an education section headed "Education".',
    )
    add_check(
        "Skills section", bool(extract_section(resume_text, "skills")), 10,
        'Add a skills section headed "Skills" or "Technical Skills" - many ATS look for that exact header.',
    )

    experience_text = extract_section(resume_text, "experience")
    has_dates = bool(re.search(r"\b(?:19|20)\d{2}\b", experience_text)) if experience_text else False
    add_check(
        "Dates in experience", has_dates, 15,
        "Add employment dates (e.g. 'Jan 2021 - Present') to each role - ATS use them to compute tenure.",
    )

    word_count = len(resume_text.split())
    lo, hi = profile["length_band"]
    partial_lo, partial_hi = profile["length_partial_band"]
    if lo <= word_count <= hi:
        length_points = 10
        length_ok = True
    elif partial_lo <= word_count < lo or hi < word_count <= partial_hi:
        length_points = 6
        length_ok = True
    else:
        length_points = 0 if word_count < lo else 5
        length_ok = False
    checks.append({"name": "Resume length", "passed": length_ok, "points": length_points})
    if not length_ok:
        if word_count < lo:
            suggestions.append(_suggestion(
                "medium",
                f"The resume is short ({word_count} words). Aim for 350-800 words: add detail, "
                f"achievements, and projects rather than padding.",
            ))
        else:
            suggestions.append(_suggestion(
                "medium",
                f"The resume is long ({word_count} words). Trim to 350-1200 words - cut old or irrelevant roles.",
            ))

    suspicious = len(_SUSPICIOUS_CHARS.findall(resume_text))
    noise_ratio = suspicious / max(len(resume_text), 1)
    noise_points = 10 if noise_ratio < 0.001 else (5 if noise_ratio < 0.01 else 0)
    noise_ok = noise_points > 5
    checks.append({"name": "Clean text extraction", "passed": noise_ok, "points": noise_points})
    if not noise_ok:
        suggestions.append(_suggestion(
            "high",
            "The file extracts with garbled characters - an ATS may fail to read it. Re-export as a "
            "text-based PDF (not a scan) or a DOCX, without text boxes, images of text, or tables.",
        ))

    score = sum(c["points"] for c in checks)
    detail = f"{sum(1 for c in checks if c['passed'])} of {len(checks)} parser-friendliness checks passed ({word_count} words)."
    return {"score": score, "detail": detail, "suggestions": suggestions, "checks": checks}


# --------------------------------------------------------------------------
# factor 7: content quality
# --------------------------------------------------------------------------

def _content_items(resume_data: dict) -> list:
    """Lines actually evaluable as achievement bullets: excludes role header
    lines ("Data Analyst, Acme Corp") and tenure lines ("Jan 2020 - Mar 2022")
    that would otherwise pollute the quantification/verb statistics."""
    items = resume_data.get("experience") or resume_data.get("projects") or []
    result = []
    for item in items:
        stripped = BULLET_PREFIX_PATTERN.sub("", item).strip()
        words = stripped.split()
        if len(words) < 5:
            continue  # too short to be a bullet (role/company headers)
        if DATE_RANGE_PATTERN.fullmatch(stripped):
            continue  # tenure line
        if (
            TITLE_BEFORE_COMMA.match(stripped)
            and not DIGIT_PATTERN.search(stripped)
            and not any(w.lower().rstrip(".,") in ACTION_VERBS for w in words)
        ):
            continue  # "Data Analyst, Acme Corp" role header
        result.append(item)
    return result


def compute_content_factor(resume_data: dict, profile: dict | None = None) -> dict:
    profile = profile or STRICTNESS_PROFILES["standard"]
    items = _content_items(resume_data)
    suggestions = []

    if not items:
        return {
            "score": None,
            "detail": "No experience or project bullets were found to evaluate content quality.",
            "suggestions": [_suggestion(
                "high",
                "Add experience or project bullets (3-6 lines each) starting with action verbs and "
                "containing measurable results - ATS content scoring has nothing to reward otherwise.",
            )],
        }

    quantified = sum(1 for item in items if _has_real_metric(item))
    quantified_ratio = quantified / len(items)
    verb_items = sum(
        1 for item in items
        if BULLET_PREFIX_PATTERN.sub("", item).split() and
        BULLET_PREFIX_PATTERN.sub("", item).split()[0].lower().rstrip(".,") in ACTION_VERBS
    )
    verb_ratio = verb_items / len(items)
    first_person_count = len(FIRST_PERSON_PATTERN.findall(" ".join(items)))

    quant_score = min(quantified_ratio / profile["quantified_target"], 1.0) * 60
    verb_score = min(verb_ratio / profile["action_verb_target"], 1.0) * 30
    pronoun_score = 10 if first_person_count == 0 else (5 if first_person_count <= 2 else 0)
    score = quant_score + verb_score + pronoun_score

    if quantified_ratio < profile["quantified_target"]:
        suggestions.append(_suggestion(
            "high" if quantified_ratio < 0.2 else "medium",
            f"Only {quantified} of {len(items)} bullets contain a number. Quantify achievements with "
            f"metrics (%, $, latency, users, throughput) - ATS ranking and recruiters both weight this heavily.",
        ))
    if verb_ratio < 0.6:
        weak = [item.split()[0].strip(".,") for item in items
                if item.split() and item.split()[0].lower().rstrip(".,") not in ACTION_VERBS][:3]
        suggestions.append(_suggestion(
            "medium",
            f"Start bullets with strong action verbs (led, built, automated, reduced, launched...). "
            f"Weak openers spotted: {', '.join(weak)}.",
        ))
    if first_person_count > 2:
        suggestions.append(_suggestion(
            "low",
            f"Remove first-person pronouns (found {first_person_count}x). Resume convention drops 'I/my' - "
            f"start with the verb instead.",
        ))

    detail = (
        f"{quantified}/{len(items)} bullets quantified ({quantified_ratio:.0%}); "
        f"{verb_items}/{len(items)} start with action verbs ({verb_ratio:.0%}); "
        f"{first_person_count} first-person pronoun(s)."
    )
    return {"score": score, "detail": detail, "suggestions": suggestions}


# --------------------------------------------------------------------------
# standalone-only factors
# --------------------------------------------------------------------------

def compute_skills_richness_factor(resume_data: dict) -> dict:
    skills = resume_data.get("skills", [])
    if not skills:
        return {
            "score": 0.0,
            "detail": "No recognized skills were detected anywhere on the resume.",
            "suggestions": [_suggestion(
                "high",
                'Add a "Skills" section listing your concrete technologies and methods - none were detected.',
            )],
        }
    categories = skill_categories()
    distinct_categories = {categories.get(s, "Other") for s in skills}
    breadth = min(len(skills) / 12, 1.0) * 70
    diversity = min(len(distinct_categories) / 4, 1.0) * 30
    score = breadth + diversity
    suggestions = []
    if len(skills) < 12:
        suggestions.append(_suggestion(
            "medium",
            f"Only {len(skills)} recognized skill(s) detected. Name your key technologies explicitly "
            f"(frameworks, languages, tools, databases) - ATS keyword parsers match exact skill names.",
        ))
    detail = f"{len(skills)} recognized skills across {len(distinct_categories)} area(s)."
    return {"score": score, "detail": detail, "suggestions": suggestions}


def compute_education_presence_factor(resume_data: dict) -> dict:
    education = resume_data.get("education", [])
    if not education:
        return {
            "score": 0.0,
            "detail": "No education section was detected.",
            "suggestions": [_suggestion(
                "medium",
                'Add an "Education" section with your degree, institution, and graduation year '
                "(or list certifications if you have no degree).",
            )],
        }
    text = " ".join(education).lower()
    has_degree = any(kw in text for kw in ("b.tech", "btech", "b.e", "bachelor", "b.sc", "bsc",
                                           "m.tech", "mtech", "master", "m.sc", "msc", "mca", "mba",
                                           "phd", "ph.d", "doctorate", "diploma"))
    if has_degree:
        return {"score": 100.0, "detail": "Education section present with a recognizable degree.", "suggestions": []}
    return {
        "score": 60.0,
        "detail": "Education section present, but no recognizable degree name was found in it.",
        "suggestions": [_suggestion(
            "low",
            "Spell out the degree name (e.g. 'B.Tech in Computer Science') so ATS parsers recognize it.",
        )],
    }


# --------------------------------------------------------------------------
# public entry points
# --------------------------------------------------------------------------

# Factors a candidate can realistically fix (add missing keywords/skills,
# align the title, fix formatting) - these are capped at 100 for the
# "potential" estimate. Things like years of experience or a degree cannot
# be changed quickly and are left at their real score.
FIXABLE_FACTORS_JOB_MATCH = {"keywords", "skills", "title", "format"}
FIXABLE_FACTORS_STANDALONE = {"format", "skills", "education"}


def _potential_total(factors: list, weights: dict, fixable_keys: set) -> dict | None:
    """Honest upper bound on the ATS score: fixable factors are capped at
    100 (they describe changes the candidate can actually make), everything
    else keeps its real score. Returns None when there is nothing to gain."""
    available = {f["key"]: f["score"] for f in factors if f["available"]}
    if not available:
        return None
    potential_scores = {k: (100.0 if k in fixable_keys else v) for k, v in available.items()}
    total_weight = sum(weights[k] for k in potential_scores)
    potential = round(
        sum(potential_scores[k] * (weights[k] / total_weight) for k in potential_scores), 2
    ) if total_weight else None
    current, _ = _weighted_total(factors, weights)
    if potential is None or current is None or potential <= current + 0.05:
        return None
    return {
        "total": potential,
        "current": current,
        "note": "Upper bound if you add the missing keywords and skills, align your "
                "job title, and fix the formatting issues flagged below. Factors you "
                "cannot quickly change (experience, education, bullet history) keep "
                "their real score.",
    }


def _radar(factors: list) -> dict | None:
    """Server-computed SVG geometry for a radar/spider chart of the available
    factors (100-unit square viewBox, center 100,100, radius 78). Rendered
    without JavaScript so it is fully deterministic and testable."""
    available = [f for f in factors if f["available"]]
    n = len(available)
    if n < 3:
        return None
    cx = cy = 100.0
    radius = 78.0

    def point(angle_deg: float, r: float) -> tuple:
        angle = math.radians(angle_deg)
        return round(cx + r * math.cos(angle), 1), round(cy + r * math.sin(angle), 1)

    axes = []
    score_points = []
    for i, factor in enumerate(available):
        angle = -90 + (360.0 / n) * i  # start at top, clockwise
        x, y = point(angle, radius)
        axes.append({
            "label": factor["label"],
            "score": factor["score"],
            "x": x,
            "y": y,
            "anchor": "middle" if abs(x - cx) < 12 else ("start" if x > cx else "end"),
            "dy": -4 if y < cy - 10 else (10 if y > cy + 10 else 4),
        })
        score_points.append(point(angle, radius * (factor["score"] / 100.0)))

    rings = []
    for level in (25, 50, 75, 100):
        ring_pts = [point(-90 + (360.0 / n) * i, radius * level / 100.0) for i in range(n)]
        rings.append(" ".join(f"{x},{y}" for x, y in ring_pts))

    return {
        "axes": axes,
        "score_polygon": " ".join(f"{x},{y}" for x, y in score_points),
        "rings": rings,
        "labels": [f["label"] for f in available],
    }


def _assemble(mode: str, weights: dict, factors: list, fixable_keys: set | None = None) -> dict:
    total, excluded = _weighted_total(factors, weights)
    grade, grade_detail = _grade(total)

    suggestions = get_change_suggestions({"mode": mode, "factors": factors, "total": total})

    # Score composition: how many of the total points each factor contributed
    # (score x normalized weight) - rendered as a stacked bar.
    available = [f for f in factors if f["available"]]
    weight_sum = sum(f["weight"] for f in available) or 1.0
    composition = [
        {"label": f["label"], "points": f["score"] * f["weight"] / weight_sum}
        for f in available
    ]

    return {
        "mode": mode,
        "total": total,
        "grade": grade,
        "grade_detail": grade_detail,
        "factors": factors,
        "excluded_factors": excluded,
        "top_suggestions": suggestions[:5],
        "potential": _potential_total(factors, weights, fixable_keys or set()),
        "radar": _radar(factors),
        "composition": composition,
    }


def score_resume_vs_jd(resume_text: str, jd_text: str, resume_data: dict,
                       jd_data: dict, match_result: dict | None = None,
                       reference_date=None, strictness: str = "standard") -> dict:
    """Full 7-factor ATS score of a resume against one job description.

    strictness: "lenient" | "standard" | "strict" - selects the scoring
    profile (typo forgiveness, partial-credit weight, length band, quality
    targets). See STRICTNESS_PROFILES."""
    weights = config.ATS_WEIGHTS_JOB_MATCH
    profile = STRICTNESS_PROFILES[_normalize_strictness(strictness)]
    keyword_match = compute_keyword_match(resume_text, jd_text, jd_data, resume_data, profile=profile)
    keyword_suggestions = [
        _suggestion(
            "high" if i < 3 else "medium",
            f'The job description mentions "{k["term"]}"'
            + (f" {k['count']}x" if k["count"] > 1 else "")
            + ' but your resume never does. Work it in where honestly applicable '
              '(skills section, bullets, or summary).',
        )
        for i, k in enumerate(keyword_match["missing"][:6])
    ]
    keyword_suggestions += [
        _suggestion(
            "medium",
            f'You use the words of "{k["term"]}" but never the exact phrase - ATS exact-phrase '
            f'matching rewards the literal keyword "'
            + k["term"] + '" once your wording honestly allows it.',
        )
        for k in keyword_match.get("partial", [])[:3]
    ]
    keyword_suggestions += [
        _suggestion(
            "medium",
            f'Your resume spells it "{t["found_as"]}" but the job description says '
            f'"{t["term"]}" - fix the spelling so literal keyword parsers recognize it.',
        )
        for t in keyword_match.get("typo_matches", [])[:4]
    ]
    keywords_factor = _factor(
        "keywords", "Keyword coverage", keyword_match["score"], weights["keywords"],
        keyword_match["detail"], keyword_suggestions,
    )
    keywords_factor["missing_keywords"] = [k["term"] for k in keyword_match["missing"][:12]]
    keywords_factor["matched_keywords"] = keyword_match["matched"][:12]
    keywords_factor["coverage_counts"] = {
        "matched": len(keyword_match["matched"]),
        "partial": len(keyword_match.get("partial", [])),
        "typo": len(keyword_match.get("typo_matches", [])),
        "missing": len(keyword_match["missing"]),
    }

    skills = compute_skills_factor(match_result, resume_data, jd_data)
    skills_factor = _factor("skills", "Skills match", skills["score"], weights["skills"],
                            skills["detail"], skills["suggestions"])

    title = compute_title_factor(resume_text, resume_data, jd_data)
    title_factor = _factor("title", "Job title match", title["score"], weights["title"],
                           title["detail"], title["suggestions"])

    experience = compute_experience_factor(resume_data, jd_data)
    experience_factor = _factor("experience", "Experience match", experience["score"], weights["experience"],
                                experience["detail"], experience["suggestions"])

    education = compute_education_factor(resume_data, jd_data)
    education_factor = _factor("education", "Education match", education["score"], weights["education"],
                               education["detail"], education["suggestions"])

    fmt = compute_format_factor(resume_text, resume_data, profile)
    format_factor = _factor("format", "Format & parseability", fmt["score"], weights["format"],
                            fmt["detail"], fmt["suggestions"], fmt["checks"])

    content = compute_content_factor(resume_data, profile)
    content_factor = _factor("content", "Content quality", content["score"], weights["content"],
                             content["detail"], content["suggestions"])

    result = _assemble("job_match", weights, [
        keywords_factor, skills_factor, title_factor,
        experience_factor, education_factor, format_factor, content_factor,
    ], fixable_keys=FIXABLE_FACTORS_JOB_MATCH)

    # If the JD yielded no detectable requirements at all, every JD-dependent
    # factor was excluded and the score silently reflects resume quality only.
    # Surface that explicitly instead of letting it read as a real match score.
    jd_dependent = {"keywords", "skills", "title", "experience", "education"}
    if not any(f["key"] in jd_dependent and f["available"] for f in result["factors"]):
        result["jd_warning"] = (
            "The job description contained no detectable skills, requirements, "
            "experience, or education - the score below reflects resume quality "
            "only, not fit for a specific job."
        )
    return result


def score_resume_standalone(resume_text: str, resume_data: dict, strictness: str = "standard") -> dict:
    """ATS audit of a resume with no job description: parseability, content
    quality, skill breadth, and education presence."""
    weights = config.ATS_WEIGHTS_STANDALONE
    profile = STRICTNESS_PROFILES[_normalize_strictness(strictness)]

    fmt = compute_format_factor(resume_text, resume_data, profile)
    format_factor = _factor("format", "Format & parseability", fmt["score"], weights["format"],
                            fmt["detail"], fmt["suggestions"], fmt["checks"])

    content = compute_content_factor(resume_data, profile)
    content_factor = _factor("content", "Content quality", content["score"], weights["content"],
                             content["detail"], content["suggestions"])

    richness = compute_skills_richness_factor(resume_data)
    skills_factor = _factor("skills", "Skill breadth", richness["score"], weights["skills"],
                            richness["detail"], richness["suggestions"])

    education = compute_education_presence_factor(resume_data)
    education_factor = _factor("education", "Education present", education["score"], weights["education"],
                               education["detail"], education["suggestions"])

    return _assemble("standalone", weights, [
        format_factor, content_factor, skills_factor, education_factor,
    ], fixable_keys=FIXABLE_FACTORS_STANDALONE)


def get_change_suggestions(ats_result: dict, limit: int | None = None) -> list:
    """
    Flatten every factor's suggestions into one prioritized "what to change"
    list, ordered by priority then by potential overall-score gain (a factor's
    headroom times its weight). Each item carries the factor it came from.
    Near-duplicate advice coming from two different factors (e.g. the same
    missing skill flagged by both keyword and skills checks) is deduplicated.
    """
    priority_order = {"high": 0, "medium": 1, "low": 2}
    items = []
    seen_texts = set()
    for m in ats_result.get("ml_suggestions", []):
        dedupe_key = re.sub(r"[^a-z0-9]+", " ", m["text"].lower()).strip()
        if dedupe_key not in seen_texts:
            seen_texts.add(dedupe_key)
            items.append({
                "priority": m["priority"],
                "factor": "ML Optimization",
                "text": m["text"],
                "potential_gain": m.get("gain", 5.0),
            })

    for factor in ats_result.get("factors", []):
        headroom = max(0.0, 100.0 - (factor["score"] if factor["score"] is not None else 100.0))
        gain = round(headroom * factor["weight"], 1)
        for suggestion in factor.get("suggestions", []):
            dedupe_key = re.sub(r"[^a-z0-9]+", " ", suggestion["text"].lower()).strip()
            if dedupe_key in seen_texts:
                continue
            seen_texts.add(dedupe_key)
            items.append({
                "priority": suggestion["priority"],
                "factor": factor["label"],
                "text": suggestion["text"],
                "potential_gain": gain,
            })
    items.sort(key=lambda item: (priority_order.get(item["priority"], 3), -item["potential_gain"]))
    return items[:limit] if limit else items
