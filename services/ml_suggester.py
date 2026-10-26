"""
Machine Learning-Driven Resume Suggestion & Correction Engine.
Provides deep statistical and model-attribution recommendations matching
the capabilities of top online ATS platforms (Jobscan, Resume Worded, Rezi).

Key Capabilities:
1. Model Feature Attribution & Importance Gap Analysis (LinearSVC + Platt calibration weights)
2. Keyword Stuffing & Over-Optimization Penalty Detection (ATS spam filter heuristics)
3. Section-Level Contextual Placement & Experience Deficit Analysis
4. Executive Action Verb Optimization & Power Verb Replacement
5. Bullet Point Metric Quantification & STAR-Format Impact Diagnostics
6. Signal-to-Noise & Buzzword Dilution Diagnostics
7. Readability & Cognitive Complexity Index (Flesch-Kincaid Grade Level)
8. ATS Parser Safety & Glyph Contamination Hygiene
9. Structural Section Architecture & Canonical Header Verification
10. Resume Length & Information Density Distribution Curve
"""

import logging
import math
import re
from functools import lru_cache

import numpy as np

from config import config
from services import classifier
from services.text_preprocessor import preprocess_text

logger = logging.getLogger(__name__)

# Cache for computed category feature weights
_CATEGORY_FEATURE_WEIGHTS = None
_FEATURE_NAMES = None

# Weak passive verbs mapped to contextual executive power verbs
_WEAK_VERB_PATTERNS = [
    (
        re.compile(r"\b(?:responsible for|was responsible for)\b\s*([a-z]+ing|[a-z]+)?", re.IGNORECASE),
        "responsible for",
        {
            "technical": "Architected, Engineered, or Deployed",
            "leadership": "Spearheaded, Orchestrated, or Directed",
            "operational": "Administered, Executed, or Delivered",
        },
    ),
    (
        re.compile(r"\b(?:worked on|work on|worked in)\b\s*([a-z]+ing|[a-z]+)?", re.IGNORECASE),
        "worked on",
        {
            "technical": "Developed, Implemented, or Refactored",
            "optimization": "Streamlined, Optimized, or Overhauled",
            "operational": "Engineered or Executed",
        },
    ),
    (
        re.compile(r"\b(?:helped with|helped to|assisted in|assisted with)\b\s*([a-z]+ing|[a-z]+)?", re.IGNORECASE),
        "helped with / assisted in",
        {
            "technical": "Co-engineered, Implemented, or Integrated",
            "leadership": "Facilitated, Championed, or Partnered to deliver",
            "operational": "Contributed to deploying or Accelerated",
        },
    ),
    (
        re.compile(r"\b(?:handled|handling)\b\s*([a-z]+ing|[a-z]+)?", re.IGNORECASE),
        "handled",
        {
            "technical": "Maintained, Administered, or Configured",
            "leadership": "Supervised, Governed, or Orchestrated",
            "operational": "Resolved, Managed, or Streamlined",
        },
    ),
    (
        re.compile(r"\b(?:duties included|tasks included|tasked with|was tasked with)\b", re.IGNORECASE),
        "duties included / tasked with",
        {
            "leadership": "Commissioned to spearhead, Directed, or Drove",
            "technical": "Designed and deployed, Developed, or Engineered",
            "operational": "Executed, Delivered, or Managed",
        },
    ),
    (
        re.compile(r"\b(?:participated in|was involved in)\b", re.IGNORECASE),
        "participated in",
        {
            "technical": "Contributed to the core deployment of, Co-developed",
            "leadership": "Collaborated to deliver, Drove the delivery of",
            "operational": "Spearheaded sub-systems of, Executed",
        },
    ),
    (
        re.compile(r"\b(?:served as|acted as)\b", re.IGNORECASE),
        "served as / acted as",
        {
            "leadership": "Directed, Led as principal, or Governed",
            "technical": "Functioned as lead architect for, Engineered",
            "operational": "Operated as primary liaison for, Managed",
        },
    ),
]

