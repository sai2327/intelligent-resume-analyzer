/* Intelligent Resume Analyzer — B.Tech project deck (20 slides)
   Design system: deep navy + electric indigo + emerald accent, light content slides. */
const pptxgen = require("pptxgenjs");

const P = new pptxgen();
P.layout = "LAYOUT_WIDE";                 // 13.33 x 7.5
P.author = "Team Intelligent Resume Analyzer";
P.title = "Intelligent Resume Analyzer";

// ---- palette (single source of truth) ----
const NAVY = "0B1F3A";      // dark background
const NAVY2 = "122B4F";     // panel on dark
const INDIGO = "4F46E5";    // primary brand
const INDIGO_D = "3730A3";
const EMERALD = "10B981";   // accent (results)
const CYAN = "06B6D4";      // ML/NLP accent
const BG = "FFFFFF";
const BG_SOFT = "F4F6FB";
const TEXT = "0F172A";
const MUTED = "64748B";
const LINE = "D8DEEA";
const WHITE = "FFFFFF";

const F = "Segoe UI";
const MONO = "Consolas";

const W = 13.33, H = 7.5, M = 0.55;
const A = "C:/Users/sai/OneDrive/Desktop/NLP/ppt_assets/";

// ---- helpers (fresh objects every call) ----
const sectionLabel = (s, text, color = INDIGO, x = M, y = 0.42) =>
  s.addText(text.toUpperCase(), { x, y, w: 6.5, h: 0.32, fontFace: F, fontSize: 12.5,
    bold: true, color, charSpacing: 3, margin: 0 });

const slideTitle = (s, text, opts = {}) =>
  s.addText(text, { x: M, y: 0.72, w: 12.2, h: 0.75, fontFace: F, fontSize: 31, bold: true,
    color: opts.color || TEXT, margin: 0 });

const pageNum = (s, n) =>
  s.addText(String(n).padStart(2, "0"), { x: W - 1.05, y: H - 0.52, w: 0.6, h: 0.3,
    fontFace: MONO, fontSize: 10.5, color: MUTED, align: "right", margin: 0 });

const footerBrand = (s, dark = false) =>
  s.addText("INTELLIGENT RESUME ANALYZER", { x: M, y: H - 0.52, w: 4.5, h: 0.3,
    fontFace: MONO, fontSize: 9, color: dark ? "5A6E93" : "A6B0C3", charSpacing: 2, margin: 0 });

const chip = (s, x, y, d, text, fill, textColor = WHITE, fontSize = 13) => {
  s.addShape(P.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill } });
  s.addText(text, { x: x - 0.1, y, w: d + 0.2, h: d, align: "center", valign: "middle",
    fontFace: F, fontSize, bold: true, color: textColor, margin: 0 });
};

const flowArrow = (s, x, y, w = 0.42) =>
  s.addShape(P.shapes.LINE, { x, y, w, h: 0, line: { color: LINE, width: 2,
    endArrowType: "triangle" } });

const mono = (s, text, o) => s.addText(text, { fontFace: MONO, ...o });

// ============================================================ 01 HERO
{
  const s = P.addSlide();
  s.background = { color: NAVY };
  // subtle node grid motif
  for (let i = 0; i < 7; i++)
    s.addShape(P.shapes.OVAL, { x: 11.1 + (i % 3) * 0.55, y: 0.6 + Math.floor(i / 3) * 0.55,
      w: 0.09, h: 0.09, fill: { color: i % 2 ? CYAN : INDIGO } });

  s.addText("B.TECH FINAL-YEAR PROJECT", { x: M, y: 1.02, w: 9, h: 0.34, fontFace: F,
    fontSize: 13, bold: true, color: CYAN, charSpacing: 4, margin: 0 });
  s.addText("Intelligent Resume\nAnalyzer", { x: M, y: 1.42, w: 10.5, h: 1.9, fontFace: F,
    fontSize: 52, bold: true, color: WHITE, margin: 0 });
  s.addText("NLP + Machine Learning for Resume Analysis, Job Matching & ATS Scoring",
    { x: M, y: 3.42, w: 10.2, h: 0.5, fontFace: F, fontSize: 18, color: "AEB8CE", margin: 0 });

  // pipeline motif: RESUME -> NLP -> ML -> ATS SCORE
  const stages = ["RESUME", "NLP", "ML", "ATS SCORE"];
  const bw = 1.72, gap = 0.52, x0 = M, y0 = 4.5;
  stages.forEach((st, i) => {
    const x = x0 + i * (bw + gap);
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x, y: y0, w: bw, h: 0.62, rectRadius: 0.09,
      fill: { color: NAVY2 }, line: { color: i === 3 ? EMERALD : INDIGO, width: 1.5 } });
    s.addText(st, { x, y: y0, w: bw, h: 0.62, align: "center", valign: "middle",
      fontFace: MONO, fontSize: 12.5, bold: true, color: i === 3 ? EMERALD : WHITE, margin: 0 });
    if (i < stages.length - 1)
      s.addShape(P.shapes.LINE, { x: x + bw + 0.08, y: y0 + 0.31, w: gap - 0.16, h: 0,
        line: { color: "5A6E93", width: 2, endArrowType: "triangle" } });
  });

  s.addText([
    { text: "Saiteja K      Gnaneswari K      Siddhardha P      Mahalaxmi M", options: { breakLine: true } },
    { text: "Department of Computer Science and Engineering", options: { color: "5A6E93", fontSize: 12 } },
  ], { x: M, y: 6.05, w: 11, h: 0.85, fontFace: F, fontSize: 15, color: WHITE, margin: 0 });
  footerBrand(s, true);
}

