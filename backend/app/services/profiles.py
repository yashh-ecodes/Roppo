"""Profile helpers shared by several routes."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models import CandidateProfile, Job, JobRequirement, User, UserSkill
from app.services.extraction import summarize_education, summarize_experience
from app.services.jobsources import ensure_skills
from app.services.matching import job_to_dict, snapshot_from_profile
from app.services.skills import build_skill_evidence


def get_profile_or_404(db: Session, user: User) -> CandidateProfile:
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if profile is None or not profile.data:
        raise HTTPException(404, "Upload a resume first to create your candidate profile.")
    return profile


def save_profile_data(db: Session, user: User, profile: CandidateProfile, data: dict) -> None:
    """Persist profile data and keep derived columns and User_Skills in sync."""
    profile.data = data
    profile.education_summary = summarize_education(data)
    profile.experience_summary = summarize_experience(data)
    sync_user_skills(db, user, data)


def sync_user_skills(db: Session, user: User, data: dict) -> None:
    skills = ensure_skills(db)
    evidence = build_skill_evidence(data)
    db.execute(delete(UserSkill).where(UserSkill.user_id == user.id))
    proficiency = {
        (s.get("name") or "").lower(): s.get("proficiency")
        for s in data.get("skills", []) if isinstance(s, dict)
    }
    for name, ev in evidence.items():
        if name not in skills:
            continue
        db.add(UserSkill(
            user_id=user.id, skill_id=skills[name].id, evidence=ev["evidence"],
            evidence_strength=ev["strength"], proficiency_self_reported=proficiency.get(name.lower()),
        ))


def load_jobs(db: Session, include_closed: bool = False) -> list[Job]:
    q = select(Job).options(selectinload(Job.requirements).selectinload(JobRequirement.skill),
                            selectinload(Job.company))
    if not include_closed:
        q = q.where(Job.status != "closed")
    return list(db.scalars(q))


def snapshot_for(user: User, profile: CandidateProfile):
    return snapshot_from_profile(profile.data, user.preferences or {})


def freshness(job: Job) -> dict:
    """Freshness info shown on every job card."""
    settings = get_settings()
    if job.listing_type == "illustrative":
        return {"label": "Illustrative example — not a live vacancy", "stale": False, "last_checked": None}
    checked = job.last_verified_at
    if checked and checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    stale = checked is None or datetime.now(timezone.utc) - checked > timedelta(days=settings.freshness_days)
    if job.status == "closed":
        label = "Closed at source"
    elif stale:
        label = "Needs re-checking"
    else:
        label = "Open at source"
    return {"label": label, "stale": stale, "last_checked": checked.isoformat() if checked else None}


def job_card(job: Job, match: dict | None = None, pref: dict | None = None) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "team": job.team,
        "company": {"id": job.company.id, "name": job.company.name, "careers_url": job.company.careers_url,
                    "is_illustrative": job.company.is_illustrative},
        "role_family": job.role_family,
        "location": job.location,
        "work_mode": job.work_mode,
        "job_type": job.job_type,
        "seniority": job.seniority,
        "experience_min_years": job.experience_min_years,
        "education_requirement": job.education_requirement,
        "salary": job.salary,
        "description": job.description,
        "source": job.source,
        "source_url": job.source_url,
        "listing_type": job.listing_type,
        "status": job.status,
        "freshness": freshness(job),
        "requirements": job_to_dict(job)["requirements"],
        "match": match,
        "preference_fit": pref,
    }
