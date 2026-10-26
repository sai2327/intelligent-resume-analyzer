const pptxgen = require("pptxgenjs");

// ---------- palette (derived from the product UI: indigo header + green ATS gauge) ----------
const BG_DARK = "1E1B4B";      // indigo-950 — title & closing
const PRIMARY = "4F46E5";      // indigo-600 — the app's header color
const PRIMARY_DARK = "3730A3"; // indigo-800
const PRIMARY_TINT = "EEF2FF"; // indigo-50
const PRIMARY_TINT2 = "E0E7FF";// indigo-100
const ACCENT = "16A34A";       // green-600 — the ATS gauge color
const ACCENT_TINT = "DCFCE7";  // green-50
const TEXT = "1E293B";         // slate-800
const MUTED = "64748B";        // slate-500
const LINE = "E2E8F0";         // slate-200 hairline
const WHITE = "FFFFFF";
const IND_LIGHT = "A5B4FC";    // indigo-300 (light text on dark bg)
const CHIP_DARK = "312E81";    // chip fill on dark bg
const FONT = "Segoe UI";

const W = 13.33, H = 7.5, M = 0.5, CW = W - 2 * M; // 12.33 usable
const MEDIA = "ppt_build/media/";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Saiteja K, Gnaneswari K, Siddhardha P, Mahalaxmi M";
pres.title = "Intelligent Resume Analyzer — Final Review";

const sh = () => ({ type: "outer", color: "1E1B4B", blur: 7, offset: 2, angle: 90, opacity: 0.14 });
const bu = () => ({ code: "2022", indent: 12 });

let pageNo = 0;
function newSlide(dark = false) {
  const s = pres.addSlide();
  s.background = { color: dark ? BG_DARK : WHITE };
  pageNo++;
  return s;
}
function pageNum(s) {
  s.addText(String(pageNo), { x: 12.55, y: 7.06, w: 0.55, h: 0.3, fontSize: 12, fontFace: FONT, color: MUTED, align: "right", margin: 0 });
}
function header(s, kicker, title, dark = false) {
  s.addText(kicker, { x: M, y: 0.40, w: CW, h: 0.28, fontSize: 12, bold: true, fontFace: FONT, color: dark ? IND_LIGHT : PRIMARY, charSpacing: 3, margin: 0 });
  s.addText(title, { x: M, y: 0.68, w: CW, h: 0.62, fontSize: 31, bold: true, fontFace: FONT, color: dark ? WHITE : TEXT, margin: 0 });
}
function card(s, x, y, w, h, fill = WHITE, radius = 0.09) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: LINE, width: 1 }, rectRadius: radius, shadow: sh() });
}
function chip(s, x, y, w, text, fill = PRIMARY_TINT, color = PRIMARY_DARK, h = 0.38, fs = 12, boldTxt = true) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { type: "none" }, rectRadius: h / 2 });
  s.addText(text, { x, y, w, h, fontSize: fs, bold: boldTxt, fontFace: FONT, color, align: "center", valign: "middle", margin: 0 });
}
function hairline(s, x, y, w) {
  s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: LINE, width: 1 } });
}
function downTri(s, cx, y, size = 0.24, color = "C7D2FE") {
  s.addShape(pres.shapes.ISOSCELES_TRIANGLE, { x: cx - size / 2, y, w: size, h: size * 0.85, fill: { color }, line: { type: "none" }, flipV: true });
}
// screenshot in a framed card; returns height used
function shot(s, img, x, y, w, ratio) {
  const h = w / ratio;
  card(s, x - 0.1, y - 0.1, w + 0.2, h + 0.2);
  s.addImage({ path: MEDIA + img, x, y, w, h });
  return h;
}
function statTile(s, x, y, w, h, num, label, numColor = PRIMARY, numSize = 30) {
  card(s, x, y, w, h, PRIMARY_TINT, 0.07);
  s.addText(num, { x: x + 0.15, y: y + 0.08, w: w - 0.3, h: h * 0.52, fontSize: numSize, bold: true, fontFace: FONT, color: numColor, margin: 0 });
  s.addText(label, { x: x + 0.15, y: y + h * 0.58, w: w - 0.3, h: h * 0.40, fontSize: 12, fontFace: FONT, color: MUTED, margin: 0 });
}

// ============================================================ S1 — TITLE (dark)
{
  const s = newSlide(true);
  chip(s, 0.9, 1.05, 1.95, "FINAL REVIEW", ACCENT, WHITE, 0.44, 13);
  s.addText("Intelligent Resume Analyzer", { x: 0.9, y: 1.7, w: 8.6, h: 1.85, fontSize: 52, bold: true, fontFace: FONT, color: WHITE, margin: 0 });
  s.addText("NLP + Machine Learning resume analysis, job matching and ATS score tracking — classify any resume, score it like a real applicant tracking system, and track the improvement over time.", { x: 0.9, y: 3.62, w: 8.3, h: 1.0, fontSize: 16, fontFace: FONT, color: IND_LIGHT, margin: 0 });
  // gauge motif (the app's real headline number from the demo run)
  s.addShape(pres.shapes.OVAL, { x: 10.05, y: 1.85, w: 2.35, h: 2.35, fill: { type: "none" }, line: { color: ACCENT, width: 13 } });
  s.addText([
    { text: "90.3", options: { fontSize: 38, bold: true, color: WHITE, breakLine: true } },
    { text: "out of 100", options: { fontSize: 12, color: IND_LIGHT } },
  ], { x: 10.05, y: 2.5, w: 2.35, h: 1.05, align: "center", valign: "middle", fontFace: FONT, margin: 0 });
  s.addText("Sample ATS audit score from the live demo", { x: 9.55, y: 4.42, w: 3.35, h: 0.55, fontSize: 12, fontFace: FONT, color: IND_LIGHT, align: "center", margin: 0 });
  // team row
  const team = [["Saiteja K", "24B11CS220"], ["Gnaneswari K", "24B11CS190"], ["Siddhardha P", "24B11CS324"], ["Mahalaxmi M", "24B11CS253"]];
  team.forEach((t, i) => {
    const x = 0.9 + i * 2.62;
    s.addText(t[0], { x, y: 5.5, w: 2.5, h: 0.35, fontSize: 15, bold: true, fontFace: FONT, color: WHITE, margin: 0 });
    s.addText(t[1], { x, y: 5.86, w: 2.5, h: 0.3, fontSize: 12, fontFace: FONT, color: IND_LIGHT, margin: 0 });
  });
  hairlineDark(s);
  s.addText("Department of Computer Science and Engineering", { x: 0.9, y: 6.5, w: 8.0, h: 0.35, fontSize: 12.5, fontFace: FONT, color: IND_LIGHT, margin: 0 });
}
function hairlineDark(s) {
  s.addShape(pres.shapes.LINE, { x: 0.9, y: 6.32, w: 11.53, h: 0, line: { color: CHIP_DARK, width: 1 } });
}

