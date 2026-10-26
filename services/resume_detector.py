"""
Heuristic document detector: decides whether an uploaded file actually IS a
resume, and if not, what it probably is instead (cover letter, academic
report/thesis, letter, invoice...).

Resumes have a recognizable signature: contact info, standard sections,
employment dates, job titles, recognizable skills, degree names, bullets.
Other document types carry their own fingerprints (abstract/chapters/
references for academic writing, "Dear ... Sincerely" for letters, invoice
totals, ...). The detector scores the positive resume evidence, subtracts
foreign-document evidence, and returns a verdict with confidence:

    verdict:  "resume" | "likely_resume" | "uncertain" | "not_resume"

Only "not_resume" blocks analysis; weaker verdicts surface as warnings.
"""

import re

from services.information_extractor import (
    DATE_RANGE_PATTERN,
    extract_education,
    extract_email,
    extract_experience,
    extract_job_titles,
    extract_phone,
    extract_section,
)
from services.skill_matcher import find_skills_in_text

# Positive evidence for "this is a resume" (max points per signal).
SIGNAL_POINTS = {
    "email": 18,
    "phone": 14,
    "experience_section": 14,
    "education_section": 10,
    "skills_section": 10,
    "date_ranges": 10,
    "job_titles": 10,
    "canonical_skills": 12,
    "degree_named": 8,
    "summary_section": 4,
    "bullets": 6,
    "healthy_length": 8,
    "action_verb_openers": 6,
}

ACADEMIC_MARKERS = re.compile(
    r"\b(abstract|introduction|literature review|methodology|conclusion|"
    r"references|bibliography|appendix|table of contents|acknowledgement[s]?|"
    r"chapter\s+\d+|figure\s+\d+[.:)]|table\s+\d+[.:)]|paragraph\s+\d+)\b",
    re.IGNORECASE,
)
LETTER_MARKERS = re.compile(
    r"(dear\s+(sir|madam|sirs|ms\.?|mr\.?|dr\.?|hiring manager|recruiter|"
    r"selection committee))|to whom (it|soever) may concern|"
    r"respected\s+(sir|madam|sir\s*/\s*madam)|"
    r"\bto\s+the\s+(manager|hr|recruitment|hiring)\b|"
    r"\b(sincerely|yours (faithfully|truly)|thank you for (your )?consideration|"
    r"i am writing to (apply|express|enquire))\b",
    re.IGNORECASE,
)
INVOICE_MARKERS = re.compile(
    r"\b(invoice|amount due|total amount|subtotal|tax invoice|purchase order|"
    r"payment terms|gst|bill to)\b",
    re.IGNORECASE,
)

MARKER_FAMILIES = (
    ("academic report, thesis, or assignment", ACADEMIC_MARKERS, 30.0, 3),
    ("cover letter or formal letter", LETTER_MARKERS, 25.0, 2),
    ("invoice, bill, or receipt", INVOICE_MARKERS, 25.0, 2),
)

_MAX_WORDS_HEALTHY = 3000

_ACTION_VERB_START = re.compile(
    r"^[•▪◦‣·\-\*–]?\s*(led|managed|developed|designed|built|implemented|created|"
    r"improved|increased|reduced|optimized|automated|launched|delivered|drove|"
    r"owned|analyzed|researched|collaborated|coordinated|mentored|trained|"
    r"presented|wrote|maintained|integrated|tested|configured|administered|"
    r"established|introduced|spearheaded|organized|executed|generated|achieved)\b",
    re.IGNORECASE,
)


def _words(text: str) -> list:
    return re.findall(r"[A-Za-z0-9']+", text)


