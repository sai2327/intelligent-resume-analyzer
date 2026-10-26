"""
Generates a SYNTHETIC, TEMPLATE-BASED demo resume dataset for development
and coursework demonstration purposes only.

This is NOT a real-world resume dataset and does NOT represent real-world
classification accuracy. It exists so the TF-IDF + SVM training pipeline
(training/train_model.py) has something concrete to train and evaluate on
without requiring a licensed real dataset. See README.md for notes on
substituting a real public dataset (e.g. from Kaggle) instead.

Usage:
    .venv\\Scripts\\python.exe -m training.generate_demo_dataset
"""

import csv
import random
from pathlib import Path

from config import config

RANDOM_SEED = 42

CATEGORIES = {
    "Software Developer": {
        "skills": ["Python", "Java", "C++", "JavaScript", "React", "Node.js", "REST API",
                   "Git", "MySQL", "MongoDB", "Docker", "Object Oriented Programming",
                   "Microservices", "Agile", "Unit Testing"],
        "roles": ["Software Developer", "Software Engineer", "Application Developer", "Backend Developer"],
        "responsibilities": [
            "designing and implementing REST APIs",
            "maintaining and refactoring legacy application modules",
            "writing unit tests to improve code coverage",
            "collaborating with cross-functional teams in an Agile environment",
            "debugging production issues and improving application performance",
        ],
        "projects": [
            "an e-commerce order management system",
            "a task management web application",
            "an internal inventory tracking tool",
            "a customer support ticketing platform",
        ],
        "certifications": ["Oracle Certified Professional Java Programmer", "Meta Back-End Developer Certificate"],
    },
    "Data Scientist": {
        "skills": ["Python", "R", "Machine Learning", "Deep Learning", "Pandas", "NumPy",
                   "Scikit-learn", "TensorFlow", "PyTorch", "Statistics", "Data Visualization",
                   "SQL", "Natural Language Processing", "Jupyter Notebook"],
        "roles": ["Data Scientist", "Junior Data Scientist", "Research Data Scientist"],
        "responsibilities": [
            "building predictive models to support business decisions",
            "performing exploratory data analysis on large datasets",
            "designing A/B tests to evaluate feature performance",
            "communicating statistical findings to non-technical stakeholders",
            "developing and validating machine learning pipelines",
        ],
        "projects": [
            "a customer churn prediction model",
            "a sales forecasting pipeline",
            "a sentiment analysis system for product reviews",
            "a recommendation engine for an online retailer",
        ],
        "certifications": ["IBM Data Science Professional Certificate", "TensorFlow Developer Certificate"],
    },
    "Data Analyst": {
        "skills": ["Excel", "SQL", "Power BI", "Tableau", "Python", "Data Visualization",
                   "Data Analysis", "Data Cleaning", "Statistics", "Google Analytics"],
        "roles": ["Data Analyst", "Business Data Analyst", "Reporting Analyst"],
        "responsibilities": [
            "building interactive dashboards for management reporting",
            "cleaning and validating raw data from multiple sources",
            "writing SQL queries to extract and aggregate business data",
            "presenting key performance indicators to stakeholders",
            "automating recurring reports to reduce manual effort",
        ],
        "projects": [
            "a sales performance dashboard",
            "a marketing campaign analysis report",
            "a customer segmentation analysis",
            "an operations KPI tracking dashboard",
        ],
        "certifications": ["Google Data Analytics Certificate", "Microsoft Power BI Data Analyst Associate"],
    },
    "Machine Learning Engineer": {
        "skills": ["Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
                   "Scikit-learn", "Docker", "Kubernetes", "AWS", "Neural Networks",
                   "Computer Vision", "Natural Language Processing", "REST API"],
        "roles": ["Machine Learning Engineer", "ML Engineer", "Applied ML Engineer"],
        "responsibilities": [
            "deploying machine learning models into production using containerized services",
            "optimizing model training pipelines for speed and accuracy",
            "building data preprocessing pipelines for large-scale datasets",
            "monitoring deployed models for performance and data drift",
            "collaborating with data scientists to productionize research prototypes",
        ],
        "projects": [
            "an image classification service deployed on the cloud",
            "a real-time fraud detection model",
            "a document classification pipeline",
            "an automated model retraining pipeline",
        ],
        "certifications": ["AWS Certified Machine Learning Specialty", "DeepLearning.AI TensorFlow Developer"],
    },
    "Web Developer": {
        "skills": ["HTML", "CSS", "JavaScript", "React", "Next.js", "Bootstrap", "Tailwind CSS",
                   "Node.js", "Express.js", "MongoDB", "REST API", "Git", "PHP"],
        "roles": ["Web Developer", "Front-End Developer", "Full-Stack Developer"],
        "responsibilities": [
            "developing responsive web interfaces from design mockups",
            "integrating front-end components with REST APIs",
            "optimizing web pages for performance and accessibility",
            "maintaining cross-browser compatibility across the product",
            "collaborating with designers to implement pixel-perfect UI",
        ],
        "projects": [
            "a responsive company portfolio website",
            "a full-stack blogging platform",
            "an online booking web application",
            "a single-page admin dashboard",
        ],
        "certifications": ["Meta Front-End Developer Certificate", "freeCodeCamp Responsive Web Design"],
    },
    "DevOps Engineer": {
        "skills": ["Docker", "Kubernetes", "Jenkins", "GitHub Actions", "CI/CD", "Terraform",
                   "Ansible", "AWS", "Linux", "Shell Scripting", "Nginx", "Git", "Prometheus"],
        "roles": ["DevOps Engineer", "Site Reliability Engineer", "Infrastructure Engineer"],
        "responsibilities": [
            "building and maintaining CI/CD pipelines for automated deployments",
            "managing containerized workloads on Kubernetes clusters",
            "provisioning cloud infrastructure using Infrastructure as Code",
            "monitoring system health and responding to production incidents",
            "automating routine operations tasks with shell scripting",
        ],
        "projects": [
            "a fully automated CI/CD pipeline for a microservices platform",
            "a Kubernetes migration for a monolithic application",
            "an infrastructure-as-code setup using Terraform",
            "a centralized logging and monitoring stack",
        ],
        "certifications": ["AWS Certified DevOps Engineer", "Certified Kubernetes Administrator"],
    },
    "Cloud Engineer": {
        "skills": ["AWS", "Azure", "Google Cloud Platform", "Docker", "Kubernetes", "Terraform",
                   "Linux", "CI/CD", "Cloud Computing", "System Design"],
        "roles": ["Cloud Engineer", "Cloud Infrastructure Engineer", "Cloud Support Engineer"],
        "responsibilities": [
            "designing scalable and fault-tolerant cloud architectures",
            "migrating on-premises workloads to the cloud",
            "managing identity, access, and security policies for cloud resources",
            "optimizing cloud costs through right-sizing and automation",
            "implementing disaster recovery and backup strategies",
        ],
        "projects": [
            "a multi-region cloud deployment for a web application",
            "a cloud cost optimization initiative",
            "a serverless data processing pipeline",
            "a cloud migration from on-premises servers",
        ],
        "certifications": ["AWS Certified Solutions Architect", "Microsoft Certified: Azure Administrator Associate"],
    },
    "UI/UX Designer": {
        "skills": ["Figma", "Adobe XD", "Sketch", "Wireframing", "Prototyping", "User Research",
                   "UI Design", "UX Design", "Adobe Photoshop", "Adobe Illustrator"],
        "roles": ["UI/UX Designer", "Product Designer", "Interaction Designer"],
        "responsibilities": [
            "conducting user research to inform design decisions",
            "creating wireframes and interactive prototypes",
            "designing user interfaces aligned with brand guidelines",
            "running usability testing sessions with end users",
            "collaborating with developers to ensure design fidelity",
        ],
        "projects": [
            "a redesign of a mobile banking application",
            "a design system for a SaaS product",
            "a user onboarding flow for a mobile app",
            "a usability study for an e-commerce checkout flow",
        ],
        "certifications": ["Google UX Design Professional Certificate", "Interaction Design Foundation Certification"],
    },
    "Business Analyst": {
        "skills": ["Excel", "SQL", "Power BI", "Requirements Gathering", "Stakeholder Management",
                   "Data Analysis", "Project Management", "Agile", "Scrum", "Data Visualization"],
        "roles": ["Business Analyst", "Business Systems Analyst", "Product Analyst"],
        "responsibilities": [
            "gathering and documenting business requirements from stakeholders",
            "analyzing business processes to identify improvement opportunities",
            "creating functional specifications for development teams",
            "facilitating meetings between business and technical stakeholders",
            "tracking project progress against defined milestones",
        ],
        "projects": [
            "a requirements analysis for a new CRM rollout",
            "a process improvement initiative for order fulfillment",
            "a stakeholder analysis for a digital transformation project",
            "a business case for a new reporting system",
        ],
        "certifications": ["Certified Business Analysis Professional (CBAP)", "PMI Professional in Business Analysis"],
    },
}