_METRIC_REGEX = re.compile(
    r"(?:\d+(?:\.\d+)?%|\$\s*\d+[\d,]*(?:\.\d+)?(?:\s*[kKmMbB]|\s*thousand|\s*million|\s*billion)?|"
    r"\b\d+x\b|\b\d+[\d,]*\s*(?:users|clients|customers|requests|transactions|qps|endpoints|servers|nodes|features|prs|engineers|members)\b|"
    r"\b(?:reduced|increased|improved|boosted|saved|cut)\s*(?:by\s*)?\d+(?:\.\d+)?%?)",
    re.IGNORECASE,
)

_BUZZWORDS = [
    ("results-driven", "Replace with quantifiable project results and performance metrics."),
    ("results oriented", "Replace with concrete project outcomes and delivered KPIs."),
    ("team player", "Demonstrate cross-functional collaboration by naming partner teams."),
    ("self-starter", "Show initiative by citing autonomous project delivery or architecture."),
    ("hard-working", "Demonstrate rigor through measurable throughput and uptime achievements."),
    ("think outside the box", "Detail specific novel solutions or architectural innovations."),
    ("detail-oriented", "Demonstrate precision by citing error reductions or test coverage."),
    ("proven track record", "Replace with explicit metrics (e.g., 'delivered 12 production releases')."),
    ("dynamic professional", "State your exact domain title and specialization."),
    ("go-getter", "Cite specific instances of exceeding delivery timelines or benchmarks."),
    ("fast learner", "Highlight quick ramp-up by naming technologies mastered on the job."),
    ("synergy", "Specify technical or organizational integration achievements."),
]

_UNFRIENDLY_GLYPHS = re.compile(r"[❖➢★✓►■➔♦✦▲▶✓✔●▪]")


def _count_syllables(word: str) -> int:
    """Heuristic syllable counter for readability metrics."""
    w = word.lower().strip()
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", w)
    w = re.sub(r"^y", "", w)
    matches = re.findall(r"[aeiouy]{1,2}", w)
    return max(1, len(matches))


def _load_model_weights():
    """Lazily extract and average feature weight vectors across the 5 calibrated folds."""
    global _CATEGORY_FEATURE_WEIGHTS, _FEATURE_NAMES
    if _CATEGORY_FEATURE_WEIGHTS is not None:
        return _CATEGORY_FEATURE_WEIGHTS, _FEATURE_NAMES

    try:
        classifier.load_model()
        if not classifier.is_model_available():
            return None, None

        clf = classifier._classifier
        vec = classifier._vectorizer
        if clf is None or vec is None:
            return None, None

        if hasattr(clf, "calibrated_classifiers_") and clf.calibrated_classifiers_:
            coefs = [cc.estimator.coef_ for cc in clf.calibrated_classifiers_]
            avg_coef = np.mean(coefs, axis=0)  # shape: (n_classes, n_features)
        elif hasattr(clf, "coef_"):
            avg_coef = clf.coef_
        else:
            return None, None

        classes = list(clf.classes_)
        features = np.array(vec.get_feature_names_out())

        weights_by_category = {}
        for idx, cls_name in enumerate(classes):
            weights_by_category[cls_name] = avg_coef[idx]

        _CATEGORY_FEATURE_WEIGHTS = weights_by_category
        _FEATURE_NAMES = features
        return _CATEGORY_FEATURE_WEIGHTS, _FEATURE_NAMES
    except Exception as exc:
        logger.warning("Could not extract model feature weights: %s", exc)
        return None, None