// ============================================================ S2 — PROBLEM & MOTIVATION
{
  const s = newSlide();
  header(s, "INTRODUCTION", "Problem Statement & Motivation");
  // left — problem
  s.addText("Resumes are written in free, unstructured text. Recruiters screen them manually — slow, inconsistent and error-prone — and applicants have no objective way to judge their own profile before applying.", { x: M, y: 1.62, w: 5.95, h: 1.15, fontSize: 14, fontFace: FONT, color: TEXT, margin: 0 });
  const pains = [
    ["Slow & inconsistent", "every recruiter applies a different, unseen rubric"],
    ["Unstructured input", "skills and experience are buried in prose, tables and layouts"],
    ["No self-service insight", "students can't tell which job categories fit their profile"],
  ];
  pains.forEach((p, i) => {
    const y = 3.05 + i * 1.28;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: y - 0.08, w: 0.34, h: 0.34, fill: { color: PRIMARY_TINT2 }, line: { type: "none" }, rectRadius: 0.06 });
    s.addText(String(i + 1), { x: M, y: y - 0.08, w: 0.34, h: 0.34, fontSize: 13, bold: true, fontFace: FONT, color: PRIMARY_DARK, align: "center", valign: "middle", margin: 0 });
    s.addText([
      { text: p[0], options: { fontSize: 14.5, bold: true, color: TEXT, breakLine: true } },
      { text: p[1], options: { fontSize: 12.5, color: MUTED } },
    ], { x: M + 0.55, y, w: 5.4, h: 1.1, fontFace: FONT, valign: "top", margin: 0 });
    if (i < 2) hairline(s, M + 0.55, y + 1.13, 5.4);
  });
  // right — motivation
  s.addText("What an NLP system changes", { x: 6.9, y: 1.62, w: 5.93, h: 0.4, fontSize: 17, bold: true, fontFace: FONT, color: TEXT, margin: 0 });
  const motiv = [
    ["Speed", "a full analysis — extraction, classification, scoring — returns in seconds"],
    ["Consistency", "the same transparent rubric and factor weights for every resume"],
    ["Clarity", "detected skills, education and experience are structured and visible"],
    ["Actionability", "prioritized fixes show exactly what to change and how many points it is worth"],
  ];
  motiv.forEach((m, i) => {
    const y = 2.25 + i * 1.18;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.9, y: y + 0.03, w: 0.14, h: 0.14, fill: { color: ACCENT }, line: { type: "none" }, rectRadius: 0.03 });
    s.addText([
      { text: m[0] + " — ", options: { fontSize: 14.5, bold: true, color: TEXT } },
      { text: m[1], options: { fontSize: 13.5, color: TEXT } },
    ], { x: 7.2, y, w: 5.6, h: 1.05, fontFace: FONT, valign: "top", margin: 0 });
  });
  s.addText("Goal: automate resume analysis with NLP and classify resumes into suitable job categories.", { x: 6.9, y: 6.85, w: 5.4, h: 0.4, fontSize: 12.5, italic: true, fontFace: FONT, color: MUTED, margin: 0 });
  pageNum(s);
}

// ============================================================ S3 — OBJECTIVES
{
  const s = newSlide();
  header(s, "SCOPE", "Project Objectives — All Delivered");
  const objs = [
    "Build an NLP-based resume analysis web system",
    "Accept PDF / DOCX uploads with validation",
    "Extract and preprocess resume text (clean, tokenize, lemmatize)",
    "Identify skills, education, experience, projects and certifications",
    "Classify resumes into job categories with TF-IDF + SVM",
    "Score resumes with a multi-factor ATS engine and track history",
  ];
  objs.forEach((o, i) => {
    const y = 1.78 + i * 0.86;
    s.addShape(pres.shapes.OVAL, { x: M, y: y + 0.02, w: 0.36, h: 0.36, fill: { color: ACCENT_TINT }, line: { type: "none" } });
    s.addText("\u2713", { x: M, y: y + 0.02, w: 0.36, h: 0.36, fontSize: 14, bold: true, fontFace: FONT, color: ACCENT, align: "center", valign: "middle", margin: 0 });
    s.addText(o, { x: M + 0.55, y: y - 0.05, w: 5.55, h: 0.75, fontSize: 14.5, fontFace: FONT, color: TEXT, valign: "middle", margin: 0 });
    if (i < 5) hairline(s, M + 0.55, y + 0.68, 5.55);
  });
  // right — expected outcome + status
  card(s, 6.9, 1.7, 5.93, 2.55, PRIMARY_TINT);
  s.addText("Expected outcome", { x: 7.15, y: 1.92, w: 5.4, h: 0.35, fontSize: 15, bold: true, fontFace: FONT, color: PRIMARY_DARK, margin: 0 });
  s.addText("From a single uploaded resume, the user gets their profile summary, a predicted job category with confidence, a transparent ATS score with prioritized fixes, and a history of every run to measure improvement.", { x: 7.15, y: 2.32, w: 5.45, h: 1.75, fontSize: 13.5, fontFace: FONT, color: TEXT, margin: 0 });
  card(s, 6.9, 4.5, 5.93, 2.25, WHITE);
  s.addText([
    { text: "6 / 6 ", options: { fontSize: 34, bold: true, color: ACCENT } },
    { text: "objectives delivered", options: { fontSize: 17, bold: true, color: TEXT } },
  ], { x: 7.15, y: 4.72, w: 5.45, h: 0.6, fontFace: FONT, margin: 0 });
  s.addText("Demonstrated live on the following slides — upload, results, scoring, tracker and history.", { x: 7.15, y: 5.42, w: 5.45, h: 1.1, fontSize: 13, fontFace: FONT, color: MUTED, margin: 0 });
  pageNum(s);
}

