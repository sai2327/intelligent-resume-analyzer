import io

import pytest

from services.docx_parser import DOCXExtractionError, extract_text_from_docx
from services.document_parser import DocumentParsingError, extract_text
from services.pdf_parser import PDFExtractionError, extract_text_from_pdf


def test_extract_text_from_pdf_bytes(sample_resume_pdf_bytes):
    text = extract_text_from_pdf(io.BytesIO(sample_resume_pdf_bytes))
    assert "Software Developer" in text
    assert "Python" in text


def test_extract_text_from_docx_bytes(sample_resume_docx_bytes):
    text = extract_text_from_docx(io.BytesIO(sample_resume_docx_bytes))
    assert "Software Developer" in text


def test_extract_text_from_pdf_corrupt_raises():
    with pytest.raises(PDFExtractionError):
        extract_text_from_pdf(io.BytesIO(b"not a real pdf"))


def test_extract_text_from_docx_corrupt_raises():
    with pytest.raises(DOCXExtractionError):
        extract_text_from_docx(io.BytesIO(b"not a real docx"))


def test_document_parser_dispatches_by_extension(sample_resume_pdf_bytes):
    text = extract_text(io.BytesIO(sample_resume_pdf_bytes), "pdf")
    assert "Python" in text


def test_document_parser_unsupported_extension_raises(sample_resume_pdf_bytes):
    with pytest.raises(DocumentParsingError):
        extract_text(io.BytesIO(sample_resume_pdf_bytes), "txt")


def test_char_spaced_pdf_text_is_normalized():
    """Some PDFs extract with every character space-separated ("C o n t a c t"),
    destroying email/section/skill detection. The parser must collapse such
    segments while leaving normal text untouched."""
    from services.pdf_parser import _normalize_char_spaced

    assert _normalize_char_spaced("C o n t a c t") == "Contact"
    assert _normalize_char_spaced("A b o u t  M e") == "About Me"
    assert _normalize_char_spaced("k u m a r i 3 3 3 @ g m a i l . c o m") == "kumari333@gmail.com"
    assert _normalize_char_spaced("+ 9 1 8 0 9 9 9 9 0 3 3 3") == "+918099990333"
    assert _normalize_char_spaced("P R O G R A M M I N G  L A N G U A G E S :   C , C + +") == \
        "PROGRAMMING LANGUAGES: C,C++"
    # Normal prose must never be mangled.
    assert _normalize_char_spaced("I am a C developer with R skills") == \
        "I am a C developer with R skills"
    assert _normalize_char_spaced(
        "Led a team of 3 analysts and reduced reporting time by 35%") == \
        "Led a team of 3 analysts and reduced reporting time by 35%"


def test_char_spaced_resume_is_detected_and_scored():
    """End-to-end: a char-spaced resume must be recognized as a resume with
    its contact info and skills recovered."""
    from services.information_extractor import extract_all
    from services.pdf_parser import _normalize_char_spaced
    from services.resume_detector import looks_like_resume

    spaced = "\n".join([
        "K U M A R I  G N A N E S W A R I",
        "k u m a r i 3 3 3 @ g m a i l . c o m",
        "+ 9 1 8 0 9 9 9 9 0 3 3 3",
        "S K I L L S",
        "P R O G R A M M I N G  L A N G U A G E S :   C , C + +   a n d   P y t h o n",
        "E D U C A T I O N",
        "B . T e c h  C o m p u t e r  S c i e n c e ,  A d i t y a  U n i v e r s i t y ,  2 0 2 8",
        "E X P E R I E N C E",
        "P r o b l e m  S o l v e r ,  L e e t c o d e",
        "J a n  2 0 2 4  -  P r e s e n t",
        "- S o l v e d  1 2 5 0 +  p r o b l e m s  w i t h  a  1 7 0 0 +  r a t i n g",
        "- B u i l t  5  p r o j e c t s  u s i n g  H T M L  a n d  C S S",
    ])
    text = _normalize_char_spaced(spaced)
    detection = looks_like_resume(text)
    assert detection["verdict"] in {"resume", "likely_resume"}
    data = extract_all(text)
    assert data["email"] == "kumari333@gmail.com"
    assert "Python" in data["skills"]
    assert "C++" in data["skills"]