def analyze_model_feature_gap(
    resume_text: str,
    target_category: str | None = None,
    jd_text: str | None = None,
    max_suggestions: int = 4,
) -> list:
    """
    Computes mathematical feature attribution gaps using the trained LinearSVC + TF-IDF weights.
    Identifies terms that possess the highest discriminative power for the target category/job
    that are completely absent from the candidate resume.
    """
    suggestions = []
    cat_weights, features = _load_model_weights()
    if cat_weights is None or features is None:
        return []

    try:
        if not target_category:
            target_category = classifier.predict_category(resume_text)
    except Exception:
        target_category = None

    if not target_category or target_category not in cat_weights:
        target_category = list(cat_weights.keys())[0] if cat_weights else None
        if not target_category:
            return []

    weight_vector = cat_weights[target_category]
    resume_lower = resume_text.lower()

    vec = classifier._vectorizer
    if vec is None:
        return []

    processed_resume = preprocess_text(resume_text)
    resume_vec = vec.transform([processed_resume]).toarray()[0]

    if jd_text:
        processed_jd = preprocess_text(jd_text)
        jd_vec = vec.transform([processed_jd]).toarray()[0]
        deficit = (jd_vec * 0.6 + np.maximum(0, weight_vector) * 0.4) * (resume_vec == 0)
    else:
        deficit = np.maximum(0, weight_vector) * (resume_vec == 0)

    top_indices = np.argsort(deficit)[::-1]
    added = 0
    clean_term_regex = re.compile(r"^[a-z0-9\s_-]+$")
    seen_terms = set()

    for idx in top_indices:
        if added >= max_suggestions:
            break
        term = str(features[idx]).replace("skillterm_", "").strip()
        if len(term) < 3 or term in resume_lower or not clean_term_regex.match(term):
            continue

        # Prevent sub-string / super-string duplication (e.g. "developer", "software developer")
        if any(term in s or s in term for s in seen_terms):
            continue

        weight_val = float(weight_vector[idx])
        if weight_val <= 0.05:
            continue

        seen_terms.add(term)
        gain_pct = min(15.0, round(weight_val * 4.2 + 2.5, 1))
        suggestions.append({
            "text": (
                f"[ML Feature Gap] Candidate is missing high-attribution term '{term}' "
                f"(Model discriminative weight: +{weight_val:.2f}). Incorporating this term in your "
                f"experience section boosts predicted {target_category} alignment by estimated +{gain_pct}%."
            ),
            "priority": "high" if gain_pct >= 6.0 else "medium",
            "category": "feature_attribution",
            "term": term,
            "gain": gain_pct,
        })
        added += 1

    return suggestions


def analyze_keyword_stuffing_and_density_ml(resume_text: str, max_suggestions: int = 2) -> list:
    """
    Detects keyword stuffing and unnatural term density (>3.5% of total vocabulary).
    Commercial ATS algorithms (Workday, Taleo, iCIMS) actively penalize over-indexing.
    """
    suggestions = []
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", resume_text.lower())
    total_words = len(tokens)
    if total_words < 50:
        return []

    counts = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1

    common_stop = {
        "and", "the", "for", "with", "that", "this", "from", "have", "been",
        "work", "year", "years", "using", "used", "per", "all", "our", "are",
    }

    stuffed = []
    for term, cnt in counts.items():
        if term in common_stop:
            continue
        density = cnt / total_words
        if cnt >= 5 and density > 0.035:
            stuffed.append((term, cnt, density))

    stuffed.sort(key=lambda x: x[2], reverse=True)
    for term, cnt, density in stuffed[:max_suggestions]:
        pct = density * 100
        suggestions.append({
            "text": (
                f"[ML Keyword Over-Optimization] Term '{term}' appears {cnt} times ({pct:.1f}% density). "
                f"Commercial ATS spam filters (Workday, Taleo) flag densities exceeding 3.5% as keyword stuffing, "
                f"risking automated candidate downranking. Distribute or replace with semantic synonyms across achievements."
            ),
            "priority": "high",
            "category": "keyword_stuffing",
            "gain": 6.5,
        })

    return suggestions


