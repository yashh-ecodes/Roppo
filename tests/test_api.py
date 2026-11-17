"""End-to-end API flow following the user journey in the concept doc (section 3)."""

import os
from pathlib import Path

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def upload(client, auth, sample_bytes, name="aarav_mehta_java_fresher.docx"):
    r = client.post("/api/resumes", headers=auth, files={"file": (name, sample_bytes(name), DOCX)})
    assert r.status_code == 201, r.text
    return r.json()


def test_auth_required(client):
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/profile", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_register_login(client):
    client.post("/api/auth/register", json={"name": "A", "email": "login@example.com", "password": "password123"})
    assert client.post("/api/auth/login", json={"email": "login@example.com", "password": "wrong-pass"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "LOGIN@example.com", "password": "password123"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_upload_rejects_bad_file(client, auth):
    r = client.post("/api/resumes", headers=auth, files={"file": ("cv.pdf", b"not really a pdf", "application/pdf")})
    assert r.status_code == 422


def test_full_journey(client, auth, sample_bytes):
    # 1. Upload -> extracted, editable profile (unconfirmed until reviewed)
    up = upload(client, auth, sample_bytes)
    assert up["profile"]["confirmed"] is False
    assert up["resume"]["versions"][0]["label"] == "Original upload"
    resume_id = up["resume"]["id"]

    # 2. Review and correct the profile
    prof = client.get("/api/profile", headers=auth).json()
    data = prof["data"]
    data["contact"]["phone"] = ""  # user chooses not to keep phone
    data["skills"].append({"name": "Docker", "source": "manual"})
    r = client.put("/api/profile", headers=auth, json={"data": data, "confirmed": True})
    assert r.status_code == 200 and r.json()["confirmed"] is True
    assert "Docker" in r.json()["skill_evidence"]

    # 3. Analysis with strengths, gaps and suggestions
    r = client.post("/api/analysis", headers=auth, json={"target_role": "Backend Developer", "use_ai": True})
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["report"]["ai"]["used"] is False  # no key/consent in tests -> rules only
    assert a["report"]["potential_gaps"]["gaps"]
    bullet = next(s for s in a["suggestions"] if s["category"] == "bullet" and "[" in s["suggested"])

    # Accepting a suggestion that still has a placeholder cannot be applied...
    client.patch(f"/api/suggestions/{bullet['id']}", headers=auth, json={"status": "accepted"})
    r = client.post(f"/api/analysis/{a['id']}/apply", headers=auth, json={})
    assert r.status_code == 422
    # ...until the user replaces it with their own words.
    final = bullet["suggested"].split(" — [")[0] + "."
    client.patch(f"/api/suggestions/{bullet['id']}", headers=auth, json={"status": "accepted", "final_text": final})
    r = client.post(f"/api/analysis/{a['id']}/apply", headers=auth, json={"label": "Clearer bullets"})
    assert r.status_code == 201, r.text
    assert r.json()["version"]["version_number"] == 2

    resumes = client.get("/api/resumes", headers=auth).json()
    versions = resumes[0]["versions"]
    assert [v["version_number"] for v in versions] == [1, 2]  # original kept
    v1 = client.get(f"/api/resumes/{resume_id}/versions/{versions[0]['id']}", headers=auth).json()
    assert bullet["original"] in v1["text"]
    exp = client.get(f"/api/resumes/{resume_id}/versions/{versions[1]['id']}/export?format=docx", headers=auth)
    assert exp.status_code == 200 and exp.content[:2] == b"PK"

    # 4. Find Companies: scored, explained, illustrative listings labelled
    jobs = client.get("/api/jobs", headers=auth).json()
    assert jobs["has_profile"] and jobs["total"] > 10
    scores = [j["match"]["score"] for j in jobs["jobs"]]
    assert scores == sorted(scores, reverse=True)
    first = jobs["jobs"][0]
    assert first["match"]["explanation"]
    assert first["freshness"]["label"].startswith("Illustrative")
    filtered = client.get("/api/jobs?work_mode=remote&hide_mandatory_gaps=true", headers=auth).json()
    assert all(j["work_mode"] == "remote" and j["match"]["meets_hard_requirements"] for j in filtered["jobs"])

    # Save a job and track application status
    s = client.post("/api/saved-jobs", headers=auth, json={"job_id": first["id"]}).json()
    s = client.patch(f"/api/saved-jobs/{s['id']}", headers=auth, json={"application_status": "applied"}).json()
    assert s["application_status"] == "applied"

    # Keyword guidance against a selected job
    g = client.post("/api/analysis/keywords", headers=auth, json={"job_id": first["id"]}).json()
    assert {"present", "weak", "missing"} <= set(g)

    # 5. Unlock Opportunities
    o = client.get("/api/opportunities", headers=auth).json()
    assert o["skills"] and o["role_families"]
    top = o["skills"][0]
    assert top["avg_score_gain"] >= 0
    detail = client.get(f"/api/opportunities/jobs/{first['id']}?skill={top['skill']}", headers=auth)
    assert detail.status_code == 200

    # 6. Career roadmap: evidenced steps pre-completed; progress + evidence -> profile
    rm = client.post("/api/roadmaps", headers=auth, json={"target_role": "Backend Java Developer"}).json()
    assert rm["steps"][0]["already_evidenced"] is True  # Core Java is evidenced
    spring = next(st for st in rm["steps"] if "Spring Boot" in st["skills"])
    r = client.post(f"/api/roadmaps/steps/{spring['id']}/add-to-profile", headers=auth)
    assert r.status_code == 422  # must complete + attach evidence first
    client.patch(f"/api/roadmaps/steps/{spring['id']}", headers=auth,
                 json={"status": "completed", "evidence_url": "https://github.com/example/demo-api",
                       "evidence_note": "Inventory API built with Spring Boot and PostgreSQL"})
    r = client.post(f"/api/roadmaps/steps/{spring['id']}/add-to-profile", headers=auth)
    assert r.status_code == 200
    ev = client.get("/api/profile", headers=auth).json()["skill_evidence"]
    assert "projects" in ev["Spring Boot"]["sections"]

    # Dashboard ties it together
    d = client.get("/api/dashboard", headers=auth).json()
    assert d["has_profile"] and d["latest_analysis"] and d["top_matches"] and d["saved_jobs"]["total"] == 1


def test_settings_consent_export_and_delete(client, auth, sample_bytes):
    upload(client, auth, sample_bytes, "priya_nair_data_analyst.docx")
    r = client.put("/api/settings", headers=auth, json={
        "ai_consent": True, "preferences": {"locations": ["Bengaluru"], "work_modes": ["hybrid"], "interests": ["Data Analyst"]}})
    assert r.json()["ai_consent"] is True and r.json()["preferences"]["interests"] == ["Data Analyst"]

    o = client.get("/api/opportunities", headers=auth).json()
    assert o["interests_applied"] == ["Data Analyst"]

    data = client.get("/api/settings/export", headers=auth).json()
    assert data["profile"]["contact"]["name"] == "Priya Nair"

    user_id = client.get("/api/auth/me", headers=auth).json()["id"]
    folder = Path(os.environ["ROPPO_STORAGE_DIR"]) / f"user_{user_id}"
    assert any(folder.iterdir())
    assert client.post("/api/settings/delete-account", headers=auth, json={"password": "bad"}).status_code == 403
    assert client.post("/api/settings/delete-account", headers=auth, json={"password": "password123"}).status_code == 204
    assert not folder.exists()
    assert client.get("/api/auth/me", headers=auth).status_code == 401


def test_users_cannot_see_each_others_data(client, auth, sample_bytes):
    up = upload(client, auth, sample_bytes)
    r = client.post("/api/auth/register", json={"name": "Other", "email": "other@example.com", "password": "password123"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    rid, vid = up["resume"]["id"], up["resume"]["versions"][0]["id"]
    assert client.get(f"/api/resumes/{rid}/versions/{vid}", headers=other).status_code == 404
    assert client.delete(f"/api/resumes/{rid}", headers=other).status_code == 404
