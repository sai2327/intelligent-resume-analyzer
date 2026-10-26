"""
Reusable NLP preprocessing pipeline shared by resume analysis, job
description analysis, TF-IDF vectorization, and classification.

Pipeline: clean_text -> tokenize_text -> remove_stopwords -> lemmatize_tokens

Technical terms that contain symbols or are multi-word phrases (C++, C#,
.NET, Node.js, CI/CD, REST API, Machine Learning, ...) are protected with
placeholder tokens BEFORE punctuation stripping so they survive the pipeline
intact instead of being mangled (e.g. "C++" and "C#" both collapsing to a
bare "c"). Human-readable skill extraction for the UI is handled separately
by services/skill_matcher.py, which matches directly against the raw text.
"""

import json
import re
from functools import lru_cache

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

from config import config

_lemmatizer = WordNetLemmatizer()

_SYMBOL_WORDS = {"+": "plus", "#": "sharp", ".": "dot", "/": "slash", "-": "dash"}


def _make_safe_token(term: str) -> str:
    """Turn a technical term into a single underscore-joined alphanumeric
    token (e.g. 'C++' -> 'skillterm_c_plus_plus') that survives whitespace
    and punctuation-based tokenization intact."""
    chars = []
    for ch in term.lower():
        if ch.isalnum():
            chars.append(ch)
        elif ch in _SYMBOL_WORDS:
            chars.append(f"_{_SYMBOL_WORDS[ch]}_")
        else:
            chars.append("_")
    safe = re.sub(r"_+", "_", "".join(chars)).strip("_")
    return f"skillterm_{safe}"


@lru_cache(maxsize=1)
def _load_skills_data() -> dict:
    with open(config.SKILLS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _term_to_canonical() -> dict:
    """Lowercased surface form (canonical skill or alias) -> canonical skill name."""
    data = _load_skills_data()
    mapping: dict[str, str] = {}
    for skills in data.get("categories", {}).values():
        for skill in skills:
            mapping[skill.lower()] = skill
    for alias, canonical in data.get("aliases", {}).items():
        mapping[alias.lower()] = canonical
    return mapping


@lru_cache(maxsize=1)
def _protected_terms_sorted() -> tuple:
    """Surface forms that punctuation-stripping would mangle (contain a
    symbol, or are multi-word phrases), longest-first for greedy matching."""
    terms = list(_term_to_canonical().keys())
    protected = [t for t in terms if (" " in t) or re.search(r"[^a-z0-9 ]", t)]
    return tuple(sorted(protected, key=len, reverse=True))


@lru_cache(maxsize=1)
def _compiled_protection_patterns() -> tuple:
    """Compiled (pattern, placeholder) pairs, built once and cached."""
    term_to_canonical = _term_to_canonical()
    patterns = []
    for term in _protected_terms_sorted():
        placeholder = _make_safe_token(term_to_canonical[term])
        pattern = re.compile(
            r"(?<![A-Za-z0-9.])" + re.escape(term) + r"(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        patterns.append((pattern, placeholder))
    return tuple(patterns)


def _protect_technical_terms(text: str) -> str:
    for pattern, placeholder in _compiled_protection_patterns():
        text = pattern.sub(placeholder, text)
    return text


@lru_cache(maxsize=1)
def _load_stopwords() -> frozenset:
    return frozenset(stopwords.words("english"))


def load_stopwords() -> frozenset:
    """Public accessor for the English stopword set (shared by the ATS
    keyword extractor so both modules filter identically)."""
    return _load_stopwords()


@lru_cache(maxsize=256)
def clean_text(text: str) -> str:
    """Protect technical terms, lowercase, strip URLs/emails/punctuation, collapse whitespace.
    Cached: the same resume text is preprocessed by both the classifier and the
    matching engine in a single request, so the regex passes run only once."""
    if not text:
        return ""
    text = text.replace("\r", " ").replace("\n", " ")
    text = _protect_technical_terms(text)
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+", " ", text)
    text = re.sub(r"[^a-z0-9_\s]", " ", text)  # underscores kept: they carry protected placeholders
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_text(text: str) -> list:
    """Tokenize already-cleaned text into words."""
    return word_tokenize(text)


def remove_stopwords(tokens: list) -> list:
    """Drop common English stopwords (kept as an explicit list, not a length filter,
    so short real skills like 'R' or 'C' are not accidentally discarded)."""
    stop_words = _load_stopwords()
    return [t for t in tokens if t not in stop_words]


def lemmatize_tokens(tokens: list) -> list:
    """Reduce tokens to their dictionary/base form. Unknown tokens (including
    protected placeholders) are returned unchanged by WordNetLemmatizer."""
    return [_lemmatizer.lemmatize(t) for t in tokens]


# WordNet POS tags for the lemmatizer, derived from NLTK's penn-treebank tags.
_PENNB_TO_WORDNET = {
    "J": "a",  # adjective
    "V": "v",  # verb
    "R": "r",  # adverb
}


def lemmatize_tokens_pos(tokens: list) -> list:
    """POS-aware lemmatization: derive each token's part of speech and pass it
    to WordNet. Nouns stay the default path; verbs/adjectives/adverbs lemmatize
    correctly ("managed" -> "manage", "analyzed" -> "analyze", "improved" ->
    "improve") instead of staying inflected, which materially improves keyword
    and TF-IDF matching between resumes and job descriptions."""
    if not tokens:
        return []
    tagged = nltk.pos_tag(tokens)
    lemmatized = []
    for token, tag in tagged:
        wordnet_pos = _PENNB_TO_WORDNET.get(tag[:1])
        lemmatized.append(
            _lemmatizer.lemmatize(token, wordnet_pos) if wordnet_pos
            else _lemmatizer.lemmatize(token)
        )
    return lemmatized


@lru_cache(maxsize=256)
def preprocess_text(text: str) -> str:
    """Full pipeline producing a single cleaned, lemmatized string ready for TF-IDF.
    Cached because tokenization + lemmatization dominate request latency and the
    same text is frequently preprocessed more than once per request."""
    cleaned = clean_text(text)
    tokens = tokenize_text(cleaned)
    tokens = remove_stopwords(tokens)
    tokens = lemmatize_tokens_pos(tokens)
    return " ".join(tokens)


def ensure_nltk_resources_available() -> list:
    """Check required NLTK resources are present. Returns a list of missing
    resource names (empty list means everything needed is installed)."""
    required = {
        "tokenizers/punkt_tab": "punkt_tab",
        "corpora/stopwords": "stopwords",
        "corpora/wordnet": "wordnet",
    }
    missing = []
    for path, name in required.items():
        try:
            nltk.data.find(path)
        except LookupError:
            missing.append(name)
    return missing
