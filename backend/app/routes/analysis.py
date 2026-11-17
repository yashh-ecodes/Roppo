"""Resume analysis, improvement suggestions, approval workflow and keyword guidance."""

import copy
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    ImprovementSuggestion,
    Job,
    JobMatch,
    Resume,
    ResumeAnalysis,
    ResumeVersion,
    SkillGap,
    User,
)
from app.services import export, llm
from app.services.analysis import build_report
from app.services.improvement import keyword_guidance
from app.services.jobsources import ensure_skills
from app.services.matching import job_to_dict, score_job, snapshot_from_profile
from app.services.profiles import get_profile_or_404, load_jobs, save_profile_data
from app.utils.security import get_current_user

router = APIRouter(tags=["analysis"])


class AnalysisIn(BaseModel):
    target_role: str | None = None
    use_ai: bool = True


class SuggestionPatch(BaseModel):
    status: str = Field(pattern="^(pending|accepted|ignored)$")
    final_text: str | None = None


class ApplyIn(BaseModel):
    label: str | None = None


class KeywordIn(BaseModel):
    job_id: int | None = None
    job_text: str | None = Field(default=None, max_length=20000)


def suggestion_out(s: ImprovementSuggestion) -> dict:
    return {"id": s.id, "category": s.category, "title": s.title, "target": s.target, "original": s.original,
            "suggested": s.suggested, "rationale": s.rationale, "applicable": s.applicable, "status": s.status,
            "final_text": s.final_text, "source": s.source}


def analysis_out(a: ResumeAnalysis) -> dict:
    return {"id": a.id, "created_at": a.created_at.isoformat(), "target_role": a.target_role,
            "llm_used": a.llm_used, "resume_id": a.resume_id, "report": a.report, "score": a.score_details,
            "suggestions": [suggestion_out(s) for s in sorted(a.suggestions, key=lambda s: s.id)]}


def _resume_text(db: Session, profile) -> str:
    if profile.resume_id:
        resume = db.get(Resume, profile.resume_id)
        if resume:
            path = get_settings().storage_dir / resume.extracted_text_reference
            if path.exists():
                return path.read_text(encoding="utf-8")
    return export.to_text(profile.data)


@router.post("/analysis", status_code=201)
def run_analysis(body: AnalysisIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile_or_404(db, user)
    data = profile.data
    meta = data.get("meta", {})
    jobs = load_jobs(db)
    job_dicts = [job_to_dict(j) for j in jobs]
    text = _resume_text(db, profile)
    report, suggestions = build_report(data, text, meta.get("page_count", 1), job_dicts, body.target_role,
                                       meta.get("warnings"))

    llm_used = False
    if body.use_ai and llm.available(user):
        enhanced = llm.enhance_analysis(data, suggestions, body.target_role)
        if enhanced:
            llm_used = True
            report["ai_overview"] = enhanced["overview"]
            for s in suggestions:
                if s["category"] == "summary" and enhanced["summary"]:
                    s.update(suggested=enhanced["summary"], source="llm",
                             rationale="AI-drafted from your verified profile details. Review and edit before using.")
            for idx, rw in enhanced["bullet_rewrites"].items():
                target = enhanced["bullet_suggestions"][idx]
                target.update(suggested=rw["suggested"], source="llm",
                              rationale=rw["rationale"] + " (AI suggestion, checked to add no new facts.)")
    report["ai"] = {"available": llm.available(user), "server_configured": llm.server_configured(),
                    "consent": user.ai_consent, "used": llm_used}

    analysis = ResumeAnalysis(user_id=user.id, resume_id=profile.resume_id, profile_id=profile.id,
                              target_role=body.target_role, score_details=report["quality"], report=report,
                              llm_used=llm_used)
    for s in suggestions:
        analysis.suggestions.append(ImprovementSuggestion(
            user_id=user.id, category=s["category"], title=s["title"], target=s.get("target", {}),
            original=s.get("original", ""), suggested=s["suggested"], rationale=s.get("rationale", ""),
            applicable=s.get("applicable", False), source=s.get("source", "rules")))
    db.add(analysis)
    db.flush()

    # Store job matches for analysis history.
    snap = snapshot_from_profile(data, user.preferences)
    scored = sorted(((j, score_job(snap, d)) for j, d in zip(jobs, job_dicts)), key=lambda x: -x[1]["score"])
    for job, result in scored[:25]:
        db.add(JobMatch(analysis_id=analysis.id, job_id=job.id, score=result["score"], score_details=result,
                        explanation=result["explanation"]))

    # Refresh stored skill gaps for the profile.
    skills = ensure_skills(db)
    db.execute(delete(SkillGap).where(SkillGap.profile_id == profile.id))
    for gap in report["potential_gaps"]["gaps"]:
        if gap["skill"] in skills:
            related = [j.id for j, d in zip(jobs, job_dicts)
                       if any(r["skill"] == gap["skill"] for r in d["requirements"])][:20]
            db.add(SkillGap(profile_id=profile.id, skill_id=skills[gap["skill"]].id,
                            priority=gap["share"] + 10 * gap["mandatory_in"], related_job_ids=related))
    db.commit()
    db.refresh(analysis)
    return analysis_out(analysis)


@router.get("/analysis")
def list_analyses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(ResumeAnalysis).where(ResumeAnalysis.user_id == user.id)
                      .order_by(ResumeAnalysis.created_at.desc()))
    return [{"id": a.id, "created_at": a.created_at.isoformat(), "target_role": a.target_role,
             "score": a.score_details.get("score"), "llm_used": a.llm_used} for a in rows]


