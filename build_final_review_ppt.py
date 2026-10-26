"""
Complete 42-Slide PowerPoint Generator for Aditya University AMSD Final Review.
Clones C:\\Users\\sai\\Downloads\\AMSD_PPT.pptx, preserving 100% of the original:
- Aditya University Logos & Layout Geometry
- Dark gradient pill header banners
- Times New Roman typography and precise font sizes
- Professional slide structure and exact presentation outline

Tailors every slide to the Intelligent Resume Analyzer project.
"""

import os
import copy
import shutil
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

SRC_PPTX = os.path.expanduser('~/Downloads/AMSD_PPT.pptx')
OUT_DIR = os.path.abspath('.')
OUT_PPTX_LOCAL = os.path.join(OUT_DIR, 'Intelligent_Resume_Analyzer_AMSD_Final_Review.pptx')
OUT_PPTX_DESKTOP = os.path.expanduser('~/OneDrive/Desktop/Intelligent_Resume_Analyzer_AMSD_Final_Review.pptx')
OUT_PPTX_DOWNLOADS = os.path.expanduser('~/Downloads/AMSD_Resume_Project_Final_Review.pptx')

FONT_NAME = "Times New Roman"
COLOR_TITLE = RGBColor(0x1F, 0x29, 0x37)
COLOR_RED = RGBColor(0xFF, 0x00, 0x00)
COLOR_NAVY = RGBColor(0x17, 0x37, 0x5E)
COLOR_BURGUNDY = RGBColor(0x94, 0x37, 0x35)


def set_text_run(paragraph, text, font_name=FONT_NAME, size_pt=20.0, bold=False, color=None):
    paragraph.text = ""
    run = paragraph.add_run()
    run.text = text
    run.font.name = font_name
    if size_pt:
        run.font.size = Pt(size_pt)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color


def update_textbox_paragraphs(shp, paragraphs_data, default_size=20.0):
    """
    paragraphs_data is a list of tuples: (text, font_size, is_bold, color)
    or just strings.
    """
    tf = shp.text_frame
    tf.clear()
    for idx, item in enumerate(paragraphs_data):
        if idx == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
            
        if isinstance(item, tuple):
            text = item[0]
            sz = item[1] if len(item) > 1 and item[1] else default_size
            b = item[2] if len(item) > 2 else False
            c = item[3] if len(item) > 3 else None
        else:
            text = str(item)
            sz = default_size
            b = False
            c = None
            
        set_text_run(p, text, font_name=FONT_NAME, size_pt=sz, bold=b, color=c)


def set_table_data(table, data):
    """
    Dynamically adjusts table rows and populates with Times New Roman cells.
    data: list of rows (each row is a list of cell strings).
    """
    num_rows = len(data)
    while len(table.rows) < num_rows:
        last_row = table.rows[len(table.rows) - 1]
        new_tr = copy.deepcopy(last_row._tr)
        table._tbl.append(new_tr)
    while len(table.rows) > num_rows:
        last_row = table.rows[len(table.rows) - 1]
        tr = last_row._tr
        table._tbl.remove(tr)

    for r_idx, row_data in enumerate(data):
        row = table.rows[r_idx]
        for c_idx, cell_value in enumerate(row_data):
            if c_idx < len(row.cells):
                cell = row.cells[c_idx]
                cell.text = ""
                p = cell.text_frame.paragraphs[0]
                run = p.add_run()
                run.text = str(cell_value)
                run.font.name = FONT_NAME
                run.font.size = Pt(13.0 if r_idx > 0 else 14.5)
                run.font.bold = (r_idx == 0)


def replace_screenshot(slide, new_image_path, is_double=False, top_img=True):
    """
    Replaces the screenshot image on implementation slides while keeping
    the Aditya University logo intact.
    """
    if not os.path.exists(new_image_path):
        print(f"Warning: image {new_image_path} does not exist.")
        return

    pics = [shp for shp in slide.shapes if shp.shape_type == 13 and shp.top > 1000000]
    if not pics:
        return

    if is_double:
        pics.sort(key=lambda p: p.top)
        target = pics[0] if top_img else pics[1]
    else:
        target = pics[0]

    left, top, w, h = target.left, target.top, target.width, target.height
    sp = target._element
    sp.getparent().remove(sp)
    slide.shapes.add_picture(new_image_path, left, top, w, h)