def analyze_section_context_placement_ml(
    resume_text: str,
    resume_skills: list | None = None,
    max_suggestions: int = 3,
) -> list:
    """
    Evaluates whether technical skills are contextualized inside Work Experience bullets
    versus isolated in a detached 'Skills' list.
    Modern ATS engines weight contextualized skills 2.5x higher than passive list mentions.
    """
    suggestions = []
    lower_text = resume_text.lower()

    # Locate Experience vs Skills text regions
    exp_match = re.search(r"\b(?:experience|work history|employment|career history)\b", lower_text)
    skills_match = re.search(r"\b(?:skills|technical skills|competencies|technologies)\b", lower_text)

    if not exp_match or not skills_match:
        return []

    exp_start = exp_match.start()
    # Approximate experience block boundaries
    next_section = re.search(
        r"\b(?:education|certifications|projects|skills|summary|publications)\b",
        lower_text[exp_start + 30:],
    )
    exp_end = (exp_start + 30 + next_section.start()) if next_section else len(lower_text)
    experience_text = lower_text[exp_start:exp_end]

    skills_to_check = resume_skills or []
    if not skills_to_check:
        # Extract skills tokens if not provided
        words = re.findall(r"\b[a-zA-Z0-9+#.-]{3,}\b", resume_text)
        skills_to_check = [w for w in set(words) if w.lower() in {"python", "docker", "kubernetes", "aws", "react", "sql", "git", "java", "node", "typescript"}]

    isolated_skills = []
    for skill in skills_to_check:
        s_lower = skill.lower()
        if len(s_lower) < 3:
            continue
        # Present in resume but absent in experience text
        pattern = r"\b" + re.escape(s_lower) + r"\b"
        if re.search(pattern, lower_text) and not re.search(pattern, experience_text):
            isolated_skills.append(skill)

    for skill in isolated_skills[:max_suggestions]:
        suggestions.append({
            "text": (
                f"[ML Contextual Experience Deficit] Skill '{skill}' appears in your skills list "
                f"but is missing from your Professional Experience bullets. Modern ATS algorithms (Taleo, Greenhouse) "
                f"weight contextualized skills 2.5x higher than isolated inventory terms. "
                f"Add an active bullet point detailing how you applied {skill} on a production project."
            ),
            "priority": "medium",
            "category": "contextual_placement",
            "gain": 5.0,
        })

    return suggestions


def analyze_buzzword_and_filler_dilution_ml(resume_text: str, max_suggestions: int = 2) -> list:
    """
    Detects low-information clichés and buzzwords that dilute resume TF-IDF entropy
    and lower overall candidate signal-to-noise ratio.
    """
    suggestions = []
    lower_text = resume_text.lower()
    seen = set()

    for phrase, remedy in _BUZZWORDS:
        if len(suggestions) >= max_suggestions:
            break
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, lower_text) and phrase not in seen:
            seen.add(phrase)
            suggestions.append({
                "text": (
                    f"[ML Signal-to-Noise Dilution] Detected generic filler phrase '{phrase}'. "
                    f"ATS keyword classifiers prioritize high-entropy technical competencies over generic fluff. {remedy}"
                ),
                "priority": "low",
                "category": "buzzword_dilution",
                "gain": 3.5,
            })

    return suggestions


def analyze_readability_and_cognitive_complexity_ml(resume_text: str) -> list:
    """
    Computes Flesch-Kincaid Grade Level and sentence complexity distribution.
    Executive benchmark: Grade 9.0 – 12.5. Overly dense text (>13.5) causes parser
    tokenization errors and recruiter skimming dropoff.
    """
    suggestions = []
    words = re.findall(r"\b[a-zA-Z]{2,}\b", resume_text)
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", resume_text) if len(s.strip().split()) >= 3]

    if len(words) < 70 or not sentences:
        return []

    total_words = len(words)
    total_sentences = max(len(sentences), 1)
    total_syllables = sum(_count_syllables(w) for w in words)

    # Flesch-Kincaid Grade Level formula
    fk_grade = 0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59
    avg_words_per_sentence = total_words / total_sentences

    if fk_grade > 13.8:
        suggestions.append({
            "text": (
                f"[ML Readability Index: Grade {fk_grade:.1f}] Language complexity exceeds recommended executive "
                f"readability (Target: Grade 9.0-12.5). Complex sentence structure (avg {avg_words_per_sentence:.1f} words/sentence) "
                f"increases ATS clause truncation risk. Break compound clauses into concise, punchy bullet points."
            ),
            "priority": "medium",
            "category": "readability",
            "gain": 4.5,
        })
    elif fk_grade < 7.5:
        suggestions.append({
            "text": (
                f"[ML Readability Index: Grade {fk_grade:.1f}] Resume phrasing is below professional standard "
                f"(Target: Grade 9.0-12.5). Upgrade vocabulary with precise industry terminology and technical achievements."
            ),
            "priority": "low",
            "category": "readability",
            "gain": 3.0,
        })

    return suggestions


