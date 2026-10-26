// Cornerstone Project Report — Intelligent Resume Analysis and Classification System
// Mirrors the structure/format of the reference NLP_REPORT.pdf (Aditya University format).
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, PageBreak, Header, Footer, PageNumber, NumberFormat,
  AlignmentType, HeadingLevel, WidthType, BorderStyle, ShadingType,
  TabStopType, TableOfContents, VerticalAlign,
} = require(__dirname + "/node_modules/docx/build/index.cjs");
const fs = require("fs");

const OUT = "../Resume_Analysis_Project_Report.docx";
const MEDIA = "media/";
const lofPages = fs.existsSync("lof_pages.json") ? JSON.parse(fs.readFileSync("lof_pages.json", "utf8")) : {};
if (fs.existsSync("toc_pages.json")) {
  const t = JSON.parse(fs.readFileSync("toc_pages.json", "utf8"));
  const map = { "CHAPTER 1": "c1", "CHAPTER 2": "c2", "CHAPTER 3": "c3", "CHAPTER 4": "c4", "CHAPTER 5": "c5", "CHAPTER 6": "c6", "CHAPTER 7": "c7", "CHAPTER 8": "c8", REFERENCES: "refs", APPENDIX: "appx" };
  for (const [k, v] of Object.entries(t)) {
    const key = map[k] || k.replace(/ (Introduction|Problem|Objectives|Scope|Proposed|System Architecture|Module|Hardware|Tools|Dataset|Data Collection|Data Preprocessing|Need for|TF-IDF Representation|Classification Implementation|Classification Matrix|Scoring Approach|Data Used|Techniques|Scoring and Prediction|Validation|NLTK Library|User Resume|Preprocessing Implementation|Classification and Scoring|Job Description|Important Code|Interface Design|Analysis Results|Recommendations|Charts|Sample Analyses|Screenshots|Results and Discussion|Conclusion|Limitations|Future).*$/, "");
    lofPages[key] = v;
  }
}
const pg = (k) => (lofPages[k] != null ? String(lofPages[k]) : "-");

const TNR = "Times New Roman", MONO = "Courier New";
const BLUE = "D9E2F3", GRAY = "F2F2F2";
const BLACK = "000000";

const bd = { style: BorderStyle.SINGLE, size: 4, color: "7F7F7F" };
const allBd = { top: bd, bottom: bd, left: bd, right: bd, insideHorizontal: bd, insideVertical: bd };
const noBd = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const allNoBd = { top: noBd, bottom: noBd, left: noBd, right: noBd, insideHorizontal: noBd, insideVertical: noBd };

// ---------- text helpers ----------
const R = (text, o = {}) => new TextRun({ text, font: { ascii: TNR, hAnsi: TNR }, size: o.size || 22, bold: !!o.bold, italics: !!o.it, color: o.color || BLACK, ...o.x });
function body(text, o = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: o.noIndent ? undefined : { firstLine: 288 },
    spacing: { line: 312, after: o.after != null ? o.after : 80 },
    keepNext: !!o.keepNext,
    children: [R(text, o)],
  });
}
function bodyRuns(runs, o = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: o.noIndent ? undefined : { firstLine: 288 },
    spacing: { line: 312, after: o.after != null ? o.after : 80 },
    keepNext: !!o.keepNext,
    children: runs,
  });
}
function bullet(text, o = {}) {
  return new Paragraph({
    bullet: { level: 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 312, after: 40 },
    children: o.lead ? [R(o.lead, { bold: true }), R(text)] : [R(text)],
  });
}
function chapter(no, title) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    pageBreakBefore: true,
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 240, line: 360 },
    children: [
      new TextRun({ text: "CHAPTER " + no, font: { ascii: TNR, hAnsi: TNR }, size: 28, bold: true, color: BLACK }),
      new TextRun({ text: title, font: { ascii: TNR, hAnsi: TNR }, size: 28, bold: true, color: BLACK, break: 1 }),
    ],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 120, line: 312 },
    children: [new TextRun({ text, font: { ascii: TNR, hAnsi: TNR }, size: 26, bold: true, color: BLACK })],
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 100, line: 312 },
    children: [new TextRun({ text, font: { ascii: TNR, hAnsi: TNR }, size: 24, bold: true, color: BLACK })],
  });
}
function fmTitle(text) { // front-matter page title
  return new Paragraph({
    pageBreakBefore: text.pb !== false,
    alignment: AlignmentType.CENTER,
    spacing: { before: 60, after: 240, line: 360 },
    children: [new TextRun({ text, font: { ascii: TNR, hAnsi: TNR }, size: 30, bold: true, color: BLACK })],
  });
}
function tblCaption(no, text) {
  return new Paragraph({
    keepNext: true, alignment: AlignmentType.CENTER,
    spacing: { before: 160, after: 80, line: 300 },
    children: [new TextRun({ text: "Table " + no + ": " + text, font: { ascii: TNR, hAnsi: TNR }, size: 21, bold: true, color: BLACK })],
  });
}
function figCaption(no, text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 200, line: 300 },
    children: [new TextRun({ text: "Figure " + no + ": " + text, font: { ascii: TNR, hAnsi: TNR }, size: 21, bold: true, color: BLACK })],
  });
}
function figure(file, w, h, capNo, capText) {
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 0 },
      children: [new ImageRun({ data: fs.readFileSync(MEDIA + file), transformation: { width: w, height: h }, type: "png" })],
    }),
    figCaption(capNo, capText),
  ];
}
// bordered table with blue header row
function btable(headers, rows, colPct, opts = {}) {
  const fsz = opts.fontSize || 20;
  const mk = (text, isHead, alignLeft, wPct) => new TableCell({
    width: { size: wPct, type: WidthType.PERCENTAGE },
    shading: { type: ShadingType.CLEAR, fill: isHead ? BLUE : "FFFFFF" },
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: alignLeft ? AlignmentType.LEFT : AlignmentType.CENTER,
      spacing: { line: 276 },
      children: [new TextRun({ text: String(text), font: { ascii: TNR, hAnsi: TNR }, size: fsz, bold: isHead || undefined, color: BLACK })],
    })],
  });
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: allBd,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((t, i) => mk(t, true, false, colPct[i])) }),
      ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => mk(t, false, opts.leftCols ? opts.leftCols.includes(i) : i > 0, colPct[i])) })),
    ],
  });
}
// plain monospace code block read from a source file
function codeBlock(from, to, file) {
  const lines = fs.readFileSync(file, "utf8").split(/\r?\n/).slice(from - 1, to);
  return lines.map((ln) => new Paragraph({
    spacing: { line: 240, after: 0 },
    shading: { type: ShadingType.CLEAR, fill: "F7F7F7" },
    children: [new TextRun({ text: ln.length ? ln : " ", font: { ascii: MONO, hAnsi: MONO }, size: 15, color: BLACK })],
  }));
}
function codeInline(lines) {
  return lines.map((ln) => new Paragraph({
    spacing: { line: 240, after: 0 },
    shading: { type: ShadingType.CLEAR, fill: "F7F7F7" },
    children: [new TextRun({ text: ln.length ? ln : " ", font: { ascii: MONO, hAnsi: MONO }, size: 15, color: BLACK })],
  }));
}

// ---------- shared header / footer ----------
function pageHeader() {
  return new Header({
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 0, line: 240 },
        children: [R("School of Computing", { size: 17, bold: true })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 0, line: 240 },
        children: [R("Department of Computer Science and Engineering", { size: 17 })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 0, line: 240 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLACK, space: 2 } },
        children: [R("NATURAL LANGUAGE PROCESSING", { size: 17, bold: true })],
      }),
    ],
  });
}
function pageFooter() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], font: { ascii: TNR, hAnsi: TNR }, size: 20, color: BLACK })],
    })],
  });
}

// ---------- title page ----------
const TEAM = [
  ["SAITEJA K", "24B11CS220"],
  ["GNANESWARI K", "24B11CS190"],
  ["SIDDHARDHA P", "24B11CS324"],
  ["MAHALAXMI M", "24B11CS253"],
];
function centerP(runs, o = {}) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: o.before || 0, after: o.after || 0, line: o.line || 312 },
    children: runs,
  });
}
const cover = [
  centerP([R("School of Computing", { size: 24, bold: true })], { before: 360 }),
  centerP([R("Department of Computer Science and Engineering", { size: 22 })], { after: 200 }),
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 260 },
    children: [new ImageRun({ data: fs.readFileSync("logo_aditya.png"), transformation: { width: 400, height: 56 }, type: "png" })],
  }),
  centerP([R("NATURAL LANGUAGE PROCESSING", { size: 32, bold: true })], { after: 320 }),
  centerP([R("A Cornerstone Project Report on", { size: 24 })], { after: 160 }),
  centerP([R("INTELLIGENT RESUME ANALYSIS AND", { size: 30, bold: true })], { line: 360 }),
  centerP([R("CLASSIFICATION SYSTEM", { size: 30, bold: true })], { after: 340, line: 360 }),
  centerP([R("Submitted by", { size: 24 })], { after: 140 }),
  ...TEAM.flatMap(([n, id]) => [
    centerP([R(n, { size: 24, bold: true })], { after: 20 }),
    centerP([R("(" + id + ")", { size: 22 })], { after: 110 }),
  ]),
  centerP([R("Under the guidance of", { size: 24 })], { after: 100 }),
  centerP([R("Dr. T. Sudha Rani", { size: 24, bold: true })], { after: 20 }),
  centerP([R("Assistant Professor, Department of CSE", { size: 22 })], { after: 240 }),
  centerP([R("in partial fulfilment of the requirements for the award of the B.Tech. degree", { size: 22 })], { line: 300 }),
  centerP([R("in Computer Science and Engineering", { size: 22 })], { after: 300, line: 300 }),
  centerP([R("ADITYA UNIVERSITY", { size: 28, bold: true })], { after: 60 }),
  centerP([R("Surampalem", { size: 24 })], { after: 160 }),
  centerP([R("Academic Year 2026\u20132027", { size: 24 })]),
];

