"""Career roadmap templates (concept doc, section 8).

A roadmap turns skill gaps into a sequence of manageable learning goals, each with the
evidence to add to the profile. Steps already evidenced in the resume are marked as such.
"""

from app.data.skills import SKILL_INDEX

# role -> [(skills, learning focus, evidence to add)]
ROADMAPS: dict[str, list[tuple[list[str], str, str]]] = {
    "Backend Java Developer": [
        (["Java", "OOP"], "Core Java and OOP", "A well-structured Java application"),
        (["SQL", "PostgreSQL"], "SQL and database design", "A project with relational data and queries"),
        (["Spring Boot"], "Spring Boot", "A backend application with a clear architecture"),
        (["REST APIs"], "REST API development", "Documented endpoints and API tests"),
        (["Docker"], "Docker", "A reproducible containerized project"),
        (["AWS"], "Cloud fundamentals", "A deployed project and deployment documentation"),
    ],
    "Python Backend Developer": [
        (["Python"], "Core Python", "A well-tested Python package or CLI"),
        (["SQL", "PostgreSQL"], "SQL and database design", "A schema with migrations and non-trivial queries"),
        (["FastAPI"], "A Python web framework (FastAPI or Django)", "An API with validation and auto-generated docs"),
        (["REST APIs", "Unit Testing"], "API design and testing", "Documented endpoints with automated tests"),
        (["Docker"], "Docker", "A containerized service with docker compose"),
        (["CI/CD"], "Continuous integration", "A pipeline that runs tests on every push"),
    ],
    "Frontend Developer": [
        (["HTML", "CSS"], "Semantic HTML and responsive CSS", "An accessible, responsive multi-page site"),
        (["JavaScript"], "Modern JavaScript", "An interactive app using a public API"),
        (["React"], "React fundamentals", "A React app with routing and state"),
        (["TypeScript"], "TypeScript", "A typed React project"),
        (["Unit Testing"], "Frontend testing", "Component and end-to-end tests"),
        (["Next.js"], "Server rendering and deployment", "A deployed Next.js site"),
    ],
    "Full-Stack Developer": [
        (["JavaScript", "HTML", "CSS"], "Web fundamentals", "A responsive front end consuming an API"),
        (["React"], "React", "A React client with routing and forms"),
        (["Node.js", "Express"], "Node.js APIs", "A REST API with authentication"),
        (["MongoDB", "SQL"], "Databases", "Persistent storage with a clear data model"),
        (["Docker"], "Containers", "The full stack running with docker compose"),
        (["CI/CD", "AWS"], "Deployment", "A deployed app with a CI pipeline"),
    ],
    "Data Analyst": [
        (["Excel"], "Spreadsheet analysis", "An analysis workbook with pivots and charts"),
        (["SQL"], "SQL for analysis", "A set of documented analytical queries over a real dataset"),
        (["Python", "Pandas"], "Python for data", "A notebook that cleans and analyses a messy dataset"),
        (["Statistics"], "Applied statistics", "An A/B test or hypothesis-testing write-up"),
        (["Power BI", "Tableau"], "BI dashboards", "A published dashboard with a short insight summary"),
        (["Communication"], "Storytelling with data", "A slide deck or blog post presenting recommendations"),
    ],
    "Data Scientist": [
        (["Python", "Pandas", "NumPy"], "Python data stack", "An exploratory analysis notebook"),
        (["Statistics"], "Statistics and experimentation", "A documented statistical analysis"),
        (["SQL"], "SQL", "Feature extraction queries over a relational dataset"),
        (["Machine Learning"], "Machine learning", "An end-to-end model with proper evaluation"),
        (["Data Visualization"], "Communicating results", "Visual report of model findings"),
        (["Deep Learning", "PyTorch"], "Deep learning (optional)", "A trained neural network with a model card"),
    ],
    "ML Engineer": [
        (["Python"], "Production Python", "A typed, tested Python package"),
        (["Machine Learning"], "ML fundamentals", "A model with evaluation and baselines"),
        (["PyTorch", "Deep Learning"], "Deep learning", "A fine-tuned model with reproducible training"),
        (["NLP", "LLMs"], "NLP and LLM applications", "A grounded LLM feature with an evaluation set"),
        (["FastAPI", "Docker"], "Model serving", "A containerized inference API"),
        (["AWS", "CI/CD"], "MLOps basics", "Automated training/deployment pipeline documentation"),
    ],
    "DevOps Engineer": [
        (["Linux", "Bash"], "Linux and scripting", "Automation scripts for a real admin task"),
        (["Git"], "Version control workflows", "Contributions with a clean branching history"),
        (["Docker"], "Containers", "A reproducible containerized project"),
        (["CI/CD"], "CI/CD pipelines", "A pipeline that tests, builds and deploys"),
        (["AWS", "Terraform"], "Cloud and infrastructure as code", "Infrastructure provisioned with Terraform"),
        (["Kubernetes", "Monitoring"], "Orchestration and observability", "A monitored service on Kubernetes"),
    ],
    "Cloud Engineer": [
        (["Networking"], "Networking fundamentals", "A documented network design for a small app"),
        (["Linux"], "Linux administration", "A configured, hardened Linux server"),
        (["AWS"], "AWS core services", "A deployed application using compute, storage and IAM"),
        (["Terraform"], "Infrastructure as code", "Reproducible infrastructure in Terraform"),
        (["Docker", "Kubernetes"], "Containers in the cloud", "A containerized deployment"),
        (["Monitoring"], "Operations", "Dashboards and alerts for the deployment"),
    ],
    "QA Engineer": [
        (["Manual Testing"], "Test design", "A test plan and test cases for a real app"),
        (["SQL"], "Data validation with SQL", "Queries that verify application data"),
        (["API Testing"], "API testing", "An automated API test collection"),
        (["Java", "Python"], "Programming for testers", "Small automation utilities"),
        (["Selenium", "Cypress"], "UI automation", "An automated regression suite"),
        (["CI/CD"], "Tests in CI", "Tests running automatically on every change"),
    ],
    "Android Developer": [
        (["Kotlin"], "Kotlin", "Small Kotlin programs and exercises"),
        (["Android"], "Android fundamentals", "An app with multiple screens and navigation"),
        (["REST APIs"], "Networking", "An app that consumes a REST API"),
        (["Unit Testing"], "Testing", "Unit and UI tests for the app"),
        (["Git", "CI/CD"], "Release workflow", "A CI build producing a signed artifact"),
    ],
    "Security Analyst": [
        (["Networking"], "Networking", "Packet captures and analysis notes"),
        (["Linux", "Bash"], "Linux and scripting", "Log-parsing scripts"),
        (["Cybersecurity"], "Security fundamentals", "A home-lab write-up mapped to OWASP Top 10"),
        (["SIEM"], "Detection and monitoring", "Detection rules and triage notes"),
        (["Penetration Testing"], "Offensive basics", "A responsible, authorised lab assessment report"),
    ],
}


def available_roles() -> list[str]:
    return list(ROADMAPS)


def build_steps(target_role: str, evidence: dict) -> list[dict]:
    template = ROADMAPS.get(target_role)
    if template is None:
        raise KeyError(target_role)
    steps = []
    for order, (skills, focus, evidence_text) in enumerate(template, start=1):
        evidenced = all(evidence.get(s, {}).get("strength", 0) >= 0.75 for s in skills[:1]) and \
            any(evidence.get(s) for s in skills)
        main = SKILL_INDEX.get(skills[0])
        steps.append({
            "order": order,
            "skills": skills,
            "learning_focus": focus,
            "evidence_to_add": evidence_text,
            "resource_title": main.resource[0] if main and main.resource else None,
            "resource_url": main.resource[1] if main and main.resource else None,
            "status": "completed" if evidenced else "planned",
            "already_evidenced": evidenced,
        })
    return steps