// ============================================================ S4 — ARCHITECTURE
{
  const s = newSlide();
  header(s, "ARCHITECTURE", "System Architecture & Modules");
  const bandY = [1.62, 3.28, 4.94], bandH = 1.42;
  const bands = [
    { label: "Interface", fill: PRIMARY_TINT2, labelColor: PRIMARY_DARK, chips: ["Web UI — upload, results, tracker, history", "JSON API — 4 endpoints", "CSV / text / JSON report exports"] },
    { label: "NLP & ML\nservices", fill: PRIMARY_TINT, labelColor: PRIMARY_DARK, chips: ["Document Parser — PDF/DOCX, in-memory", "Resume Detector", "Text Preprocessor — LRU-cached", "Information Extractor", "Skill Matcher — 178 skills", "Classifier — TF-IDF + SVM"] },
    { label: "Scoring &\nstorage", fill: ACCENT_TINT, labelColor: "166534", chips: ["ATS Scorer — 7 factors", "Matching Engine", "Recommendation Engine", "SQLite history", "Gemini — optional phrasing"] },
  ];
  bands.forEach((b, bi) => {
    const y = bandY[bi];
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y, w: CW, h: bandH, fill: { color: b.fill }, line: { type: "none" }, rectRadius: 0.08 });
    s.addText(b.label, { x: M + 0.18, y: y + 0.12, w: 1.45, h: bandH - 0.24, fontSize: 13.5, bold: true, fontFace: FONT, color: b.labelColor, valign: "middle", margin: 0 });
    const n = b.chips.length, gap = 0.12;
    const cw = (CW - 1.75 - (n - 1) * gap) / n;
    b.chips.forEach((c, ci) => {
      const x = M + 1.75 + ci * (cw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: y + 0.22, w: cw, h: bandH - 0.44, fill: { color: WHITE }, line: { color: LINE, width: 1 }, rectRadius: 0.06 });
      s.addText(c, { x: x + 0.08, y: y + 0.22, w: cw - 0.16, h: bandH - 0.44, fontSize: 12, fontFace: FONT, color: TEXT, align: "center", valign: "middle", margin: 0 });
    });
    if (bi < 2) downTri(s, W / 2, y + bandH + 0.03);
  });
  s.addText("app.py keeps HTTP routes only; every capability lives in an isolated service under services/ — config and secrets come from .env", { x: M, y: 6.62, w: CW, h: 0.4, fontSize: 12.5, italic: true, fontFace: FONT, color: MUTED, align: "center", margin: 0 });
  pageNum(s);
}

// ============================================================ S5 — TECH STACK
{
  const s = newSlide();
  header(s, "TOOLS", "Technology Stack");
  const rows = [
    ["Python 3", "core application — Flask server, 15+ isolated services under services/"],
    ["NLTK · spaCy", "tokenization, stop-word removal, lemmatization, name detection"],
    ["scikit-learn", "TF-IDF vectorizer + LinearSVC wrapped in CalibratedClassifierCV"],
    ["pypdf · python-docx", "PDF / DOCX text extraction — fully in-memory"],
    ["Flask · Bootstrap · JS", "web interface, results pages, tracker and history views"],
    ["SQLite", "analysis history, score tracking and resume progress — via database/"],
    ["waitress · pytest", "production WSGI server; 149-test quality suite"],
    ["VS Code · Git · Jupyter", "development, version control and model experiments"],
  ];
  rows.forEach((r, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = M + col * 6.42, y = 1.78 + row * 1.28;
    s.addText([
      { text: r[0], options: { fontSize: 15, bold: true, color: PRIMARY_DARK, breakLine: true } },
      { text: r[1], options: { fontSize: 12.5, color: MUTED } },
    ], { x, y, w: 5.9, h: 1.1, fontFace: FONT, margin: 0 });
    if (row < 3) hairline(s, x, y + 1.06, 5.9);
  });
  s.addText("Everything runs locally — no data leaves the machine. Gemini is used only if an API key is configured.", { x: M, y: 6.85, w: CW, h: 0.35, fontSize: 12.5, italic: true, fontFace: FONT, color: MUTED, align: "center", margin: 0 });
  pageNum(s);
}