// ---------- front matter ----------
const certSig = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  borders: allNoBd,
  rows: [new TableRow({ cantSplit: true, children: [
    new TableCell({
      width: { size: 50, type: WidthType.PERCENTAGE }, borders: allNoBd, margins: { top: 700, bottom: 40, left: 80, right: 80 },
      children: [
        new Paragraph({ spacing: { line: 300 }, children: [R("Project Guide", { size: 24, bold: true })] }),
        new Paragraph({ spacing: { line: 300 }, children: [R("Dr. T. Sudha Rani", { size: 24 })] }),
        new Paragraph({ spacing: { line: 300 }, children: [R("Assistant Professor", { size: 24 })] }),
        new Paragraph({ spacing: { line: 300 }, children: [R("Department of CSE", { size: 24 })] }),
      ],
    }),
    new TableCell({
      width: { size: 50, type: WidthType.PERCENTAGE }, borders: allNoBd, margins: { top: 700, bottom: 40, left: 80, right: 80 },
      children: [
        new Paragraph({ spacing: { line: 300 }, children: [R("Head of the Department", { size: 24, bold: true })] }),
        new Paragraph({ spacing: { line: 300 }, children: [R("Dr. A. Phani Sridhar", { size: 24 })] }),
        new Paragraph({ spacing: { line: 300 }, children: [R("Associate Professor and HOD", { size: 24 })] }),
        new Paragraph({ spacing: { line: 300 }, children: [R("Department of CSE", { size: 24 })] }),
      ],
    }),
  ] })],
});

