"""One-click demo accounts for presentations.

Each click creates a fresh, private account pre-filled with a FICTIONAL resume that goes
through the real pipeline (extraction → confirmed profile → analysis → roadmap → saved jobs).
Demo accounts are deleted automatically after DEMO_TTL_HOURS.
"""

import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.utils.security import hash_password

DEMO_DOMAIN = "demo.roppo.local"
DEMO_TTL_HOURS = 24
DEMO_RESUME = Path(__file__).resolve().parent.parent / "data" / "demo" / "demo_resume.pdf"


def cleanup_expired(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=DEMO_TTL_HOURS)
    removed = 0
    for user in db.scalars(select(User).where(User.email.like(f"%@{DEMO_DOMAIN}"))):
        created = user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=timezone.utc)
        if created < cutoff:
            shutil.rmtree(get_settings().storage_dir / f"user_{user.id}", ignore_errors=True)
            db.delete(user)
            removed += 1
    db.commit()
    return removed


def create_demo_user(db: Session) -> User:
    # Route functions are plain callables; reusing them keeps the demo on the real code path.
    from app.routes.analysis import AnalysisIn, run_analysis
    from app.routes.career import RoadmapIn, create_roadmap
    from app.routes.jobs import list_jobs
    from app.routes.resumes import ingest_resume
    from app.models import CandidateProfile, SavedJob

    cleanup_expired(db)
    user = User(
        name="Aarav Mehta (demo)",
        email=f"{uuid.uuid4().hex[:12]}@{DEMO_DOMAIN}",
        password_hash=hash_password(uuid.uuid4().hex),  # random: demo accounts can't be logged into twice
        preferences={"locations": ["Pune", "Bengaluru"], "work_modes": ["hybrid", "remote"],
                     "job_types": [], "interests": ["Backend Developer", "Full-Stack Developer"]},
    )
    db.add(user)
    db.commit()

    ingest_resume(db, user, "aarav_mehta_resume.pdf", DEMO_RESUME.read_bytes())
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    profile.confirmed = True
    db.commit()

    run_analysis(AnalysisIn(target_role="Backend Developer", use_ai=False), user, db)
    create_roadmap(RoadmapIn(target_role="Backend Java Developer"), user, db)

    jobs = list_jobs(q=None, role_family=None, location=None, work_mode=[], job_type=[], seniority=[], min_score=0,
                     hide_mandatory_gaps=False, listing="all", preferences_only=False, sort="score",
                     user=user, db=db)["jobs"]
    for job, status in zip(jobs[:2], ("applied", "saved")):
        db.add(SavedJob(user_id=user.id, job_id=job["id"], application_status=status))
    db.commit()
    return user