// ============================================================ S6 — WORKFLOW
{
  const s = newSlide();
  header(s, "PIPELINE", "End-to-End Workflow");
  const steps = [
    ["Upload", "PDF / DOCX resume, up to 10 MB"],
    ["Validate & detect", "file checks; non-resumes are refused"],
    ["Extract text", "pypdf / python-docx, in memory"],
    ["Preprocess", "clean \u2192 tokenize \u2192 stop-words \u2192 lemmatize"],
    ["Extract info", "skills, education, experience, projects, certifications"],
    ["Classify", "TF-IDF \u2192 calibrated SVM \u2192 job category"],
    ["Score", "7-factor ATS audit + prioritized fixes"],
    ["Deliver", "results page, history tracker, CSV / JSON exports"],
  ];
  const bw = 2.92, bh = 1.62, gapX = (CW - 4 * bw) / 3;
  function stepBox(st, x, y, n) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: bh, fill: { color: n <= 4 ? PRIMARY_TINT : ACCENT_TINT }, line: { type: "none" }, rectRadius: 0.08, shadow: sh() });
    s.addText(String(n), { x: x + 0.14, y: y + 0.12, w: 0.5, h: 0.5, fontSize: 20, bold: true, fontFace: FONT, color: n <= 4 ? PRIMARY : ACCENT, margin: 0 });
    s.addText([
      { text: st[0], options: { fontSize: 14.5, bold: true, color: TEXT, breakLine: true } },
      { text: st[1], options: { fontSize: 12, color: MUTED } },
    ], { x: x + 0.14, y: y + 0.6, w: bw - 0.28, h: bh - 0.72, fontFace: FONT, margin: 0 });
  }
  // row 1: steps 1-4 left->right ; row 2: steps 5-8 right->left (serpentine)
  for (let i = 0; i < 4; i++) {
    const x = M + i * (bw + gapX);
    stepBox(steps[i], x, 1.72, i + 1);
    if (i < 3) s.addText("\u2192", { x: x + bw, y: 2.3, w: gapX, h: 0.45, fontSize: 20, bold: true, fontFace: FONT, color: "94A3B8", align: "center", margin: 0 });
  }
  downTri(s, M + 3 * (bw + gapX) + bw / 2, 3.52, 0.3, PRIMARY);
  for (let i = 0; i < 4; i++) {
    const n = 5 + i, col = 3 - i; // place 5 at right, 8 at left
    const x = M + col * (bw + gapX);
    stepBox(steps[i + 4], x, 4.02, n);
    if (i < 3) s.addText("\u2190", { x: x - gapX, y: 4.6, w: gapX, h: 0.45, fontSize: 20, bold: true, fontFace: FONT, color: "94A3B8", align: "center", margin: 0 });
  }
  s.addText("Uploaded files are parsed in memory and never written to disk — the database stores scores and file names only.", { x: M, y: 6.85, w: CW, h: 0.35, fontSize: 12.5, italic: true, fontFace: FONT, color: MUTED, align: "center", margin: 0 });
  pageNum(s);
}

// ============================================================ S7 — CLASSIFICATION MODEL
{
  const s = newSlide();
  header(s, "MACHINE LEARNING", "Resume Classification Model");
  // left: training/serving flow
  const flow = [
    "Cleaned resume text",
    "TF-IDF vectors — unigrams + bigrams, sublinear TF",
    "LinearSVC — linear support vector machine",
    "CalibratedClassifierCV — sigmoid, 5-fold CV",
    "Predicted category + calibrated confidence",
  ];
  flow.forEach((f, i) => {
    const y = 1.66 + i * 0.86;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y, w: 5.0, h: 0.6, fill: { color: i === 4 ? ACCENT_TINT : PRIMARY_TINT }, line: { type: "none" }, rectRadius: 0.07 });
    s.addText(f, { x: M + 0.18, y, w: 4.7, h: 0.6, fontSize: 12.5, bold: i === 4, fontFace: FONT, color: i === 4 ? "166534" : TEXT, valign: "middle", margin: 0 });
    if (i < 4) downTri(s, M + 2.5, y + 0.61, 0.2);
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.92, w: 5.0, h: 1.22, fill: { color: "FEF9C3" }, line: { type: "none" }, rectRadius: 0.07 });
  s.addText("Honest caveat: trained on a synthetic, template-based demo dataset — the 1.00 accuracy reflects clean separability, not real-world performance. A real labeled dataset is future work.", { x: M + 0.14, y: 6.0, w: 4.72, h: 1.06, fontSize: 12, italic: true, fontFace: FONT, color: "713F12", margin: 0 });
  // right: stats + categories
  const tiles = [["1.00", "test accuracy (252 held-out rows)"], ["9", "job categories"], ["1,260", "labeled resumes (1,008 train / 252 test)"], ["5-fold", "cross-validated sigmoid calibration"]];
  tiles.forEach((t, i) => {
    const x = 6.0 + (i % 2) * 3.2, y = 1.66 + Math.floor(i / 2) * 1.42;
    statTile(s, x, y, 2.95, 1.22, t[0], t[1]);
  });
  s.addText("Predicted categories", { x: 6.0, y: 4.62, w: 6.15, h: 0.32, fontSize: 13, bold: true, fontFace: FONT, color: TEXT, margin: 0 });
  const cats = ["Business Analyst", "Cloud Engineer", "Data Analyst", "Data Scientist", "DevOps Engineer", "ML Engineer", "Software Developer", "UI/UX Designer", "Web Developer"];
  cats.forEach((c, i) => {
    const x = 6.0 + (i % 3) * 2.1, y = 5.02 + Math.floor(i / 3) * 0.62;
    chip(s, x, y, 1.96, c, i === 6 ? ACCENT_TINT : PRIMARY_TINT, i === 6 ? "166534" : PRIMARY_DARK, 0.48, 12);
  });
  pageNum(s);
}