DEGREES = [
    "B.Tech in Computer Science", "B.E. in Information Technology",
    "Bachelor of Science in Computer Applications", "M.Sc. in Data Science",
    "MCA (Master of Computer Applications)", "B.Tech in Electronics and Communication",
    "Bachelor of Business Administration", "M.Tech in Computer Science",
]

UNIVERSITIES = [
    "National Institute of Technology", "State University of Engineering",
    "Global Institute of Technology", "Metro City University",
    "Silverline University", "Greenfield College of Engineering",
    "Riverside Institute of Technology", "Summit State University",
]

COMPANIES = [
    "TechNova Solutions", "BrightPath Systems", "Skyline Analytics",
    "Quantum Softworks", "NextGen Cloud Labs", "Pixel Forge Studios",
    "DataSprout Inc.", "CoreLogic Systems", "BlueWave Technologies",
    "Innoventure Labs", "Orbit Digital", "Northfield Software",
]

SUMMARY_TEMPLATES = [
    "Motivated {role} with {years} years of experience in {domain_hint}.",
    "Results-driven {role} with a strong background in {domain_hint} and a passion for solving real-world problems.",
    "{role} with {years} years of professional experience, skilled in {domain_hint}.",
    "Detail-oriented {role} with {years} years of hands-on experience in {domain_hint}.",
]