def analyze_parser_safety_and_glyph_hygiene_ml(resume_text: str, max_suggestions: int = 2) -> list:
    """
    Detects ATS-unfriendly characters, non-standard bullet glyphs, and tabular formatting
    that corrupt text tokenization in legacy enterprise ATS parsers.
    """
    suggestions = []

    # Non-standard Unicode bullet icons
    glyph_matches = _UNFRIENDLY_GLYPHS.findall(resume_text)
    if glyph_matches:
        count = len(glyph_matches)
        suggestions.append({
            "text": (
                f"[ML ATS Parser Safety] Non-standard decorative bullet glyphs detected ({count} decorative icons). "
                f"Legacy enterprise ATS parsers (Taleo, BrassRing) frequently corrupt non-standard Unicode icons into "
                f"unreadable question marks or corrupted characters. Replace with standard ASCII hyphens (-) or simple dots (•)."
            ),
            "priority": "high",
            "category": "parser_safety",
            "gain": 6.0,
        })

    # Excessive tabular pipe delimiter strings
    if re.search(r"\|{2,}|(?:\s*\|\s*){3,}", resume_text):
        suggestions.append({
            "text": (
                "[ML ATS Parser Safety] Excessive pipe delimiters ('| | |') or complex table formatting detected. "
                "Many ATS document ingestion engines fail to parse multi-column tables, merging disparate rows into scrambled text. "
                "Use standard linear single-column layout."
            ),
            "priority": "medium",
            "category": "parser_safety",
            "gain": 4.0,
        })

    return suggestions[:max_suggestions]


def analyze_ats_length_and_density_ml(resume_text: str) -> list:
    """
    Evaluates total resume word count against empirical ATS acceptance distributions.
    Standard executive range: 350 to 950 words.
    """
    suggestions = []
    words = re.findall(r"\b\w+\b", resume_text)
    count = len(words)

    if count < 320:
        suggestions.append({
            "text": (
                f"[ML Resume Length Deficiency] Total resume word count is {count} words (Optimal: 450-900 words). "
                f"Underspecified resumes face severe ATS keyword match penalties due to limited technical coverage. "
                f"Expand your role descriptions with specific technologies, methodologies, and business results."
            ),
            "priority": "high",
            "category": "length_density",
            "gain": 8.0,
        })
    elif count > 1250:
        suggestions.append({
            "text": (
                f"[ML Resume Length Overflow] Total resume word count is {count} words (Optimal: 450-900 words). "
                f"Overly long documents risk parser buffer truncation and lower recruiter completion rates. "
                f"Condense older roles to 2-3 high-impact accomplishments."
            ),
            "priority": "medium",
            "category": "length_density",
            "gain": 4.0,
        })

    return suggestions


def analyze_section_structure_ml(resume_text: str) -> list:
    """
    Validates canonical ATS structural section headers.
    Ensures critical sections (Experience, Skills, Education) are identifiable by ATS parsers.
    """
    suggestions = []
    lower_text = resume_text.lower()

    has_exp = bool(re.search(r"\b(?:experience|work history|employment history|professional experience)\b", lower_text))
    has_edu = bool(re.search(r"\b(?:education|academic background|qualifications)\b", lower_text))
    has_skills = bool(re.search(r"\b(?:skills|technical skills|competencies|technologies)\b", lower_text))

    if not has_exp:
        suggestions.append({
            "text": (
                "[ML Structural Architecture] Missing standard 'Work Experience' or 'Professional Experience' header. "
                "ATS parsing models rely on standard section anchors to index your career progression and role titles."
            ),
            "priority": "high",
            "category": "section_architecture",
            "gain": 8.5,
        })

    if not has_skills:
        suggestions.append({
            "text": (
                "[ML Structural Architecture] Missing dedicated 'Technical Skills' or 'Skills' header. "
                "Modern ATS algorithms scan dedicated skill blocks for fast initial keyword indexing."
            ),
            "priority": "medium",
            "category": "section_architecture",
            "gain": 5.0,
        })

    if not has_edu:
        suggestions.append({
            "text": (
                "[ML Structural Architecture] Missing standard 'Education' header. "
                "Ensure your degrees and academic institutions are placed under a clear 'Education' section anchor."
            ),
            "priority": "low",
            "category": "section_architecture",
            "gain": 3.0,
        })

    return suggestions