// ============================================================ S8 — ATS METHODOLOGY
{
  const s = newSlide();
  header(s, "SCORING", "ATS Score Methodology");
  s.addText("Weighted factors — resume vs job description", { x: M, y: 1.58, w: 7.0, h: 0.32, fontSize: 14, bold: true, fontFace: FONT, color: TEXT, margin: 0 });
  s.addChart(pres.charts.BAR, [{
    name: "Weight",
    labels: ["Education", "Content quality", "Format & parsing", "Job title match", "Experience", "Skills match", "Keyword coverage"],
    values: [5, 10, 10, 10, 15, 25, 25],
  }], {
    x: M, y: 2.0, w: 7.1, h: 3.55, barDir: "bar",
    varyColors: true,
    chartColors: ["4F46E5", "4F46E5", "4F46E5", "4F46E5", "4F46E5", "16A34A", "16A34A"],
    chartArea: { fill: { color: "FFFFFF" } },
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', dataLabelColor: TEXT, dataLabelFontSize: 12, dataLabelFontFace: FONT,
    catAxisLabelColor: TEXT, catAxisLabelFontSize: 12, catAxisLabelFontFace: FONT, catAxisLineShow: false,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, barGapWidthPct: 45, valAxisMaxVal: 30,
  });
  s.addText("Green: what keyword-parsing ATS platforms (Taleo, Workday, iCIMS…) rank on first. Any factor that cannot be computed is excluded and its weight redistributed — missing information never drags the score.", { x: M, y: 5.7, w: 7.1, h: 0.85, fontSize: 12.5, italic: true, fontFace: FONT, color: MUTED, margin: 0 });
  // right: standalone audit + grade bands
  s.addText("Standalone resume audit (no JD)", { x: 8.0, y: 1.58, w: 4.83, h: 0.32, fontSize: 14, bold: true, fontFace: FONT, color: TEXT, margin: 0 });
  const stand = [["Format & parseability", 35], ["Content quality", 30], ["Skill breadth", 20], ["Education present", 15]];
  stand.forEach((r, i) => {
    const y = 2.05 + i * 0.62;
    s.addText(r[0], { x: 8.0, y, w: 2.9, h: 0.3, fontSize: 12.5, fontFace: FONT, color: TEXT, margin: 0 });
    s.addText(r[1] + "%", { x: 11.6, y, w: 1.2, h: 0.3, fontSize: 12.5, bold: true, fontFace: FONT, color: PRIMARY_DARK, align: "right", margin: 0 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.0, y: y + 0.3, w: 4.8, h: 0.12, fill: { color: LINE }, line: { type: "none" }, rectRadius: 0.06 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.0, y: y + 0.3, w: 4.8 * (r[1] / 35), h: 0.12, fill: { color: PRIMARY }, line: { type: "none" }, rectRadius: 0.06 });
  });
  s.addText("Grade bands", { x: 8.0, y: 4.72, w: 4.8, h: 0.3, fontSize: 13, bold: true, fontFace: FONT, color: TEXT, margin: 0 });
  const grades = [[">=85 Excellent", ACCENT_TINT, "166534"], [">=70 Strong", PRIMARY_TINT, PRIMARY_DARK], [">=55 Fair", PRIMARY_TINT2, PRIMARY_DARK], [">=40 Needs work", "FEF3C7", "92400E"], ["<40 High risk", "FEE2E2", "991B1B"]];
  grades.forEach((g, i) => {
    chip(s, 8.0, 5.02 + i * 0.47, 2.6, g[0], g[1], g[2], 0.4, 12);
  });
  pageNum(s);
}

// ============================================================ S9 — FEATURE 01 UPLOAD UI
{
  const s = newSlide();
  header(s, "FEATURE 01", "Resume Upload & Analysis Interface");
  const h = shot(s, "slide12_4.png", (W - 10.35) / 2, 1.68, 10.35, 1263 / 553);
  s.addText([
    { text: "One screen, four analysis modes: ", options: { bold: true, color: TEXT } },
    { text: "standalone audit · match against one job description · rank up to 10 JDs · compare 2–5 resumes. Advanced options cover ATS strictness (lenient / standard / strict) and a target job-title override.", options: { color: MUTED } },
  ], { x: M + 0.2, y: 1.68 + h + 0.26, w: 11.8, h: 0.8, fontSize: 13.5, fontFace: FONT, margin: 0 });
  pageNum(s);
}

// ============================================================ S10 — FEATURE 02 RESULTS
{
  const s = newSlide();
  header(s, "FEATURE 02", "Analysis Results & Category Prediction");
  const h = shot(s, "slide13_4.png", M, 1.85, 8.35, 1252 / 543);
  s.addText("Candidate information, predicted category and the ATS gauge land on one screen; every run is linked to JSON, text-report and score-history views.", { x: M, y: 1.85 + h + 0.25, w: 8.35, h: 0.8, fontSize: 13, fontFace: FONT, color: MUTED, margin: 0 });
  const stats = [
    ["90.3 / 100", "ATS score — standalone audit of the demo resume", ACCENT],
    ["51.6%", "top prediction: Software Developer — Data Analyst (10.1%) and ML Engineer (7.5%) follow", PRIMARY],
    ["100%", "resume-detection confidence — thesis, report or invoice uploads are politely refused instead of scored", PRIMARY],
  ];
  stats.forEach((t, i) => {
    const y = 1.85 + i * 1.62;
    card(s, 9.15, y, 3.68, 1.42, PRIMARY_TINT, 0.07);
    s.addText(t[0], { x: 9.35, y: y + 0.1, w: 3.3, h: 0.5, fontSize: 24, bold: true, fontFace: FONT, color: t[2], margin: 0 });
    s.addText(t[1], { x: 9.35, y: y + 0.62, w: 3.3, h: 0.75, fontSize: 12, fontFace: FONT, color: MUTED, margin: 0 });
  });
  pageNum(s);
}

// ============================================================ S11 — FEATURE 03 ATS BREAKDOWN
{
  const s = newSlide();
  header(s, "FEATURE 03", "ATS Score Breakdown — Fully Explained");
  const h = shot(s, "slide14_4.png", (W - 10.15) / 2, 1.68, 10.15, 1179 / 527);
  s.addText([
    { text: "No black box: ", options: { bold: true, color: TEXT } },
    { text: "every factor shows its subscore and weight, with parser checks and the full score composition. A separate potential score shows the honest upper bound — only factors the user can change are capped.", options: { color: MUTED } },
  ], { x: M + 0.2, y: 1.68 + h + 0.26, w: 11.8, h: 0.8, fontSize: 13.5, fontFace: FONT, margin: 0 });
  pageNum(s);
}