const certDecl = [
  fmTitle("CERTIFICATE"),
  body("This is to certify that the Cornerstone project work entitled \u201CINTELLIGENT RESUME ANALYSIS AND CLASSIFICATION SYSTEM\u201D is submitted by", { noIndent: true, after: 120 }),
  ...TEAM.flatMap(([n, id]) => [
    centerP([R(n, { size: 24, bold: true })], { after: 20 }),
    centerP([R("(" + id + ")", { size: 22 })], { after: 90 }),
  ]),
  body("in partial fulfilment of the requirements for the award of the B.Tech. degree in Computer Science and Engineering during the academic year 2026-2027.", { noIndent: true, after: 200 }),
  certSig,
];
const declaration = [
  fmTitle("DECLARATION"),
  body("We hereby declare that the project entitled \u201CINTELLIGENT RESUME ANALYSIS AND CLASSIFICATION SYSTEM\u201D is our original work and is submitted to ADITYA UNIVERSITY, Surampalem, in partial fulfilment of the requirements for the award of the B.Tech. degree in Computer Science and Engineering. We further declare that this project work has not been submitted, either in full or in part, for the award of any degree or diploma in this or any other institution. We also confirm that this work has been carried out with academic honesty and complies with the Institutional Academic Integrity and AI Usage Policy.", { noIndent: true, after: 400 }),
  new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 3400 }, spacing: { line: 300, after: 20 }, children: [R("Place: Surampalem", { size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 3400 }, spacing: { line: 300, after: 500 }, children: [R("Date: 17-10-2026", { size: 24 })] }),
  body("By", { noIndent: true, after: 60 }),
  ...TEAM.flatMap(([n, id]) => [
    centerP([R(n, { size: 24, bold: true })], { after: 20 }),
    centerP([R("(" + id + ")", { size: 22 })], { after: 90 }),
  ]),
];
const acknowledgement = [
  fmTitle("ACKNOWLEDGEMENT"),
  body("It is with immense pleasure that we express our sincere gratitude to our Cornerstone Project Guide, Dr. T. Sudha Rani, Assistant Professor, who has guided us throughout the project. Her valuable support, encouragement and guidance have greatly contributed to the successful completion of this work.", { noIndent: true, after: 160 }),
  body("We would like to thank our Deputy Heads of the Department, Dr. Hari J, Professor, Dr. Siva Satya Prasad P, Assistant Professor and Dr. Chandra Sekhar K, Associate Professor, Department of CSE, for their support and valuable suggestions.", { noIndent: true, after: 160 }),
  body("Our deepest thanks to our Head of the Department, Dr. A. Phani Sridhar, Associate Professor and HOD, for his inspiration and for providing all the necessary facilities and resources required for this project.", { noIndent: true, after: 160 }),
  body("We also extend our sincere thanks to Dr. M.V. Rajesh, Associate Dean, School of Computing, for his encouragement and support during our project.", { noIndent: true, after: 160 }),
  body("We would like to express our sincere gratitude to Dr. G. Suresh, Registrar; Dr. A. Ramesh, Pro Vice-Chancellor (Engineering & Sciences); Dr. S. Rama Sree, Pro Vice-Chancellor (Academics); Dr. M.B. Srinivas, Vice-Chancellor; and Dr. M. Sreenivasa Reddy, Deputy Pro Chancellor and Management, Aditya University, for providing excellent infrastructure and state-of-the-art laboratories.", { noIndent: true, after: 160 }),
  body("Finally, we would like to thank the faculty members, lab technicians, non-teaching staff, and our friends who have directly or indirectly supported us in completing this Cornerstone project successfully.", { noIndent: true, after: 160 }),
];
const swHwTable = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  borders: allNoBd,
  rows: [new TableRow({ cantSplit: true, children: [
    new TableCell({
      width: { size: 50, type: WidthType.PERCENTAGE }, borders: allNoBd, margins: { top: 60, bottom: 60, left: 80, right: 200 },
      children: [
        new Paragraph({ spacing: { after: 60, line: 300 }, children: [R("Software Requirements:", { size: 24, bold: true })] }),
        bullet("Operating System: Windows 10 / 11"),
        bullet("Programming Language: Python 3.11"),
        bullet("IDE: Visual Studio Code"),
        bullet("Libraries: NLTK, spaCy, scikit-learn, Flask, pandas, pypdf, python-docx"),
        bullet("Database: SQLite"),
      ],
    }),
    new TableCell({
      width: { size: 50, type: WidthType.PERCENTAGE }, borders: allNoBd, margins: { top: 60, bottom: 60, left: 200, right: 80 },
      children: [
        new Paragraph({ spacing: { after: 60, line: 300 }, children: [R("Hardware Requirements:", { size: 24, bold: true })] }),
        bullet("Processor: Intel i5 or above"),
        bullet("RAM: Minimum 8 GB"),
        bullet("Hard Disk: 50 GB free space"),
      ],
    }),
  ] })],
});
const abstractPage = [
  fmTitle("ABSTRACT"),
  centerP([R("INTELLIGENT RESUME ANALYSIS AND CLASSIFICATION SYSTEM", { size: 26, bold: true })], { after: 240, line: 340 }),
  body("The Intelligent Resume Analyzer is a Natural Language Processing (NLP) and Machine Learning (ML) web application that reads a resume in PDF or DOCX format, extracts its structure (skills, education, experience, projects and certifications), classifies it into one of nine job categories and scores it the way an applicant tracking system (ATS) would. The text pipeline is built on NLTK: cleaning, tokenization, stop-word removal and lemmatization. Classification uses a TF-IDF representation (unigrams and bigrams) fed to a Linear Support Vector Machine wrapped in CalibratedClassifierCV, so every prediction also carries a calibrated confidence value.", { noIndent: true, after: 160 }),
  body("The ATS engine audits each resume against seven weighted factors - keyword coverage, skills match, job-title match, experience, education, format and parseability, and content quality - and produces prioritized improvement suggestions ordered by the number of points each fix is worth. A job-match mode blends skills, TF-IDF text similarity, experience and education into a transparent match score, and a tracker stores every run in an SQLite database so users can measure score progress over time. The system is fully local: uploaded files are parsed in memory and never written to disk.", { noIndent: true, after: 160 }),
  body("On the held-out test split of 1,817 labeled resumes (1,453 training / 364 test rows), the calibrated SVM reaches 94.51% accuracy across the nine categories; a neural-network alternative and a soft-voting ensemble were also evaluated (92.03% and 92.58%) and the SVM was selected. The complete application is delivered as a Flask web interface with a JSON API, protected by 149 automated tests that include an 8x8 cross-domain validation matrix and causal checks confirming that following the tool's advice raises the ATS score by 15 to 23 points.", { noIndent: true, after: 240 }),
  swHwTable,
  new Paragraph({ spacing: { before: 200, after: 60, line: 300 }, alignment: AlignmentType.CENTER, children: [R("Project Team", { size: 24, bold: true })] }),
  centerP([R("SAITEJA K (24B11CS220)  \u00B7  GNANESWARI K (24B11CS190)", { size: 22 })], { after: 40 }),
  centerP([R("SIDDHARDHA P (24B11CS324)  \u00B7  MAHALAXMI M (24B11CS253)", { size: 22 })]),
];
const TOC_ROWS = [
  ["1", "Title Page", "i", 0],
  ["2", "Certificate", "ii", 0],
  ["3", "Declaration", "iii", 0],
  ["4", "Acknowledgement", "iv", 0],
  ["5", "Abstract", "v", 0],
  ["6", "Table of Contents", "vi", 0],
  ["7", "List of Figures", "viii", 0],
  ["8", "List of Tables", "ix", 0],
  ["Chapter 1", "Introduction", pg("c1"), 1],
  ["1.1", "Introduction to the Project", pg("1.1"), 0],
  ["1.2", "Problem Statement", pg("1.2"), 0],
  ["1.3", "Objectives of the Project", pg("1.3"), 0],
  ["1.4", "Scope of the Project", pg("1.4"), 0],
  ["Chapter 2", "System Analysis and Design, Requirement Analysis", pg("c2"), 1],
  ["2.1", "Proposed System", pg("2.1"), 0],
  ["2.2", "System Architecture / System Work Flow", pg("2.2"), 0],
  ["2.3", "Module Description", pg("2.3"), 0],
  ["2.4", "Hardware Requirements and Software Requirements", pg("2.4"), 0],
  ["2.5", "Tools and Technologies", pg("2.5"), 0],
  ["Chapter 3", "Dataset and Data Preprocessing", pg("c3"), 1],
  ["3.1", "Dataset Description and Data Format", pg("3.1"), 0],
  ["3.2", "Data Collection", pg("3.2"), 0],
  ["3.3", "Data Preprocessing (Text Cleaning, Lowercasing, Punctuation Removal, Tokenization, Stopword Removal, Lemmatization)", pg("3.3"), 0],
  ["Chapter 4", "Resume Classification Using TF-IDF and Calibrated SVM", pg("c4"), 1],
  ["4.1", "Need for Machine-Learning Classification", pg("4.1"), 0],
  ["4.2", "TF-IDF Representation, Scoring Method and Numerical Example", pg("4.2"), 0],
  ["4.3", "Classification Implementation: LinearSVC and Probability Calibration", pg("4.3"), 0],
  ["4.4", "Classification Matrix and Sample Output", pg("4.4"), 0],
  ["Chapter 5", "ATS Scoring, Job Matching and Validation", pg("c5"), 1],
  ["5.1", "Scoring Approach", pg("5.1"), 0],
  ["5.2", "Data Used for Scoring", pg("5.2"), 0],
  ["5.3", "Techniques Used", pg("5.3"), 0],
  ["5.4", "Scoring and Prediction Process", pg("5.4"), 0],
  ["5.5", "Validation Results", pg("5.5"), 0],
  ["Chapter 6", "Implementation", pg("c6"), 1],
  ["6.1", "NLTK Library and Keywords Used", pg("6.1"), 0],
  ["6.2", "User Resume Input", pg("6.2"), 0],
  ["6.3", "Preprocessing Implementation", pg("6.3"), 0],
  ["6.4", "Classification and Scoring Implementation", pg("6.4"), 0],
  ["6.5", "Job Description Parsing and Validation Implementation", pg("6.5"), 0],
  ["6.6", "Important Code Snippets", pg("6.6"), 0],
  ["Chapter 7", "Result Visualization and Web Interface", pg("c7"), 1],
  ["7.1", "Interface Design", pg("7.1"), 0],
  ["7.2", "Analysis Results Presentation", pg("7.2"), 0],
  ["7.3", "Recommendations and Detected Skills", pg("7.3"), 0],
  ["7.4", "Charts / Graphs: ATS Tracker and Progress", pg("7.4"), 0],
  ["7.5", "Sample Analyses and Predictions", pg("7.5"), 0],
  ["7.6", "Screenshots", pg("7.6"), 0],
  ["7.7", "Results and Discussion", pg("7.7"), 0],
  ["Chapter 8", "Conclusion and Future Enhancements", pg("c8"), 1],
  ["8.1", "Conclusion", pg("8.1"), 0],
  ["8.2", "Limitations", pg("8.2"), 0],
  ["8.3", "Future Enhancements", pg("8.3"), 0],
  ["9", "References", pg("refs"), 1],
  ["10", "Appendix \u2013 Source Code", pg("appx"), 1],
];
function tocTable() {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: allBd,
    rows: TOC_ROWS.map(([no, title, page, bold]) => new TableRow({
      cantSplit: true,
      children: [
        new TableCell({
          width: { size: 14, type: WidthType.PERCENTAGE },
          shading: { type: ShadingType.CLEAR, fill: "FFFFFF" },
          margins: { top: 30, bottom: 30, left: 80, right: 80 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ spacing: { line: 276 }, children: [new TextRun({ text: no, font: { ascii: TNR, hAnsi: TNR }, size: 20, bold: !!bold, color: BLACK })] })],
        }),
        new TableCell({
          width: { size: 72, type: WidthType.PERCENTAGE },
          shading: { type: ShadingType.CLEAR, fill: "FFFFFF" },
          margins: { top: 30, bottom: 30, left: 80, right: 80 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ spacing: { line: 276 }, children: [new TextRun({ text: title, font: { ascii: TNR, hAnsi: TNR }, size: 20, bold: !!bold, color: BLACK })] })],
        }),
        new TableCell({
          width: { size: 14, type: WidthType.PERCENTAGE },
          shading: { type: ShadingType.CLEAR, fill: "FFFFFF" },
          margins: { top: 30, bottom: 30, left: 80, right: 80 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { line: 276 }, children: [new TextRun({ text: page, font: { ascii: TNR, hAnsi: TNR }, size: 20, bold: !!bold, color: BLACK })] })],
        }),
      ],
    })),
  });
}
const tocPage = [
  fmTitle("TABLE OF CONTENTS"),
  tocTable(),
];
function listTable(rows, head1) { // LoF / LoT
  return btable([head1, "Caption", "Page"], rows, [12, 74, 14]);
}
const lofPage = [
  fmTitle("LIST OF FIGURES"),
  listTable([
    ["2.1", "System Architecture and Workflow of the Proposed System", pg("2.1")],
    ["3.1", "Raw Dataset (resume_dataset.csv) Opened in a Spreadsheet View", pg("3.1")],
    ["3.2", "Processed Dataset (resume_dataset_processed.csv) Opened in a Spreadsheet View", pg("3.2")],
    ["5.1", "ATS Factor Weights in the Resume vs Job Description Mode", pg("5.1")],
    ["7.1", "Resume Upload and Analysis Interface", pg("7.1")],
    ["7.2", "Analysis Results: Predicted Category and ATS Score Gauge", pg("7.2")],
    ["7.3", "ATS Score Breakdown and Parser Checks", pg("7.3")],
    ["7.4", "Prioritized Recommendations and Detected Skills", pg("7.4")],
    ["7.5", "ATS Tracker Dashboard with Score Trend", pg("7.5")],
    ["7.6", "Resume Progress Comparison", pg("7.6")],
    ["7.7", "Analysis History Table", pg("7.7")],
  ], "Figure No."),
];
const lotPage = [
  fmTitle("LIST OF TABLES"),
  listTable([
    ["2.1", "Modules of the Proposed System", pg("t2.1")],
    ["2.2", "Hardware Requirements", pg("t2.2")],
    ["2.3", "Software Requirements", pg("t2.3")],
    ["2.4", "Tools and Technologies Used", pg("t2.4")],
    ["3.1", "Attributes of the Resume Dataset", pg("t3.1")],
    ["3.2", "Category Distribution of the Training Dataset", pg("t3.2")],
    ["3.3", "Examples of Text Preprocessing (Before and After)", pg("t3.3")],
    ["4.1", "TF-IDF Weights for a Sample Preprocessed Sentence", pg("t4.1")],
    ["4.2", "Classification Report on the Held-out Test Set (364 Resumes)", pg("t4.2")],
    ["4.3", "Confusion Matrix of the Test Set (Rows: Actual, Columns: Predicted)", pg("t4.3")],
    ["5.1", "ATS Factors, Weights and Meaning (Resume vs Job Description)", pg("t5.1")],
    ["5.2", "ATS Grade Bands", pg("t5.2")],
    ["6.1", "NLTK Components Used in the System", pg("t6.1")],
    ["6.2", "Important Functions and Keywords of the Pipeline", pg("t6.2")],
    ["7.1", "Aggregate Results across the 571 Stored Analyses", pg("t7.1")],
    ["7.2", "Sample Analyses and Predictions from the History Database", pg("t7.2")],
  ], "Table No."),
];