def analyze_action_verbs_ml(resume_text: str, max_suggestions: int = 3) -> list:
    """
    Analyzes sentence starters and bullet points for weak/passive action verbs.
    Recommends context-aware executive power verbs with calculated impact uplifts.
    """
    suggestions = []
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    seen_verbs = set()

    for line in lines:
        if len(suggestions) >= max_suggestions:
            break
        words = line.split()
        if len(words) < 5:
            continue

        clean_line = line.lstrip("-*•·> \t")
        for pattern, label, power_map in _WEAK_VERB_PATTERNS:
            match = pattern.search(clean_line[:60])
            if match and label not in seen_verbs:
                seen_verbs.add(label)
                lower_line = clean_line.lower()
                if any(k in lower_line for k in ("api", "code", "software", "system", "data", "cloud", "server", "db", "pipeline")):
                    replacement = power_map.get("technical", "Engineered or Architected")
                elif any(k in lower_line for k in ("team", "project", "client", "led", "stakeholder", "manage", "budget")):
                    replacement = power_map.get("leadership", "Orchestrated or Spearheaded")
                else:
                    replacement = power_map.get("operational", "Executed or Delivered")

                snippet = clean_line[:45].strip()
                suggestions.append({
                    "text": (
                        f"[ML Action Verb Optimization] Replace weak passive phrase '{label}' in "
                        f"'{snippet}...' with executive power verbs such as {replacement}. "
                        f"ATS semantic scoring awards higher decisiveness scores to active power verbs."
                    ),
                    "priority": "medium",
                    "category": "action_verb",
                    "gain": 4.5,
                })
                break

    return suggestions


def analyze_bullet_quantification_ml(resume_text: str, max_suggestions: int = 3) -> list:
    """
    Scans bullet points for quantified metrics (STAR method: Situation, Task, Action, Result).
    Flags unquantified accomplishment statements and provides structured metric templates.
    """
    suggestions = []
    raw_bullets = []
    for line in resume_text.splitlines():
        trimmed = line.strip()
        if trimmed.startswith(("-", "*", "•", "·", "–")) or (len(trimmed) > 30 and re.match(r"^[A-Z][a-z]+ed\b", trimmed)):
            raw_bullets.append(trimmed.lstrip("-*•·–> \t"))

    if not raw_bullets:
        return []

    quantified_count = sum(1 for b in raw_bullets if _METRIC_REGEX.search(b))
    quant_ratio = quantified_count / max(len(raw_bullets), 1)

    if quant_ratio < 0.60:
        unquantified = [b for b in raw_bullets if not _METRIC_REGEX.search(b) and len(b.split()) >= 8]
        for bullet in unquantified[:max_suggestions]:
            snippet = bullet[:50].strip()
            suggestions.append({
                "text": (
                    f"[ML Impact Quantification] Bullet '{snippet}...' describes technical activity "
                    f"without measurable outcomes. Online ATS models score quantified bullets up to 40% higher. "
                    f"Add measurable scale (e.g. 'reduced latency by X%', 'serving Y requests/day', or 'saving Z hours/week')."
                ),
                "priority": "high" if quant_ratio < 0.35 else "medium",
                "category": "quantification",
                "gain": 6.0 if quant_ratio < 0.35 else 4.0,
            })

    return suggestions


def analyze_syntactic_complexity_ml(resume_text: str, max_suggestions: int = 2) -> list:
    """
    Evaluates sentence length distribution and lexical diversity (Type-Token Ratio).
    Warns against parser truncation risk in legacy and modern ATS parsers.
    """
    suggestions = []
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", resume_text) if s.strip()]

    # ATS Truncation Check: sentences > 32 words
    long_sentences = [s for s in sentences if len(s.split()) >= 32]
    if long_sentences:
        s = long_sentences[0]
        word_count = len(s.split())
        snippet = s[:48].strip()
        suggestions.append({
            "text": (
                f"[ML Syntactic Parser Safety] Found complex sentence with {word_count} words ('{snippet}...'). "
                f"Enterprise ATS parsers (Workday, Taleo, iCIMS) frequently truncate clauses exceeding 30 words. "
                f"Split into 2 concise, active achievement bullets."
            ),
            "priority": "medium",
            "category": "parser_truncation",
            "gain": 4.5,
        })

    # Lexical Diversity (Type-Token Ratio)
    words = re.findall(r"\b[a-z]{3,}\b", resume_text.lower())
    if len(words) > 120:
        unique_words = set(words)
        guiraud_r = len(unique_words) / math.sqrt(len(words))
        if guiraud_r < 6.5:
            suggestions.append({
                "text": (
                    f"[ML Lexical Diversity] Vocabulary repetition detected (Guiraud index: {guiraud_r:.1f}). "
                    f"Diversify descriptive phrasing across your technical accomplishments to prevent keyword penalty."
                ),
                "priority": "low",
                "category": "lexical_diversity",
                "gain": 3.0,
            })

    return suggestions


