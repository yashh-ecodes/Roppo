from app.services.analysis import build_report
from app.services.improvement import improve_bullet, keyword_guidance, summary_suggestion
from app.services.llm import is_grounded, redact_profile


def test_weak_openers_are_rewritten_without_inventing_numbers():
    text, reasons = improve_bullet("Responsible for building REST APIs in Java")
    assert text.startswith("Built REST APIs in Java")
    assert "[" in text  # metric placeholder, never an invented number
    assert not any(ch.isdigit() for ch in text.split("[")[0])


def test_shared_work_stays_shared():
    text, _ = improve_bullet("Helped the team write JUnit tests")
    assert text.startswith("Contributed to writing JUnit tests")


def test_strong_bullets_are_left_alone():
    assert improve_bullet("Optimized SQL queries, reducing report latency by 40%") is None


def test_summary_uses_only_verified_details(java_profile):
    s = summary_suggestion(java_profile, "Backend Developer")
    assert "Java" in s["suggested"] and "Backend Developer" in s["suggested"]
    assert "Kubernetes" not in s["suggested"]


def test_keyword_guidance_separates_missing_weak_and_present(java_profile):
    jd = ("Requirements: Java, Spring Boot and SQL. Experience with Git.\n"
          "Nice to have: Docker")
    g = keyword_guidance(java_profile, jd)
    assert {"skill": "Spring Boot", "type": "mandatory"} in g["missing"]
    assert any(x["skill"] == "Docker" and x["type"] == "preferred" for x in g["missing"])
    assert any(x["skill"] == "Git" for x in g["weak"])
    assert any(x["skill"] == "Java" for x in g["present"])
    assert "genuinely" in g["note"]


def test_report_has_all_sections_and_explained_score(java_profile):
    report, suggestions = build_report(java_profile, "text " * 300, 1, [], None)
    for key in ("overview", "strengths", "skill_coverage", "content_quality", "potential_gaps", "quality"):
        assert key in report
    q = report["quality"]
    assert 0 <= q["score"] <= 100
    assert sum(f["weight"] for f in q["factors"]) == 100
    assert all(f["explanation"] for f in q["factors"])
    assert "not a measure of your worth" in q["disclaimer"]
    assert {s["category"] for s in suggestions} >= {"summary", "bullet"}


def test_llm_grounding_guard_rejects_new_facts():
    original = "Built REST APIs in Java for an inventory tool"
    skills = {"Java", "REST APIs"}
    assert is_grounded(original, "Built Java REST APIs for an inventory tool [add % improvement]", skills)
    assert not is_grounded(original, "Built REST APIs in Java serving 10,000 users", skills)
    assert not is_grounded(original, "Built REST APIs in Java and Kubernetes", skills)


def test_redaction_removes_contact_details(java_profile):
    red = redact_profile(java_profile)
    blob = str(red)
    assert "contact" not in red
    assert "aarav.mehta@example.com" not in blob and "+91" not in blob