@router.get("/analysis/latest")
def latest_analysis(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.scalar(select(ResumeAnalysis).where(ResumeAnalysis.user_id == user.id)
                  .order_by(ResumeAnalysis.created_at.desc(), ResumeAnalysis.id.desc()).limit(1))
    if a is None:
        raise HTTPException(404, "No analysis yet.")
    return analysis_out(a)


@router.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(ResumeAnalysis, analysis_id)
    if a is None or a.user_id != user.id:
        raise HTTPException(404, "Analysis not found.")
    return analysis_out(a)


@router.patch("/suggestions/{suggestion_id}")
def update_suggestion(suggestion_id: int, body: SuggestionPatch, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    s = db.get(ImprovementSuggestion, suggestion_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(404, "Suggestion not found.")
    s.status = body.status
    if body.final_text is not None:
        s.final_text = body.final_text.strip()
    db.commit()
    return suggestion_out(s)


PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]")


@router.post("/analysis/{analysis_id}/apply", status_code=201)
def apply_changes(analysis_id: int, body: ApplyIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """Save accepted changes as a NEW resume version. The original upload is never modified."""
    a = db.get(ResumeAnalysis, analysis_id)
    if a is None or a.user_id != user.id:
        raise HTTPException(404, "Analysis not found.")
    accepted = [s for s in a.suggestions if s.status == "accepted" and s.applicable]
    if not accepted:
        raise HTTPException(422, "Accept at least one applicable suggestion first.")
    unresolved = [s.id for s in accepted if PLACEHOLDER_RE.search(s.final_text or s.suggested)]
    if unresolved:
        raise HTTPException(422, {
            "message": "Some accepted suggestions still contain [placeholders]. Replace them with your real "
                       "details or remove them before saving — Roppo never fills them in for you.",
            "suggestion_ids": unresolved,
        })

    profile = get_profile_or_404(db, user)
    data = copy.deepcopy(profile.data)
    applied = []
    for s in accepted:
        text = (s.final_text or s.suggested).strip()
        t = s.target or {}
        if s.category == "summary":
            data["summary"] = text
        elif s.category == "bullet":
            try:
                data[t["section"]][t["index"]]["bullets"][t["bullet"]] = text
            except (KeyError, IndexError, TypeError):
                continue
        else:
            continue
        applied.append({"suggestion_id": s.id, "category": s.category, "target": t, "before": s.original, "after": text})

    resume = db.get(Resume, profile.resume_id) if profile.resume_id else None
    if resume is None:
        raise HTTPException(409, "The source resume for this profile was deleted.")
    number = max((v.version_number for v in resume.versions), default=0) + 1
    version = ResumeVersion(resume_id=resume.id, version_number=number,
                            label=body.label or f"Version {number} — {len(applied)} approved change(s)",
                            source="approved_changes", content=data, applied_changes=applied)
    db.add(version)
    save_profile_data(db, user, profile, data)
    db.commit()
    return {"version": {"id": version.id, "version_number": number, "label": version.label,
                        "resume_id": resume.id, "changes": applied}}


@router.post("/analysis/keywords")
def keywords(body: KeywordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile_or_404(db, user)
    if body.job_id:
        job = db.get(Job, body.job_id)
        if job is None:
            raise HTTPException(404, "Job not found.")
        d = job_to_dict(job)
        return {"job": {"id": job.id, "title": job.title, "company": job.company.name},
                **keyword_guidance(profile.data, job.description, d["requirements"])}
    if not body.job_text or len(body.job_text.strip()) < 30:
        raise HTTPException(422, "Paste a job description (at least a few sentences) or choose a job.")
    return {"job": None, **keyword_guidance(profile.data, body.job_text)}