// ============================================================ 02 PROBLEM
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "The Problem");
  slideTitle(s, "Resume screening is slow, lossy and opaque");

  const probs = [
    ["01", "Manual screening", "Recruiters evaluate dense documents one by one — slow and inconsistent."],
    ["02", "Unstructured formats", "Skills and experience hide inside dozens of different layouts and styles."],
    ["03", "No actionable feedback", "Applicants are rejected silently, with no idea what to improve."],
  ];
  probs.forEach((p, i) => {
    const x = M + i * 4.18;
    s.addText(p[0], { x, y: 1.78, w: 1.2, h: 0.75, fontFace: MONO, fontSize: 34, bold: true,
      color: INDIGO, margin: 0 });
    s.addText(p[1], { x, y: 2.55, w: 3.75, h: 0.45, fontFace: F, fontSize: 18.5, bold: true,
      color: TEXT, margin: 0 });
    s.addText(p[2], { x, y: 3.02, w: 3.7, h: 0.95, fontFace: F, fontSize: 13.5, color: MUTED, margin: 0 });
    if (i < 2) s.addShape(P.shapes.LINE, { x: x + 3.95, y: 1.95, w: 0, h: 1.9,
      line: { color: LINE, width: 1 } });
  });

  // flow
  const steps = ["RESUME", "UNSTRUCTURED TEXT", "MANUAL SCREENING", "INCONSISTENT DECISION"];
  const bw = 2.62, gap = 0.5, y0 = 4.55;
  steps.forEach((st, i) => {
    const x = M + i * (bw + gap);
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x, y: y0, w: bw, h: 0.6, rectRadius: 0.08,
      fill: { color: BG_SOFT }, line: { color: LINE, width: 1 } });
    s.addText(st, { x, y: y0, w: bw, h: 0.6, align: "center", valign: "middle",
      fontFace: MONO, fontSize: 12, bold: true, color: "334155", margin: 0 });
    if (i < steps.length - 1)
      s.addShape(P.shapes.LINE, { x: x + bw + 0.07, y: y0 + 0.3, w: gap - 0.14, h: 0,
        line: { color: MUTED, width: 2, endArrowType: "triangle" } });
  });

  s.addText([
    { text: "Our question:  ", options: { bold: true, color: TEXT } },
    { text: "Can NLP + Machine Learning make resume analysis faster, transparent and actionable?",
      options: { color: INDIGO, italic: true } },
  ], { x: M, y: 5.75, w: 12.2, h: 0.6, fontFace: F, fontSize: 17, margin: 0 });
  footerBrand(s); pageNum(s, 2);
}

// ============================================================ 03 SOLUTION
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "Our Solution");
  slideTitle(s, "From resume document to structured intelligence");

  const stages = [
    ["PDF / DOCX", "upload", "F59E0B"],
    ["Text Extraction", "pypdf · python-docx", "8B5CF6"],
    ["NLP Processing", "NLTK · spaCy", "06B6D4"],
    ["Information Extraction", "skills · dates · entities", "06B6D4"],
    ["ML Classification", "TF-IDF + LinearSVC", "4F46E5"],
    ["ATS Scoring", "7 weighted factors", "10B981"],
    ["Advice + Tracking", "recommendations · history", "10B981"],
  ];
  const bw = 1.545, gap = 0.225, y0 = 2.3;
  stages.forEach((st, i) => {
    const x = M + i * (bw + gap);
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x, y: y0, w: bw, h: 1.5, rectRadius: 0.09,
      fill: { color: BG_SOFT }, line: { color: st[2], width: 1.5 } });
    s.addText(st[0], { x: x + 0.05, y: y0 + 0.12, w: bw - 0.1, h: 0.85, align: "center",
      fontFace: F, fontSize: 12, bold: true, color: TEXT, margin: 0 });
    mono(s, st[1], { x: x + 0.03, y: y0 + 1.02, w: bw - 0.06, h: 0.4, align: "center",
      fontSize: 8, color: MUTED });
    if (i < stages.length - 1)
      s.addShape(P.shapes.LINE, { x: x + bw, y: y0 + 0.75, w: gap, h: 0,
        line: { color: MUTED, width: 2, endArrowType: "triangle" } });
  });

  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y: 4.6, w: 12.23, h: 1.5, rectRadius: 0.1,
    fill: { color: NAVY } });
  s.addText([
    { text: "One resume  →  ", options: { color: "AEB8CE" } },
    { text: "structured profile + job category + ATS score + improvement advice",
      options: { bold: true, color: WHITE } },
  ], { x: M + 0.3, y: 4.6, w: 11.6, h: 1.5, fontFace: F, fontSize: 18, valign: "middle", margin: 0 });
  s.addText("Every stage runs locally — nothing leaves the machine.",
    { x: M, y: 6.35, w: 9, h: 0.35, fontFace: F, fontSize: 12.5, italic: true, color: MUTED, margin: 0 });
  footerBrand(s); pageNum(s, 3);
}

// ============================================================ 04 ARCHITECTURE
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "System Design");
  slideTitle(s, "Layered architecture — HTTP routes, isolated services");

  const layer = (y, h, label, fill, textColor, items, fontSize = 13) => {
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y, w: 12.23, h, rectRadius: 0.07,
      fill: { color: fill }, line: { color: LINE, width: 1 } });
    s.addText(label, { x: M + 0.25, y: y + (h - 0.3) / 2 - 0.05, w: 2.6, h: 0.4, fontFace: MONO,
      fontSize: 11, bold: true, color: textColor, margin: 0 });
    if (items) {
      const n = items.length, iw = (12.23 - 3.2) / n;
      items.forEach((it, i) => {
        const x = M + 2.9 + i * iw;
        s.addText(it, { x, y: y + (h - 0.55) / 2, w: iw - 0.1, h: 0.55, align: "center",
          valign: "middle", fontFace: F, fontSize, bold: true, color: TEXT, margin: 0 });
      });
    }
  };

  layer(1.65, 0.62, "USER", "F1F5F9", "334155", ["Recruiter", "Applicant"], 13);
  s.addShape(P.shapes.LINE, { x: 6.6, y: 2.27, w: 0, h: 0.28, line: { color: MUTED, width: 2, endArrowType: "triangle" } });
  layer(2.55, 0.62, "WEB INTERFACE", "EEF2FF", INDIGO_D, ["Flask + Jinja templates", "Bootstrap UI", "SVG charts"]);
  s.addShape(P.shapes.LINE, { x: 6.6, y: 3.17, w: 0, h: 0.28, line: { color: MUTED, width: 2, endArrowType: "triangle" } });
  layer(3.45, 0.62, "FLASK APP (app.py)", BG_SOFT, "334155", ["HTTP + JSON API routing only", "validation · jobs · telemetry"]);

  // services layer
  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y: 4.42, w: 12.23, h: 1.72, rectRadius: 0.07,
    fill: { color: NAVY } });
  s.addText("NLP / ML SERVICES", { x: M + 0.25, y: 4.55, w: 2.7, h: 0.4, fontFace: MONO,
    fontSize: 11, bold: true, color: CYAN, margin: 0 });
  const svcs = ["Document Parser", "Text Preprocessor", "Information Extractor", "Skill Matcher",
    "Classifier", "Matching Engine", "ATS Scorer", "Recommendations", "Resume Detector", "Shortlist Jobs"];
  svcs.forEach((it, i) => {
    const col = i % 5, row = Math.floor(i / 5);
    const x = M + 2.85 + col * 1.88, y = 4.55 + row * 0.72;
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x, y, w: 1.74, h: 0.6, rectRadius: 0.06,
      fill: { color: NAVY2 }, line: { color: "2A4A7F", width: 1 } });
    s.addText(it, { x: x + 0.03, y, w: 1.68, h: 0.6, align: "center", valign: "middle",
      fontFace: F, fontSize: 10.5, bold: true, color: WHITE, margin: 0 });
  });

  s.addShape(P.shapes.LINE, { x: 6.6, y: 6.14, w: 0, h: 0.24, line: { color: MUTED, width: 2, endArrowType: "triangle" } });
  layer(6.38, 0.56, "DATABASE", "ECFDF5", "065F46", ["SQLite (WAL) — analysis history · JSON · CSV / TXT export"]);

  footerBrand(s); pageNum(s, 4);
}