// ============================================================ S12 — FEATURE 04 RECOMMENDATIONS
{
  const s = newSlide();
  header(s, "FEATURE 04", "Recommendations & Detected Skills");
  const h = shot(s, "slide15_4.png", (W - 10.15) / 2, 1.68, 10.15, 1189 / 533);
  s.addText([
    { text: "Prioritized, specific fixes ", options: { bold: true, color: TEXT } },
    { text: "ordered by potential score gain — each suggestion names the exact section to change. Detected skills are grouped (languages, frontend, databases, AI/ML), and adjacent-skill advice points out skills you are one step away from.", options: { color: MUTED } },
  ], { x: M + 0.2, y: 1.68 + h + 0.26, w: 11.8, h: 0.8, fontSize: 13.5, fontFace: FONT, margin: 0 });
  pageNum(s);
}

// ============================================================ S13 — FEATURE 05 MATCH / RANK / COMPARE
{
  const s = newSlide();
  header(s, "FEATURE 05", "Job Match, Multi-JD Ranking & Comparison");
  const cards = [
    { tag: "MATCH", title: "Job match score", body: null, rows: [["Skills", "50%"], ["TF-IDF text similarity", "25%"], ["Experience", "15%"], ["Education", "10%"]], note: "A transparent, env-tunable weighted blend." },
    { tag: "RANK", title: "Multi-JD ranking", rows: null, bullets: ["Paste up to 10 job descriptions", "Ranked best-fit first for your resume", "Per-JD factor breakdown", "Weak JDs flagged by the quality checker"] },
    { tag: "COMPARE", title: "Resume comparison", rows: null, bullets: ["2–5 resumes head-to-head vs a JD", "Winner card + per-factor gap table", "Potential score for every resume", "Also exposed as POST /api/compare"] },
  ];
  cards.forEach((c, ci) => {
    const x = M + ci * 4.19, y = 1.62, cw = 3.95, ch = 4.55;
    card(s, x, y, cw, ch);
    chip(s, x + 0.25, y + 0.25, 1.35, c.tag, ci === 0 ? ACCENT_TINT : PRIMARY_TINT, ci === 0 ? "166534" : PRIMARY_DARK, 0.36, 11.5);
    s.addText(c.title, { x: x + 0.25, y: y + 0.75, w: cw - 0.5, h: 0.4, fontSize: 17, bold: true, fontFace: FONT, color: TEXT, margin: 0 });
    if (c.rows) {
      c.rows.forEach((r, ri) => {
        const ry = y + 1.35 + ri * 0.62;
        s.addText(r[0], { x: x + 0.25, y: ry, w: 2.5, h: 0.35, fontSize: 13, fontFace: FONT, color: TEXT, margin: 0 });
        s.addText(r[1], { x: x + cw - 1.05, y: ry, w: 0.8, h: 0.35, fontSize: 13, bold: true, fontFace: FONT, color: PRIMARY_DARK, align: "right", margin: 0 });
        if (ri < 3) hairline(s, x + 0.25, ry + 0.44, cw - 0.5);
      });
      s.addText(c.note, { x: x + 0.25, y: y + 3.85, w: cw - 0.5, h: 0.6, fontSize: 12, italic: true, fontFace: FONT, color: MUTED, margin: 0 });
    }
    if (c.bullets) {
      s.addText(c.bullets.map((b, bi) => ({ text: b, options: { bullet: bu(), breakLine: true, bulletColor: "94A3B8" } })), { x: x + 0.25, y: y + 1.35, w: cw - 0.5, h: 2.9, fontSize: 13, fontFace: FONT, color: TEXT, paraSpaceAfter: 10, valign: "top", margin: 0 });
    }
  });
  s.addText("All three flows are also available as JSON endpoints — /api/match · /api/rank-jds · /api/compare — for programmatic access.", { x: M, y: 6.55, w: CW, h: 0.35, fontSize: 12.5, italic: true, fontFace: FONT, color: MUTED, align: "center", margin: 0 });
  pageNum(s);
}

// ============================================================ S14 — FEATURE 06 TRACKER
{
  const s = newSlide();
  header(s, "FEATURE 06", "ATS Tracker Dashboard");
  const h = shot(s, "slide16_4.png", (W - 10.5) / 2, 1.68, 10.5, 1251 / 539);
  s.addText([
    { text: "Every analysis run is recorded: ", options: { bold: true, color: TEXT } },
    { text: "average and best ATS score, average job-match value, and a score-trend chart across recent runs. The full history downloads as CSV; each run keeps its JSON details.", options: { color: MUTED } },
  ], { x: M + 0.2, y: 1.68 + h + 0.26, w: 11.8, h: 0.8, fontSize: 13.5, fontFace: FONT, margin: 0 });
  pageNum(s);
}

// ============================================================ S15 — FEATURE 07 PROGRESS + HISTORY
{
  const s = newSlide();
  header(s, "FEATURE 07", "Resume Progress & Analysis History");
  const h1 = shot(s, "slide17_4.png", M, 1.72, 5.95, 1091 / 533);
  const h2 = shot(s, "slide18_4.png", 6.88, 1.72, 5.95, 1132 / 532);
  s.addText([
    { text: "Resume progress — ", options: { bold: true, color: TEXT } },
    { text: "resumes analyzed more than once show first \u2192 latest \u2192 best scores with a trend badge.", options: { color: MUTED } },
  ], { x: M, y: 1.72 + h1 + 0.24, w: 5.95, h: 0.85, fontSize: 12.5, fontFace: FONT, margin: 0 });
  s.addText([
    { text: "Analysis history — ", options: { bold: true, color: TEXT } },
    { text: "each run logs date, resume, analysis type, ATS score, grade and job-match, with JSON details one click away.", options: { color: MUTED } },
  ], { x: 6.88, y: 1.72 + h2 + 0.24, w: 5.95, h: 0.85, fontSize: 12.5, fontFace: FONT, margin: 0 });
  const strip = [["first \u2192 latest \u2192 best", "tracked per resume file"], ["grade + job-match", "stored for every run"], ["CSV export", "full tracker history downloads"]];
  strip.forEach((t, i) => {
    const x = M + i * 4.19;
    chip(s, x, 6.35, 3.95, t[0], PRIMARY_TINT, PRIMARY_DARK, 0.44, 12.5);
    s.addText(t[1], { x, y: 6.88, w: 3.95, h: 0.3, fontSize: 12, fontFace: FONT, color: MUTED, align: "center", margin: 0 });
  });
  pageNum(s);
}