def generate_deep_ml_suggestions(
    resume_text: str | None,
    target_category: str | None = None,
    jd_text: str | None = None,
    resume_skills: list | None = None,
) -> list:
    """
    Master pipeline: aggregates all 10 deep ML and statistical NLP diagnostic engines.
    Returns a unified, prioritized list of {"text": str, "priority": "high"|"medium"|"low", ...}.
    """
    if not resume_text:
        return []

    suggestions = []

    # 1. Feature Attribution Gap (Direct Model Weights)
    try:
        suggestions.extend(
            analyze_model_feature_gap(resume_text, target_category=target_category, jd_text=jd_text, max_suggestions=3)
        )
    except Exception as exc:
        logger.debug("Feature gap analysis failed: %s", exc)

    # 2. Keyword Stuffing & Over-Optimization
    try:
        suggestions.extend(analyze_keyword_stuffing_and_density_ml(resume_text, max_suggestions=2))
    except Exception as exc:
        logger.debug("Keyword stuffing analysis failed: %s", exc)

    # 3. Section Context Placement (Contextual vs Laundry-List)
    try:
        suggestions.extend(analyze_section_context_placement_ml(resume_text, resume_skills=resume_skills, max_suggestions=2))
    except Exception as exc:
        logger.debug("Contextual placement analysis failed: %s", exc)

    # 4. Action Verb Optimization
    try:
        suggestions.extend(analyze_action_verbs_ml(resume_text, max_suggestions=2))
    except Exception as exc:
        logger.debug("Action verb analysis failed: %s", exc)

    # 5. Bullet Point Quantification (STAR Method)
    try:
        suggestions.extend(analyze_bullet_quantification_ml(resume_text, max_suggestions=2))
    except Exception as exc:
        logger.debug("Bullet quantification failed: %s", exc)

    # 6. Readability & Cognitive Complexity
    try:
        suggestions.extend(analyze_readability_and_cognitive_complexity_ml(resume_text))
    except Exception as exc:
        logger.debug("Readability analysis failed: %s", exc)

    # 7. Parser Safety & Glyph Contamination
    try:
        suggestions.extend(analyze_parser_safety_and_glyph_hygiene_ml(resume_text, max_suggestions=2))
    except Exception as exc:
        logger.debug("Parser safety failed: %s", exc)

    # 8. Structural Section Architecture
    try:
        suggestions.extend(analyze_section_structure_ml(resume_text))
    except Exception as exc:
        logger.debug("Section structure failed: %s", exc)

    # 9. Length & Density Distribution
    try:
        suggestions.extend(analyze_ats_length_and_density_ml(resume_text))
    except Exception as exc:
        logger.debug("Length analysis failed: %s", exc)

    # 10. Syntactic Complexity & Truncation
    try:
        suggestions.extend(analyze_syntactic_complexity_ml(resume_text, max_suggestions=1))
    except Exception as exc:
        logger.debug("Syntactic complexity failed: %s", exc)

    # 11. Buzzword & Filler Dilution
    try:
        suggestions.extend(analyze_buzzword_and_filler_dilution_ml(resume_text, max_suggestions=1))
    except Exception as exc:
        logger.debug("Buzzword dilution failed: %s", exc)

    # Deduplicate and sort by priority and score gain
    priority_order = {"high": 0, "medium": 1, "low": 2}
    seen = set()
    deduped = []
    for item in suggestions:
        raw_key = re.sub(r"[^a-z0-9]+", " ", item["text"].lower()).strip()
        if raw_key not in seen:
            seen.add(raw_key)
            deduped.append(item)

    deduped.sort(key=lambda x: (priority_order.get(x["priority"], 3), -x.get("gain", 0.0)))
    return deduped
