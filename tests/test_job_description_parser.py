from services.job_description_parser import parse_job_description


def test_parse_job_description_splits_required_and_preferred(sample_jd_text):
    jd_data = parse_job_description(sample_jd_text)
    assert "Python" in jd_data["required_skills"]
    assert "AWS" in jd_data["preferred_skills"]
    assert "AWS" not in jd_data["required_skills"]


def test_parse_job_description_extracts_experience_and_education(sample_jd_text):
    jd_data = parse_job_description(sample_jd_text)
    assert jd_data["experience_requirement"] == 3.0
    assert jd_data["education_requirement"] is not None
    assert "bachelor" in jd_data["education_requirement"].lower()


def test_parse_job_description_extracts_responsibilities(sample_jd_text):
    jd_data = parse_job_description(sample_jd_text)
    assert len(jd_data["responsibilities"]) >= 1


def test_parse_job_description_with_no_sections_treats_all_as_required():
    jd_data = parse_job_description("This role requires Python and SQL experience.")
    assert "Python" in jd_data["required_skills"]
    assert jd_data["preferred_skills"] == []
