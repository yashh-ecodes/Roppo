"""Find Companies (current opportunities) and saved jobs / application tracking."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import CandidateProfile, Job, SavedJob, User
from app.services import llm
from app.services.jobsources import ensure_skills, sync_all, upsert_job
from app.services.matching import job_to_dict, preference_fit, score_job, snapshot_from_profile
from app.services.profiles import job_card, load_jobs
from app.utils.security import get_current_user

router = APIRouter(tags=["jobs"])

APPLICATION_STATUSES = ("saved", "applied", "interviewing", "offer", "rejected", "withdrawn")


def _snapshot(db: Session, user: User):
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if profile is None or not profile.data:
        return None, None
    return profile, snapshot_from_profile(profile.data, user.preferences or {})


@router.get("/jobs/meta")
def jobs_meta(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = load_jobs(db)
    return {
        "role_families": sorted({j.role_family for j in jobs}),
        "locations": sorted({j.location for j in jobs if j.location}),
        "work_modes": ["remote", "hybrid", "onsite"],
        "job_types": sorted({j.job_type for j in jobs}),
        "seniority": ["entry", "junior", "mid", "senior"],
        "counts": {"live": sum(j.listing_type == "live_vacancy" for j in jobs),
                   "illustrative": sum(j.listing_type == "illustrative" for j in jobs)},
        "live_sources_configured": bool(get_settings().greenhouse_boards or get_settings().lever_companies),
    }


@router.get("/jobs")
def list_jobs(
    q: str | None = None,
    role_family: str | None = None,
    location: str | None = None,
    work_mode: list[str] = Query(default=[]),
    job_type: list[str] = Query(default=[]),
    seniority: list[str] = Query(default=[]),
    min_score: float = 0,
    hide_mandatory_gaps: bool = False,
    listing: str = Query(default="all", pattern="^(all|live|illustrative)$"),
    preferences_only: bool = False,
    sort: str = Query(default="score", pattern="^(score|recent|company)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, snap = _snapshot(db, user)
    saved = {s.job_id: s.application_status for s in db.scalars(select(SavedJob).where(SavedJob.user_id == user.id))}
    prefs = user.preferences or {}
    out = []
    for job in load_jobs(db):
        if listing == "live" and job.listing_type != "live_vacancy":
            continue
        if listing == "illustrative" and job.listing_type != "illustrative":
            continue
        if q:
            hay = " ".join([job.title, job.company.name, job.role_family, job.team or "", job.description]).lower()
            if not all(term in hay for term in q.lower().split()):
                continue
        if role_family and job.role_family != role_family:
            continue
        if location and location.lower() not in (job.location or "").lower():
            continue
        if work_mode and job.work_mode not in work_mode:
            continue
        if job_type and job.job_type not in job_type:
            continue
        if seniority and job.seniority not in seniority:
            continue
        d = job_to_dict(job)
        match = score_job(snap, d) if snap else None
        pref = preference_fit(d, prefs)
        if preferences_only and not pref["fits"]:
            continue
        if match and match["score"] < min_score:
            continue
        if match and hide_mandatory_gaps and not match["meets_hard_requirements"]:
            continue
        card = job_card(job, match, pref)
        card["saved_status"] = saved.get(job.id)
        out.append(card)

    if sort == "score" and snap:
        # Live vacancies first at equal score — a company name alone is not an opportunity.
        out.sort(key=lambda c: (-c["match"]["score"], c["listing_type"] != "live_vacancy"))
    elif sort == "company":
        out.sort(key=lambda c: (c["company"]["name"], c["title"]))
    else:
        out.sort(key=lambda c: c["freshness"]["last_checked"] or "", reverse=True)
    return {"jobs": out, "total": len(out), "has_profile": snap is not None}


@router.get("/jobs/{job_id}")
def get_job(job_id: int, explain: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    profile, snap = _snapshot(db, user)
    d = job_to_dict(job)
    match = score_job(snap, d) if snap else None
    card = job_card(job, match, preference_fit(d, user.preferences or {}))
    saved = db.scalar(select(SavedJob).where(SavedJob.user_id == user.id, SavedJob.job_id == job.id))
    card["saved_status"] = saved.application_status if saved else None
    card["ai_explanation"] = None
    if explain and match and llm.available(user):
        card["ai_explanation"] = llm.explain_match(profile.data, d, match)
    return card


class ManualJobIn(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    source_url: HttpUrl
    location: str = ""
    work_mode: str = Field(default="onsite", pattern="^(remote|hybrid|onsite)$")
    job_type: str = Field(default="full-time", pattern="^(full-time|internship|contract)$")
    description: str = Field(min_length=50, max_length=20000)


@router.post("/jobs", status_code=201)
def add_job(body: ManualJobIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a listing copied from an employer's official careers page. Requirements are
    inferred from the description and can be reviewed on the job page."""
    skills = ensure_skills(db)
    job = upsert_job(db, skills, company=body.company, careers_url=None, source=f"Added by user {user.id}",
                     external_id=str(body.source_url), title=body.title, location=body.location,
                     work_mode=body.work_mode, job_type=body.job_type, team=None, description=body.description,
                     source_url=str(body.source_url))
    db.commit()
    db.refresh(job)
    return job_card(job)


@router.post("/jobs/sync")
def sync_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Refresh live vacancies from the configured official job-board APIs."""
    s = get_settings()
    gh = [b.strip() for b in s.greenhouse_boards.split(",") if b.strip()]
    lv = [c.strip() for c in s.lever_companies.split(",") if c.strip()]
    if not gh and not lv:
        raise HTTPException(400, "No live job sources are configured (ROPPO_GREENHOUSE_BOARDS / ROPPO_LEVER_COMPANIES).")
    return {"results": sync_all(db, gh, lv)}


# ------------------------------------------------------------------ saved jobs
class SaveIn(BaseModel):
    job_id: int


class SavedPatch(BaseModel):
    application_status: str | None = Field(default=None, pattern="^(" + "|".join(APPLICATION_STATUSES) + ")$")
    notes: str | None = Field(default=None, max_length=2000)


def saved_out(s: SavedJob, snap=None) -> dict:
    match = score_job(snap, job_to_dict(s.job)) if snap else None
    return {"id": s.id, "saved_at": s.saved_at.isoformat(), "application_status": s.application_status,
            "notes": s.notes, "job": job_card(s.job, match)}


@router.get("/saved-jobs")
def list_saved(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, snap = _snapshot(db, user)
    rows = db.scalars(select(SavedJob).where(SavedJob.user_id == user.id).order_by(SavedJob.saved_at.desc()))
    return [saved_out(s, snap) for s in rows]


@router.post("/saved-jobs", status_code=201)
def save_job(body: SaveIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(Job, body.job_id) is None:
        raise HTTPException(404, "Job not found.")
    existing = db.scalar(select(SavedJob).where(SavedJob.user_id == user.id, SavedJob.job_id == body.job_id))
    if existing:
        return saved_out(existing)
    s = SavedJob(user_id=user.id, job_id=body.job_id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return saved_out(s)


@router.patch("/saved-jobs/{saved_id}")
def update_saved(saved_id: int, body: SavedPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(SavedJob, saved_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(404, "Saved job not found.")
    if body.application_status:
        s.application_status = body.application_status
    if body.notes is not None:
        s.notes = body.notes
    db.commit()
    return saved_out(s)


@router.delete("/saved-jobs/{saved_id}", status_code=204)
def delete_saved(saved_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(SavedJob, saved_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(404, "Saved job not found.")
    db.delete(s)
    db.commit()