def build_deck():
    print(f"Loading template from {SRC_PPTX}...")
    prs = Presentation(SRC_PPTX)
    print(f"Loaded presentation: {len(prs.slides)} slides.")

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides[0]
    for shp in s1.shapes:
        if shp.has_text_frame:
            tf = shp.text_frame
            if any("presented" in p.text.lower() for p in tf.paragraphs):
                tf.clear()
                p0 = tf.paragraphs[0]
                set_text_run(p0, "Intelligent Resume Analyzer", size_pt=24.0, bold=True, color=COLOR_NAVY)
                p0.alignment = PP_ALIGN.CENTER
                
                tf.add_paragraph() # space
                
                p_pres = tf.add_paragraph()
                set_text_run(p_pres, "Presented by", size_pt=22.0, bold=True, color=COLOR_RED)
                p_pres.alignment = PP_ALIGN.CENTER
                
                tf.add_paragraph() # space
                
                students = [
                    "Saiteja K (24B11CS220)",
                    "Gnaneswari K (24B11CS190)",
                    "Siddhardha P (24B11CS324)",
                    "Mahalaxmi M (24B11CS253)",
                ]
                for s_name in students:
                    p_s = tf.add_paragraph()
                    set_text_run(p_s, s_name, size_pt=20.0, bold=False, color=COLOR_NAVY)
                    p_s.alignment = PP_ALIGN.CENTER
                    
                tf.add_paragraph() # space
                
                p_dept = tf.add_paragraph()
                set_text_run(p_dept, "Department of Computer Science and Engineering", size_pt=22.0, bold=True, color=COLOR_BURGUNDY)
                p_dept.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 2: PRESENTATION OUTLINE
    # =========================================================================
    s2 = prs.slides[1]
    # Outline remains identical to standard: Abstract, Introduction, Problem Statement, etc.

    # =========================================================================
    # SLIDE 3: ABSTRACT (Part 1 - Purpose & NLP/ML Solution)
    # =========================================================================
    s3 = prs.slides[2]
    tb3 = [shp for shp in s3.shapes if shp.has_text_frame and "campusmate" in shp.text_frame.text.lower()][0]
    update_textbox_paragraphs(tb3, [
        ("The Intelligent Resume Analyzer is an advanced web-based Natural Language Processing (NLP) and Machine Learning application designed to automate resume evaluation, job description alignment, and applicant tracking system (ATS) auditing by replacing opaque screening with transparent algorithmic scoring.", 22.0, False),
        ("The system provides automated multi-format document ingestion, semantic skill extraction, tri-model technical career classification, transparent 7-factor ATS scoring, and prioritized ML corrective recommendations. It empowers candidates to optimize their resumes before submission while enabling recruiters to perform batch shortlisting and comparative talent ranking with explainable metrics.", 22.0, False)
    ], default_size=22.0)

    # =========================================================================
    # SLIDE 4: ABSTRACT (Part 2 - Technologies & Architecture)
    # =========================================================================
    s4 = prs.slides[3]
    tb4 = [shp for shp in s4.shapes if shp.has_text_frame and ("technology" in shp.text_frame.text.lower() or "application" in shp.text_frame.text.lower())][0]
    update_textbox_paragraphs(tb4, [
        ("The application is engineered using high-performance Python with Flask for backend micro-services, NLTK and scikit-learn for NLP tokenization and TF-IDF feature extraction, a Calibrated LinearSVC + MLP Neural Network ensemble (94.51% holdout accuracy) for career classification, and SQLite with Write-Ahead Logging (WAL) for persistent audit tracking.", 22.0, False)
    ], default_size=22.0)

    # =========================================================================
    # SLIDE 5: INTRODUCTION
    # =========================================================================
    s5 = prs.slides[4]
    tb5 = [shp for shp in s5.shapes if shp.has_text_frame and shp.top > 1200000][0]
    update_textbox_paragraphs(tb5, [
        ("In modern recruitment, enterprise hiring portals receive hundreds of resumes per job posting, creating severe screening bottlenecks and delayed hiring cycles.", 22.0, False),
        ("Commercial Applicant Tracking Systems (ATS) automatically filter over 75% of applications using rigid keyword heuristics, leaving qualified candidates unaware of why their resumes were rejected.", 22.0, False),
        ("The Intelligent Resume Analyzer provides a transparent, dual-benefit platform: candidates receive granular subscores and ML attribution gaps to optimize their resumes, while recruiters can parse, rank, and shortlist applicant batches in seconds.", 22.0, False)
    ], default_size=22.0)

    # =========================================================================
    # SLIDE 6: PROBLEM STATEMENT
    # =========================================================================
    s6 = prs.slides[5]
    tb6 = [shp for shp in s6.shapes if shp.has_text_frame and shp.top > 1200000][0]
    update_textbox_paragraphs(tb6, [
        ("In traditional and modern recruitment pipelines, job seekers and talent acquisition teams face major systemic challenges:", 22.0, False),
        ("• Manual screening is labor-intensive, inconsistent, and highly susceptible to subjective recruiter bias.", 22.0, False),
        ("• Commercial ATS platforms act as 'black boxes' that silently discard qualified resumes without actionable feedback.", 22.0, False),
        ("• Candidates lack concrete diagnostics on missing category features, passive action verbs, and unquantified achievements.", 22.0, False),
        ("• Recruiters struggle to evaluate and comparatively rank large batches of heterogeneous resumes against complex job requirements. These issues motivated the development of the Intelligent Resume Analyzer.", 22.0, False)
    ], default_size=22.0)

    # =========================================================================
    # SLIDE 7: SYSTEM ANALYSIS (Functional Requirements - Candidate Core Operations)
    # =========================================================================
    s7 = prs.slides[6]
    tb7 = [shp for shp in s7.shapes if shp.has_text_frame and shp.top > 1200000][0]
    update_textbox_paragraphs(tb7, [
        ("Functional Requirements (Candidate & Analysis Pipeline):", 24.0, True, COLOR_NAVY),
        ("The system allows candidates to upload resumes in PDF, DOCX, or TXT format and automatically normalizes, cleans, and extracts structured sections (Skills, Experience, Education, Projects).", 22.0, False),
        ("It provides high-precision multi-category ML classification across 9 technical career tracks (e.g. Software Developer, Data Scientist, Cloud Engineer, DevOps) with probabilistic confidence scores.", 22.0, False),
        ("The scoring engine evaluates the resume across 7 transparent ATS dimensions (Keyword Coverage, Skill Breadth, Experience Relevance, Education Alignment, Section Parseability, Action Verbs, and Formatting Safety).", 22.0, False)
    ], default_size=22.0)

    # =========================================================================
    # SLIDE 8: SYSTEM ANALYSIS (Functional Requirements - Recruiter Operations & Diagnostics)
    # =========================================================================
    s8 = prs.slides[7]
    tb8 = [shp for shp in s8.shapes if shp.has_text_frame and shp.top > 1200000][0]
    update_textbox_paragraphs(tb8, [
        ("The system supports technical recruiters with automated multi-resume batch processing, interactive cut-off threshold filtering, side-by-side comparison, and ranked candidate shortlisting.", 22.0, False),
        ("Candidates and recruiters can view deep Machine Learning diagnostics (LinearSVC feature gap attribution, keyword stuffing penalties, STAR-format metric quantification, and Flesch-Kincaid readability indices) to maximize hiring success.", 22.0, False)
    ], default_size=22.0)

    # =========================================================================
    # SLIDE 9: SYSTEM ANALYSIS (Minimum Hardware Requirements)
    # =========================================================================
    s9 = prs.slides[8]
    tb9 = [shp for shp in s9.shapes if shp.has_text_frame and shp.top > 1000000][0]
    update_textbox_paragraphs(tb9, [
        ("Minimum Hardware Requirements", 22.0, True, COLOR_NAVY),
        ("Processor: Intel Core i3 (10th Gen) / AMD Ryzen 3 or above", 22.0, False),
        ("RAM: Minimum 8 GB (16 GB recommended for neural network training)", 22.0, False),
        ("Storage: 2 GB free space (excluding OS, Python runtime, and datasets)", 22.0, False),
        ("Input Devices: Keyboard, Mouse", 22.0, False),
        ("Output Device: Monitor (1080p Full HD recommended for dashboards)", 22.0, False),
        ("Network: Localhost / Intranet HTTP connectivity for web access", 22.0, False)
    ], default_size=22.0)

    # =========================================================================
    # SLIDE 10: SYSTEM ANALYSIS (Software Requirements & Platform Stack)
    # =========================================================================
    s10 = prs.slides[9]
    tb10 = [shp for shp in s10.shapes if shp.has_text_frame and shp.top > 1000000][0]
    update_textbox_paragraphs(tb10, [
        ("Software Requirements & Technology Stack", 22.0, True, COLOR_NAVY),
        ("Operating System: Windows 10/11 / Linux (Ubuntu) / macOS", 22.0, False),
        ("Programming Language: Python 3.10+ (Tested on Python 3.14)", 22.0, False),
        ("Backend Framework: Flask 3.1 (RESTful routes, Jinja2 templating)", 22.0, False),
        ("Machine Learning & NLP: Scikit-learn 1.7, NLTK, NumPy, Pandas", 22.0, False),
        ("Database: SQLite 3 with Write-Ahead Logging (WAL Mode)", 22.0, False),
        ("Frontend: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, SVG Charts", 22.0, False),
        ("Development Tools: Visual Studio Code, Git, GitHub, Pytest (170 tests)", 22.0, False)
    ], default_size=22.0)

    # =========================================================================
    # SLIDE 11: DATABASE DESIGN OVERVIEW
    # =========================================================================
    s11 = prs.slides[10]
    for shp in s11.shapes:
        if shp.name == "object 9" and shp.has_text_frame:
            set_text_run(shp.text_frame.paragraphs[0], "Database Design", size_pt=19.5, bold=False)
    tb11 = [shp for shp in s11.shapes if shp.has_text_frame and shp.top > 1100000][0]
    update_textbox_paragraphs(tb11, [
        ("The Intelligent Resume Analyzer uses an ACID-compliant SQLite relational database running in Write-Ahead Logging (WAL) mode for high-concurrency read/write operations.", 20.0, False),
        ("It maintains normalized schemas across the following primary tables:", 20.0, True),
        ("• Resumes & Evaluation Master Table (evaluations)", 20.0, False),
        ("• ATS Factor Breakdown & Headroom Table (factor_breakdowns)", 20.0, False),
        ("• Job Descriptions & Skill Criteria Table (job_descriptions)", 20.0, False),
        ("• Candidate Rankings & Shortlist Table (shortlist_rankings)", 20.0, False),
        ("• Deep ML Suggestions & Audit Logs Table (ml_suggestions)", 20.0, False),
        ("The relational design eliminates data redundancy and supports fast indexed joins across candidate evaluations.", 20.0, False),
        ("Foreign key integrity and optimized SQLite indices ensure sub-second dashboard loading and persistent history tracking.", 20.0, False)
    ], default_size=20.0)

    # =========================================================================
    # SLIDE 12: DATABASE DESIGN - TABLE 1 (evaluations)
    # =========================================================================
    s12 = prs.slides[11]
    for shp in s12.shapes:
        if shp.name == "object 9" and shp.has_text_frame:
            set_text_run(shp.text_frame.paragraphs[0], "Database Design", size_pt=19.5, bold=False)
        elif shp.has_text_frame and "database collections:" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Database Tables:", size_pt=20.0, bold=True, color=COLOR_NAVY)
        elif shp.has_text_frame and "students collection" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Evaluations Master Table (evaluations) :", size_pt=20.0, bold=True, color=COLOR_NAVY)
    tbl12 = [shp for shp in s12.shapes if shp.has_table][0].table
    set_table_data(tbl12, [
        ["Field Name", "Data Type", "Constraint", "Description"],
        ["id", "Integer", "Primary Key, Auto", "Unique evaluation record identifier"],
        ["candidate_name", "String", "Required", "Extracted applicant full name"],
        ["filename", "String", "Required", "Uploaded resume document name"],
        ["predicted_category", "String", "Required", "ML predicted technical domain (9 roles)"],
        ["confidence", "Float", "Required", "Classification confidence probability (0-1)"],
        ["overall_ats_score", "Float", "Required", "Composite weighted ATS score (0-100)"],
        ["created_at", "DateTime", "Required", "Audit record creation timestamp"]
    ])

    # =========================================================================
    # SLIDE 13: DATABASE DESIGN - TABLE 2 (factor_breakdowns)
    # =========================================================================
    s13 = prs.slides[12]
    for shp in s13.shapes:
        if shp.name == "object 9" and shp.has_text_frame:
            set_text_run(shp.text_frame.paragraphs[0], "Database Design", size_pt=19.5, bold=False)
        elif shp.has_text_frame and "database collections:" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Database Tables:", size_pt=20.0, bold=True, color=COLOR_NAVY)
        elif shp.has_text_frame and "faculty collection" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Factor Breakdowns Table (factor_breakdowns) :", size_pt=20.0, bold=True, color=COLOR_NAVY)
    tbl13 = [shp for shp in s13.shapes if shp.has_table][0].table
    set_table_data(tbl13, [
        ["Field Name", "Data Type", "Constraint", "Description"],
        ["id", "Integer", "Primary Key, Auto", "Factor entry record identifier"],
        ["evaluation_id", "Integer", "Foreign Key, Req", "Linked parent evaluation identifier"],
        ["factor_key", "String", "Required", "Dimension key (keywords, skills, format)"],
        ["score", "Float", "Required", "Computed factor subscore (0 to 100)"],
        ["weight", "Float", "Required", "Normalized factor weight contribution"],
        ["potential_gain", "Float", "Required", "Headroom points available from fixes"]
    ])

    # =========================================================================
    # SLIDE 14: DATABASE DESIGN - TABLE 3 (job_descriptions)
    # =========================================================================
    s14 = prs.slides[13]
    for shp in s14.shapes:
        if shp.name == "object 9" and shp.has_text_frame:
            set_text_run(shp.text_frame.paragraphs[0], "Database Design", size_pt=19.5, bold=False)
        elif shp.has_text_frame and "database collections:" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Database Tables:", size_pt=20.0, bold=True, color=COLOR_NAVY)
        elif shp.has_text_frame and "timetable collection" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Job Descriptions Table (job_descriptions) :", size_pt=20.0, bold=True, color=COLOR_NAVY)
    tbl14 = [shp for shp in s14.shapes if shp.has_table][0].table
    set_table_data(tbl14, [
        ["Field Name", "Data Type", "Constraint", "Description"],
        ["id", "Integer", "Primary Key, Auto", "Unique job description identifier"],
        ["job_title", "String", "Required", "Target job title and role designation"],
        ["target_category", "String", "Required", "Target technical career domain"],
        ["raw_text", "Text", "Required", "Full unstructured job description text"],
        ["min_experience", "Integer", "Required", "Minimum mandatory experience years"],
        ["required_skills", "Text/JSON", "Required", "List of required technical skills"]
    ])

    # =========================================================================
    # SLIDE 15: DATABASE DESIGN - TABLE 4 (shortlist_rankings)
    # =========================================================================
    s15 = prs.slides[14]
    for shp in s15.shapes:
        if shp.name == "object 9" and shp.has_text_frame:
            set_text_run(shp.text_frame.paragraphs[0], "Database Design", size_pt=19.5, bold=False)
        elif shp.has_text_frame and "database collections:" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Database Tables:", size_pt=20.0, bold=True, color=COLOR_NAVY)
        elif shp.has_text_frame and "syllabus collection" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Shortlist Rankings Table (shortlist_rankings) :", size_pt=20.0, bold=True, color=COLOR_NAVY)
    tbl15 = [shp for shp in s15.shapes if shp.has_table][0].table
    set_table_data(tbl15, [
        ["Field Name", "Data Type", "Constraint", "Description"],
        ["id", "Integer", "Primary Key, Auto", "Candidate ranking entry identifier"],
        ["batch_id", "String", "Required, Indexed", "Candidate screening batch session ID"],
        ["candidate_name", "String", "Required", "Applicant name and document alias"],
        ["overall_match", "Float", "Required", "Computed job fit percentage (0-100)"],
        ["rank_position", "Integer", "Required", "Candidate rank in screened batch"],
        ["shortlisted", "Boolean", "Required", "Threshold cutoff pass/fail status"]
    ])

    # =========================================================================
    # SLIDE 16: DATABASE DESIGN - TABLE 5 (ml_suggestions)
    # =========================================================================
    s16 = prs.slides[15]
    for shp in s16.shapes:
        if shp.name == "object 9" and shp.has_text_frame:
            set_text_run(shp.text_frame.paragraphs[0], "Database Design", size_pt=19.5, bold=False)
        elif shp.has_text_frame and "database collections:" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Database Tables:", size_pt=20.0, bold=True, color=COLOR_NAVY)
        elif shp.has_text_frame and "admin collection" in shp.text_frame.text.lower():
            set_text_run(shp.text_frame.paragraphs[0], "Deep ML Suggestions Table (ml_suggestions) :", size_pt=20.0, bold=True, color=COLOR_NAVY)
    tbl16 = [shp for shp in s16.shapes if shp.has_table][0].table
    set_table_data(tbl16, [
        ["Field Name", "Data Type", "Constraint", "Description"],
        ["id", "Integer", "Primary Key, Auto", "ML suggestion record identifier"],
        ["evaluation_id", "Integer", "Foreign Key, Req", "Linked parent evaluation identifier"],
        ["diagnostic_type", "String", "Required", "Diagnostic engine (gap, stuffing, verb)"],
        ["priority", "String", "Required", "Urgency tier (High, Medium, Low)"],
        ["suggestion_text", "Text", "Required", "Actionable statistical correction text"],
        ["potential_gain", "Float", "Required", "Estimated ATS score gain points"]
    ])

    # =========================================================================
    # SLIDE 17: SYSTEM DESIGN (Core Modules 1-4)
    # =========================================================================
    s17 = prs.slides[16]
    tb17 = [shp for shp in s17.shapes if shp.has_text_frame and shp.top > 1200000][0]
    update_textbox_paragraphs(tb17, [
        ("Document Ingestion & Parsing Module", 20.0, True, COLOR_NAVY),
        ("Extracts raw text and structural sections from PDF, DOCX, and TXT files, handling multi-column layouts, phone/email parsing, and section header detection.", 18.0, False),
        ("NLP Preprocessing & Feature Extraction Module", 20.0, True, COLOR_NAVY),
        ("Performs lemmatization, stopword filtering, boilerplate removal, and sublinear n-gram TF-IDF vectorization (1-3 grams, 10,000 discriminative features).", 18.0, False),
        ("Tri-Model Machine Learning Classification Ensemble", 20.0, True, COLOR_NAVY),
        ("Combines a Calibrated LinearSVC (Platt scaling, 94.51% holdout accuracy), a 3-layer MLP Neural Network (384-128-64), and Multinomial Logistic Regression.", 18.0, False),
        ("Multi-Factor ATS Scoring Engine", 20.0, True, COLOR_NAVY),
        ("Computes transparent subscores across 7 key dimensions with dynamic proportional weight redistribution for missing information.", 18.0, False)
    ], default_size=18.0)

    # =========================================================================
    # SLIDE 18: SYSTEM DESIGN (Advanced Modules 5-8)
    # =========================================================================
    s18 = prs.slides[17]
    tb18 = [shp for shp in s18.shapes if shp.has_text_frame and shp.top > 1200000][0]
    update_textbox_paragraphs(tb18, [
        ("Deep ML Suggestion & Correction Engine", 20.0, True, COLOR_NAVY),
        ("Executes 10 statistical NLP diagnostics including model feature attribution gaps, keyword stuffing detection, and executive power verb recommendations.", 18.0, False),
        ("Job Description Semantic Matching Engine", 20.0, True, COLOR_NAVY),
        ("Performs multi-dimensional alignment across mandatory skills, adjacent competencies, years of experience, and educational qualifications.", 18.0, False),
        ("Multi-Candidate Batch Shortlisting & Ranking Module", 20.0, True, COLOR_NAVY),
        ("Enables recruiters to screen candidate batches against target job descriptions with dynamic threshold filtering and CSV candidate dossier export.", 18.0, False),
        ("Historical Progress Tracking & Audit Database Module", 20.0, True, COLOR_NAVY),
        ("Stores all candidate evaluations and factor breakdowns in SQLite (WAL mode), enabling historical tracking of resume score improvements over time.", 18.0, False)
    ], default_size=18.0)

    # =========================================================================
    # SLIDES 19 to 37: SYSTEM IMPLEMENTATION (19 Slides with Screenshots)
    # =========================================================================
    impl_configs = [
        # Slide 19 (idx 18)
        {
            "slide_idx": 18,
            "title": "Document Ingestion & Upload Portal (Home):",
            "desc": "Displays the modern executive upload interface supporting drag-and-drop ingestion of PDF, DOCX, and TXT resumes, direct text paste, and sample test resumes.",
            "img": "ppt_assets/home.png",
            "double": False
        },
        # Slide 20 (idx 19)
        {
            "slide_idx": 19,
            "title": "Candidate Evaluation Dashboard (Executive Dossier):",
            "desc": "Presents applicant profile, overall ATS score (Grade A: 90.3/100), potential headroom score (+9.7 pts), and predicted technical career category.",
            "img": "ppt_assets/results_analyze_top.png",
            "double": False
        },
        # Slide 21 (idx 20)
        {
            "slide_idx": 20,
            "title": "ML Category Prediction & Confidence Distribution:",
            "desc": "Displays the machine learning classification outcome (Software Developer: 94.5% confidence) alongside top alternative predictions and model calibration metrics.",
            "img": "extracted_screenshots/pic_10_2.png",
            "double": False
        },
        # Slide 22 (idx 21)
        {
            "slide_idx": 21,
            "title": "Multi-Factor ATS Score Breakdown Matrix:",
            "desc": "Details transparent subscores, proportional weights, and pass/fail checks across keyword coverage, skills breadth, format parseability, and content quality.",
            "img": "extracted_screenshots/pic_11_3.png",
            "double": False
        },
        # Slide 23 (idx 22)
        {
            "slide_idx": 22,
            "title": "ATS Scoring Factor Weights & Dimensional Balance:",
            "desc": "Illustrates the dimensional balance chart depicting the relative contribution of keyword match (35%), skills breadth (20%), format (15%), and quality factors.",
            "img": "ppt_build/fig_ats_weights.png",
            "double": False
        },
        # Slide 24 (idx 23)
        {
            "slide_idx": 23,
            "title": "Job Matching & Semantic Alignment Dashboard:",
            "desc": "Evaluates candidate resume against specific Job Descriptions (e.g. Software Engineer at Stripe), computing composite match fit (82%) and qualification tiers.",
            "img": "ppt_assets/results_match_top.png",
            "double": False
        },
        # Slide 25 (idx 24)
        {
            "slide_idx": 24,
            "title": "Skill Alignment & Missing Requirements Audit:",
            "desc": "Highlights matched technical competencies in green, partial/typo matches in amber, and missing mandatory skills (e.g. Docker, Redis) in red with concrete advice.",
            "img": "extracted_screenshots/pic_12_4.png",
            "double": False
        },
        # Slide 26 (idx 25)
        {
            "slide_idx": 25,
            "title": "Career Timeline & Experience Verification:",
            "desc": "Verifies candidate employment history against the JD experience threshold, analyzing job titles, employment date ranges, and relevant tenure.",
            "img": "extracted_screenshots/pic_15_6.png",
            "double": False
        },
        # Slide 27 (idx 26)
        {
            "slide_idx": 26,
            "title": "End-to-End System Architecture & ML Pipeline:",
            "desc": "Visualizes the complete engineering pipeline from multi-document ingestion and regex extraction through TF-IDF vectorization to the tri-model ensemble.",
            "img": "ppt_build/fig_architecture.png",
            "double": False
        },
        # Slide 28 (idx 27) - Double screenshot
        {
            "slide_idx": 27,
            "title": "Executive Action Verb & Impact Quantification (STAR):",
            "desc": "Detects weak passive starters ('responsible for', 'worked on') and recommends executive power verbs alongside STAR-format metrics (+40% higher ATS score).",
            "img_top": "ppt_assets/results_analyze.png",
            "img_bot": "extracted_screenshots/pic_12_4.png",
            "double": True
        },
        # Slide 29 (idx 28) - Double screenshot
        {
            "slide_idx": 28,
            "title": "Keyword Stuffing Detection & Prioritized Remediation:",
            "desc": "Monitors keyword density to protect against commercial ATS spam filters (>3.5% density) and generates the prioritized 'What to change' remediation checklist.",
            "img_top": "ppt_assets/results_analyze.png",
            "img_bot": "extracted_screenshots/pic_11_3.png",
            "double": True
        },
        # Slide 30 (idx 29)
        {
            "slide_idx": 29,
            "title": "Cognitive Readability & Parser Safety Diagnostics:",
            "desc": "Computes Flesch-Kincaid Grade Level (Target: 9-12) to prevent sentence truncation in legacy parsers (Workday, Taleo) and flags non-standard Unicode bullet glyphs.",
            "img": "ppt_assets/results_analyze.png",
            "double": False
        },
        # Slide 31 (idx 30)
        {
            "slide_idx": 30,
            "title": "Side-by-Side Candidate Comparison Interface:",
            "desc": "Allows recruiters and candidates to compare two resumes side-by-side across overall ATS score, category prediction, matched skills, and experience tenure.",
            "img": "extracted_screenshots/pic_15_7.png",
            "double": False
        },
        # Slide 32 (idx 31)
        {
            "slide_idx": 31,
            "title": "Comparative Metric Delta & Gap Breakdown:",
            "desc": "Displays differential metric analysis showing exact skill differences, keyword coverage deltas, and scoring headroom between competing candidates.",
            "img": "extracted_screenshots/pic_15_7.png",
            "double": False
        },
        # Slide 33 (idx 32)
        {
            "slide_idx": 32,
            "title": "Multi-Candidate Batch Shortlisting & Screening:",
            "desc": "Enables corporate recruiters to ingest multi-resume batches against a target job specification, computing instant rankings and fit percentiles.",
            "img": "ppt_assets/shortlist_top.png",
            "double": False
        },
        # Slide 34 (idx 33)
        {
            "slide_idx": 33,
            "title": "Interactive Shortlisting Cutoff Threshold Slider:",
            "desc": "Provides real-time dynamic slider controls allowing recruiters to adjust the qualification cutoff threshold (e.g. 70%) and immediately update candidate eligibility.",
            "img": "ppt_assets/shortlist_top.png",
            "double": False
        },
        # Slide 35 (idx 34)
        {
            "slide_idx": 34,
            "title": "Resume Evolution & Progress Tracking View:",
            "desc": "Plots candidate score progression over successive resume iterations, demonstrating quantitative score gains after applying ML diagnostic suggestions.",
            "img": "extracted_screenshots/pic_14_5.png",
            "double": False
        },
        # Slide 36 (idx 35)
        {
            "slide_idx": 35,
            "title": "ATS Audit Tracker & Historical Evaluation Log:",
            "desc": "Displays the persistent SQLite evaluation history ledger with candidate names, audit dates, overall scores, grade badges, and one-click detailed reports.",
            "img": "ppt_assets/tracker_top.png",
            "double": False
        },
        # Slide 37 (idx 36)
        {
            "slide_idx": 36,
            "title": "Model Training Analytics & Dataset Category Balance:",
            "desc": "Presents dataset distribution across 1,817 real and synthetic resumes in 9 balanced tech categories, validating model generalizability and holdout metrics.",
            "img": "ppt_build/fig_dataset_processed.png",
            "double": False
        },
    ]

    for cfg in impl_configs:
        idx = cfg["slide_idx"]
        s = prs.slides[idx]
        tb = [shp for shp in s.shapes if shp.has_text_frame and (shp.top > 800000 and shp.top < 2200000)][0]
        update_textbox_paragraphs(tb, [
            (cfg["title"], 20.0, True, COLOR_NAVY),
            (cfg["desc"], 18.0, False)
        ], default_size=18.0)
        
        if cfg["double"]:
            replace_screenshot(s, cfg["img_top"], is_double=True, top_img=True)
            replace_screenshot(s, cfg["img_bot"], is_double=True, top_img=False)
        else:
            replace_screenshot(s, cfg["img"], is_double=False)

    # =========================================================================
    # SLIDE 38: FUTURE ENHANCEMENTS (Part 1)
    # =========================================================================
    s38 = prs.slides[37]
    tb38 = [shp for shp in s38.shapes if shp.has_text_frame and shp.top > 1000000][0]
    update_textbox_paragraphs(tb38, [
        ("The Intelligent Resume Analyzer system developed in this project provides comprehensive, production-grade resume scoring and ML diagnostics. However, the system can be further enhanced by incorporating advanced intelligent capabilities:", 20.0, False),
        ("Some possible future enhancements include:", 20.0, True),
        ("•  Large Language Model (LLM) Integration:", 20.0, True, COLOR_NAVY),
        ("Deploying local fine-tuned LLMs (e.g. LLaMA-3 / Mistral) to generate automated resume sentence rewrites, executive summaries, and tailored cover letters.", 19.0, False),
        ("•  Multi-Lingual Resume Parsing:", 20.0, True, COLOR_NAVY),
        ("Expanding the NLP tokenizer and feature extractors to evaluate resumes written in German, French, Spanish, and regional Indian languages.", 19.0, False),
        ("•  Optical Character Recognition (OCR) Engine:", 20.0, True, COLOR_NAVY),
        ("Integrating Tesseract OCR / PaddleOCR to parse graphic resumes, design portfolios, and scanned multi-layer PDF documents.", 19.0, False),
        ("•  Real-Time Collaborative Mentorship:", 20.0, True, COLOR_NAVY),
        ("Enabling career counselors and peer reviewers to annotate resumes and share revision notes within the evaluation dashboard.", 19.0, False)
    ], default_size=19.0)

    # =========================================================================
    # SLIDE 39: FUTURE ENHANCEMENTS (Part 2)
    # =========================================================================
    s39 = prs.slides[38]
    tb39 = [shp for shp in s39.shapes if shp.has_text_frame and shp.top > 1000000][0]
    update_textbox_paragraphs(tb39, [
        ("Additional strategic future enhancements include:", 20.0, True),
        ("•  Enterprise HRIS / ATS Integration:", 20.0, True, COLOR_NAVY),
        ("Integrating direct webhook APIs with enterprise platforms (Workday, Greenhouse, Taleo, and Lever) for bidirectional candidate synchronization.", 19.0, False),
        ("•  Video Interview & Voice Sentiment Analysis:", 20.0, True, COLOR_NAVY),
        ("Incorporating Whisper speech-to-text to evaluate candidate communication skills and technical depth in pre-recorded screening interviews.", 19.0, False),
        ("•  Cross-Platform Native Mobile Application:", 20.0, True, COLOR_NAVY),
        ("Developing an iOS and Android app with instant push notifications for candidate shortlisting updates and application status alerts.", 19.0, False),
        ("•  Explainable AI (XAI) Enterprise Compliance:", 20.0, True, COLOR_NAVY),
        ("Providing SHAP (Shapley Additive exPlanations) visualizations to comply with global AI hiring regulations and fair-hiring audits.", 19.0, False),
        ("These enhancements will make the system an all-in-one institutional talent intelligence suite.", 19.0, False)
    ], default_size=19.0)

    # =========================================================================
    # SLIDE 40: REFERENCES
    # =========================================================================
    s40 = prs.slides[39]
    tb40 = [shp for shp in s40.shapes if shp.has_text_frame and shp.top > 1000000][0]
    update_textbox_paragraphs(tb40, [
        ("The following academic literature, frameworks, and technical documentation were referenced during development:", 20.0, True),
        ("1.  Scikit-learn: Machine Learning in Python, Pedregosa et al., Journal of Machine Learning Research (JMLR 12), pp. 2825-2830.", 19.0, False),
        ("2.  Flask Web Development Framework Documentation, Pallets Projects, https://flask.palletsprojects.com/", 19.0, False),
        ("3.  Natural Language Toolkit (NLTK) Documentation, Bird, S., Klein, E., & Loper, E., O'Reilly Media, https://www.nltk.org/", 19.0, False),
        ("4.  SQLite Database Engine & Write-Ahead Logging (WAL) Architecture, Hipp, D. R. et al., https://www.sqlite.org/wal.html", 19.0, False),
        ("5.  Jobscan & Commercial ATS Parsing Standards, Heuristics and Industry Research, https://www.jobscan.co/", 19.0, False),
        ("6.  Bootstrap 5 Component Library & Design Architecture, https://getbootstrap.com/", 19.0, False),
        ("7.  Python 3 Documentation & Standard Library, Python Software Foundation, https://docs.python.org/3/", 19.0, False),
        ("8.  MDN Web Docs: Web Technologies, JavaScript ES6 & DOM Standards, Mozilla, https://developer.mozilla.org/", 19.0, False)
    ], default_size=19.0)

    # =========================================================================
    # SLIDE 41: CONCLUSION
    # =========================================================================
    s41 = prs.slides[40]
    tb41 = [shp for shp in s41.shapes if shp.has_text_frame and shp.top > 1000000][0]
    update_textbox_paragraphs(tb41, [
        ("The Intelligent Resume Analyzer was successfully engineered and deployed as a high-performance web platform combining machine learning, computational linguistics, and transparent ATS auditing.", 20.0, False),
        ("The system effectively solves the recruitment bottleneck by automating multi-format resume parsing, job description matching, and batch candidate shortlisting with explainable, data-backed metrics.", 20.0, False),
        ("The tri-model machine learning ensemble achieved 94.51% classification accuracy across 9 technical career tracks, supported by 10 deep statistical NLP diagnostic engines that empower candidates to maximize interview callback rates.", 20.0, False),
        ("A comprehensive test suite of 170 passing unit tests validates end-to-end stability, fast sub-second inference, and robust ACID database persistence, delivering an institutional-grade solution for modern talent acquisition.", 20.0, False)
    ], default_size=20.0)

    # =========================================================================
    # SLIDE 42: THANK YOU
    # =========================================================================
    # Slide 42 has 'THANK YOU' in 48pt Times New Roman, already styled perfectly.

    # Save outputs
    print(f"Saving presentation to {OUT_PPTX_LOCAL}...")
    prs.save(OUT_PPTX_LOCAL)
    
    try:
        shutil.copy2(OUT_PPTX_LOCAL, OUT_PPTX_DESKTOP)
        print(f"Copied presentation to Desktop: {OUT_PPTX_DESKTOP}")
    except Exception as e:
        print(f"Could not copy to Desktop: {e}")

    try:
        shutil.copy2(OUT_PPTX_LOCAL, OUT_PPTX_DOWNLOADS)
        print(f"Copied presentation to Downloads: {OUT_PPTX_DOWNLOADS}")
    except Exception as e:
        print(f"Could not copy to Downloads: {e}")

    print("Presentation successfully created!")

if __name__ == "__main__":
    build_deck()