def _positive_signal_score(text: str) -> tuple:
    """Score resume-positive evidence; returns (score, hits, word_count)."""
    score = 0.0
    hits = []

    def add(name, condition):
        nonlocal score
        if condition:
            score += SIGNAL_POINTS[name]
            hits.append(name)

    add("email", extract_email(text) is not None)
    add("phone", extract_phone(text) is not None)
    add("experience_section", bool(extract_experience(text)))
    add("education_section", bool(extract_education(text)))
    skills_section = extract_section(text, "skills")
    add("skills_section", bool(skills_section))
    add("summary_section", bool(extract_section(text, "summary")))

    experience_text = extract_section(text, "experience")
    add("date_ranges", bool(experience_text) and bool(DATE_RANGE_PATTERN.search(experience_text)))

    add("job_titles", bool(extract_job_titles(text)))

    canonical = find_skills_in_text(text)
    add("canonical_skills", len(canonical) >= 3)

    education_text = " ".join(extract_education(text)).lower()
    add("degree_named", any(kw in education_text for kw in (
        "b.tech", "btech", "b.e", "bachelor", "b.sc", "bsc", "m.tech", "mtech",
        "master", "m.sc", "msc", "mca", "mba", "phd", "ph.d", "doctorate", "diploma")))

    bullets = [ln for ln in text.splitlines()
               if len(ln.split()) >= 5 and _ACTION_VERB_START.match(ln.strip())]
    add("bullets", len(bullets) >= 3)

    word_count = len(_words(text))
    add("healthy_length", 120 <= word_count <= _MAX_WORDS_HEALTHY)

    return score, hits, word_count


def _foreign_document_evidence(text: str) -> tuple:
    """Detect fingerprints of non-resume document types.
    Returns (total_penalty, matched_families, total_marker_count)."""
    penalty = 0.0
    matched = []
    total_markers = 0
    for label, pattern, cap, threshold in MARKER_FAMILIES:
        found = set(m.group(0).lower() for m in pattern.finditer(text))
        total_markers += len(found)
        if len(found) >= threshold:
            penalty += cap
            matched.append(label)
    return penalty, matched, total_markers


def looks_like_resume(text: str) -> dict:
    """Classify the document. Returns verdict, 0-100 confidence, the most
    likely non-resume document type (when applicable), and human-readable
    reasons for the decision."""
    if not text or not text.strip():
        return {"verdict": "not_resume", "confidence": 0.0, "document_type": None,
                "reasons": ["The document is empty."]}

    score, hits, word_count = _positive_signal_score(text)
    penalty, families, marker_count = _foreign_document_evidence(text)

    reasons = []
    if not hits:
        reasons.append("No resume features were found: no contact info, no standard sections, no recognizable skills.")
    elif "email" not in hits and "phone" not in hits:
        score -= 10.0
        reasons.append("No email address or phone number anywhere in the document - resumes virtually always carry contact info.")

    if word_count > _MAX_WORDS_HEALTHY:
        score -= 15.0
        reasons.append(f"The document is very long ({word_count} words) - far beyond resume length.")

    document_type = families[0] if families else None
    if families:
        reasons.append(f"The document contains characteristic {families[0]} content.")

    confidence = max(0.0, min(100.0, score - penalty))
    if 65 <= confidence < 100 and not families:
        confidence = min(100.0, confidence + (5.0 if len(hits) >= 6 else 0.0))

    if confidence >= 65:
        verdict = "resume"
    elif confidence >= 40:
        verdict = "likely_resume"
    elif confidence >= 20:
        verdict = "uncertain"
    else:
        verdict = "not_resume"

    if verdict != "resume" and not reasons:
        reasons.append(f"Only weak resume signals were detected (evidence score {confidence:.0f}%).")
    if verdict == "resume" and reasons:
        reasons = []  # no need to explain a confident pass

    return {
        "verdict": verdict,
        "confidence": round(confidence, 1),
        "document_type": document_type,
        "reasons": reasons,
    }


def rejection_message(detection: dict) -> str:
    """User-facing rejection text for a not_resume verdict."""
    type_bit = f" It appears to be a {detection['document_type']}." if detection.get("document_type") else ""
    reasons = " ".join(detection.get("reasons", []))
    return (
        "This does not look like a resume"
        f" (resume confidence: {detection['confidence']:.0f}%).{type_bit} "
        f"{reasons} Please upload an actual resume (PDF or DOCX)."
    )
