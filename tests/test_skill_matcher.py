from services.skill_matcher import find_skills_in_text, normalize_skill


def test_find_skills_detects_canonical_and_alias_forms():
    text = "Experienced with ReactJS, Node.js, and machine learning projects."
    skills = find_skills_in_text(text)
    assert "React" in skills
    assert "Node.js" in skills
    assert "Machine Learning" in skills


def test_find_skills_does_not_false_positive_substring():
    text = "I am highly skilled in JavaScript development."
    skills = find_skills_in_text(text)
    assert "JavaScript" in skills
    assert "Java" not in skills


def test_find_skills_empty_text_returns_empty_list():
    assert find_skills_in_text("") == []


def test_normalize_skill_resolves_alias():
    assert normalize_skill("reactjs") == "React"
    assert normalize_skill("k8s") == "Kubernetes"
    assert normalize_skill("UnknownSkillXYZ") == "UnknownSkillXYZ"