// ============================================================ 05 TECH STACK
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "Technology");
  slideTitle(s, "A deliberately boring, battle-tested stack");

  const rows = [
    ["APPLICATION", "Flask  ·  Jinja2  ·  Bootstrap 5  ·  SVG charts", "F59E0B"],
    ["NLP", "NLTK  ·  spaCy (NER)  ·  WordNet lemmatizer", "06B6D4"],
    ["MACHINE LEARNING", "scikit-learn  ·  TF-IDF  ·  LinearSVC  ·  CalibratedClassifierCV", "4F46E5"],
    ["DOCUMENT PARSING", "pypdf  ·  python-docx", "8B5CF6"],
    ["DATABASE", "SQLite (WAL mode) + schema migrations", "10B981"],
    ["TESTING / SERVER", "pytest  ·  waitress (production WSGI)", "EF4444"],
  ];
  rows.forEach((r, i) => {
    const y = 1.75 + i * 0.82;
    s.addText(r[0], { x: M, y, w: 3.3, h: 0.6, fontFace: MONO, fontSize: 12.5, bold: true,
      color: r[2], valign: "middle", margin: 0 });
    s.addText(r[1], { x: 4.1, y, w: 8.6, h: 0.6, fontFace: F, fontSize: 15.5, color: TEXT,
      valign: "middle", margin: 0 });
    if (i < rows.length - 1)
      s.addShape(P.shapes.LINE, { x: M, y: y + 0.72, w: 12.2, h: 0, line: { color: LINE, width: 1 } });
  });

  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y: 6.42, w: 12.23, h: 0.6, rectRadius: 0.09,
    fill: { color: NAVY } });
  s.addText("PYTHON — one language across the whole pipeline  ·  100% local processing",
    { x: M, y: 6.42, w: 12.23, h: 0.6, align: "center", valign: "middle", fontFace: MONO,
      fontSize: 12.5, bold: true, color: WHITE, margin: 0 });
  footerBrand(s); pageNum(s, 5);
}

// ============================================================ 06 PIPELINE 8 STAGES
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "End-to-End Pipeline");
  slideTitle(s, "How one resume becomes a score");

  const stages = [
    ["01", "Upload", "PDF / DOCX in memory"],
    ["02", "Validate", "type, size, resume check"],
    ["03", "Extract", "raw text, page-safe"],
    ["04", "Preprocess", "clean · tokenize · lemma"],
    ["05", "Understand", "skills · dates · entities"],
    ["06", "Classify", "9 job categories"],
    ["07", "Score", "7-factor ATS engine"],
    ["08", "Deliver", "reports · charts · API"],
  ];
  stages.forEach((st, i) => {
    const col = i % 4, row = Math.floor(i / 4);
    const x = M + col * 3.12, y = 1.95 + row * 2.15;
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.86, h: 1.72, rectRadius: 0.09,
      fill: { color: BG_SOFT }, line: { color: LINE, width: 1 },
      shadow: { type: "outer", color: "9AA5B8", blur: 5, offset: 2, angle: 90, opacity: 0.18 } });
    s.addText(st[0], { x: x + 0.16, y: y + 0.12, w: 1.2, h: 0.5, fontFace: MONO, fontSize: 20,
      bold: true, color: INDIGO, margin: 0 });
    s.addText(st[1], { x: x + 0.16, y: y + 0.62, w: 2.55, h: 0.42, fontFace: F, fontSize: 16.5,
      bold: true, color: TEXT, margin: 0 });
    mono(s, st[2], { x: x + 0.16, y: y + 1.08, w: 2.6, h: 0.4, fontSize: 10.5, color: MUTED });
    if (col < 3) s.addShape(P.shapes.LINE, { x: x + 2.86, y: y + 0.86, w: 0.26, h: 0,
      line: { color: MUTED, width: 2, endArrowType: "triangle" } });
  });
  s.addShape(P.shapes.LINE, { x: 12.05, y: 3.72, w: 0, h: 0.38, line: { color: MUTED, width: 2, endArrowType: "triangle" } });

  s.addText("Uploaded files are parsed entirely in memory — never written to disk.",
    { x: M, y: 6.45, w: 12, h: 0.35, fontFace: F, fontSize: 13, italic: true, color: MUTED, margin: 0 });
  footerBrand(s); pageNum(s, 6);
}

