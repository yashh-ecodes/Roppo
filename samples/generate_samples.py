"""Generate FICTIONAL sample resumes (PDF + DOCX) for testing and demos.

All people, contact details, employers and achievements below are invented.
Never commit real personal resumes to this repository.

Usage:  python samples/generate_samples.py
"""

from pathlib import Path

import pymupdf
from docx import Document
from docx.shared import Pt

OUT = Path(__file__).resolve().parent

CANDIDATES = {
    "aarav_mehta_java_fresher": {
        "name": "Aarav Mehta",
        "headline": "Aspiring Backend Developer",
        "contact": "Pune, Maharashtra | aarav.mehta@example.com | +91 90000 00001 | github.com/aarav-demo",
        "sections": [
            ("SUMMARY", ["Final-year computer engineering student interested in backend development."]),
            ("EDUCATION", ["B.E. in Computer Engineering, Savitribai Phule Pune University",
                           "2021 – 2025 | CGPA: 8.4/10",
                           "", "Higher Secondary (HSC), Fergusson College, 2021, 88%"]),
            ("EXPERIENCE", ["Software Development Intern | Acme Technologies Pvt Ltd | Jun 2024 – Aug 2024",
                            "• Responsible for building REST APIs in Java for an internal inventory tool",
                            "• Worked on SQL queries to generate monthly reports, reducing manual effort by 30%",
                            "• Helped the team write JUnit tests"]),
            ("PROJECTS", ["Library Management System | Java, MySQL, JDBC",
                          "• Built a desktop application to manage book issue and return using object-oriented design",
                          "• Designed a normalized MySQL schema with 8 tables",
                          "", "Weather Dashboard (React, JavaScript)",
                          "• Created a React dashboard that consumes a public weather API"]),
            ("TECHNICAL SKILLS", ["Languages: Java, SQL, JavaScript, C",
                                  "Frameworks: React (basic)", "Tools: Git, IntelliJ IDEA, VS Code"]),
            ("CERTIFICATIONS", ["• Oracle Certified Associate, Java SE 8 Programmer"]),
            ("ACHIEVEMENTS", ["• Finalist, college hackathon 2023"]),
        ],
    },
    "priya_nair_data_analyst": {
        "name": "Priya Nair",
        "headline": "Data Analyst",
        "contact": "Bengaluru, Karnataka | priya.nair@example.com | +91 90000 00002 | linkedin.com/in/priya-nair-demo",
        "sections": [
            ("PROFESSIONAL SUMMARY", ["Data analyst with 2 years of experience turning sales data into dashboards "
                                      "and recommendations for business teams."]),
            ("WORK EXPERIENCE", ["Data Analyst | Fictional Retail Co | Jul 2023 – Present",
                                 "• Built Power BI dashboards tracking weekly sales for 40 stores",
                                 "• Wrote SQL queries to clean and join transaction data from 3 sources",
                                 "• Presented monthly insights to regional managers",
                                 "", "Analytics Intern | Sample Insights LLP | Jan 2023 – Jun 2023",
                                 "• Automated an Excel report with Python and pandas, cutting preparation time from 4 hours to 30 minutes"]),
            ("PROJECTS", ["Customer Churn Analysis | Python, Pandas, Matplotlib",
                          "• Analysed a public telecom dataset to identify churn drivers using statistics"]),
            ("EDUCATION", ["B.Sc. in Statistics, Example University, 2019 – 2022, 78%"]),
            ("SKILLS", ["SQL, Excel, Power BI, Python, Pandas, Statistics, Communication"]),
        ],
    },
    "rohan_das_career_switcher": {
        "name": "Rohan Das",
        "headline": "Mechanical Engineer moving into DevOps",
        "contact": "Hyderabad | rohan.das@example.com | +91 90000 00003",
        "sections": [
            ("OBJECTIVE", ["Mechanical engineer transitioning to cloud and DevOps roles."]),
            ("EXPERIENCE", ["Production Engineer, Demo Manufacturing Ltd, Aug 2020 – Present",
                            "• Managed a shop-floor team of 12 operators",
                            "• I wrote Bash scripts on Linux machines to back up machine logs every night",
                            "• Involved in process improvement initiatives"]),
            ("PROJECTS", ["Personal Blog Deployment",
                          "• Deployed a static blog with Docker on a Linux VPS and set up GitHub Actions for automatic builds"]),
            ("EDUCATION", ["B.Tech in Mechanical Engineering, Sample Institute of Technology, 2016 – 2020"]),
            ("SKILLS", ["Linux, Bash, Docker, Git, AutoCAD, Leadership"]),
            ("CERTIFICATIONS", ["AWS Certified Cloud Practitioner (in progress)"]),
        ],
    },
}


def write_docx(c: dict, path: Path) -> None:
    doc = Document()
    doc.styles["Normal"].font.size = Pt(10.5)
    doc.add_paragraph(c["name"]).runs[0].bold = True
    doc.add_paragraph(c["headline"])
    doc.add_paragraph(c["contact"])
    for heading, lines in c["sections"]:
        doc.add_paragraph(heading).runs[0].bold = True
        for line in lines:
            if line.startswith("• "):
                doc.add_paragraph(line[2:], style="List Bullet")
            else:
                doc.add_paragraph(line)
    doc.save(path)


def write_pdf(c: dict, path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 50

    def line(text: str, size: float = 10, bold: bool = False):
        nonlocal page, y
        if y > 800:
            page, y = doc.new_page(), 50
        # Base-14 PDF fonts only cover Latin-1, so map typographic dashes/bullets to ASCII.
        text = text.replace("–", "-").replace("—", "-").replace("•", "-")
        page.insert_text((50, y), text, fontsize=size, fontname="hebo" if bold else "helv")
        y += size + 5

    line(c["name"], 16, True)
    line(c["headline"], 11)
    line(c["contact"], 9)
    for heading, lines in c["sections"]:
        y += 6
        line(heading, 11, True)
        for text in lines:
            if not text:
                y += 4
                continue
            # wrap long lines
            words, buf = text.split(), ""
            for w in words:
                if len(buf) + len(w) > 95:
                    line(buf)
                    buf = "  " + w
                else:
                    buf = f"{buf} {w}".strip() if buf.strip() else (buf + w)
            line(buf)
    doc.save(path)


if __name__ == "__main__":
    for slug, cand in CANDIDATES.items():
        write_docx(cand, OUT / f"{slug}.docx")
        write_pdf(cand, OUT / f"{slug}.pdf")
        print("wrote", slug)
