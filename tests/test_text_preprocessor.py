from services.text_preprocessor import clean_text, preprocess_text


def test_clean_text_preserves_technical_terms():
    text = "I know C++, C#, .NET, and Node.js very well."
    cleaned = clean_text(text)
    assert "skillterm_c_plus_plus" in cleaned
    assert "skillterm_c_sharp" in cleaned
    # ".NET" resolves to the canonical skill "ASP.NET", so the placeholder
    # spells out the full canonical name.
    assert "skillterm_asp_dot_net" in cleaned
    assert "skillterm_node_dot_js" in cleaned


def test_preprocess_text_removes_stopwords():
    processed = preprocess_text("This is a simple test of the preprocessing pipeline.")
    tokens = processed.split()
    assert "is" not in tokens
    assert "the" not in tokens
    assert "of" not in tokens


def test_preprocess_text_handles_empty_string():
    assert preprocess_text("") == ""


def test_preprocess_text_keeps_short_real_skills():
    # "R" and "Go" are real language names and must not be dropped as noise.
    processed = preprocess_text("I have experience with R and Go programming.")
    assert "r" in processed.split()
    assert "go" in processed.split()