// ============================================================ 07 NLP ENGINE
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "NLP Engine");
  slideTitle(s, "Understanding the resume");

  // left: NLP pipeline (vertical)
  const steps = ["Raw resume text", "Text cleaning + technical-term protection",
    "Tokenization", "Stop-word filtering", "POS-aware lemmatization", "Section + entity extraction"];
  steps.forEach((st, i) => {
    const y = 1.72 + i * 0.78;
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y, w: 5.1, h: 0.58, rectRadius: 0.08,
      fill: { color: i === 4 ? "ECFEFF" : BG_SOFT }, line: { color: i === 4 ? CYAN : LINE, width: 1.25 } });
    s.addText(st, { x: M + 0.2, y, w: 4.8, h: 0.58, valign: "middle", fontFace: F,
      fontSize: 13.5, bold: i === 4, color: TEXT, margin: 0 });
    if (i < steps.length - 1)
      s.addShape(P.shapes.LINE, { x: 1.4, y: y + 0.58, w: 0, h: 0.2,
        line: { color: MUTED, width: 2, endArrowType: "triangle" } });
  });

  // right: extracted entities + skill engine
  s.addText("EXTRACTED STRUCTURE", { x: 6.3, y: 1.72, w: 4, h: 0.3, fontFace: MONO,
    fontSize: 11, bold: true, color: MUTED, charSpacing: 2, margin: 0 });
  const ents = ["Skills", "Experience + tenure", "Education", "Projects", "Certifications", "Contact + profiles"];
  ents.forEach((e, i) => {
    const y = 2.12 + i * 0.52;
    s.addShape(P.shapes.OVAL, { x: 6.32, y: y + 0.1, w: 0.12, h: 0.12, fill: { color: EMERALD } });
    s.addText(e, { x: 6.55, y, w: 3.4, h: 0.4, fontFace: F, fontSize: 14, color: TEXT,
      valign: "middle", margin: 0 });
  });

  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: 10.15, y: 1.72, w: 2.63, h: 4.05, rectRadius: 0.09,
    fill: { color: NAVY } });
  s.addText("SKILL ENGINE", { x: 10.38, y: 1.92, w: 2.2, h: 0.3, fontFace: MONO, fontSize: 10.5,
    bold: true, color: CYAN, charSpacing: 2, margin: 0 });
  [["178", "canonical skills"], ["120", "aliases"], ["298", "surface forms"]].forEach((k, i) => {
    const y = 2.3 + i * 1.1;
    s.addText(k[0], { x: 10.38, y, w: 2.2, h: 0.55, fontFace: F, fontSize: 30, bold: true,
      color: WHITE, margin: 0 });
    s.addText(k[1], { x: 10.38, y: y + 0.52, w: 2.2, h: 0.3, fontFace: F, fontSize: 11,
      color: "AEB8CE", margin: 0 });
  });

  s.addText("POS-aware lemmatization: “managed / managing” → manage — resumes and job descriptions finally speak the same tense.",
    { x: 6.3, y: 6.0, w: 6.4, h: 0.6, fontFace: F, fontSize: 12.5, italic: true, color: MUTED, margin: 0 });
  footerBrand(s); pageNum(s, 7);
}

// ============================================================ 08 ML MODEL
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "Machine Learning");
  slideTitle(s, "Resume classification model");

  const steps = [
    ["Resume text", "preprocessed corpus"],
    ["TF-IDF vectorizer", "unigrams + bigrams · sublinear TF · 5,000 features"],
    ["LinearSVC", "9-class linear classifier"],
    ["CalibratedClassifierCV", "5-fold sigmoid calibration"],
    ["Category + confidence", "honest, normalized probabilities"],
  ];
  steps.forEach((st, i) => {
    const y = 1.72 + i * 0.92;
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y, w: 6.2, h: 0.7, rectRadius: 0.08,
      fill: { color: i === 4 ? "EEF2FF" : BG_SOFT }, line: { color: i === 4 ? INDIGO : LINE, width: 1.25 } });
    s.addText(st[0], { x: M + 0.22, y, w: 2.6, h: 0.7, valign: "middle", fontFace: F,
      fontSize: 14.5, bold: true, color: TEXT, margin: 0 });
    s.addText(st[1], { x: M + 2.9, y, w: 3.2, h: 0.7, valign: "middle", fontFace: MONO,
      fontSize: 10, color: MUTED, margin: 0 });
    if (i < steps.length - 1)
      s.addShape(P.shapes.LINE, { x: 1.5, y: y + 0.7, w: 0, h: 0.22,
        line: { color: MUTED, width: 2, endArrowType: "triangle" } });
  });

  s.addText("9 JOB CATEGORIES", { x: 7.3, y: 1.72, w: 4, h: 0.3, fontFace: MONO, fontSize: 11,
    bold: true, color: MUTED, charSpacing: 2, margin: 0 });
  const cats = ["Software Developer", "Data Analyst", "Data Scientist", "ML Engineer",
    "DevOps Engineer", "Cloud Engineer", "Web Developer", "UI/UX Designer", "Business Analyst"];
  cats.forEach((c, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: 7.3 + col * 1.95, y: 2.12 + row * 0.62,
      w: 1.82, h: 0.5, rectRadius: 0.25, fill: { color: "EEF2FF" }, line: { color: INDIGO, width: 1 } });
    s.addText(c, { x: 7.3 + col * 1.95, y: 2.12 + row * 0.62, w: 1.82, h: 0.5, align: "center",
      valign: "middle", fontFace: F, fontSize: 10.5, bold: true, color: INDIGO_D, margin: 0 });
  });

  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: 7.3, y: 4.25, w: 5.48, h: 2.3, rectRadius: 0.09,
    fill: { color: "FFFBEB" }, line: { color: "F59E0B", width: 1.25 } });
  s.addText([
    { text: "Honest limitation\n", options: { bold: true, fontSize: 14, color: "92400E", breakLine: true } },
    { text: "The training corpus is synthetic (1,260 generated resumes, 3 layouts). Held-out accuracy is 100% because the templates are cleanly separable — it does not measure real-world production accuracy. Swapping in a labeled real-world dataset is the next milestone.",
      options: { fontSize: 11.5, color: "78350F" } },
  ], { x: 7.5, y: 4.4, w: 5.1, h: 2.05, fontFace: F, margin: 0 });

  footerBrand(s); pageNum(s, 8);
}

