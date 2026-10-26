"""
Generic section-splitting for semi-structured documents (resumes, job
descriptions). Detects header lines (e.g. "EDUCATION", "Required Skills")
from a caller-supplied keyword map and slices the text between consecutive
headers. Shared by services/information_extractor.py and
services/job_description_parser.py so both use identical splitting logic.
"""

import re


def find_section_headers(lines: list, header_map: dict) -> list:
    """
    header_map: section_name -> list of recognized header phrases (lowercase,
    letters/spaces/ampersand only).
    Returns [(line_index, section_name), ...] in document order.
    """
    headers = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 40:
            continue
        normalized = re.sub(r"[^a-z& ]", "", stripped.lower()).strip()
        for section_name, keywords in header_map.items():
            if normalized in keywords:
                headers.append((i, section_name))
                break
    return headers


def extract_section(text: str, section_name: str, header_map: dict) -> str:
    """Return the raw text between section_name's header and the next
    detected header (or end of document). Returns '' if not found."""
    lines = text.splitlines()
    headers = find_section_headers(lines, header_map)
    for idx, (line_no, name) in enumerate(headers):
        if name == section_name:
            start = line_no + 1
            end = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
            section_lines = [ln.strip() for ln in lines[start:end] if ln.strip()]
            return "\n".join(section_lines)
    return ""


def split_into_items(section_text: str) -> list:
    """Split a section's text into individual bullet/line items."""
    if not section_text:
        return []
    raw_items = re.split(r"\n+", section_text)
    cleaned = [re.sub(r"^[•▪◦\-\*]\s*", "", item).strip() for item in raw_items]
    return [item for item in cleaned if item]
