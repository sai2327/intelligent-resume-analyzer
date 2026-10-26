"""
Centralized skill matching against the canonical skills database
(data/skills.json). Used by BOTH resume information extraction and job
description parsing so skill names are normalized identically on both sides
(e.g. "ReactJS" on a resume and "React.js" in a job description both resolve
to the single canonical name "React").
"""

import json
import re
from functools import lru_cache

from config import config


@lru_cache(maxsize=1)
def _load_skills_data() -> dict:
    with open(config.SKILLS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _term_to_canonical() -> dict:
    """Lowercased surface form (canonical skill or alias) -> canonical skill name."""
    data = _load_skills_data()
    mapping: dict[str, str] = {}
    for skills in data.get("categories", {}).values():
        for skill in skills:
            mapping[skill.lower()] = skill
    for alias, canonical in data.get("aliases", {}).items():
        mapping[alias.lower()] = canonical
    return mapping


@lru_cache(maxsize=1)
def all_canonical_skills() -> list:
    """Sorted list of every distinct canonical skill name in the database."""
    data = _load_skills_data()
    names = set()
    for skills in data.get("categories", {}).values():
        names.update(skills)
    return sorted(names)


@lru_cache(maxsize=1)
def skill_categories() -> dict:
    """canonical skill name -> category name."""
    data = _load_skills_data()
    mapping = {}
    for category, skills in data.get("categories", {}).items():
        for skill in skills:
            mapping[skill] = category
    return mapping


@lru_cache(maxsize=1)
def _compiled_patterns() -> tuple:
    """Compiled (pattern, canonical_name) pairs, longest surface form first
    so multi-word phrases are matched before shorter overlapping ones."""
    term_to_canonical = _term_to_canonical()
    terms_sorted = sorted(term_to_canonical.keys(), key=len, reverse=True)
    patterns = []
    for term in terms_sorted:
        # A preceding dot is excluded from the boundary: "Node.js" must not
        # trigger the alias "js" -> JavaScript (same for Next.js, Express.js...).
        pattern = re.compile(
            r"(?<![A-Za-z0-9.])" + re.escape(term) + r"(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        patterns.append((pattern, term_to_canonical[term]))
    return tuple(patterns)


def normalize_skill(raw_skill: str) -> str:
    """Resolve a raw skill string (canonical or alias, any case) to its
    canonical name. Returns the trimmed input unchanged if it is not a
    recognized skill or alias."""
    cleaned = raw_skill.strip()
    return _term_to_canonical().get(cleaned.lower(), cleaned)


@lru_cache(maxsize=128)
def find_skills_in_text(text: str) -> list:
    """Scan raw text and return a sorted, deduplicated list of canonical
    skill names mentioned in it. Matching is case-insensitive with strict
    boundaries so e.g. 'Java' does not match inside 'JavaScript'. Cached:
    resumes and JDs are scanned repeatedly within a request (whole text +
    section slices), and the same JD is re-parsed for every resume analyzed
    against it."""
    if not text:
        return []
    found = set()
    for pattern, canonical in _compiled_patterns():
        if pattern.search(text):
            found.add(canonical)
    return sorted(found)


def categorize_skills(skills: list) -> dict:
    """Group a list of canonical skill names by their category (unknown
    skills are grouped under 'Other')."""
    categories = skill_categories()
    grouped: dict[str, list] = {}
    for skill in skills:
        category = categories.get(skill, "Other")
        grouped.setdefault(category, []).append(skill)
    return grouped
