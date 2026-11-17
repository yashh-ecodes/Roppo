import httpx
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Job
from app.services.jobsources import infer_requirements, infer_role_family, infer_seniority, sync_greenhouse

GREENHOUSE_PAYLOAD = {
    "jobs": [
        {
            "id": 101, "title": "Junior Backend Engineer", "absolute_url": "https://boards.greenhouse.io/demo/jobs/101",
            "location": {"name": "Remote - India"}, "departments": [{"name": "Platform"}],
            "content": "&lt;p&gt;Requirements:&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Python and SQL&lt;/li&gt;"
                       "&lt;li&gt;1+ years building REST APIs&lt;/li&gt;&lt;/ul&gt;"
                       "&lt;p&gt;Nice to have:&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Docker&lt;/li&gt;&lt;/ul&gt;",
        }
    ]
}


def test_inference_helpers():
    assert infer_role_family("Senior Data Engineer") == "Data Engineer"
    assert infer_role_family("Frontend Developer (React)") == "Frontend Developer"
    assert infer_seniority("Software Engineering Intern", 0) == "entry"
    assert infer_seniority("Senior Backend Engineer", 0) == "senior"
    reqs = {s: t for s, t, _ in infer_requirements("Requirements:\n- Java, SQL\nNice to have:\n- Kubernetes")}
    assert reqs == {"Java": "mandatory", "SQL": "mandatory", "Kubernetes": "preferred"}


def test_greenhouse_sync_marks_live_and_closes_removed(client):
    payload = {"value": GREENHOUSE_PAYLOAD}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "boards-api.greenhouse.io"
        return httpx.Response(200, json=payload["value"])

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with SessionLocal() as db:
        assert sync_greenhouse(db, "demo", http) == 1
        job = db.scalar(select(Job).where(Job.source == "Greenhouse:demo"))
        assert job.listing_type == "live_vacancy" and job.status == "open" and job.last_verified_at
        assert job.work_mode == "remote" and job.experience_min_years == 1
        types = {r.skill.canonical_name: r.requirement_type for r in job.requirements}
        assert types["Python"] == "mandatory" and types["Docker"] == "preferred"

        payload["value"] = {"jobs": []}  # the posting was removed at source
        sync_greenhouse(db, "demo", http)
        db.refresh(job)
        assert job.status == "closed"