// ============================================================ 09 ATS SCORING
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "ATS Scoring Engine");
  slideTitle(s, "A transparent 7-factor ATS score");

  s.addChart(P.charts.DOUGHNUT, [{
    name: "Factor weight",
    labels: ["Keyword coverage", "Skills match", "Experience", "Job title", "Format / parsing", "Content quality", "Education"],
    values: [25, 25, 15, 10, 10, 10, 5],
  }], {
    x: M - 0.05, y: 1.72, w: 5.3, h: 4.6,
    holeSize: 62, showPercent: true, dataLabelColor: "FFFFFF", dataLabelFontSize: 11,
    chartColors: ["4F46E5", "06B6D4", "10B981", "F59E0B", "8B5CF6", "EC4899", "94A3B8"],
    showLegend: true, legendPos: "b", legendFontSize: 10, legendColor: MUTED,
    chartArea: { fill: { color: "FFFFFF" } }, showTitle: false,
  });

  const factors = [
    ["Keyword coverage", "25%", "weighted JD keywords found on the resume"],
    ["Skills match", "25%", "required + preferred skill overlap"],
    ["Experience", "15%", "date-range math vs requirement"],
    ["Job title", "10%", "posting title vs resume titles"],
    ["Format / parsing", "10%", "8 parser-friendliness checks"],
    ["Content quality", "10%", "metrics, action verbs, pronouns"],
    ["Education", "5%", "degree level vs requirement"],
  ];
  factors.forEach((f2, i) => {
    const y = 1.78 + i * 0.63;
    s.addText(f2[1], { x: 5.6, y, w: 0.85, h: 0.5, fontFace: MONO, fontSize: 16, bold: true,
      color: INDIGO, valign: "middle", margin: 0 });
    s.addText(f2[0], { x: 6.5, y, w: 2.7, h: 0.5, fontFace: F, fontSize: 13.5, bold: true,
      color: TEXT, valign: "middle", margin: 0 });
    s.addText(f2[2], { x: 9.25, y, w: 3.5, h: 0.5, fontFace: F, fontSize: 11.5, color: MUTED,
      valign: "middle", margin: 0 });
  });

  s.addText("Unavailable factors are excluded and their weight is redistributed — missing data never skews the score.",
    { x: 5.6, y: 6.32, w: 7.1, h: 0.55, fontFace: F, fontSize: 12.5, italic: true, color: MUTED, margin: 0 });
  footerBrand(s); pageNum(s, 9);
}

// ============================================================ 10 PRODUCT: UPLOAD
{
  const s = P.addSlide();
  s.background = { color: BG_SOFT };
  sectionLabel(s, "Product Experience");
  slideTitle(s, "The analyzer in action");

  // screenshot (1600x1000 → 16:10)
  s.addImage({ path: A + "home.png", x: M, y: 1.62, w: 8.53, h: 5.33,
    shadow: { type: "outer", color: "1E293B", blur: 10, offset: 3, angle: 90, opacity: 0.3 } });
  const callouts = [
    ["1", 1.0, 3.55], ["2", 2.9, 2.42], ["3", 3.6, 4.6], ["4", 5.4, 6.0],
  ];
  callouts.forEach(([n, x, y]) => chip(s, x, y, 0.4, n, NAVY, WHITE, 14));

  const steps = [
    ["1", "Upload resume", "drag & drop PDF or DOCX"],
    ["2", "Pick a mode", "analyze · match · rank · compare"],
    ["3", "Configure ATS options", "strictness, threshold, target title"],
    ["4", "Run analysis", "results render in milliseconds"],
  ];
  steps.forEach((st, i) => {
    const y = 1.9 + i * 1.18;
    s.addText(st[0], { x: 9.35, y, w: 0.55, h: 0.5, fontFace: MONO, fontSize: 22, bold: true,
      color: INDIGO, margin: 0 });
    s.addText(st[1], { x: 9.95, y, w: 3.0, h: 0.42, fontFace: F, fontSize: 15, bold: true,
      color: TEXT, margin: 0 });
    s.addText(st[2], { x: 9.95, y: y + 0.4, w: 3.0, h: 0.55, fontFace: F, fontSize: 12,
      color: MUTED, margin: 0 });
  });
  footerBrand(s); pageNum(s, 10);
}

// ============================================================ 11 RESULTS DASHBOARD
{
  const s = P.addSlide();
  s.background = { color: BG_SOFT };
  sectionLabel(s, "Results Dashboard");
  slideTitle(s, "From resume to explainable results");

  // KPI rail on the left
  const kpis = [
    ["90.3 / 100", "ATS score — Excellent band", EMERALD],
    ["55.5%", "top predicted category confidence", INDIGO],
    ["100%", "resume detection confidence", CYAN],
  ];
  kpis.forEach((k, i) => {
    const y = 1.85 + i * 1.55;
    s.addText(k[0], { x: M, y, w: 3.4, h: 0.85, fontFace: F, fontSize: 42, bold: true,
      color: k[2], margin: 0 });
    s.addText(k[1], { x: M, y: y + 0.85, w: 3.5, h: 0.4, fontFace: F, fontSize: 12.5,
      color: MUTED, margin: 0 });
  });

  s.addImage({ path: A + "results_analyze_top.png", x: 4.25, y: 1.62, w: 8.53, h: 5.33,
    shadow: { type: "outer", color: "1E293B", blur: 10, offset: 3, angle: 90, opacity: 0.3 } });
  s.addText("Real output — Sai Teja Resume (updated).docx",
    { x: 4.25, y: 7.0, w: 8.5, h: 0.3, fontFace: MONO, fontSize: 9.5, color: MUTED, margin: 0 });
  footerBrand(s); pageNum(s, 11);
}

// ============================================================ 12 EXPLAINABILITY
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "Explainability");
  slideTitle(s, "Not just a score — we show WHY");

  s.addImage({ path: A + "results_analyze_top.png", x: M, y: 1.62, w: 8.1, h: 5.06,
    shadow: { type: "outer", color: "1E293B", blur: 10, offset: 3, angle: 90, opacity: 0.3 } });

  const ann = [
    ["Factor subscores", "every factor scored 0–100"],
    ["Weights", "shown next to each factor"],
    ["Radar", "factor profile at a glance"],
    ["Score composition", "points each factor contributed"],
    ["Potential score", "the ceiling if flagged fixes are applied"],
    ["Parser checks", "8 pass/fail parseability tests"],
  ];
  ann.forEach((a, i) => {
    const y = 1.75 + i * 0.88;
    s.addText(a[0], { x: 9.35, y, w: 3.4, h: 0.38, fontFace: F, fontSize: 14.5, bold: true,
      color: INDIGO, margin: 0 });
    s.addText(a[1], { x: 9.35, y: y + 0.37, w: 3.4, h: 0.42, fontFace: F, fontSize: 11.5,
      color: MUTED, margin: 0 });
  });

  s.addText("“Every score can be traced back to measurable factors.”",
    { x: M, y: 6.78, w: 8.1, h: 0.3, fontFace: F, fontSize: 12.5, italic: true, color: MUTED, margin: 0 });
  footerBrand(s); pageNum(s, 12);
}