// ---------- chapter 1 ----------
const ch1 = [
  chapter(1, "INTRODUCTION"),
  h2("1.1 Introduction to the Project"),
  body("Resumes are the primary medium through which candidates present their skills, education and professional experience to employers. At the same time, most resumes are written as free-form, unstructured text: the same skill can appear under a dozen different names, experience is scattered across sections, and formatting choices vary from candidate to candidate. For a recruiter who screens hundreds of applications, and for a student who wants to know which job roles actually fit their profile, this unstructured format makes evaluation slow, inconsistent and error-prone."),
  body("The Intelligent Resume Analysis and Classification System addresses this problem with Natural Language Processing (NLP) and Machine Learning (ML). The user uploads a resume in PDF or DOCX format through a web interface. The system extracts the text, detects whether the document really is a resume, cleans and normalizes the text using an NLTK pipeline, extracts structured information (skills, education, experience, projects and certifications), classifies the resume into one of nine job categories using a TF-IDF and Support Vector Machine model, and finally scores the resume with a seven-factor ATS (Applicant Tracking System) audit that explains exactly which changes would raise the score."),
  body("Unlike a one-shot classifier, the system is built around measurability. Every analysis run is stored in an SQLite database, so a user who edits their resume can re-upload it and see whether the ATS score actually improved. The results are presented on a Flask web dashboard with an ATS tracker, a progress comparison view, a full analysis history and downloadable reports, and the same capabilities are exposed through a JSON API for programmatic access."),
  h2("1.2 Problem Statement"),
  body("Manual resume screening is time-consuming, inconsistent and error-prone. Resumes contain large amounts of unstructured text, so two recruiters reading the same resume may reach different conclusions, and applicants themselves have no objective way to evaluate their own profiles before applying. In addition, most large employers filter resumes with keyword-based applicant tracking systems, and candidates rarely know how their document performs against such a parser."),
  body("There is therefore a need for an automated system that can (i) read resumes in common file formats, (ii) extract and structure the key information, (iii) classify each resume into a suitable job category, (iv) score the resume against a transparent, ATS-like rubric with concrete improvement advice, and (v) track the score over time so improvement can be measured rather than guessed."),
  h2("1.3 Objectives of the Project"),
  bullet("Build an NLP-based resume analysis system with a web interface."),
  bullet("Accept PDF and DOCX uploads with file-type and size validation."),
  bullet("Extract and preprocess resume text (cleaning, tokenization, stop-word removal, lemmatization)."),
  bullet("Identify skills, education, experience, projects and certifications from raw resume text."),
  bullet("Classify resumes into nine job categories using TF-IDF features and a calibrated SVM."),
  bullet("Score resumes with a transparent multi-factor ATS engine and generate prioritized improvement suggestions."),
  bullet("Track scores across repeated analyses and present results through a dashboard, history view and CSV export."),
  h2("1.4 Scope of the Project"),
  body("The project covers the complete pipeline from file upload to scored, explained results: document parsing, resume detection, NLP preprocessing, information extraction, classification, ATS scoring, job-description matching, recommendation generation, persistence and web presentation. The classifier is trained on 1,817 labeled resumes and the scoring engine is validated with an automated test suite of 149 tests, including cross-domain and causal checks."),
  body("The scope deliberately excludes online job scraping, user accounts with authentication, and cloud deployment: the system runs entirely on a local machine and stores no personal data beyond scores and file names, which keeps it suitable for coursework and privacy-sensitive use. Optional Gemini AI integration exists only for re-phrasing recommendation text and never computes or alters any score."),
];

// ---------- chapter 2 ----------
const ch2 = [
  chapter(2, "SYSTEM ANALYSIS AND DESIGN, REQUIREMENT ANALYSIS"),
  h2("2.1 Proposed System"),
  body("The proposed system is a modular web application. A Flask server exposes the pages and the JSON API, and delegates all processing to focused service modules: document parsing, resume detection, text preprocessing, information extraction, skill matching, classification, ATS scoring, job matching and recommendation generation. Configuration (weights, limits, API keys) is loaded from environment variables through a single config module."),
  body("Three properties shape the design. First, transparency: every ATS factor publishes its own subscore, weight and explanation, and any factor that cannot be computed for a particular resume is excluded with its weight redistributed rather than silently dragging the score down. Second, privacy: uploaded files are parsed in memory and never written to disk, and the database stores only scores, grades and file names - never resume text, names, e-mails or phone numbers. Third, speed: preprocessing, job-description parsing and skill scanning are memoized, so the common workflow of scoring many resumes against one job description runs at roughly 5 milliseconds per analysis once warm."),
  body("The user-facing flow is: upload a resume, optionally paste a job description, choose an analysis mode (standalone audit, single-JD match, multi-JD ranking or resume comparison), and receive the predicted category, the ATS score with its factor breakdown, detected skills and prioritized recommendations. Every run is recorded for later progress tracking."),
  h2("2.2 System Architecture / System Work Flow"),
  body("Figure 2.1 shows the architecture and the flow of data through the system. After validation, the uploaded file is parsed to plain text and checked by the resume detector. The preprocessing service normalizes the text, which then feeds four parallel capabilities: information extraction, classification, ATS scoring and skill matching. An analysis service assembles the results, writes a history record to SQLite and renders the web response.", { keepNext: true }),
  ...figure("fig_architecture.png", 500, 402, "2.1", "System Architecture and Workflow of the Proposed System"),
  h2("2.3 Module Description"),
  body("The system is organized into twelve modules, each with a single responsibility. Table 2.1 lists the modules with their function and output.", { keepNext: true }),
  tblCaption("2.1", "Modules of the Proposed System"),
  btable(
    ["S.No", "Module", "Description", "Output"],
    [
      ["1", "Resume Upload", "Web form accepting PDF/DOCX up to 10 MB with file-type and size validation", "Validated file stream"],
      ["2", "Document Parser", "Extracts plain text from PDF (pypdf) and DOCX (python-docx) fully in memory", "Resume text"],
      ["3", "Resume Detector", "Classifies the document type; non-resumes (thesis, report, invoice) are refused", "Verdict + confidence"],
      ["4", "NLP Preprocessor", "Cleaning, tokenization, stop-word removal, lemmatization; protects terms like C++", "Processed text"],
      ["5", "Information Extractor", "Contact info, sections, titles, experience from claims and date-range math", "Structured profile"],
      ["6", "Skill Matcher", "Maps 273 recognized surface forms to 178 canonical skills", "Detected skills"],
      ["7", "Resume Classifier", "TF-IDF (unigrams+bigrams) + calibrated LinearSVC", "Category + confidence"],
      ["8", "ATS Scorer", "Seven-factor weighted audit, grade bands, potential score, suggestions", "ATS score + breakdown"],
      ["9", "Matching Engine", "Skills 50% + TF-IDF similarity 25% + experience 15% + education 10%", "Job match score"],
      ["10", "Recommendation Engine", "Prioritizes fixes by expected score gain; adjacent-skill advice", "Recommendations"],
      ["11", "History & Tracker", "SQLite persistence, progress comparison, CSV export", "Tracker data"],
      ["12", "Web Interface & API", "Flask pages plus /api/analyze, /api/match, /api/rank-jds, /api/compare", "HTML / JSON responses"],
    ],
    [8, 22, 48, 22], { fontSize: 19, leftCols: [2, 3] }
  ),
  h2("2.4 Hardware Requirements and Software Requirements"),
  body("The application runs on an ordinary laptop; training the classifier completes in under a minute on the same hardware. Tables 2.2 and 2.3 list the requirements.", { keepNext: true }),
  tblCaption("2.2", "Hardware Requirements"),
  btable(["Component", "Requirement"], [
    ["Processor", "Intel Core i5 or equivalent"],
    ["RAM", "Minimum 8 GB"],
    ["Hard Disk", "50 GB free space"],
    ["Display", "1366 x 768 or higher"],
  ], [30, 70], { leftCols: [1] }),
  tblCaption("2.3", "Software Requirements"),
  btable(["Component", "Requirement"], [
    ["Operating System", "Windows 10 / 11 (also runs on Linux and macOS)"],
    ["Programming Language", "Python 3.11"],
    ["Web Framework", "Flask 3.1 with waitress WSGI server"],
    ["NLP Libraries", "NLTK 3.9, spaCy 3.8"],
    ["ML Libraries", "scikit-learn 1.7, pandas, numpy, joblib"],
    ["Document Parsing", "pypdf 5.9, python-docx 1.2"],
    ["Database", "SQLite 3 (built into Python)"],
    ["IDE / Tools", "Visual Studio Code, Git, browser"],
  ], [30, 70], { leftCols: [1] }),
  h2("2.5 Tools and Technologies"),
  body("Table 2.4 summarizes the tools and technologies used at each layer of the system.", { keepNext: true }),
  tblCaption("2.4", "Tools and Technologies Used"),
  btable(["Technology", "Role in the Project"], [
    ["Python", "Core implementation language for the whole pipeline"],
    ["NLTK / spaCy", "Tokenization, stop-word lists, lemmatization, name detection"],
    ["scikit-learn", "TF-IDF vectorizer, LinearSVC, calibration, MLP baseline"],
    ["pypdf / python-docx", "PDF and DOCX text extraction"],
    ["Flask + waitress", "Web routes, templates and production WSGI serving"],
    ["Bootstrap / JavaScript", "Responsive dashboard, charts and client-side interactions"],
    ["SQLite", "Analysis history, ATS tracker and progress persistence"],
    ["pytest", "149 automated tests: unit, route, regression and fuzz"],
    ["Git / VS Code", "Version control and development environment"],
  ], [28, 72], { leftCols: [1] }),
];

