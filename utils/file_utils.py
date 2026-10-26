"""Small filename helpers used for upload validation. Uploaded resume/job
description files are processed entirely in memory and never written to
disk (see services/document_parser.py), so no file-saving helpers live here."""

from pathlib import Path


def get_extension(filename: str) -> str:
    """Return the lowercase extension of a filename, without the dot."""
    return Path(filename).suffix.lower().lstrip(".")


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check whether a filename has one of the allowed extensions."""
    if not filename or "." not in filename:
        return False
    return get_extension(filename) in allowed_extensions
