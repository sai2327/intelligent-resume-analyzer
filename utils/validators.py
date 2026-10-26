"""Input validation helpers shared across upload and text-paste routes."""

from werkzeug.datastructures import FileStorage

from utils.file_utils import allowed_file, get_extension


class ValidationError(Exception):
    """Raised when user-supplied input fails validation. Message is safe to show to the user."""


def validate_upload_file(
    file_storage: FileStorage | None,
    allowed_extensions: set[str],
    max_size_bytes: int,
) -> None:
    """
    Validate an uploaded file's presence, extension, and size.

    Flask's MAX_CONTENT_LENGTH already rejects oversized request bodies before
    this runs; the explicit size check here provides a clearer, user-facing
    error message for the common case of a single oversized file.
    """
    if file_storage is None or not file_storage.filename:
        raise ValidationError("No file was uploaded. Please choose a PDF or DOCX file.")

    if not allowed_file(file_storage.filename, allowed_extensions):
        extension = get_extension(file_storage.filename) or "(none)"
        raise ValidationError(
            f"Unsupported file type '.{extension}'. Allowed types: "
            f"{', '.join(sorted(allowed_extensions))}."
        )

    file_storage.stream.seek(0, 2)  # seek to end
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)

    if size == 0:
        raise ValidationError("The uploaded file is empty.")

    if size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValidationError(f"File is too large. Maximum allowed size is {max_mb:.0f} MB.")


def validate_text_input(text: str | None, field_name: str, min_length: int = 20) -> str:
    """Validate that pasted text input is present and reasonably long."""
    if text is None or not text.strip():
        raise ValidationError(f"{field_name} cannot be empty.")

    cleaned = text.strip()
    if len(cleaned) < min_length:
        raise ValidationError(
            f"{field_name} is too short to analyze meaningfully "
            f"(minimum {min_length} characters)."
        )
    return cleaned
