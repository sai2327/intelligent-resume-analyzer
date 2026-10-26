"""Tests for the resume detector: real resumes must pass; academic papers,
cover letters, invoices, and gibberish must be identified and rejected."""

import pytest

from services.resume_detector import looks_like_resume, rejection_message

REAL_RESUME = """Jane Smith
Email: jane@example.com | Phone: 555-123-4567

SUMMARY
Data Analyst with 4 years of experience.

SKILLS
Python, SQL, Tableau, Machine Learning

EXPERIENCE
Data Analyst, Acme Corp
Jan 2020 - Mar 2022
- Analyzed customer data and built 12 dashboards in Tableau
- Reduced reporting time by 40% using Python automation

EDUCATION
B.Tech in Computer Science, XYZ University, 2019
"""

ACADEMIC_DOC = """Final University ERP OOAD Document

Abstract
This document describes the analysis and design of a University ERP system.

Table of Contents
1. Introduction
2. System Analysis

Chapter 1: Introduction
1.1 Purpose
The purpose of this document is to define the requirements of the ERP system.

Chapter 2: System Analysis
Figure 1: Use case diagram of the registration module
Table 4: Functional requirements

Chapter 3: Design
3.1 Class Diagram
The class diagram models students, courses, and faculty.

Chapter 4: Conclusion
In conclusion, the ERP system design satisfies all requirements.

References
[1] Sommerville, Software Engineering, 2016.
"""

COVER_LETTER = """Dear Hiring Manager,

I am writing to apply for the Data Analyst position at your company. I have
three years of experience and I am very excited about this opportunity.

Thank you for your consideration.

Sincerely,
John Doe
john.doe@example.com
"""

INVOICE = """INVOICE #2043
Bill to: Acme Corp
Subtotal: 500.00
Tax: 90.00
Amount Due: 590.00
Payment terms: Net 30
"""


def test_real_resume_passes_with_high_confidence():
    detection = looks_like_resume(REAL_RESUME)
    assert detection["verdict"] == "resume"
    assert detection["confidence"] >= 65
    assert detection["document_type"] is None
    assert detection["reasons"] == []


def test_academic_document_rejected_with_type():
    detection = looks_like_resume(ACADEMIC_DOC)
    assert detection["verdict"] == "not_resume"
    assert "academic" in detection["document_type"]
    msg = rejection_message(detection)
    assert "does not look like a resume" in msg
    assert "academic" in msg


def test_cover_letter_detected_as_letter():
    detection = looks_like_resume(COVER_LETTER)
    assert detection["verdict"] == "not_resume"
    assert "cover letter" in detection["document_type"]


def test_invoice_rejected():
    detection = looks_like_resume(INVOICE)
    assert detection["verdict"] == "not_resume"
    assert "invoice" in detection["document_type"]


def test_minimal_but_valid_document_is_not_blocked():
    # Small legitimate resume-like text must NOT be rejected outright.
    minimal = """Bob Brown
bob@x.com
555-999-8888
Worked as a cashier at Store X for 2 years.
High school diploma, 2015.
"""
    detection = looks_like_resume(minimal)
    assert detection["verdict"] in {"uncertain", "likely_resume", "resume"}


def test_empty_and_gibberish_rejected():
    assert looks_like_resume("")["verdict"] == "not_resume"
    assert looks_like_resume("hello world")["verdict"] == "not_resume"


def test_resumes_without_email_get_contact_penalty():
    no_contact = REAL_RESUME.replace("Email: jane@example.com | Phone: 555-123-4567\n", "")
    d_with = looks_like_resume(REAL_RESUME)
    d_without = looks_like_resume(no_contact)
    assert d_without["confidence"] < d_with["confidence"]
    assert d_without["verdict"] in {"resume", "likely_resume"}  # still resume-ish


@pytest.mark.parametrize("text", [ACADEMIC_DOC, INVOICE])
def test_rejection_message_contains_confidence(text):
    msg = rejection_message(looks_like_resume(text))
    assert "resume confidence" in msg
    assert "Please upload an actual resume" in msg


def test_indian_application_letter_rejected():
    """Real-world pattern: formal Indian application letters open with
    'Respected sir' / 'To The Manager' instead of 'Dear Hiring Manager'."""
    letter = """To
The Manager,

Respected sir,

I am great pleasure to introduce myself as a Diploma Mechanical Engineer with
above 24 Years of experience in Mechanical Maintenance department. At present
I am working as Engineer (Mechanical dept.) at AM Green ammonia private LTD.
Hands on experience of Corrective maintenance and Trouble shutting of
Mechanical rotating Equipment.

I am here with furnishing my curriculum vitae for your kind consideration.

Contact: +91 8099990333
"""
    detection = looks_like_resume(letter)
    assert detection["verdict"] in {"not_resume", "uncertain"}
    assert detection["document_type"] and "cover letter" in detection["document_type"]
