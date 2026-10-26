"""
Generates sample resume and job description documents (PDF and DOCX) used
for manually testing and demonstrating the full pipeline end-to-end.

Usage:
    .venv\\Scripts\\python.exe -m samples.generate_samples
"""

from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

SAMPLES_DIR = Path(__file__).resolve().parent

# Sample 1: Software Developer resume
SOFTWARE_DEVELOPER_RESUME = [
    ("", "John A. Doe"),
    ("", "Email: john.doe@example.com | Phone: +1-555-123-4567"),
    ("SUMMARY", "Motivated Software Developer with 3 years of professional experience "
                "building and maintaining scalable web applications."),
    ("SKILLS", "Python, Java, JavaScript, React, Node.js, REST API, Git, MySQL, MongoDB, "
               "Docker, Agile"),
    ("EDUCATION", "B.Tech in Computer Science, National Institute of Technology, 2021"),
    ("EXPERIENCE",
     "Worked as a Software Developer at TechNova Solutions for 3 years, responsible for "
     "designing and implementing REST APIs and collaborating with cross-functional teams "
     "in an Agile environment.\n"
     "Worked as a Junior Developer at BrightPath Systems for 1 year, responsible for "
     "maintaining and refactoring legacy application modules."),
    ("PROJECTS",
     "Built an e-commerce order management system using Python and React.\n"
     "Built a task management web application using Node.js and MongoDB."),
    ("CERTIFICATIONS", "Meta Back-End Developer Certificate"),
]

# Sample 2: Data Science resume
DATA_SCIENTIST_RESUME = [
    ("", "Priya Sharma"),
    ("", "Email: priya.sharma@example.com | Phone: (555) 987-6543"),
    ("SUMMARY", "Detail-oriented Data Scientist with 2 years of hands-on experience "
                "analyzing complex datasets and building machine learning models."),
    ("SKILLS", "Python, R, Machine Learning, Deep Learning, Pandas, NumPy, Scikit-learn, "
               "TensorFlow, SQL, Data Visualization, Statistics"),
    ("EDUCATION", "M.Sc. in Data Science, Global Institute of Technology, 2022"),
    ("EXPERIENCE",
     "Worked as a Data Scientist at Skyline Analytics for 2 years, responsible for "
     "building predictive models to support business decisions and performing "
     "exploratory data analysis on large datasets."),
    ("PROJECTS",
     "Built a customer churn prediction model using Python and Scikit-learn.\n"
     "Built a sentiment analysis system for product reviews using Python and TensorFlow."),
    ("CERTIFICATIONS", "IBM Data Science Professional Certificate"),
]

# Sample 3: Software Developer job description
SOFTWARE_DEVELOPER_JD = [
    ("", "Job Title: Software Developer"),
    ("REQUIREMENTS",
     "3+ years of experience in software development.\n"
     "Bachelor's degree in Computer Science or related field.\n"
     "Strong proficiency in Python and JavaScript.\n"
     "Experience with React and Node.js.\n"
     "Experience with REST API design.\n"
     "Familiarity with Docker and CI/CD pipelines.\n"
     "Experience with MySQL or MongoDB."),
    ("PREFERRED SKILLS",
     "Experience with AWS.\n"
     "Experience with Kubernetes.\n"
     "Knowledge of TypeScript."),
    ("RESPONSIBILITIES",
     "Design and implement scalable backend services.\n"
     "Collaborate with front-end developers to integrate APIs.\n"
     "Write unit tests and participate in code reviews.\n"
     "Participate in Agile ceremonies and sprint planning."),
]


def _write_docx(sections, output_path: Path) -> None:
    document = Document()
    for header, content in sections:
        if header:
            document.add_heading(header, level=2)
        for line in content.split("\n"):
            document.add_paragraph(line)
    document.save(str(output_path))


def _write_pdf(sections, output_path: Path) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(output_path), pagesize=LETTER)
    story = []
    for header, content in sections:
        if header:
            story.append(Paragraph(escape(header), styles["Heading2"]))
        for line in content.split("\n"):
            story.append(Paragraph(escape(line), styles["Normal"]))
        story.append(Spacer(1, 8))
    doc.build(story)


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    _write_docx(DATA_SCIENTIST_RESUME, SAMPLES_DIR / "sample_resume_data_scientist.docx")
    _write_pdf(SOFTWARE_DEVELOPER_RESUME, SAMPLES_DIR / "sample_resume_software_developer.pdf")
    _write_docx(SOFTWARE_DEVELOPER_JD, SAMPLES_DIR / "sample_job_description_software_developer.docx")
    _write_pdf(SOFTWARE_DEVELOPER_JD, SAMPLES_DIR / "sample_job_description_software_developer.pdf")

    print("Sample documents generated in:", SAMPLES_DIR)
    for f in sorted(SAMPLES_DIR.glob("sample_*")):
        print(" -", f.name)


if __name__ == "__main__":
    main()
