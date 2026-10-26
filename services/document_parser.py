"""Unified document text extraction, dispatching by an explicit file extension."""

from services.docx_parser import DOCXExtractionError, extract_text_from_docx
from services.pdf_parser import PDFExtractionError, extract_text_from_pdf

SUPPORTED_EXTENSIONS = {"pdf", "docx"}


class UnsupportedFileTypeError(Exception):
    """Raised when a file extension is not supported."""


class DocumentParsingError(Exception):
    """User-safe wrapper for any document parsing failure."""


def extract_text(file, extension: str) -> str:
    """
    Extract text from a PDF or DOCX source. `file` may be a path string or a
    file-like object (e.g. an uploaded file's stream, never written to disk);
    `extension` must be supplied explicitly (e.g. 'pdf'). Raises
    DocumentParsingError on any failure.
    """
    extension = extension.lower().lstrip(".")
    try:
        if extension == "pdf":
            return extract_text_from_pdf(file)
        if extension == "docx":
            return extract_text_from_docx(file)
        raise UnsupportedFileTypeError(
            f"Unsupported file type '.{extension}'. Supported types: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
        )
    except (PDFExtractionError, DOCXExtractionError, UnsupportedFileTypeError) as exc:
        raise DocumentParsingError(str(exc)) from exc