// ---------- chapter 3 ----------
const ch3 = [
  chapter(3, "DATASET AND DATA PREPROCESSING"),
  h2("3.1 Dataset Description and Data Format"),
  body("The classifier is trained on a labeled corpus of 1,817 resumes spread over nine job categories. Each record has two fields: the full resume text and its category label. The raw corpus combines two sources: 1,260 resumes generated from a parameterized template generator written for this project (nine categories x 140 resumes with randomized skills, roles and responsibilities), and 557 real, publicly available labeled resumes mapped onto the same nine categories. Figure 3.1 shows the raw dataset opened in a spreadsheet view, and Table 3.1 describes the attributes.", { keepNext: true }),
  ...figure("fig_dataset_raw.png", 590, 220, "3.1", "Raw Dataset (resume_dataset.csv) Opened in a Spreadsheet View"),
  tblCaption("3.1", "Attributes of the Resume Dataset"),
  btable(["Attribute", "Type", "Description"], [
    ["resume_text", "string", "Full plain text of the resume, including summary, skills, experience and education sections"],
    ["processed_text", "string", "Output of the NLP preprocessing pipeline; added by training/prepare_dataset.py"],
    ["category", "string", "One of nine labels: Business Analyst, Cloud Engineer, Data Analyst, Data Scientist, DevOps Engineer, Machine Learning Engineer, Software Developer, UI/UX Designer, Web Developer"],
  ], [20, 12, 68], { fontSize: 19, leftCols: [2] }),
  h2("3.2 Data Collection"),
  body("The template-based portion was produced by training/generate_demo_dataset.py with a fixed random seed (42) for reproducibility: each category has a curated skill pool, role titles, responsibility sentences and project descriptions, and every resume samples from these pools so that texts differ while labels remain correct. The real portion was collected from public resume datasets available on Kaggle and mapped to the project's nine categories; only records whose text was non-empty and whose label could be mapped unambiguously were kept. During preparation the corpus is cleaned (missing values removed, exact-duplicate resume texts dropped) before preprocessing.", { keepNext: true }),
  tblCaption("3.2", "Category Distribution of the Training Dataset"),
  btable(["Category", "Resumes", "Share"], [
    ["Business Analyst", "374", "20.6%"],
    ["Software Developer", "260", "14.3%"],
    ["UI/UX Designer", "247", "13.6%"],
    ["Web Developer", "236", "13.0%"],
    ["Cloud Engineer", "140", "7.7%"],
    ["Data Analyst", "140", "7.7%"],
    ["Data Scientist", "140", "7.7%"],
    ["Machine Learning Engineer", "140", "7.7%"],
    ["DevOps Engineer", "140", "7.7%"],
    ["Total", "1,817", "100%"],
  ], [46, 27, 27]),
  body("The distribution is moderately imbalanced: Business Analyst is over-represented because most real resumes mapped to it, while the five technical infrastructure categories rely on the synthetic portion alone. The LinearSVC therefore trains with class_weight balanced so the margin is not biased toward the majority class."),
  h2("3.3 Data Preprocessing (Text Cleaning, Lowercasing, Punctuation Removal, Tokenization, Stopword Removal, Lemmatization)"),
  body("All text, for both training and live analysis, passes through one shared pipeline in services/text_preprocessor.py: (1) cleaning and lowercasing with regular expressions, (2) tokenization with NLTK's word_tokenize, (3) English stop-word removal, and (4) lemmatization with the WordNetLemmatizer. Before punctuation is stripped, technical terms that contain symbols (C++, C#, .NET, Node.js, CI/CD) or are multi-word phrases (REST API, Power BI, Spring Boot) are replaced by protected placeholder tokens so they survive tokenization instead of collapsing to a bare letter. Results are memoized, so repeated analyses of the same text cost nothing."),
  body("Figure 3.2 shows the processed dataset with the added processed_text column, and Table 3.3 lists real before/after examples produced by the pipeline.", { keepNext: true }),
  ...figure("fig_dataset_processed.png", 590, 220, "3.2", "Processed Dataset (resume_dataset_processed.csv) Opened in a Spreadsheet View"),
  tblCaption("3.3", "Examples of Text Preprocessing (Before and After)"),
  btable(["Original Text", "Processed Text"], [
    ["Experienced Software Developer with 5 years in Python, Django, and REST APIs. Built scalable web applications at Infosys.",
     "experienced software developer 5 year python django skillterm_rest_api build scalable web application infosys"],
    ["PROFESSIONAL SUMMARY: Data Analyst skilled in SQL, Tableau & Power BI. Improved reporting accuracy by 30%!",
     "professional summary data analyst skilled sql tableau skillterm_power_bi improve report accuracy 30"],
    ["Education: B.Tech in Computer Science, Aditya University (2024). Skills: Java, Spring Boot, MySQL, Docker, C++.",
     "education b tech computer science aditya university 2024 skill java skillterm_spring_boot mysql docker skillterm_c_plus_plus"],
  ], [50, 50], { fontSize: 18, leftCols: [0, 1] }),
  body("Note how the protected tokens keep REST API, Power BI, Spring Boot and C++ as single units, inflected verbs collapse to their lemmas (built becomes build, improved becomes improve), and casing, punctuation and stop-words disappear. The processed text is what the TF-IDF vectorizer consumes in Chapter 4."),
];

// ---------- chapter 4 ----------
const ch4 = [
  chapter(4, "RESUME CLASSIFICATION USING TF-IDF AND CALIBRATED SVM"),
  h2("4.1 Need for Machine-Learning Classification"),
  body("A computer cannot map a free-form resume to a job category by string comparison alone: the same role is described with different words, and categories overlap (a Web Developer resume mentions Python; a Data Analyst resume mentions SQL). Rule-based keyword counting would require maintaining hundreds of hand-written rules per category. Supervised learning solves this by deriving the decision boundary from labeled examples: the classifier learns which term combinations distinguish, say, a DevOps Engineer from a Data Scientist, directly from the corpus of Chapter 3. Because the output should also express how certain the system is, the model must produce probabilities - which motivates the calibration step described below."),
  h2("4.2 TF-IDF Representation, Scoring Method and Numerical Example"),
  body("Each processed resume is converted into a TF-IDF vector using scikit-learn's TfidfVectorizer with unigrams and bigrams (ngram_range 1-2), a vocabulary capped at the 5,000 most frequent terms, a document frequency floor of min_df 2, and sublinear term frequency. TF-IDF weighs a term by how often it appears in the resume but down-weights terms that appear in almost every resume, so discriminative phrases such as \"software developer\" or \"skillterm_c_plus_plus\" dominate the vector while generic words vanish. Bigrams let the model use phrases (\"machine learning\", \"web application\") that single tokens would blur."),
  body("As a real numerical example, Table 4.1 lists the non-zero TF-IDF weights the trained vectorizer assigns to the first sample sentence of Table 3.3.", { keepNext: true }),
  tblCaption("4.1", "TF-IDF Weights for a Sample Preprocessed Sentence"),
  btable(["Term (unigram / bigram)", "TF-IDF Weight"], [
    ["experienced", "0.512"],
    ["software developer", "0.442"],
    ["developer year", "0.301"],
    ["web application", "0.275"],
    ["scalable", "0.261"],
    ["skillterm_rest_api", "0.254"],
    ["python", "0.231"],
    ["web", "0.230"],
    ["developer", "0.220"],
    ["software", "0.197"],
  ], [64, 36]),
  h2("4.3 Classification Implementation: LinearSVC and Probability Calibration"),
  body("The classifier is a linear Support Vector Machine (LinearSVC, C = 1.0, class_weight = balanced, max_iter = 10,000) trained on the TF-IDF vectors of 1,453 resumes; 364 resumes are held out for evaluation with a stratified 80/20 split (random_state 42). A linear kernel suits text classification because documents are sparse high-dimensional vectors where classes are close to linearly separable, and LinearSVC trains in seconds on this corpus."),
  body("LinearSVC outputs signed margins, not probabilities. To attach an honest confidence to each prediction, the SVM is wrapped in CalibratedClassifierCV with method sigmoid (Platt scaling) and cv 5: five internal folds fit sigmoid curves that map margins to probabilities. The training script additionally trains a dense alternative - a two-layer MLP (256, 64) on scaled TF-IDF features - and a soft-voting ensemble of both, then keeps whichever model wins on the held-out split. In the final run the calibrated SVM won (94.51% against 92.03% MLP and 92.58% ensemble), so the deployed system predicts with the SVM alone; the comparison is stored in models/model_metadata.json."),
  h2("4.4 Classification Matrix and Sample Output"),
  body("Table 4.2 reports precision, recall and F1 per category on the 364 held-out resumes, and Table 4.3 the confusion matrix.", { keepNext: true }),
  tblCaption("4.2", "Classification Report on the Held-out Test Set (364 Resumes)"),
  btable(["Category", "Precision", "Recall", "F1-Score", "Support"], [
    ["Business Analyst", "0.88", "0.85", "0.86", "75"],
    ["Cloud Engineer", "1.00", "1.00", "1.00", "28"],
    ["Data Analyst", "1.00", "1.00", "1.00", "28"],
    ["Data Scientist", "1.00", "1.00", "1.00", "28"],
    ["DevOps Engineer", "1.00", "1.00", "1.00", "28"],
    ["Machine Learning Engineer", "1.00", "1.00", "1.00", "28"],
    ["Software Developer", "0.88", "0.96", "0.92", "52"],
    ["UI/UX Designer", "1.00", "0.94", "0.97", "50"],
    ["Web Developer", "0.91", "0.91", "0.91", "47"],
    ["Accuracy (macro / weighted avg)", "0.96 / 0.95", "-", "0.96 / 0.95", "364"],
  ], [36, 16, 16, 16, 16], { fontSize: 19 }),
  tblCaption("4.3", "Confusion Matrix of the Test Set (Rows: Actual, Columns: Predicted)"),
  btable(
    ["Actual \\ Predicted", "BA", "CE", "DA", "DS", "DE", "ML", "SD", "UX", "WD"],
    [
      ["Business Analyst (75)", "64", "0", "0", "0", "0", "0", "7", "0", "4"],
      ["Cloud Engineer (28)", "0", "28", "0", "0", "0", "0", "0", "0", "0"],
      ["Data Analyst (28)", "0", "0", "28", "0", "0", "0", "0", "0", "0"],
      ["Data Scientist (28)", "0", "0", "0", "28", "0", "0", "0", "0", "0"],
      ["DevOps Engineer (28)", "0", "0", "0", "0", "28", "0", "0", "0", "0"],
      ["ML Engineer (28)", "0", "0", "0", "0", "0", "28", "0", "0", "0"],
      ["Software Developer (52)", "2", "0", "0", "0", "0", "0", "50", "0", "0"],
      ["UI/UX Designer (50)", "3", "0", "0", "0", "0", "0", "0", "47", "0"],
      ["Web Developer (47)", "4", "0", "0", "0", "0", "0", "0", "0", "43"],
    ],
    [29, 7.9, 7.9, 7.9, 7.9, 7.9, 7.9, 7.9, 7.9, 7.9], { fontSize: 18 }
  ),
  body("Six of the nine categories are separated perfectly. All 20 residual errors flow into Business Analyst, which is expected given its over-representation and its generic business vocabulary that overlaps with developer, designer and web resumes. At inference time the system returns the top three categories with their calibrated confidences; a typical strong prediction reads Software Developer 51.6%, Data Analyst 10.1%, Machine Learning Engineer 7.5%. The training caveats are stated honestly in models/training_report.txt: part of the corpus is template-generated, so real-world accuracy will be lower, and the confidence values are approximations from the calibration curves, not exact likelihoods."),
];

