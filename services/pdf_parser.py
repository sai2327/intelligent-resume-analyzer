"""PDF text extraction using pypdf. Accepts a file path or an in-memory file-like object."""

import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PDFExtractionError(Exception):
    """Raised when a PDF file cannot be read or contains no extractable text."""


# Some PDF fonts/layouts extract with every character separated by a space
# ("C o n t a c t", "k . u m a r i @ g m a i l . c o m"), which destroys all
# downstream matching. Within such segments, real word boundaries appear as
# runs of 2+ spaces, so: split on multi-space runs, collapse segments that
# are mostly single-character tokens, rejoin.
_CHAR_SPACED_SEGMENT = re.compile(r"\S+(?: \S+)*")


def _collapse_char_spaced_segment(segment: str) -> str:
    tokens = segment.split(" ")
    if len(tokens) < 2:
        return segment
    single = sum(1 for token in tokens if len(token) == 1)
    # Mostly single-character tokens => char-spaced word ("C o n t a c t").
    # A run of ONLY single characters is always collapsed ("M e" -> "Me",
    # "S Q L" -> "SQL"); longer mixed segments need the 60% majority.
    if single == len(tokens) or (len(tokens) >= 4 and single / len(tokens) >= 0.6):
        return "".join(tokens)
    return segment


def _normalize_char_spaced(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if " " in line:
            segments = re.split(r"(?<=\S)  +(?=\S)", line)  # split on 2+ space runs
            line = " ".join(_collapse_char_spaced_segment(seg) for seg in segments)
        lines.append(line)
    return "\n".join(lines)


def extract_text_from_pdf(file) -> str:
    """Extract all text from a PDF, page by page. `file` may be a path string
    or a file-like object (e.g. an uploaded file's stream) - uploads are never
    written to disk."""
    try:
        reader = PdfReader(file)
    except PdfReadError as exc:
        raise PDFExtractionError(f"The PDF file is corrupt or unreadable: {exc}") from exc
    except Exception as exc:
        raise PDFExtractionError(f"Could not open PDF file: {exc}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")  # try an empty password first, as some exports use this
        except Exception:
            pass
        if reader.is_encrypted:
            raise PDFExtractionError(
                "This PDF is password-protected. Please upload an unprotected file."
            )

    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            text_parts.append("")

    full_text = _normalize_char_spaced("\n".join(text_parts)).strip()
    if not full_text:
        raise PDFExtractionError(
            "No extractable text was found in this PDF. It may be a scanned "
            "image without a text layer (OCR is not supported)."
        )
    return full_text