// ============================================================ S16 — TESTING & VALIDATION
{
  const s = newSlide();
  header(s, "QUALITY", "Testing & Validation");
  const stats = [["149", "automated tests — all passing"], ["8 \u00d7 8", "cross-domain validation matrix"], ["+15\u201323 pts", "score gain when the tool's advice is followed"], ["100%", "suite pass rate on every run"]];
  stats.forEach((t, i) => {
    const x = M + i * 3.14;
    card(s, x, 1.66, 2.9, 1.55, PRIMARY_TINT, 0.07);
    s.addText(t[0], { x: x + 0.18, y: 1.78, w: 2.55, h: 0.62, fontSize: 30, bold: true, fontFace: FONT, color: i === 2 ? ACCENT : PRIMARY, margin: 0 });
    s.addText(t[1], { x: x + 0.18, y: 2.44, w: 2.55, h: 0.68, fontSize: 12, fontFace: FONT, color: MUTED, margin: 0 });
  });
  const rows = [
    ["Unit · route · golden regression", "canonical scores for the fixture resume/JD are pinned — any scoring change must consciously update them"],
    ["Fuzz & property tests", "a seeded random corpus asserts bounds, determinism and monotonicity — adding a missing skill never lowers the score"],
    ["Cross-domain matrix", "each tailored resume ranks its own JD first across 8 domains; matched > partial > weak ordering holds everywhere"],
    ["Input robustness", "CRLF, unicode, unpunctuated and degenerate inputs handled; tests run on isolated temp databases, never the real one"],
  ];
  rows.forEach((r, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = M + col * 6.42, y = 3.62 + row * 1.62;
    s.addText([
      { text: r[0], options: { fontSize: 14.5, bold: true, color: TEXT, breakLine: true } },
      { text: r[1], options: { fontSize: 12.5, color: MUTED } },
    ], { x, y, w: 5.9, h: 1.45, fontFace: FONT, margin: 0 });
    if (row < 1) hairline(s, x, y + 1.42, 5.9);
  });
  pageNum(s);
}

// ============================================================ S17 — PRIVACY & ENGINEERING
{
  const s = newSlide();
  header(s, "ENGINEERING", "Privacy & Engineering Practices");
  const rows = [
    ["In-memory parsing", "uploaded files are parsed and discarded — never written to disk"],
    ["No PII stored", "the database keeps scores and file names only — never resume text, names, emails or phone numbers"],
    ["Memoized pipeline", "preprocessing, JD parsing and skill scanning are cached — about 5 ms per analysis once warm"],
    ["Env-driven configuration", "all weights, limits and keys load from .env — nothing machine-specific is hardcoded"],
    ["Structured logging", "every request and analysis run is logged to logs/app.log for debugging"],
    ["Optional Gemini enhancement", "AI only re-phrases recommendation wording — it never computes or alters scores"],
  ];
  rows.forEach((r, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = M + col * 6.42, y = 1.85 + row * 1.62;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: y - 0.05, w: 0.3, h: 0.3, fill: { color: ACCENT_TINT }, line: { type: "none" }, rectRadius: 0.06 });
    s.addText("\u2713", { x, y: y - 0.05, w: 0.3, h: 0.3, fontSize: 13, bold: true, fontFace: FONT, color: ACCENT, align: "center", valign: "middle", margin: 0 });
    s.addText([
      { text: r[0], options: { fontSize: 14.5, bold: true, color: TEXT, breakLine: true } },
      { text: r[1], options: { fontSize: 12.5, color: MUTED } },
    ], { x: x + 0.48, y, w: 5.45, h: 1.45, fontFace: FONT, valign: "top", margin: 0 });
    if (row < 1) hairline(s, x + 0.48, y + 1.42, 5.45);
  });
  s.addText("Privacy is a design constraint, not a setting — the resume content never persists anywhere.", { x: M, y: 6.85, w: CW, h: 0.35, fontSize: 12.5, italic: true, fontFace: FONT, color: MUTED, align: "center", margin: 0 });
  pageNum(s);
}

// ============================================================ S18 — TEAM
{
  const s = newSlide();
  header(s, "TEAM", "Team Contributions");
  const team = [
    ["SK", "Saiteja K", "24B11CS220", "NLP Developer", ["Text preprocessing pipeline", "Information extraction — skills, education, experience"]],
    ["GK", "Gnaneswari K", "24B11CS190", "ML Developer", ["TF-IDF + SVM model training", "Model evaluation & calibration"]],
    ["SP", "Siddhardha P", "24B11CS324", "Backend & DB", ["Flask routes & upload handling", "SQLite integration & history"]],
    ["MM", "Mahalaxmi M", "24B11CS253", "Frontend & Docs", ["Bootstrap UI & visualization", "Testing, documentation, reviews"]],
  ];
  team.forEach((t, i) => {
    const x = M + i * 3.14, y = 1.75, cw = 2.9, ch = 4.7;
    card(s, x, y, cw, ch);
    s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: y + 0.3, w: 0.85, h: 0.85, fill: { color: PRIMARY_TINT2 }, line: { type: "none" } });
    s.addText(t[0], { x: x + 0.25, y: y + 0.3, w: 0.85, h: 0.85, fontSize: 17, bold: true, fontFace: FONT, color: PRIMARY_DARK, align: "center", valign: "middle", margin: 0 });
    s.addText(t[1], { x: x + 0.25, y: y + 1.35, w: cw - 0.5, h: 0.35, fontSize: 15, bold: true, fontFace: FONT, color: TEXT, margin: 0 });
    s.addText(t[2], { x: x + 0.25, y: y + 1.7, w: cw - 0.5, h: 0.3, fontSize: 12, fontFace: FONT, color: MUTED, margin: 0 });
    chip(s, x + 0.25, y + 2.12, 1.9, t[3], ACCENT_TINT, "166534", 0.4, 11.5);
    s.addText(t[4].map((b, bi) => ({ text: b, options: { bullet: bu(), breakLine: true, bulletColor: "94A3B8" } })), { x: x + 0.25, y: y + 2.72, w: cw - 0.45, h: 1.8, fontSize: 12.5, fontFace: FONT, color: TEXT, paraSpaceAfter: 8, valign: "top", margin: 0 });
  });
  pageNum(s);
}

