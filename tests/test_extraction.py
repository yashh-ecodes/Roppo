from app.services.extraction import degree_level, extract_profile, parse_date_range
from app.services.skills import build_skill_evidence, find_skills


def test_profile_sections(java_profile):
    p = java_profile
    assert p["contact"]["name"] == "Aarav Mehta"
    assert p["contact"]["email"] == "aarav.mehta@example.com"
    assert {"education", "experience", "projects", "skills"} <= set(p["sections_found"])
    assert p["experience"][0]["organization"] == "Acme Technologies Pvt Ltd"
    assert p["experience"][0]["type"] == "internship"
    assert len(p["experience"][0]["bullets"]) == 3
    assert [x["name"] for x in p["projects"]] == ["Library Management System", "Weather Dashboard"]
    edu = p["education"][0]
    assert edu["level"] == 3 and edu["institution"].startswith("Savitribai")


def test_date_ranges():
    assert parse_date_range("Jun 2024 – Aug 2024")[2] == 3
    assert parse_date_range("2016 - 2020")[2] == 60
    assert parse_date_range("06/2021 to 05/2022")[2] == 12
    assert parse_date_range("Jan 2020 – Present")[2] > 60


def test_degree_levels():
    assert degree_level("B.E. in Computer Engineering")[0] == 3
    assert degree_level("M.Tech, Data Science")[0] == 4
    assert degree_level("Higher Secondary (HSC)")[0] == 1
    assert degree_level("I want to be a developer")[0] == 0


def test_ambiguous_skill_aliases():
    assert "Excel" not in find_skills("I excel at teamwork", "experience")
    assert "Excel" in find_skills("Built Excel dashboards", "experience")
    assert "Go" not in find_skills("Drove the go-to-market launch", "experience")
    assert "Go" in find_skills("Go, Python, SQL", "skills")
    assert "C" not in find_skills("Grade C in physics", "education")
    assert "REST APIs" not in find_skills("Worked with the rest of the team", "experience")
    assert "Spring Boot" not in find_skills("Spring 2023 semester", "education")


def test_evidence_strength_prefers_projects_over_skill_lists(java_profile):
    ev = build_skill_evidence(java_profile)
    assert ev["Java"]["strength"] == 1.0  # used in experience
    assert ev["Git"]["sections"] == ["skills"]  # only listed
    assert ev["Git"]["strength"] < ev["MySQL"]["strength"]


def test_no_skills_section_falls_back_to_text():
    p = extract_profile("Jane Example\njane@example.com\n\nEXPERIENCE\nEngineer | Demo Corp | 2020 - 2022\n"
                        "• Built Python services on AWS")
    names = {s["name"] for s in p["skills"]}
    assert {"Python", "AWS"} <= names
