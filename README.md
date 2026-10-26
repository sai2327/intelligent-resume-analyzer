# Intelligent Resume Analyzer

NLP + Machine Learning powered resume analysis, job matching, and **ATS score
tracking** — 100% offline, no external AI services.

Upload a resume (PDF/DOCX), optionally paste or upload a job description, and
get:

- a **7-factor ATS score** modeling how keyword-parsing applicant tracking
  systems (Taleo, Workday, iCIMS, Greenhouse…) evaluate resumes
- **prioritized, specific "what to change" advice** ordered by potential score
  gain
- a **job match score** (skills / text similarity / experience / education)
- resume classification into 9 job categories with calibrated confidence
- a **score history tracker** so you can measure improvement over time
- **non-resume rejection**: uploading a thesis, report, cover letter, or
  invoice is politely refused (with the detected document type) instead of
  returning a meaningless score
- **potential score**: an honest upper bound ("up to 94.3") showing how many
  points the flagged fixes are worth — only factors you can actually change
  (keywords, skills, title, formatting) are capped; experience and education
  keep their real score
- **factor radar chart**: server-rendered SVG spider chart of all factors
- **multi-JD ranking**: paste up to 10 job descriptions and get them ranked
  best-fit first for your resume
- **bulk shortlisting (recruiter mode)**: upload up to 50 resumes + one job
  description; every candidate is scored, ranked, and marked
  Shortlisted / Maybe / Rejected against a configurable threshold, on a
  background job with live progress (budget: 7s per resume, typical ~0.2s)
- **resume comparison**: upload 2-5 resumes and compare them head-to-head
  (against a JD or standalone) - winner card, per-factor gap table, and
  per-resume potential scores. Also available as `POST /api/compare`
- **resume progress tracking**: analyze the same file repeatedly and the
  tracker shows first → latest → best score with an up/down trend badge
- **adjacent-skill advice**: for missing skills you are close to (another
  skill from the same category is already on your resume), recommendations
  say so explicitly
- **JD quality checker**: weak job descriptions (too short, few skills, no
  title/requirements) are flagged so you know which match numbers to trust
- **JSON API**: `/api/analyze`, `/api/match`, `/api/rank-jds`, `/api/compare`
  for programmatic access
- **advanced options**: ATS strictness (lenient / standard / strict), target
  job title override, downloadable text and JSON reports, CSV history export

---

## Quickstart

```bash
pip install -r requirements.txt
python setup_nlp.py          # optional: installs spaCy model for name detection
python -m samples.generate_samples   # optional: demo PDF/DOCX files
python app.py                # http://127.0.0.5:5000
```

Train the resume classifier once (a pre-trained model ships in `models/`):

```bash
python -m training.train_model
```

Everything runs 100% locally — no external AI services, no API keys.

## Using it

| Page | What it does |
|---|---|
| `/` | Upload resume: analyze, match one JD, rank multiple JDs, shortlist candidates + advanced options |
| results page | ATS gauge, potential score, factor breakdown + radar, keyword chips, "What to change", match scores, recommendations |
| `/history` | ATS score tracker: every past run, mini score bars, aggregate stats |
| `/history/export.csv` | Download the full tracker history as CSV |
| `/results/<id>` | Full JSON breakdown of any past run |
| `/report/<id>.txt` | Downloadable plain-text ATS report for any past run |
| `/health` | Liveness + model availability |

### JSON API

```bash
# Standalone ATS audit (multipart upload)
curl -F "resume_file=@resume.pdf" -F "strictness=strict" http://127.0.0.1:5000/api/analyze

# Match against one job description
curl -F "resume_file=@resume.pdf" -F "jd_text=$(cat jd.txt)" http://127.0.0.1:5000/api/match

# Rank one resume against several job descriptions
curl -H "Content-Type: application/json" \
     -d '{"resume_text": "...", "jds": ["jd one", "jd two"]}' \
     http://127.0.0.1:5000/api/rank-jds
```

All three endpoints return structured JSON (scores, factor breakdowns,
prioritized change suggestions, detection verdict) and reject non-resumes
with a JSON error. Ranking accepts at most 10 JDs per request.

### Advanced options

- **ATS strictness** — `Lenient` forgives more (typo matching, wider length
  band, lower quality targets); `Strict` models a rigid keyword parser (no
  typo forgiveness, half partial credit, tighter rules); `Standard` is the
  default and what all validation numbers refer to.
- **Target job title** — an explicitly stated target title overrides JD title
  extraction for the job-title match factor.
- **Resume detection** — every upload is checked first; non-resumes are
  rejected with the likely document type and confidence. Borderline documents
  are analyzed but flagged with a warning banner.