// ============================================================ 13 RECOMMENDATIONS
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "Recommendation Engine");
  slideTitle(s, "Turning scores into action");

  const boxes = [
    ["LOW-SCORING FACTOR", "Content quality\n29 / 100", NAVY2, WHITE],
    ["DETECTED ISSUE", "Only 50% of bullets quantified · weak action verbs · 1 first-person pronoun", INDIGO, WHITE],
    ["RECOMMENDED FIX", "Quantify achievements with metrics — %, $, latency, users", "065F46", WHITE],
  ];
  boxes.forEach((b, i) => {
    const x = M + i * 4.28;
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x, y: 2.1, w: 3.85, h: 1.9, rectRadius: 0.1,
      fill: { color: b[2] }, line: { color: i === 2 ? EMERALD : "none", width: 1.5 } });
    s.addText(b[0], { x: x + 0.25, y: 2.3, w: 3.35, h: 0.35, fontFace: MONO, fontSize: 10.5,
      bold: true, color: i === 0 ? CYAN : (i === 1 ? "A5B4FC" : "6EE7B7"), charSpacing: 2, margin: 0 });
    s.addText(b[1], { x: x + 0.25, y: 2.72, w: 3.35, h: 1.15, fontFace: F, fontSize: 15,
      bold: i === 1, color: b[3], margin: 0 });
    if (i < 2) s.addShape(P.shapes.LINE, { x: x + 3.9, y: 3.05, w: 0.33, h: 0,
      line: { color: MUTED, width: 2.5, endArrowType: "triangle" } });
  });

  s.addText("Every recommendation is prioritized by potential score gain — the engine even computes how many points each fix is worth.",
    { x: M, y: 4.35, w: 12.2, h: 0.6, fontFace: F, fontSize: 15, color: TEXT, margin: 0 });

  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.15, w: 12.23, h: 1.4, rectRadius: 0.1,
    fill: { color: BG_SOFT } });
  s.addText([
    { text: "Examples from the live engine\n", options: { bold: true, fontSize: 12.5, color: TEXT, breakLine: true } },
    { text: "Add these required skills: Docker, MySQL  ·  You already work with Pandas — Machine Learning is a small step  ·  Only 7/14 bullets quantified (50%)",
      options: { fontSize: 13, color: "334155" } },
  ], { x: M + 0.3, y: 5.3, w: 11.6, h: 1.1, fontFace: F, margin: 0 });
  footerBrand(s); pageNum(s, 13);
}

// ============================================================ 14 BEYOND ANALYSIS
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "Beyond Single-Resume Analysis");
  slideTitle(s, "An ecosystem, not a one-shot tool");

  const caps = [
    ["MATCH", "Resume vs one job description", "skills · TF-IDF similarity · experience · education", INDIGO],
    ["RANK", "1 resume × up to 10 job descriptions", "scored, sorted best-fit first, charted", CYAN],
    ["COMPARE", "2–5 resumes × 1 job description", "winner + per-factor gap analysis", EMERALD],
    ["SHORTLIST", "up to 50 resumes × 1 job description", "ranked shortlist · Maybe band · skipped-file reasons", "F59E0B"],
  ];
  caps.forEach((c, i) => {
    const x = M + i * 3.12;
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x, y: 1.95, w: 2.86, h: 3.3, rectRadius: 0.1,
      fill: { color: i === 0 ? NAVY : BG_SOFT }, line: { color: c[3], width: 1.5 } });
    s.addText(c[0], { x: x + 0.22, y: 2.18, w: 2.4, h: 0.5, fontFace: MONO, fontSize: 17,
      bold: true, color: i === 0 ? WHITE : c[3], margin: 0 });
    s.addText(c[1], { x: x + 0.22, y: 2.75, w: 2.45, h: 0.85, fontFace: F, fontSize: 13,
      bold: true, color: i === 0 ? WHITE : TEXT, margin: 0 });
    s.addText(c[2], { x: x + 0.22, y: 3.7, w: 2.45, h: 1.35, fontFace: F, fontSize: 11.5,
      color: i === 0 ? "AEB8CE" : MUTED, margin: 0 });
  });

  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.65, w: 12.23, h: 1.0, rectRadius: 0.1,
    fill: { color: "EEF2FF" } });
  s.addText("All four modes share one scoring engine — the same 7 factors, weights and advice everywhere, plus a JSON API for each.",
    { x: M + 0.3, y: 5.65, w: 11.6, h: 1.0, fontFace: F, fontSize: 14.5, color: INDIGO_D,
      valign: "middle", margin: 0 });
  footerBrand(s); pageNum(s, 14);
}

// ============================================================ 15 TRACKER
{
  const s = P.addSlide();
  s.background = { color: BG_SOFT };
  sectionLabel(s, "Tracking & Progress");
  slideTitle(s, "Measure improvement, not just scores");

  s.addImage({ path: A + "tracker_top.png", x: M, y: 1.62, w: 8.53, h: 5.33,
    shadow: { type: "outer", color: "1E293B", blur: 10, offset: 3, angle: 90, opacity: 0.3 } });

  const items = [
    ["Score trend", "last 50 runs, chronological"],
    ["Progress sparklines", "per resume, run by run"],
    ["First / latest / best", "delta per resume version"],
    ["CSV export", "take the data anywhere"],
  ];
  items.forEach((it, i) => {
    const y = 1.9 + i * 1.18;
    s.addText(it[0], { x: 9.35, y, w: 3.4, h: 0.4, fontFace: F, fontSize: 15, bold: true,
      color: TEXT, margin: 0 });
    s.addText(it[1], { x: 9.35, y: y + 0.38, w: 3.4, h: 0.55, fontFace: F, fontSize: 12,
      color: MUTED, margin: 0 });
  });
  s.addText("Improve → re-run → watch the score climb.",
    { x: 9.35, y: 6.6, w: 3.4, h: 0.6, fontFace: F, fontSize: 12.5, italic: true, color: INDIGO, margin: 0 });
  footerBrand(s); pageNum(s, 15);
}

