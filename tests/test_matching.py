import pytest

from app.services.matching import (
    MATCH_WEIGHTS,
    preference_fit,
    score_job,
    snapshot_from_profile,
    with_added_skills,
)
from app.services.opportunities import analyse, opportunity_detail


def job(**kw):
    base = {
        "id": 1, "title": "Junior Java Developer", "role_family": "Backend Developer", "seniority": "entry",
        "experience_min_years": 0, "education_requirement": None, "education_mandatory": False,
        "location": "Pune", "work_mode": "hybrid", "job_type": "full-time",
        "requirements": [
            {"skill": "Java", "type": "mandatory", "description": ""},
            {"skill": "SQL", "type": "mandatory", "description": ""},
            {"skill": "Spring Boot", "type": "mandatory", "description": "REST services use Spring Boot."},
            {"skill": "Git", "type": "preferred", "description": ""},
            {"skill": "PostgreSQL", "type": "preferred", "description": ""},
        ],
    }
    base.update(kw)
    return base


def test_weights_sum_to_one():
    assert sum(MATCH_WEIGHTS.values()) == pytest.approx(1.0)


def test_mandatory_gaps_are_flagged_not_hidden(java_profile):
    snap = snapshot_from_profile(java_profile)
    r = score_job(snap, job())
    assert r["mandatory"] == {"total": 3, "matched": 2}
    assert not r["meets_hard_requirements"]
    assert "Mandatory skill not evidenced: Spring Boot" in r["hard_requirement_flags"]
    assert r["band"] != "Strong match"
    assert "Spring Boot" in r["explanation"]


def test_listed_only_skills_are_marked_weaker(java_profile):
    r = score_job(snapshot_from_profile(java_profile), job())
    git = next(m for m in r["matched_skills"] if m["skill"] == "Git")
    java = next(m for m in r["matched_skills"] if m["skill"] == "Java")
    assert git["listed_only"] and not java["listed_only"]
    assert git["strength"] < java["strength"]


def test_related_skills_are_surfaced_but_not_counted(java_profile):
    r = score_job(snapshot_from_profile(java_profile), job())
    pg = next(m for m in r["missing_skills"] if m["skill"] == "PostgreSQL")
    assert "MySQL" in pg["related_you_have"]
    assert r["preferred"]["matched"] == 1  # Git only; MySQL is NOT counted as PostgreSQL


def test_experience_and_education_hard_requirements(java_profile):
    snap = snapshot_from_profile(java_profile)
    r = score_job(snap, job(experience_min_years=3, education_requirement="Master's degree in CS",
                            education_mandatory=True))
    flags = " ".join(r["hard_requirement_flags"])
    assert "3+ years" in flags and "Education requirement" in flags


def test_adding_a_skill_improves_match(java_profile):
    snap = snapshot_from_profile(java_profile)
    before = score_job(snap, job())
    after = score_job(with_added_skills(snap, ["Spring Boot"]), job())
    assert after["score"] > before["score"]
    assert after["mandatory"]["matched"] == 3


def test_preference_fit():
    prefs = {"locations": ["Bengaluru"], "work_modes": ["remote"], "job_types": []}
    assert not preference_fit(job(), prefs)["fits"]
    assert preference_fit(job(location="Remote", work_mode="remote"), prefs)["fits"]


def test_unlock_opportunities_ranks_recurring_gaps(java_profile):
    jobs = [job(id=i) for i in range(1, 4)] + [
        job(id=9, title="DevOps", role_family="DevOps Engineer",
            requirements=[{"skill": "Docker", "type": "mandatory", "description": ""}])]
    result = analyse(snapshot_from_profile(java_profile), jobs)
    top = result["skills"][0]
    assert top["skill"] == "Spring Boot"
    assert top["mandatory_in"] == 3
    assert set(top["jobs_all_mandatory_met"]) == {1, 2, 3}
    assert "guarantee" in result["disclaimer"]


def test_opportunity_detail_shows_remaining_requirements(java_profile):
    d = opportunity_detail(snapshot_from_profile(java_profile), job(), "Spring Boot")
    assert d["after_selected_skill"]["score"] > d["current"]["score"]
    assert "PostgreSQL (preferred)" in d["after_selected_skill"]["remaining_requirements"]
    assert any(m["resource"] for m in d["missing_detail"])
