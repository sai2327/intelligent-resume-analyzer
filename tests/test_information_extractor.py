from services.information_extractor import (
    extract_certifications,
    extract_education,
    extract_email,
    extract_experience,
    extract_phone,
    extract_projects,
    extract_years_of_experience,
)


def test_extract_email(sample_resume_text):
    assert extract_email(sample_resume_text) == "john.doe@example.com"


def test_extract_phone(sample_resume_text):
    phone = extract_phone(sample_resume_text)
    assert phone is not None
    assert "555" in phone


def test_extract_education_section(sample_resume_text):
    education = extract_education(sample_resume_text)
    assert any("National Institute of Technology" in item for item in education)


def test_extract_experience_section(sample_resume_text):
    experience = extract_experience(sample_resume_text)
    assert any("TechNova Solutions" in item for item in experience)


def test_extract_projects_section(sample_resume_text):
    projects = extract_projects(sample_resume_text)
    assert any("e-commerce" in item for item in projects)


def test_extract_certifications_section(sample_resume_text):
    certifications = extract_certifications(sample_resume_text)
    assert any("Meta" in item for item in certifications)


def test_extract_years_of_experience(sample_resume_text):
    assert extract_years_of_experience(sample_resume_text) == 3.0


def test_extract_years_of_experience_returns_none_when_absent():
    assert extract_years_of_experience("No experience figures mentioned here.") is None