// ============================================================ S19 — CONCLUSION & FUTURE
{
  const s = newSlide();
  header(s, "WRAP-UP", "Conclusion & Future Enhancements");
  s.addText("The system automates resume analysis end-to-end: NLP extracts and structures resume content, a calibrated TF-IDF + SVM model predicts the job category, and a transparent 7-factor ATS engine scores every resume against real applicant-tracking-system behaviour — turning hours of manual screening into seconds of consistent, explainable feedback, with history to measure progress.", { x: M, y: 1.7, w: 6.35, h: 2.1, fontSize: 14, fontFace: FONT, color: TEXT, margin: 0 });
  s.addText("Delivered in this project", { x: M, y: 4.0, w: 6.35, h: 0.35, fontSize: 14, bold: true, fontFace: FONT, color: TEXT, margin: 0 });
  const deliv = [["Web application", 1.85], ["JSON API — 4 endpoints", 2.35], ["9-category classifier", 2.1], ["7-factor ATS engine", 2.1], ["History & progress tracker", 2.6], ["149 passing tests", 1.8]];
  let dx = M, dy = 4.45;
  deliv.forEach((d) => {
    if (dx + d[1] > M + 6.35) { dx = M; dy += 0.55; }
    chip(s, dx, dy, d[1], d[0], PRIMARY_TINT, PRIMARY_DARK, 0.42, 12);
    dx += d[1] + 0.15;
  });
  card(s, 7.35, 1.7, 5.48, 5.3, PRIMARY_TINT);
  s.addText("Future enhancements", { x: 7.6, y: 1.95, w: 5.0, h: 0.4, fontSize: 16, bold: true, fontFace: FONT, color: PRIMARY_DARK, margin: 0 });
  const fut = [
    "Train on a real, labeled resume dataset; move to a Transformer / BERT-based classifier",
    "Personalized job recommendations from the best-matching JDs",
    "Skill-gap analysis with course suggestions per target role",
    "Resume-vs-resume leaderboard for campus placement cells",
    "Docker / cloud deployment with user accounts",
  ];
  fut.forEach((f, i) => {
    const y = 2.5 + i * 0.92;
    s.addShape(pres.shapes.OVAL, { x: 7.6, y: y - 0.07, w: 0.34, h: 0.34, fill: { color: WHITE }, line: { color: PRIMARY, width: 1.25 } });
    s.addText(String(i + 1), { x: 7.6, y: y - 0.07, w: 0.34, h: 0.34, fontSize: 12.5, bold: true, fontFace: FONT, color: PRIMARY, align: "center", valign: "middle", margin: 0 });
    s.addText(f, { x: 8.08, y, w: 4.6, h: 0.85, fontSize: 12.5, fontFace: FONT, color: TEXT, valign: "top", margin: 0 });
  });
  pageNum(s);
}

// ============================================================ S20 — CLOSING (dark)
{
  const s = newSlide(true);
  s.addText("Thank You", { x: 0, y: 2.0, w: W, h: 1.1, fontSize: 54, bold: true, fontFace: FONT, color: WHITE, align: "center", margin: 0 });
  s.addText("Intelligent Resume Analyzer — NLP + Machine Learning", { x: 0, y: 3.2, w: W, h: 0.45, fontSize: 17, fontFace: FONT, color: IND_LIGHT, align: "center", margin: 0 });
  const chips = [["9 job categories", 2.1], ["7-factor ATS score", 2.15], ["149 tests · 100% pass", 2.5], ["~5 ms per analysis (warm)", 2.6]];
  let total = chips.reduce((a, c) => a + c[1], 0) + 0.45;
  let cx = (W - total) / 2;
  chips.forEach((c) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: 4.15, w: c[1], h: 0.5, fill: { color: CHIP_DARK }, line: { type: "none" }, rectRadius: 0.25 });
    s.addText(c[0], { x: cx, y: 4.15, w: c[1], h: 0.5, fontSize: 12.5, bold: true, fontFace: FONT, color: WHITE, align: "center", valign: "middle", margin: 0 });
    cx += c[1] + 0.15;
  });
  s.addText("Saiteja K · Gnaneswari K · Siddhardha P · Mahalaxmi M", { x: 0, y: 5.35, w: W, h: 0.4, fontSize: 14, bold: true, fontFace: FONT, color: WHITE, align: "center", margin: 0 });
  s.addText("Department of Computer Science and Engineering", { x: 0, y: 5.8, w: W, h: 0.35, fontSize: 12.5, fontFace: FONT, color: IND_LIGHT, align: "center", margin: 0 });
  s.addText("Questions & discussion welcome", { x: 0, y: 6.5, w: W, h: 0.4, fontSize: 14, fontFace: FONT, color: ACCENT, align: "center", margin: 0 });
}

pres.writeFile({ fileName: "Resume_Classification_Final_Review.pptx" }).then(() => console.log("WROTE Resume_Classification_Final_Review.pptx — slides:", pageNo));