// ---------- chapter 5 ----------
const ch5 = [
  chapter(5, "ATS SCORING, JOB MATCHING AND VALIDATION"),
  h2("5.1 Scoring Approach"),
  body("Classification answers \"what role is this resume closest to?\"; the ATS engine answers \"how does this resume survive a keyword-parsing applicant tracking system?\". The engine models how platforms such as Taleo, Workday, iCIMS or Greenhouse evaluate a resume: as a set of measurable factors - keyword coverage, required skills, title match, experience, education, parseability and content quality - combined with explicit weights. Every factor returns a 0-100 subscore, and the weighted mean is the ATS score. A factor that cannot be computed (for example, education when the job description states no requirement) is excluded and its weight is redistributed proportionally, so missing information never silently pulls the score toward 0 or 100."),
  h2("5.2 Data Used for Scoring"),
  body("Two inputs feed the engine. The resume side uses the structured profile from the information extractor (sections, skills, titles, experience intervals, education) plus the raw and processed text. The job-description side, when the user provides one, is parsed by a dedicated JD parser that extracts the posting title, seniority, required and preferred skills and the requirement/responsibility text; benefit and EEO boilerplate is stripped so it can never penalize the candidate. When no JD is given, the engine switches to a standalone audit with four factors (format 35%, content 30%, skill breadth 20%, education presence 15%)."),
  h2("5.3 Techniques Used"),
  body("Table 5.1 lists the seven factors of the job-match mode with their weights, and Figure 5.1 visualizes them. Keyword matching is inflection-aware (analyzed matches analyze), irregular-verb-aware (built matches build) and typo-tolerant (a JD keyword one edit away from a resume word counts, and the typo is flagged with a fix suggestion). Experience uses interval-union date arithmetic over the experience section - overlapping roles never double-count and Present is resolved - taking the maximum of the computed years and any self-reported claim. Format runs eight parser checks (contact info, name, standard section headers, dates, healthy length, clean extraction); content quality measures quantified bullets (target 40%), action-verb openers (target 60%) and absence of first-person pronouns.", { keepNext: true }),
  tblCaption("5.1", "ATS Factors, Weights and Meaning (Resume vs Job Description)"),
  btable(["Factor", "Weight", "What It Measures"], [
    ["Keyword coverage", "25%", "Weighted JD keywords found on the resume; skills count heaviest, boilerplate stripped"],
    ["Skills match", "25%", "Required-skill coverage (75%) blended with preferred skills (25%)"],
    ["Experience", "15%", "Years evidenced vs required, from interval-union date math and claims"],
    ["Job title match", "10%", "Posting title vs resume titles/headline (string ratio + token overlap)"],
    ["Format & parseability", "10%", "Eight parser checks: contact, name, sections, dates, length, extraction quality"],
    ["Content quality", "10%", "Quantified achievements, action-verb openers, no first-person pronouns"],
    ["Education", "5%", "Degree level vs the requirement"],
  ], [24, 10, 66], { fontSize: 19, leftCols: [2] }),
  ...figure("fig_ats_weights.png", 480, 230, "5.1", "ATS Factor Weights in the Resume vs Job Description Mode"),
  body("The engine also computes a potential score - an honest upper bound showing how many points the flagged fixes are worth. Only factors the candidate can actually change (keywords, skills, title, formatting) are capped at their potential; experience and education keep their real values. Table 5.2 defines the grade bands shown in the interface.", { keepNext: true }),
  tblCaption("5.2", "ATS Grade Bands"),
  btable(["ATS Score", "Grade"], [
    ["85 - 100", "Excellent"],
    ["70 - 84.9", "Strong"],
    ["55 - 69.9", "Fair"],
    ["40 - 54.9", "Needs work"],
    ["Below 40", "High risk"],
  ], [50, 50]),
  h2("5.4 Scoring and Prediction Process"),
  body("A scoring run proceeds as: parse resume, detect non-resumes (borderline documents proceed with a warning banner), preprocess text, parse the JD if present, then compute each factor with its checks and suggestions. The job-match score shown alongside is a transparent blend - skills 50%, TF-IDF text similarity (unigrams + bigrams, sublinear TF) 25%, experience 15%, education 10% - with all weights configurable through environment variables. Finally the recommendation engine sorts the collected suggestions by expected score gain and emits adjacent-skill advice (a missing skill from a category the resume already demonstrates is called out explicitly)."),
  h2("5.5 Validation Results"),
  body("The scoring engine is validated by an 8x8 cross-domain matrix (validate_ats_matrix.py): eight tailored resumes are each scored against all eight job descriptions, and every tailored resume must rank its own JD first - diagonal dominance holds in all 64 cells. Causal checks confirm that applying the tool's advice to a resume raises its score by 15 to 23 points, and that gutting skills never raises a score while adding a missing skill never lowers it (enforced by the fuzz/property test suite). A JD quality checker flags weak job descriptions (too short, few skills, no requirements) so users know which match numbers to trust."),
];