// ============================================================ 16 ENGINEERING QUALITY
{
  const s = P.addSlide();
  s.background = { color: NAVY };
  sectionLabel(s, "Engineering Quality", CYAN);
  slideTitle(s, "Built to be tested, not just demonstrated", { color: WHITE });

  const metrics = [
    ["159", "automated tests"],
    ["19", "test files"],
    ["4", "validation harnesses"],
    ["9,427", "lines of Python"],
  ];
  metrics.forEach((m2, i) => {
    const x = M + i * 3.12;
    s.addText(m2[0], { x, y: 1.95, w: 2.8, h: 1.15, fontFace: F, fontSize: 64, bold: true,
      color: i === 0 ? EMERALD : WHITE, margin: 0 });
    s.addText(m2[1], { x: x + 0.05, y: 3.12, w: 2.8, h: 0.4, fontFace: F, fontSize: 14,
      color: "AEB8CE", margin: 0 });
  });

  s.addShape(P.shapes.LINE, { x: M, y: 3.85, w: 12.2, h: 0, line: { color: "2A4A7F", width: 1 } });

  const types = ["Unit tests", "Route tests", "Golden regression", "Fuzz / property tests",
    "Concurrency tests", "Real-file validation"];
  types.forEach((t, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = M + col * 4.14, y = 4.15 + row * 0.72;
    s.addShape(P.shapes.OVAL, { x, y: y + 0.12, w: 0.14, h: 0.14, fill: { color: EMERALD } });
    s.addText(t, { x: x + 0.3, y, w: 3.6, h: 0.45, fontFace: F, fontSize: 15, color: WHITE,
      valign: "middle", margin: 0 });
  });

  s.addText("Every claim in this deck is backed by automated validation — 4 harnesses re-run against 19 real resumes.",
    { x: M, y: 6.05, w: 12.2, h: 0.6, fontFace: F, fontSize: 14.5, color: "AEB8CE", margin: 0 });
  footerBrand(s, true); pageNum(s, 16);
}

// ============================================================ 17 PERFORMANCE + PRIVACY
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "Performance & Privacy");
  slideTitle(s, "Fast, local and privacy-aware");

  // left: performance
  s.addText("PERFORMANCE", { x: M, y: 1.72, w: 4, h: 0.3, fontFace: MONO, fontSize: 11.5,
    bold: true, color: INDIGO, charSpacing: 2, margin: 0 });
  const perf = [
    ["4–13 ms", "warm full analysis"],
    ["~30 ms", "first-pass (model load)"],
    ["100–150 ms", "live HTTP round trip"],
    ["≤70 ms / resume", "bulk screening budget: 7 s"],
  ];
  perf.forEach((p2, i) => {
    const y = 2.15 + i * 1.05;
    s.addText(p2[0], { x: M, y, w: 3.6, h: 0.6, fontFace: F, fontSize: 30, bold: true,
      color: i === 0 ? EMERALD : TEXT, margin: 0 });
    s.addText(p2[1], { x: M, y: y + 0.58, w: 4.2, h: 0.35, fontFace: F, fontSize: 12.5,
      color: MUTED, margin: 0 });
  });

  // divider
  s.addShape(P.shapes.LINE, { x: 6.35, y: 1.8, w: 0, h: 4.9, line: { color: LINE, width: 1 } });

  // right: privacy flow
  s.addText("PRIVACY", { x: 6.8, y: 1.72, w: 4, h: 0.3, fontFace: MONO, fontSize: 11.5,
    bold: true, color: "065F46", charSpacing: 2, margin: 0 });
  const priv = [
    "Uploaded files parsed in memory — never written to disk",
    "No resume text, names, emails or phones persisted",
    "Zero external AI calls — no Gemini, no cloud APIs",
    "SQLite stores scores and history only (WAL, migrations)",
    "Optional candidate cache headers only on immutable reports",
  ];
  priv.forEach((p2, i) => {
    const y = 2.2 + i * 0.85;
    s.addShape(P.shapes.OVAL, { x: 6.82, y: y + 0.1, w: 0.14, h: 0.14, fill: { color: EMERALD } });
    s.addText(p2, { x: 7.1, y, w: 5.6, h: 0.75, fontFace: F, fontSize: 13.5, color: TEXT,
      valign: "top", margin: 0 });
  });

  s.addText("Resumes are personal data. Local-only processing is a feature, not an accident.",
    { x: M, y: 6.55, w: 12, h: 0.32, fontFace: F, fontSize: 12.5, italic: true, color: MUTED, margin: 0 });
  footerBrand(s); pageNum(s, 17);
}

