"""Shared pytest fixtures: in-memory sample resume PDF/DOCX bytes and JD text."""

import io

import pytest
from docx import Document
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app import app as flask_app
from config import config
from database import database

SAMPLE_RESUME_TEXT_LINES = [
    "John A. Doe",
    "Email: john.doe@example.com | Phone: +1-555-123-4567",
    "SUMMARY",
    "Motivated Software Developer with 3 years of professional experience.",
    "SKILLS",
    "Python, JavaScript, React, Node.js, REST API, Git, MySQL, Docker",
    "EDUCATION",
    "B.Tech in Computer Science, National Institute of Technology, 2021",
    "EXPERIENCE",
    "Worked as a Software Developer at TechNova Solutions for 3 years, "
    "responsible for designing and implementing REST APIs.",
    "PROJECTS",
    "Built an e-commerce order management system using Python and React.",
    "CERTIFICATIONS",
    "Meta Back-End Developer Certificate",
]

SAMPLE_JD_TEXT = """Job Title: Software Developer

REQUIREMENTS
3+ years of experience in software development.
Bachelor's degree in Computer Science or related field.
Strong proficiency in Python and JavaScript.
Experience with React and Node.js.
Experience with MySQL.

PREFERRED SKILLS
Experience with AWS.
Experience with Kubernetes.

RESPONSIBILITIES
Design and implement scalable backend services.
Write unit tests and participate in code reviews.
"""


@pytest.fixture
def sample_resume_text() -> str:
    return "\n".join(SAMPLE_RESUME_TEXT_LINES)


@pytest.fixture
def sample_jd_text() -> str:
    return SAMPLE_JD_TEXT


@pytest.fixture
def sample_resume_pdf_bytes() -> bytes:
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = [Paragraph(line, styles["Normal"]) for line in SAMPLE_RESUME_TEXT_LINES]
    doc.build(story)
    return buffer.getvalue()


@pytest.fixture
def sample_resume_docx_bytes() -> bytes:
    buffer = io.BytesIO()
    document = Document()
    for line in SAMPLE_RESUME_TEXT_LINES:
        document.add_paragraph(line)
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def academic_pdf_bytes():
    lines = [
        "University ERP System - Final Document", "Abstract",
        "This document describes the analysis and design of the ERP system.",
        "Table of Contents", "Chapter 1: Introduction", "1.1 Purpose",
        "The purpose of this document is to define the requirements.",
        "Chapter 2: System Analysis", "Figure 1: Use case diagram",
        "Chapter 3: Conclusion", "In conclusion the design satisfies all requirements.",
        "References", "[1] Sommerville, Software Engineering, 2016.",
    ]
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    doc.build([Paragraph(line, styles["Normal"]) for line in lines])
    return buffer.getvalue()


@pytest.fixture
def app(tmp_path):
    # Route tests must never write to the developer's real app.db.
    config.DATABASE_PATH = str(tmp_path / "test.db")
    database.init_db()
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