// ---------- chapter 6 ----------
const ch6 = [
  chapter(6, "IMPLEMENTATION"),
  h2("6.1 NLTK Library and Keywords Used"),
  body("The preprocessing layer is built on NLTK (Natural Language Toolkit). Its data packages are downloaded once at setup; every loader has an offline fallback so the pipeline also works without network access. Table 6.1 lists the components used, and Table 6.2 the key functions of the pipeline.", { keepNext: true }),
  tblCaption("6.1", "NLTK Components Used in the System"),
  btable(["Component", "Package / Class", "Purpose"], [
    ["word_tokenize", "nltk.tokenize (Punkt)", "Splits cleaned text into word tokens"],
    ["stopwords", "nltk.corpus.stopwords", "English stop-word list for filtering"],
    ["WordNetLemmatizer", "nltk.stem", "Reduces inflected words to their dictionary lemma"],
    ["wordnet", "nltk.corpus (WordNet)", "Lemma database used by the lemmatizer"],
    ["averaged_perceptron_tagger", "nltk.tag", "POS tags for lemma accuracy where applicable"],
  ], [30, 30, 40], { fontSize: 19, leftCols: [1, 2] }),
  tblCaption("6.2", "Important Functions and Keywords of the Pipeline"),
  btable(["Function / Keyword", "Module", "Purpose"], [
    ["preprocess_text()", "services/text_preprocessor.py", "Full pipeline: clean, tokenize, stop-words, lemmatize"],
    ["_make_safe_token()", "services/text_preprocessor.py", "Turns C++, REST API etc. into protected single tokens"],
    ["@lru_cache", "functools", "Memoizes preprocessing and JD parsing for repeated inputs"],
    ["predict_with_confidence()", "services/classifier.py", "Top-N categories with calibrated probabilities"],
    ["compute_keyword_match()", "services/ats_scorer.py", "Inflection- and typo-aware keyword coverage"],
    ["compute_experience_factor()", "services/ats_scorer.py", "Interval-union years-of-experience math"],
    ["_weighted_total() / _grade()", "services/ats_scorer.py", "Weighted ATS total and grade band"],
    ["match_resume_to_jd()", "services/matching_engine.py", "Skills + TF-IDF similarity blend"],
    ["detect_document_type()", "services/resume_detector.py", "Non-resume rejection with confidence"],
    ["create_app()", "app.py", "Flask application factory with all routes"],
  ], [30, 30, 40], { fontSize: 18, leftCols: [0, 2] }),
  h2("6.2 User Resume Input"),
  body("The upload page (route \"/\") renders a Bootstrap form. It accepts a resume file (PDF or DOCX, at most 10 MB - enforced both client-side and by Flask's MAX_CONTENT_LENGTH), optional JD text or file, the analysis mode (standalone audit, single match, rank up to 10 JDs, or compare 2-5 resumes) and advanced options: ATS strictness (lenient / standard / strict) and a target job-title override. Invalid extensions and oversized files are rejected with a clear error before any parsing starts. The JSON API endpoint /api/analyze accepts the same payload programmatically."),
  h2("6.3 Preprocessing Implementation"),
  body("The shared pipeline lives in services/text_preprocessor.py and is used identically for training and for live analysis - one code path, so training and inference can never drift apart. The full listing is included in Appendix A. In summary: re-based cleaning lowercases and strips non-alphabetic characters (after protecting skill terms), word_tokenize splits the text, the NLTK English stop-word list (plus a built-in fallback) removes function words, and WordNetLemmatizer produces the lemmas. The output string is cached with lru_cache keyed on the input text."),
  h2("6.4 Classification and Scoring Implementation"),
  body("services/classifier.py loads the joblib-persisted vectorizer and calibrated SVM once at startup and memoizes predictions per resume text (the tracker re-analyzes the same files repeatedly, so this matters). The ATS scorer (services/ats_scorer.py, roughly 1,200 lines) computes each factor in isolation, collects evidence and suggestions, redistributes the weights of non-computable factors, and derives the grade and potential score. The analysis service then assembles category, factors, skills, match results and recommendations into one response object that both the HTML templates and the JSON API consume."),
  h2("6.5 Job Description Parsing and Validation Implementation"),
  body("services/job_description_parser.py extracts the title, seniority, required and preferred skills and the requirement text from a pasted or uploaded JD, stripping benefits and equal-opportunity boilerplate. services/resume_detector.py guards the pipeline entrance: every upload is classified first, and non-resumes (thesis, report, cover letter, invoice) are refused politely with the detected document type and confidence instead of receiving a meaningless score. Borderline documents proceed but are flagged with a warning banner in the results."),
  h2("6.6 Important Code Snippets"),
  body("Training is executed from the project root with a single command:", { noIndent: true, after: 60 }),
  ...codeInline(["(.venv) python -m training.prepare_dataset", "(.venv) python -m training.train_model"]),
  body("The core of the classifier training (from training/train_model.py) is:", { noIndent: true, after: 60, keepNext: true }),
  ...codeInline([
    "vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000,",
    "                            min_df=2, sublinear_tf=True)",
    "X_train_vec = vectorizer.fit_transform(X_train)",
    "",
    "base_svm = LinearSVC(C=1.0, class_weight=\"balanced\", max_iter=10000)",
    "classifier = CalibratedClassifierCV(base_svm, method=\"sigmoid\", cv=5)",
    "classifier.fit(X_train_vec, y_train)",
  ]),
  body("and prediction with calibrated confidence (from services/classifier.py):", { noIndent: true, after: 60, keepNext: true }),
  ...codeInline([
    "processed = preprocess_text(resume_text)",
    "vector = _vectorizer.transform([processed])",
    "probabilities = _classifier.predict_proba(vector)[0]",
    "ranked = sorted(zip(_classifier.classes_, probabilities),",
    "                key=lambda p: p[1], reverse=True)",
  ]),
  body("The complete source files are reproduced in the Appendix.", { noIndent: true }),
];

// ---------- chapter 7 ----------
const ch7 = [
  chapter(7, "RESULT VISUALIZATION AND WEB INTERFACE"),
  h2("7.1 Interface Design"),
  body("The web interface is a Flask application serving Bootstrap templates. Figure 7.1 shows the upload page: the resume picker, the four analysis modes, the job-description panel and the advanced options are all on one screen so a first-time user needs no instructions.", { keepNext: true }),
  ...figure("slide12_4.png", 580, 254, "7.1", "Resume Upload and Analysis Interface"),
  h2("7.2 Analysis Results Presentation"),
  body("After analysis, the results page leads with the candidate summary, the predicted category and its confidence, and the ATS gauge with the score and grade (Figure 7.2). A sample run shown during the review predicted Software Developer with 51.6% calibrated confidence and an ATS score of 90.3/100 (grade Excellent).", { keepNext: true }),
  ...figure("slide13_4.png", 580, 251, "7.2", "Analysis Results: Predicted Category and ATS Score Gauge"),
  body("Below the gauge, every factor is displayed with its subscore, weight and the checks behind it (Figure 7.3), together with the potential score that quantifies how much the flagged fixes are worth.", { keepNext: true }),
  ...figure("slide14_4.png", 580, 259, "7.3", "ATS Score Breakdown and Parser Checks"),
  h2("7.3 Recommendations and Detected Skills"),
  body("The recommendations panel (Figure 7.4) lists the improvement suggestions in priority order - each names the exact section to change and the points it is worth - and the detected-skills panel groups the recognized skills into categories such as programming languages, frontend development, databases and AI/ML.", { keepNext: true }),
  ...figure("slide15_4.png", 580, 260, "7.4", "Prioritized Recommendations and Detected Skills"),
  h2("7.4 Charts / Graphs: ATS Tracker and Progress"),
  body("The tracker page summarizes all stored runs: average and best ATS scores, average job-match value and a score-trend chart across recent runs (Figure 7.5). The progress view (Figure 7.6) compares resumes analyzed more than once, showing first, latest and best scores with a trend badge - this is the view that turns advice into measurable improvement.", { keepNext: true }),
  ...figure("slide16_4.png", 580, 250, "7.5", "ATS Tracker Dashboard with Score Trend"),
  ...figure("slide17_4.png", 560, 274, "7.6", "Resume Progress Comparison"),
  h2("7.5 Sample Analyses and Predictions"),
  body("Table 7.1 aggregates the 571 analyses recorded in the development database, and Table 7.2 lists a representative sample of real stored runs (file names as uploaded).", { keepNext: true }),
  tblCaption("7.1", "Aggregate Results across the 571 Stored Analyses"),
  btable(["Metric", "Value"], [
    ["Total analysis runs stored", "571"],
    ["Distinct resumes analyzed", "32"],
    ["Standalone audits (no JD)", "288 runs, average ATS 76.8"],
    ["Job-match analyses (with JD)", "282 runs, average ATS 45.8"],
    ["Best ATS score recorded", "97.5 / 100"],
    ["Average ATS score (all runs)", "61.5"],
    ["Average TF-IDF similarity (job-match runs)", "3.22 / 5"],
    ["Analyses that used Gemini phrasing", "0 (fully offline)"],
  ], [55, 45], { leftCols: [0, 1] }),
  tblCaption("7.2", "Sample Analyses and Predictions from the History Database"),
  btable(["Resume File", "Mode", "Predicted Category", "ATS Score", "Grade"], [
    ["Sai_Teja_Resume(updated).docx", "Standalone", "Software Developer", "90.3", "Excellent"],
    ["Divya_Resume.pdf", "Standalone", "Software Developer", "77.5", "Strong"],
    ["resume_hari (3).pdf", "Standalone", "Software Developer", "74.7", "Strong"],
    ["Venkata_Natesh_Nallam_Resume.pdf", "Standalone", "Software Developer", "68.9", "Fair"],
    ["Naga_Sathwika_Kovvuri_Google.pdf", "Job match", "Software Developer", "61.9", "Fair"],
    ["SWATI PRIYA.pdf", "Job match", "Web Developer", "38.0", "High risk"],
    ["SRIRAM SIDDHARDHA REDDY PADALA (1).pdf", "Job match", "Software Developer", "22.0", "High risk"],
  ], [36, 15, 23, 13, 13], { fontSize: 18, leftCols: [0] }),
  h2("7.6 Screenshots"),
  body("Figure 7.7 shows the analysis history table: every run with its date, resume, analysis type, ATS score, grade and job-match value, one click away from its full JSON details and downloadable text report.", { keepNext: true }),
  ...figure("slide18_4.png", 560, 263, "7.7", "Analysis History Table"),
  h2("7.7 Results and Discussion"),
  body("Three observations stand out from the stored runs. First, standalone audits score systematically higher than job-match analyses (76.8 vs 45.8 on average): a resume can be well-formatted and rich in skills yet still miss the specific keywords of a concrete job description - exactly the gap the recommendations are designed to close. Second, repeated analyses of the same file are deterministic; the progress view therefore reflects real edits, not noise. Third, the spread of grades in Table 7.2 (Excellent to High risk) shows the engine discriminates across resume quality rather than clustering every input in the middle."),
  body("The classification results of Chapter 4 and these interface-level results are consistent: every stored run predicted a plausible category, and the calibrated confidence was high exactly for the resumes whose content matched a category vocabulary. The high-risk job-match scores in Table 7.2 belong to resumes scored against a JD whose required skills they barely touch - the factor breakdown makes the reason visible in each case."),
];

