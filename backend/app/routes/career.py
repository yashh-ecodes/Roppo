"""Unlock Opportunities, Career Roadmap, Dashboard and Profile & Settings."""

import shutil

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import CareerRoadmap, Job, ResumeAnalysis, RoadmapStep, SavedJob, User
from app.services import llm
from app.services.matching import MATCH_WEIGHTS, job_to_dict, score_job
from app.services.opportunities import analyse, opportunity_detail
from app.services.profiles import get_profile_or_404, job_card, load_jobs, save_profile_data, snapshot_for
from app.services.roadmap import ROADMAPS, available_roles, build_steps
from app.services.skills import build_skill_evidence
from app.utils.security import get_current_user, verify_password

router = APIRouter(tags=["career"])


# ------------------------------------------------------------------ Unlock Opportunities
@router.get("/opportunities")
def opportunities(interests: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile_or_404(db, user)
    chosen = [i.strip() for i in (interests.split(",") if interests else (user.preferences or {}).get("interests", []))
              if i and i.strip()]
    jobs = load_jobs(db)
    result = analyse(snapshot_for(user, profile), [job_to_dict(j) for j in jobs], chosen)
    by_id = {j.id: j for j in jobs}
    # Companies with relevant roles for the top skills, labelled live vs illustrative.
    for row in result["skills"]:
        ids = set(row["jobs_all_mandatory_met"]) | set(row["jobs_reaching_good_match"])
        row["example_roles"] = [
            {"job_id": jid, "title": by_id[jid].title, "company": by_id[jid].company.name,
             "listing_type": by_id[jid].listing_type}
            for jid in list(ids)[:4] if jid in by_id
        ]
    return result


@router.get("/opportunities/jobs/{job_id}")
def opportunity_job(job_id: int, skill: str | None = None, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    profile = get_profile_or_404(db, user)
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    detail = opportunity_detail(snapshot_for(user, profile), job_to_dict(job), skill)
    return {"job": job_card(job), **detail}


# ------------------------------------------------------------------ Career Roadmap
class RoadmapIn(BaseModel):
    target_role: str


class StepPatch(BaseModel):
    status: str | None = Field(default=None, pattern="^(planned|in_progress|completed)$")
    evidence_url: str | None = Field(default=None, max_length=500)
    evidence_note: str | None = Field(default=None, max_length=2000)


def step_out(s: RoadmapStep) -> dict:
    return {"id": s.id, "order": s.order, "skills": s.skills, "learning_focus": s.learning_focus,
            "evidence_to_add": s.evidence_to_add, "resource_title": s.resource_title, "resource_url": s.resource_url,
            "status": s.status, "already_evidenced": s.already_evidenced, "evidence_url": s.evidence_url,
            "evidence_note": s.evidence_note, "added_to_profile": s.added_to_profile}


def roadmap_out(r: CareerRoadmap) -> dict:
    steps = [step_out(s) for s in r.steps]
    done = sum(s["status"] == "completed" for s in steps)
    return {"id": r.id, "target_role": r.target_role, "status": r.status, "created_at": r.created_at.isoformat(),
            "steps": steps, "progress": round(100 * done / len(steps)) if steps else 0}


@router.get("/roadmaps/roles")
def roadmap_roles():
    return [{"role": r, "steps": len(s)} for r, s in ROADMAPS.items()]


@router.get("/roadmaps")
def list_roadmaps(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(CareerRoadmap).where(CareerRoadmap.user_id == user.id, CareerRoadmap.status == "active")
                      .order_by(CareerRoadmap.created_at.desc()))
    return [roadmap_out(r) for r in rows]


@router.post("/roadmaps", status_code=201)
def create_roadmap(body: RoadmapIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.target_role not in available_roles():
        raise HTTPException(422, "Unknown target role.")
    profile = get_profile_or_404(db, user)
    evidence = build_skill_evidence(profile.data)
    roadmap = CareerRoadmap(user_id=user.id, target_role=body.target_role)
    for st in build_steps(body.target_role, evidence):
        roadmap.steps.append(RoadmapStep(**st))
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)
    return roadmap_out(roadmap)


def _own_step(db: Session, user: User, step_id: int) -> RoadmapStep:
    step = db.get(RoadmapStep, step_id)
    if step is None or step.roadmap.user_id != user.id:
        raise HTTPException(404, "Step not found.")
    return step


@router.patch("/roadmaps/steps/{step_id}")
def update_step(step_id: int, body: StepPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    step = _own_step(db, user, step_id)
    for field in ("status", "evidence_url", "evidence_note"):
        value = getattr(body, field)
        if value is not None:
            setattr(step, field, value)
    db.commit()
    return step_out(step)


@router.post("/roadmaps/steps/{step_id}/add-to-profile")
def add_step_to_profile(step_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a completed step's project evidence to the profile so matches can be refreshed."""
    step = _own_step(db, user, step_id)
    if step.status != "completed":
        raise HTTPException(422, "Mark the step as completed first.")
    if not (step.evidence_note or step.evidence_url):
        raise HTTPException(422, "Attach project evidence (a link or a short description of what you built) first.")
    profile = get_profile_or_404(db, user)
    data = dict(profile.data)
    project = {
        "name": (step.evidence_note or step.learning_focus).split(".")[0][:80],
        "technologies": ", ".join(step.skills),
        "link": step.evidence_url or "",
        "bullets": [step.evidence_note] if step.evidence_note else [],
    }
    data["projects"] = list(data.get("projects", [])) + [project]
    names = {(s.get("name") or "").lower() for s in data.get("skills", [])}
    data["skills"] = list(data.get("skills", [])) + [
        {"name": s, "source": "roadmap", "evidence_note": f"Roadmap: {step.learning_focus}"}
        for s in step.skills if s.lower() not in names
    ]
    save_profile_data(db, user, profile, data)
    step.added_to_profile = True
    db.commit()
    return {"step": step_out(step), "message": "Added to your profile. Matches on Find Companies now reflect it."}


@router.delete("/roadmaps/{roadmap_id}", status_code=204)
def archive_roadmap(roadmap_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(CareerRoadmap, roadmap_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(404, "Roadmap not found.")
    db.delete(r)
    db.commit()


# ------------------------------------------------------------------ Dashboard
@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import CandidateProfile

    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    latest = db.scalar(select(ResumeAnalysis).where(ResumeAnalysis.user_id == user.id)
                       .order_by(ResumeAnalysis.created_at.desc(), ResumeAnalysis.id.desc()).limit(1))
    saved = list(db.scalars(select(SavedJob).where(SavedJob.user_id == user.id)))
    roadmaps = list(db.scalars(select(CareerRoadmap).where(CareerRoadmap.user_id == user.id,
                                                           CareerRoadmap.status == "active")))
    out = {
        "user": {"name": user.name},
        "has_profile": bool(profile and profile.data),
        "profile_confirmed": bool(profile and profile.confirmed),
        "profile": None, "latest_analysis": None, "top_matches": [], "recommended_actions": [],
        "saved_jobs": {"total": len(saved), "by_status": {}},
        "roadmaps": [roadmap_out(r) for r in roadmaps][:2],
    }
    for s in saved:
        out["saved_jobs"]["by_status"][s.application_status] = out["saved_jobs"]["by_status"].get(s.application_status, 0) + 1
    if profile and profile.data:
        ev = build_skill_evidence(profile.data)
        out["profile"] = {
            "name": profile.data.get("contact", {}).get("name"), "headline": profile.data.get("contact", {}).get("headline"),
            "education": profile.education_summary, "experience": profile.experience_summary,
            "skills": len(ev), "strong_skills": [s for s, e in ev.items() if e["strength"] >= 0.9][:8],
        }
        snap = snapshot_for(user, profile)
        scored = sorted(((j, score_job(snap, job_to_dict(j))) for j in load_jobs(db)), key=lambda x: -x[1]["score"])
        out["top_matches"] = [
            {"job_id": j.id, "title": j.title, "company": j.company.name, "score": m["score"], "band": m["band"],
             "listing_type": j.listing_type, "mandatory_gaps": m["mandatory"]["total"] - m["mandatory"]["matched"]}
            for j, m in scored[:5]
        ]
    if latest:
        out["latest_analysis"] = {"id": latest.id, "created_at": latest.created_at.isoformat(),
                                  "score": latest.score_details.get("score"), "overview": latest.report.get("overview"),
                                  "target_role": latest.target_role}
        pending = [s for s in latest.suggestions if s.status == "pending" and s.category != "formatting"]
        out["recommended_actions"] = [{"id": s.id, "title": s.title, "category": s.category} for s in pending[:5]]
    if not out["has_profile"]:
        out["recommended_actions"] = [{"id": None, "title": "Upload your resume to get started", "category": "start"}]
    elif not out["profile_confirmed"]:
        out["recommended_actions"].insert(0, {"id": None, "title": "Review and confirm your extracted profile",
                                              "category": "profile"})
    return out


# ------------------------------------------------------------------ Profile & Settings
class SettingsIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    ai_consent: bool | None = None
    preferences: dict | None = None


class DeleteAccountIn(BaseModel):
    password: str


@router.get("/settings")
def get_settings_route(user: User = Depends(get_current_user)):
    return {
        "name": user.name, "email": user.email, "ai_consent": user.ai_consent, "preferences": user.preferences or {},
        "ai": {"server_configured": llm.server_configured(), "provider": "Anthropic (Claude)",
               "model": get_settings().llm_model},
        "matching_weights": MATCH_WEIGHTS,
    }


@router.put("/settings")
def update_settings(body: SettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.name is not None:
        user.name = body.name.strip()
    if body.ai_consent is not None:
        user.ai_consent = body.ai_consent
    if body.preferences is not None:
        allowed = {"locations", "work_modes", "job_types", "interests"}
        user.preferences = {k: [str(x)[:80] for x in v][:20] for k, v in body.preferences.items()
                            if k in allowed and isinstance(v, list)}
    db.commit()
    return get_settings_route(user)


@router.get("/settings/export")
def export_my_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Download everything Roppo stores about you (except uploaded files and your password hash)."""
    from app.models import CandidateProfile

    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    analyses = db.scalars(select(ResumeAnalysis).where(ResumeAnalysis.user_id == user.id))
    return {
        "account": {"name": user.name, "email": user.email, "ai_consent": user.ai_consent,
                    "preferences": user.preferences, "created_at": user.created_at.isoformat()},
        "profile": profile.data if profile else None,
        "resumes": [{"filename": r.filename, "versions": [v.content for v in r.versions]} for r in user.resumes],
        "analyses": [{"created_at": a.created_at.isoformat(), "report": a.report} for a in analyses],
        "saved_jobs": [{"job_id": s.job_id, "status": s.application_status, "notes": s.notes}
                       for s in db.scalars(select(SavedJob).where(SavedJob.user_id == user.id))],
    }


@router.delete("/settings/analysis-history", status_code=204)
def delete_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(delete(ResumeAnalysis).where(ResumeAnalysis.user_id == user.id))
    db.commit()


@router.post("/settings/delete-account", status_code=204)
def delete_account(body: DeleteAccountIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Permanently delete the account, resumes (files included), profile, analyses and saved items."""
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(403, "Password is incorrect.")
    folder = get_settings().storage_dir / f"user_{user.id}"
    db.delete(user)
    db.commit()
    shutil.rmtree(folder, ignore_errors=True)