## ATS score methodology

Every factor returns a 0–100 subscore with a weight. A factor that cannot be
computed (e.g. the JD states no education requirement) is **excluded and its
weight redistributed** — missing information never silently drags the score
toward 0 or 100.

### Resume vs job description

| Factor | Weight | What it measures |
|---|---|---|
| Keyword coverage | 25% | Weighted JD keywords found on the resume. Skills from the canonical database count heaviest; remaining unigrams/bigrams are harvested from requirement/responsibility sections (benefits/EEO boilerplate is stripped, never penalized). Inflection-aware ("analyzed" ↔ "analyze"), irregular-verb-aware ("built" ↔ "build"), typo-tolerant ("Pyhton" → flagged with a fix suggestion). |
| Skills match | 25% | Required-skill coverage (75%) blended with preferred (25%) |
| Job title match | 10% | Posting title vs resume titles/headline (string ratio + token overlap) |
| Experience | 15% | Years evidenced vs required — max of self-reported claims and interval-union date math over the experience section (overlaps never double-counted, "Present" resolved) |
| Education | 5% | Degree level vs requirement |
| Format & parseability | 10% | 8 checks: contact info, name, standard section headers, dates, healthy length, clean text extraction |
| Content quality | 10% | Quantified bullets (≥40% target), action-verb openers (≥60% target), no first-person pronouns |

### Standalone (no JD)

Format & parseability 35% · Content quality 30% · Skill breadth 20% ·
Education present 15%.

If the JD contains no detectable requirements at all, the UI says so
explicitly instead of showing a number that silently means resume quality only.

### Grade bands

≥85 Excellent · ≥70 Strong · ≥55 Fair · ≥40 Needs work · <40 High risk

## Job match score

Transparent weighted blend (weights in `config.py`, env-overridable):
skills 50% · TF-IDF text similarity (unigrams+bigrams, sublinear TF) 25% ·
experience 15% · education 10%.

## Architecture

```
app.py                    HTTP routes only (validation + orchestration)
config.py                 all settings from environment / .env
services/
  document_parser.py      PDF/DOCX → text (in-memory, never written to disk)
  information_extractor.py  contact info, sections, skills, titles,
                          experience from claims + date-range math
  job_description_parser.py  JD title, seniority, required/preferred skills
  skill_matcher.py        canonical skill database (data/skills.json,
                          178 skills / 273 recognized surface forms), cached
  matching_engine.py      skill overlap + TF-IDF similarity + transparent blend
  ats_scorer.py           the ATS score tracker (7 factors, suggestions)
  recommendation_engine.py  prioritized recommendations
  text_preprocessor.py    shared NLP pipeline, LRU-cached
  classifier.py           TF-IDF + calibrated LinearSVC, with an MLP head trained
                          alongside it — holdout-selected at training time
database/database.py      SQLite history (schema migrations included)
templates/, static/       Bootstrap UI (results, tracker, history)
```

Models: the classifier corpus is 1,817 rows — 1,260 synthetic resumes plus
557 real labeled resumes (public dataset, mapped to the 9 categories). Training
evaluates a calibrated SVM, an MLP neural network (256,64) and their soft-vote
ensemble on a held-out split, and the runtime automatically serves whichever
model won. Recent run: SVM 94.5%, MLP 92.0%, ensemble 92.6% → SVM selected.

Performance: preprocessing, JD parsing, skill scanning, and keyword
extraction are all memoized — the classic "one JD × many resumes" workflow
runs at ~5 ms per analysis warm (first request pays one-time model loading).

## Testing

```bash
python -m pytest -q            # 69 tests: units, routes, golden regression, fuzz
python validate_ats_matrix.py  # 8x8 cross-domain matrix + causal checks
```

- **Golden regression** (`tests/test_golden_regression.py`) pins canonical
  scores for the fixture resume/JD — any scoring change must consciously
  update them.
- **Fuzz/property suite** (`tests/test_fuzz_stress.py`) pushes a seeded random
  corpus through the pipeline asserting bounds, determinism, and monotonicity
  (adding a missing skill never lowers the score; gutting skills never raises it).
- **Validation matrix** proves diagonal dominance (each tailored resume ranks
  its own JD first across 8 domains), matched > partial > weak ordering,
  causality (following the tool's advice raises the score by +15–23 pts), and
  robustness against CRLF/unicode/unpunctuated/degenerate inputs.

Tests use isolated temp databases; your real `database/app.db` is never touched.

## Privacy

Uploaded files are parsed in memory and never written to disk. The database
stores scores and filenames only — never resume text, names, emails, or phones.