// ---------- chapter 8 ----------
const ch8 = [
  chapter(8, "CONCLUSION AND FUTURE ENHANCEMENTS"),
  h2("8.1 Conclusion"),
  body("This project demonstrated how an NLP-plus-ML pipeline can automate the analysis of resumes end to end. A shared preprocessing pipeline (cleaning, tokenization, stop-word removal, lemmatization, protected technical terms) feeds a TF-IDF + calibrated SVM classifier that reaches 94.51% accuracy over nine job categories on the held-out test set, with honest per-category metrics and a documented comparison against a neural-network alternative. Around the classifier, the system extracts structured profile information, matches resumes against job descriptions, scores them with a transparent seven-factor ATS engine, generates prioritized and quantified improvement advice, and tracks score history so that improvement is measured, not assumed."),
  body("The engineering wrapped around the pipeline is part of the contribution: every capability is a small isolated service, all weights and limits are configuration-driven, uploaded files never touch the disk, the database stores no personal data, and 149 automated tests - including an 8x8 cross-domain matrix and causal checks - protect the scoring behaviour. The result is a working web application that turns hours of manual, inconsistent screening into seconds of consistent, explainable feedback."),
  h2("8.2 Limitations"),
  bullet("Part of the training corpus (1,260 of 1,817 resumes) is template-generated; real-world accuracy will be lower than the 94.51% held-out figure, although the merged real-resume portion (557 documents) narrows the gap.", { lead: "Dataset - " }),
  bullet("Calibrated confidences are sigmoid approximations of LinearSVC margins, not exact likelihoods; borderline resumes can therefore show flattened probability differences.", { lead: "Calibration - " }),
  bullet("The ATS engine models keyword-parsing systems; it cannot capture proprietary ranking logic, semantic reading or recruiter judgement.", { lead: "ATS modelling - " }),
  bullet("Experience parsing depends on recognizable date ranges; unusual formats can undercount years.", { lead: "Experience extraction - " }),
  bullet("The system runs as a single-process local application with no user accounts - appropriate for the project scope, but not yet multi-tenant.", { lead: "Deployment - " }),
  h2("8.3 Future Enhancements"),
  bullet("Replace or augment the SVM with a transformer model (BERT-family) fine-tuned on a larger real resume corpus for better real-world accuracy."),
  bullet("Train on a fully real, larger labeled dataset as the primary accuracy lever."),
  bullet("Personalized job recommendations from the ranked-JD mode and external job feeds."),
  bullet("Skill-gap analysis with concrete course or project suggestions per target role."),
  bullet("Resume-to-resume leaderboards for placement cells, and Docker-based cloud deployment with authentication."),
  bullet("Multilingual resume support and richer PDF layout analysis (columns, tables, graphics)."),
];

// ---------- references ----------
function refPara(text) {
  return new Paragraph({
    indent: { left: 567, hanging: 567 },
    spacing: { line: 300, after: 100 },
    alignment: AlignmentType.JUSTIFIED,
    children: [R(text, { size: 21 })],
  });
}
const references = [
  new Paragraph({
    heading: HeadingLevel.HEADING_1, pageBreakBefore: true, alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 240, line: 360 },
    children: [new TextRun({ text: "REFERENCES", font: { ascii: TNR, hAnsi: TNR }, size: 28, bold: true, color: BLACK })],
  }),
  refPara("[1] S. Bird, E. Klein and E. Loper, Natural Language Processing with Python. Sebastopol, CA, USA: O'Reilly Media, 2009."),
  refPara("[2] NLTK Project, \"Natural Language Toolkit Documentation.\" [Online]. Available: https://www.nltk.org"),
  refPara("[3] F. Pedregosa et al., \"Scikit-learn: Machine Learning in Python,\" Journal of Machine Learning Research, vol. 12, pp. 2825-2830, 2011."),
  refPara("[4] G. Salton and C. Buckley, \"Term-weighting approaches for automatic text retrieval,\" Information Processing & Management, vol. 24, no. 5, pp. 513-523, 1988."),
  refPara("[5] C. Cortes and V. Vapnik, \"Support-vector networks,\" Machine Learning, vol. 20, no. 3, pp. 273-297, 1995."),
  refPara("[6] J. Platt, \"Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods,\" in Advances in Large Margin Classifiers, Cambridge, MA, USA: MIT Press, 1999, pp. 61-74."),
  refPara("[7] R. Baeza-Yates and B. Ribeiro-Neto, Modern Information Retrieval. Boston, MA, USA: Addison-Wesley, 1999."),
  refPara("[8] Pallets Projects, \"Flask Documentation.\" [Online]. Available: https://flask.palletsprojects.com"),
  refPara("[9] pypdf Contributors, \"pypdf Documentation.\" [Online]. Available: https://pypdf.readthedocs.io"),
  refPara("[10] python-docx Contributors, \"python-docx Documentation.\" [Online]. Available: https://python-docx.readthedocs.io"),
  refPara("[11] Explosion AI, \"spaCy: Industrial-Strength Natural Language Processing.\" [Online]. Available: https://spacy.io"),
  refPara("[12] Kaggle, \"Resume Datasets.\" [Online]. Available: https://www.kaggle.com"),
  refPara("[13] Jobscan, \"What Is an Applicant Tracking System?\" [Online]. Available: https://www.jobscan.co/blog/what-is-an-applicant-tracking-system/"),
];

// ---------- appendix ----------
function appendixHead(text) {
  return new Paragraph({
    spacing: { before: 240, after: 120, line: 312 },
    children: [new TextRun({ text, font: { ascii: TNR, hAnsi: TNR }, size: 24, bold: true, color: BLACK })],
  });
}
const appendix = [
  new Paragraph({
    heading: HeadingLevel.HEADING_1, pageBreakBefore: true, alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 240, line: 360 },
    children: [new TextRun({ text: "APPENDIX \u2013 SOURCE CODE", font: { ascii: TNR, hAnsi: TNR }, size: 28, bold: true, color: BLACK })],
  }),
  body("The listings below reproduce the three core modules of the system verbatim from the project repository: the shared NLP preprocessing pipeline, the classifier training script and the runtime classifier service.", { noIndent: true, after: 160 }),
  appendixHead("A. services/text_preprocessor.py"),
  ...codeBlock(1, 195, "../services/text_preprocessor.py"),
  appendixHead("B. training/train_model.py"),
  ...codeBlock(1, 191, "../training/train_model.py"),
  appendixHead("C. services/classifier.py"),
  ...codeBlock(1, 121, "../services/classifier.py"),
];

// ---------- assemble ----------
const pageSetup = {
  size: { width: 11906, height: 16838 },
  margin: { top: 1250, bottom: 1150, left: 1440, right: 1440, header: 640, footer: 640 },
};
const doc = new Document({
  creator: "Saiteja K, Gnaneswari K, Siddhardha P, Mahalaxmi M",
  title: "Intelligent Resume Analysis and Classification System - Cornerstone Project Report",
  styles: {
    default: {
      document: {
        run: { font: { ascii: TNR, hAnsi: TNR, eastAsia: TNR }, size: 22, color: BLACK },
        paragraph: { spacing: { line: 312 } },
      },
      heading1: {
        run: { font: { ascii: TNR, hAnsi: TNR }, size: 28, bold: true, color: BLACK },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240, line: 360 } },
      },
      heading2: {
        run: { font: { ascii: TNR, hAnsi: TNR }, size: 26, bold: true, color: BLACK },
        paragraph: { spacing: { before: 240, after: 120, line: 312 } },
      },
      heading3: {
        run: { font: { ascii: TNR, hAnsi: TNR }, size: 24, bold: true, color: BLACK },
        paragraph: { spacing: { before: 200, after: 100, line: 312 } },
      },
    },
  },
  sections: [
    { // title page
      properties: { page: { ...pageSetup, margin: { top: 900, bottom: 900, left: 1440, right: 1440 } } },
      children: cover,
    },
    { // front matter: roman numerals from ii
      properties: {
        type: "nextPage",
        page: { ...pageSetup, pageNumbers: { start: 2, formatType: NumberFormat.LOWER_ROMAN } },
      },
      headers: { default: pageHeader() },
      footers: { default: pageFooter() },
      children: [...certDecl, ...declaration, ...acknowledgement, ...abstractPage, ...tocPage, ...lofPage, ...lotPage],
    },
    { // body: arabic from 1
      properties: {
        type: "nextPage",
        page: { ...pageSetup, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } },
      },
      headers: { default: pageHeader() },
      footers: { default: pageFooter() },
      children: [...ch1, ...ch2, ...ch3, ...ch4, ...ch5, ...ch6, ...ch7, ...ch8, ...references, ...appendix],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("WROTE " + OUT + " (" + Math.round(buf.length / 1024) + " KB)");
});
