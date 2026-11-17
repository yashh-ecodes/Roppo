"""Resume upload/management, resume versions and the editable candidate profile."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import CandidateProfile, Resume, ResumeVersion, User
from app.schemas import ProfileData, ProfileUpdate, SkillEntry
from app.services import export
from app.services.extraction import degree_level, parse_date_range
from app.services.parsing import DocumentError, extract_text, validate_upload
from app.services.profiles import get_profile_or_404, save_profile_data
from app.services.skills import build_skill_evidence, canonical
from app.utils.security import get_current_user

log = logging.getLogger("roppo.resumes")
router = APIRouter(tags=["resumes"])


def _user_dir(user: User) -> Path:
    path = get_settings().storage_dir / f"user_{user.id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resume_out(r: Resume) -> dict:
    return {
        "id": r.id, "filename": r.filename, "file_type": r.file_type, "size_bytes": r.size_bytes,
        "created_at": r.created_at.isoformat(),
        "versions": [{"id": v.id, "version_number": v.version_number, "label": v.label, "source": v.source,
                      "created_at": v.created_at.isoformat(), "changes": len(v.applied_changes or [])}
                     for v in r.versions],
    }


def profile_out(p: CandidateProfile) -> dict:
    return {
        "id": p.id, "resume_id": p.resume_id, "data": p.data, "confirmed": p.confirmed,
        "education_summary": p.education_summary, "experience_summary": p.experience_summary,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "skill_evidence": build_skill_evidence(p.data or {}),
    }


@router.post("/resumes", status_code=201)
async def upload_resume(file: UploadFile = File(...), user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    settings = get_settings()
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    filename = Path(file.filename or "resume").name[:200]
    try:
        file_type = validate_upload(filename, content, settings.max_upload_mb)
        doc = extract_text(file_type, content)
    except DocumentError as exc:
        raise HTTPException(422, str(exc)) from None

    from app.services.extraction import extract_profile

    data = ProfileData.model_validate(extract_profile(doc.text)).model_dump()
    data["meta"] = {"page_count": doc.page_count, "warnings": doc.warnings, "word_count": len(doc.text.split())}

    folder = _user_dir(user)
    stem = uuid.uuid4().hex
    (folder / f"{stem}.{file_type}").write_bytes(content)
    (folder / f"{stem}.txt").write_text(doc.text, encoding="utf-8")

    resume = Resume(user_id=user.id, filename=filename, file_type=file_type, size_bytes=len(content),
                    storage_reference=f"user_{user.id}/{stem}.{file_type}",
                    extracted_text_reference=f"user_{user.id}/{stem}.txt")
    resume.versions.append(ResumeVersion(version_number=1, label="Original upload", source="original",
                                         content=data, applied_changes=[]))
    db.add(resume)
    db.flush()

    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if profile is None:
        profile = CandidateProfile(user_id=user.id)
        db.add(profile)
    profile.resume_id = resume.id
    profile.confirmed = False
    save_profile_data(db, user, profile, data)
    db.commit()
    # Never log resume contents — only metadata.
    log.info("resume uploaded user=%s type=%s size=%s", user.id, file_type, len(content))
    return {"resume": resume_out(resume), "profile": profile_out(profile), "warnings": doc.warnings}


@router.get("/resumes")
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()))
    return [resume_out(r) for r in rows]


def _own_resume(db: Session, user: User, resume_id: int) -> Resume:
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(404, "Resume not found.")
    return resume


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = _own_resume(db, user, resume_id)
    root = get_settings().storage_dir
    for ref in (resume.storage_reference, resume.extracted_text_reference):
        (root / ref).unlink(missing_ok=True)
    db.delete(resume)
    db.commit()


@router.get("/resumes/{resume_id}/versions/{version_id}")
def get_version(resume_id: int, version_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = _own_resume(db, user, resume_id)
    version = next((v for v in resume.versions if v.id == version_id), None)
    if version is None:
        raise HTTPException(404, "Version not found.")
    return {"id": version.id, "version_number": version.version_number, "label": version.label,
            "content": version.content, "applied_changes": version.applied_changes,
            "text": export.to_text(version.content)}


@router.get("/resumes/{resume_id}/versions/{version_id}/export")
def export_version(resume_id: int, version_id: int, format: str = "docx", user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    resume = _own_resume(db, user, resume_id)
    version = next((v for v in resume.versions if v.id == version_id), None)
    if version is None:
        raise HTTPException(404, "Version not found.")
    base = Path(resume.filename).stem + f"-v{version.version_number}"
    if format == "txt":
        return Response(export.to_text(version.content), media_type="text/plain",
                        headers={"Content-Disposition": f'attachment; filename="{base}.txt"'})
    return Response(export.to_docx(version.content),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{base}.docx"'})


@router.post("/resumes/{resume_id}/versions/{version_id}/restore")
def restore_version(resume_id: int, version_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Make a stored version the working candidate profile again (e.g. go back to the original)."""
    resume = _own_resume(db, user, resume_id)
    version = next((v for v in resume.versions if v.id == version_id), None)
    if version is None:
        raise HTTPException(404, "Version not found.")
    profile = get_profile_or_404(db, user)
    profile.resume_id = resume.id
    save_profile_data(db, user, profile, dict(version.content))
    db.commit()
    return profile_out(profile)


# ------------------------------------------------------------------ candidate profile
@router.get("/profile")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return profile_out(get_profile_or_404(db, user))


@router.put("/profile")
def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile_or_404(db, user)
    data = body.data.model_dump()
    # Recompute derived fields the user may have edited.
    for edu in data["education"]:
        edu["level"], edu["level_label"] = degree_level(edu.get("degree", ""))
    for exp in data["experience"]:
        _, _, months = parse_date_range(f"{exp.get('start', '')} - {exp.get('end', '')}")
        exp["months"] = months or exp.get("months", 0)
    data["meta"] = (profile.data or {}).get("meta", {})
    save_profile_data(db, user, profile, data)
    profile.confirmed = body.confirmed
    db.commit()
    return profile_out(profile)


@router.post("/profile/skills")
def add_skill(entry: SkillEntry, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a skill manually (e.g. one you have but didn't list). Counts as weak evidence until
    it is backed by a project or experience bullet."""
    profile = get_profile_or_404(db, user)
    data = dict(profile.data)
    name = canonical(entry.name) or entry.name.strip()
    if not any((s.get("name") or "").lower() == name.lower() for s in data.get("skills", [])):
        data["skills"] = data.get("skills", []) + [{**entry.model_dump(), "name": name, "source": entry.source or "manual"}]
    save_profile_data(db, user, profile, data)
    db.commit()
    return profile_out(profile)