// ============================================================ 18 LIMITATIONS + FUTURE
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "Boundaries & Roadmap");
  slideTitle(s, "Current boundaries → next steps");

  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y: 1.75, w: 5.9, h: 4.7, rectRadius: 0.1,
    fill: { color: BG_SOFT } });
  s.addText("CURRENT LIMITATIONS", { x: M + 0.3, y: 2.0, w: 5, h: 0.3, fontFace: MONO,
    fontSize: 11.5, bold: true, color: MUTED, charSpacing: 2, margin: 0 });
  [["Synthetic training corpus", "classifier accuracy is template-bound"],
   ["English-language resumes", "pipeline and lexicon are English-only"],
   ["Scanned / image PDFs", "need OCR — out of scope today"]].forEach((li, i) => {
    const y = 2.5 + i * 1.25;
    s.addText(li[0], { x: M + 0.3, y, w: 5.3, h: 0.4, fontFace: F, fontSize: 15.5, bold: true,
      color: TEXT, margin: 0 });
    s.addText(li[1], { x: M + 0.3, y: y + 0.4, w: 5.3, h: 0.4, fontFace: F, fontSize: 12.5,
      color: MUTED, margin: 0 });
  });

  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: 6.85, y: 1.75, w: 5.9, h: 4.7, rectRadius: 0.1,
    fill: { color: "EEF2FF" } });
  s.addText("NEXT STEPS", { x: 7.15, y: 2.0, w: 5, h: 0.3, fontFace: MONO, fontSize: 11.5,
    bold: true, color: INDIGO, charSpacing: 2, margin: 0 });
  const future = ["Real labeled resume dataset", "Transformer (BERT) classifier",
    "Personalized job recommendations", "Skill-gap + course suggestions",
    "Docker / cloud deployment", "User accounts & auth"];
  future.forEach((f2, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 7.15 + col * 2.85, y = 2.5 + row * 1.0;
    s.addShape(P.shapes.OVAL, { x, y: y + 0.1, w: 0.12, h: 0.12, fill: { color: INDIGO } });
    s.addText(f2, { x: x + 0.24, y, w: 2.6, h: 0.85, fontFace: F, fontSize: 12.5, bold: true,
      color: TEXT, margin: 0 });
  });

  s.addText("The architecture is ready for each step — services are isolated, scored by contract, and fully tested.",
    { x: M, y: 6.6, w: 12, h: 0.32, fontFace: F, fontSize: 12.5, italic: true, color: MUTED, margin: 0 });
  footerBrand(s); pageNum(s, 18);
}

// ============================================================ 19 TEAM
{
  const s = P.addSlide();
  s.background = { color: BG };
  sectionLabel(s, "Team");
  slideTitle(s, "Team & technical contributions");

  const team = [
    ["Saiteja K", "NLP Developer", "text preprocessing · information extraction", INDIGO],
    ["Gnaneswari K", "ML Developer", "TF-IDF + SVM · model evaluation & calibration", CYAN],
    ["Siddhardha P", "Backend & Database", "Flask services · SQLite & history", EMERALD],
    ["Mahalaxmi M", "Frontend & Docs", "UI · testing & documentation", "F59E0B"],
  ];
  team.forEach((t, i) => {
    const x = M + i * 3.12;
    s.addShape(P.shapes.LINE, { x: x + 0.1, y: 2.0, w: 0, h: 2.2, line: { color: t[3], width: 3 } });
    s.addText(t[0], { x: x + 0.35, y: 2.0, w: 2.6, h: 0.5, fontFace: F, fontSize: 19, bold: true,
      color: TEXT, margin: 0 });
    s.addText(t[1], { x: x + 0.35, y: 2.52, w: 2.6, h: 0.4, fontFace: F, fontSize: 13,
      bold: true, color: t[3], margin: 0 });
    s.addText(t[2], { x: x + 0.35, y: 2.95, w: 2.55, h: 1.2, fontFace: F, fontSize: 12,
      color: MUTED, margin: 0 });
  });

  s.addShape(P.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.15, w: 12.23, h: 1.3, rectRadius: 0.1,
    fill: { color: BG_SOFT } });
  s.addText("Department of Computer Science and Engineering  ·  B.Tech Final-Year Project  ·  Academic Year 2025–26",
    { x: M, y: 5.15, w: 12.23, h: 1.3, align: "center", valign: "middle", fontFace: F,
      fontSize: 14, color: "334155", margin: 0 });
  footerBrand(s); pageNum(s, 19);
}

// ============================================================ 20 FINAL
{
  const s = P.addSlide();
  s.background = { color: NAVY };
  s.addText("CONCLUSION", { x: M, y: 1.0, w: 6, h: 0.34, fontFace: F, fontSize: 13, bold: true,
    color: CYAN, charSpacing: 4, margin: 0 });

  const chain = ["RESUME", "NLP", "ML", "ATS SCORE", "ACTION", "IMPROVEMENT"];
  const bw = 1.78, gap = 0.36, y0 = 1.7;
  chain.forEach((c, i) => {
    const x = M + i * (bw + gap);
    s.addShape(P.shapes.ROUNDED_RECTANGLE, { x, y: y0, w: bw, h: 0.66, rectRadius: 0.09,
      fill: { color: i === 3 ? EMERALD : NAVY2 }, line: { color: i === 3 ? EMERALD : "2A4A7F", width: 1.5 } });
    s.addText(c, { x, y: y0, w: bw, h: 0.66, align: "center", valign: "middle", fontFace: MONO,
      fontSize: 12, bold: true, color: i === 3 ? NAVY : WHITE, margin: 0 });
    if (i < chain.length - 1)
      s.addShape(P.shapes.LINE, { x: x + bw + 0.06, y: y0 + 0.33, w: gap - 0.12, h: 0,
        line: { color: "5A6E93", width: 2, endArrowType: "triangle" } });
  });

  s.addText("Intelligent Resume Analyzer", { x: M, y: 3.0, w: 12.2, h: 0.95, fontFace: F,
    fontSize: 44, bold: true, color: WHITE, margin: 0 });
  s.addText("“Analyze. Understand. Improve.”", { x: M, y: 4.05, w: 11, h: 0.55, fontFace: F,
    fontSize: 20, italic: true, color: EMERALD, margin: 0 });

  s.addText("NLP      |      MACHINE LEARNING      |      ATS SCORING      |      JOB MATCHING      |      TRACKING",
    { x: M, y: 4.85, w: 12.2, h: 0.4, fontFace: MONO, fontSize: 12.5, color: "AEB8CE",
      charSpacing: 1, margin: 0 });

  s.addShape(P.shapes.LINE, { x: M, y: 5.75, w: 12.2, h: 0, line: { color: "2A4A7F", width: 1 } });
  s.addText("Thank You", { x: M, y: 6.0, w: 6, h: 0.6, fontFace: F, fontSize: 26, bold: true,
    color: WHITE, margin: 0 });
  s.addText("Questions & Discussion", { x: M, y: 6.62, w: 6, h: 0.4, fontFace: F, fontSize: 15,
    color: "AEB8CE", margin: 0 });
  footerBrand(s, true);
}

P.writeFile({ fileName: "C:/Users/sai/OneDrive/Desktop/NLP/Intelligent_Resume_Analyzer_Presentation.pptx" })
  .then(() => console.log("DECK WRITTEN"));
