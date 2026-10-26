"""
Unit tests for the Machine Learning Resume Suggestion & Correction Engine (services/ml_suggester.py).
Tests all 10 ML diagnostic capabilities matching top commercial ATS platforms (Jobscan, Rezi, Resume Worded).
"""

import pytest

from services import ml_suggester


SAMPLE_TECH_RESUME = """John Doe
john.doe@example.com | +1 555-0199

SUMMARY
Results-driven software engineer and dedicated team player with a proven track record.

TECHNICAL SKILLS
Languages: Python, JavaScript, SQL
Tools & Platforms: Docker, Kubernetes, AWS, Git, React

PROFESSIONAL EXPERIENCE
Senior Software Engineer - Tech Solutions Inc.
January 2021 - Present
- Responsible for writing backend APIs in Python and Django
- Worked on optimizing SQL database query performance
- Helped with container deployments and infrastructure configuration
- Assisted in bug fixing and issue resolution across microservices

EDUCATION
Bachelor of Science in Computer Science, University of Technology, 2020
"""


def test_empty_resume_returns_empty():
    assert ml_suggester.generate_deep_ml_suggestions("") == []
    assert ml_suggester.generate_deep_ml_suggestions(None) == []


def test_feature_gap_analysis():
    # Target category Software Developer
    suggestions = ml_suggester.analyze_model_feature_gap(
        "Basic resume with no tech terms",
        target_category="Software Developer",
        max_suggestions=3,
    )
    assert isinstance(suggestions, list)
    for s in suggestions:
        assert "[ML Feature Gap]" in s["text"]
        assert s["priority"] in {"high", "medium", "low"}
        assert "gain" in s
        assert s["gain"] > 0


def test_keyword_stuffing_detection():
    # Artificially repeat "python" to create > 3.5% density
    stuffed_resume = "Software Developer. " + "Python python python " * 30 + " developing web apps."
    suggestions = ml_suggester.analyze_keyword_stuffing_and_density_ml(stuffed_resume)
    assert len(suggestions) > 0
    assert any("[ML Keyword Over-Optimization]" in s["text"] for s in suggestions)
    assert any("python" in s["text"].lower() for s in suggestions)


def test_contextual_placement_detection():
    # Docker and Kubernetes are in the skills list, but not in work experience
    resume = """
    SUMMARY
    Senior Engineer
    SKILLS
    Docker, Kubernetes, Python
    WORK EXPERIENCE
    Software Engineer at Acme
    - Built web services using Python
    EDUCATION
    B.S. CS 2020
    """
    suggestions = ml_suggester.analyze_section_context_placement_ml(
        resume,
        resume_skills=["Docker", "Kubernetes", "Python"],
    )
    assert len(suggestions) > 0
    assert any("[ML Contextual Experience Deficit]" in s["text"] for s in suggestions)
    joined = " ".join(s["text"] for s in suggestions)
    assert "Docker" in joined or "Kubernetes" in joined


def test_buzzword_dilution_detection():
    text = "A results-driven team player with a proven track record and dynamic professional."
    suggestions = ml_suggester.analyze_buzzword_and_filler_dilution_ml(text)
    assert len(suggestions) > 0
    assert any("[ML Signal-to-Noise Dilution]" in s["text"] for s in suggestions)


def test_parser_safety_glyphs():
    text = "Experience:\n* Deployed app\n\u2605 Star performer\n| | | table artifact"
    suggestions = ml_suggester.analyze_parser_safety_and_glyph_hygiene_ml(text)
    assert len(suggestions) > 0
    assert any("[ML ATS Parser Safety]" in s["text"] for s in suggestions)


def test_section_structure_missing_headers():
    text = "Just a plain text block without standard section headers."
    suggestions = ml_suggester.analyze_section_structure_ml(text)
    assert len(suggestions) >= 2
    assert any("[ML Structural Architecture]" in s["text"] for s in suggestions)


def test_resume_length_deficiency():
    text = "Short text with only ten words total in the resume."
    suggestions = ml_suggester.analyze_ats_length_and_density_ml(text)
    assert len(suggestions) == 1
    assert "[ML Resume Length Deficiency]" in suggestions[0]["text"]


def test_action_verbs_optimization():
    text = "- Responsible for building APIs\n- Worked on database tuning"
    suggestions = ml_suggester.analyze_action_verbs_ml(text)
    assert len(suggestions) > 0
    assert any("[ML Action Verb Optimization]" in s["text"] for s in suggestions)


def test_bullet_quantification():
    text = """
    EXPERIENCE
    Software Engineer
    - Developed backend services for customers without any metrics
    - Designed database tables and schemas for the internal application
    - Handled customer tickets and issues during release cycles
    """
    suggestions = ml_suggester.analyze_bullet_quantification_ml(text)
    assert len(suggestions) > 0
    assert any("[ML Impact Quantification]" in s["text"] for s in suggestions)


def test_generate_deep_ml_suggestions_master():
    suggestions = ml_suggester.generate_deep_ml_suggestions(
        SAMPLE_TECH_RESUME,
        target_category="Software Developer",
        resume_skills=["Docker", "Kubernetes", "AWS", "Python"],
    )
    assert len(suggestions) > 0
    # Must have priority and gain
    for s in suggestions:
        assert s["priority"] in {"high", "medium", "low"}
        assert "text" in s
        assert "gain" in s

    # Priorities must be sorted high -> medium -> low
    p_order = {"high": 0, "medium": 1, "low": 2}
    ranks = [p_order[s["priority"]] for s in suggestions]
    assert ranks == sorted(ranks)