DOMAIN_HINTS = {
    "Software Developer": "building and maintaining scalable software applications",
    "Data Scientist": "analyzing complex datasets and building machine learning models",
    "Data Analyst": "transforming raw data into actionable business insights",
    "Machine Learning Engineer": "designing and deploying production machine learning systems",
    "Web Developer": "building responsive and user-friendly web applications",
    "DevOps Engineer": "automating deployments and managing cloud infrastructure",
    "Cloud Engineer": "designing and operating scalable cloud infrastructure",
    "UI/UX Designer": "designing intuitive and user-centered digital products",
    "Business Analyst": "bridging business needs and technical solutions",
}


def _generate_resume_text(category: str, rng: random.Random) -> str:
    info = CATEGORIES[category]
    years = rng.choice([1, 2, 2, 3, 3, 4, 5, 6, 8])
    role = rng.choice(info["roles"])
    summary = rng.choice(SUMMARY_TEMPLATES).format(
        role=role, years=years, domain_hint=DOMAIN_HINTS[category]
    )

    num_skills = rng.randint(5, min(12, len(info["skills"])))
    skills = rng.sample(info["skills"], num_skills)
    # Real resumes carry adjacent-category noise skills (a data analyst who
    # knows some Git, a developer who used Tableau once). Sample 0-2 from a
    # random other category so the classifier learns from mixed signals.
    other_categories = [c for c in CATEGORIES if c != category]
    noise = rng.sample(
        CATEGORIES[rng.choice(other_categories)]["skills"], rng.randint(0, 2)
    )
    all_skills = skills + [s for s in noise if s not in skills]
    rng.shuffle(all_skills)
    skills_line = "Skills: " + ", ".join(all_skills) + "."

    degree = rng.choice(DEGREES)
    university = rng.choice(UNIVERSITIES)
    grad_year = rng.choice(range(2014, 2024))
    education_line = f"Education: {degree}, {university}, {grad_year}."

    num_exp = rng.randint(1, 2)
    experience_lines = []
    for _ in range(num_exp):
        company = rng.choice(COMPANIES)
        exp_years = rng.choice([1, 1, 2, 2, 3, 4])
        responsibility = rng.choice(info["responsibilities"])
        if rng.random() < 0.5:
            # Date-range style (how most real resumes present tenure).
            start_year = max(2014, grad_year - exp_years - rng.randint(0, 4))
            end_year = min(2024, start_year + exp_years)
            month = rng.choice(["Jan", "Mar", "Jun", "Sep", "Nov"])
            experience_lines.append(
                f"{role} at {company} ({month} {start_year} - {end_year}): "
                f"responsible for {responsibility}."
            )
        else:
            experience_lines.append(
                f"Worked as a {role} at {company} for {exp_years} years, responsible for {responsibility}."
            )
    experience_text = " ".join(experience_lines)

    num_projects = rng.randint(1, 2)
    project_texts = []
    for _ in range(num_projects):
        project = rng.choice(info["projects"])
        tech = rng.sample(skills, min(2, len(skills)))
        project_texts.append(f"Built {project} using {' and '.join(tech)}.")
    projects_text = "Projects: " + " ".join(project_texts)

    certifications_text = ""
    if rng.random() < 0.6:
        cert = rng.choice(info["certifications"])
        certifications_text = f"Certifications: {cert}."

    # Style A (legacy paragraph style) plus two realistic layouts: a
    # structured, section-headed resume with bullets, and a terse minimal CV.
    style = rng.random()
    if style < 0.4:
        parts = [summary, skills_line, education_line, experience_text, projects_text, certifications_text]
        return " ".join(p for p in parts if p)

    if style < 0.85:
        contact = f"{rng.choice(['Alex Kumar', 'Sam Lee', 'Priya Sharma', 'John Doe'])}\n{university}"
        sections = [
            ("SUMMARY", summary),
            ("SKILLS", ", ".join(all_skills)),
            ("EXPERIENCE", "\n".join(f"- {line}" for line in experience_lines)),
            ("EDUCATION", f"{degree}, {university}, {grad_year}"),
            ("PROJECTS", "\n".join(f"- Built {p} using {' and '.join(rng.sample(skills, min(2, len(skills))))}."
                                   for p in rng.sample(info["projects"], num_projects))),
        ]
        if certifications_text:
            sections.append(("CERTIFICATIONS", certifications_text.removeprefix("Certifications: ").rstrip(".")))
        rng.shuffle(sections)  # real resumes vary section order
        return contact + "\n\n" + "\n\n".join(f"{header}\n{body}" for header, body in sections)

    # Minimal terse CV.
    text = "\n".join(filter(None, [
        summary,
        "Skills: " + ", ".join(all_skills[:7]),
        "Experience: " + experience_text,
        f"Education: {degree}, {grad_year}.",
    ]))

    # Typo robustness: ~8% of resumes carry one transposition typo in a skill,
    # so the classifier (and the typo-tolerant matcher) see realistic noise.
    if rng.random() < 0.08 and all_skills:
        word = rng.choice(all_skills)
        if len(word) >= 5 and " " not in word:
            j = len(word) // 2
            typo = word[:j] + word[j + 1] + word[j] + word[j + 2:]
            text = text.replace(word, typo, 1)
    return text


def generate_dataset(rows_per_category: int = 160, seed: int = RANDOM_SEED) -> list:
    """Build the full list of {resume_text, category} rows. 160 per category
    (1,440 total) across 3 layout styles with noise skills, shuffled sections
    and ~8% typo noise, so the classifier must generalize instead of
    memorizing one template."""
    rng = random.Random(seed)
    rows = []
    for category in CATEGORIES:
        for _ in range(rows_per_category):
            rows.append({"resume_text": _generate_resume_text(category, rng), "category": category})
    rng.shuffle(rows)
    return rows


def save_dataset(rows: list, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["resume_text", "category"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = generate_dataset()
    save_dataset(rows, config.RAW_DATASET_PATH)
    print(f"Generated {len(rows)} synthetic demo resumes across {len(CATEGORIES)} categories.")
    print(f"Saved to: {config.RAW_DATASET_PATH}")
    print(
        "\nNOTE: This is a SYNTHETIC, TEMPLATE-BASED demo dataset for development "
        "and coursework purposes only. It does NOT represent real-world resume "
        "diversity or real-world classification accuracy. See README.md for how "
        "to substitute a real public dataset."
    )


if __name__ == "__main__":
    main()
