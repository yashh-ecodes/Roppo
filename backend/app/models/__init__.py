"""SQLAlchemy models — mirrors the initial database design in the concept doc (section 12),
plus resume versions, improvement suggestions and roadmap steps."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # Explicit consent before any resume content is sent to an external AI provider.
    ai_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    # {"locations": [], "work_modes": [], "job_types": [], "interests": []}
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    resumes: Mapped[list["Resume"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    profile: Mapped["CandidateProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_reference: Mapped[str] = mapped_column(String(255))  # private path, never public
    extracted_text_reference: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="resumes")
    versions: Mapped[list["ResumeVersion"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", order_by="ResumeVersion.version_number"
    )


class ResumeVersion(Base):
    """The original upload is version 1; every approved set of edits creates a new version."""

    __tablename__ = "resume_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(30))  # original | approved_changes
    content: Mapped[dict] = mapped_column(JSON)  # structured profile snapshot
    applied_changes: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    resume: Mapped[Resume] = relationship(back_populates="versions")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    # contact, headline, summary, education[], experience[], projects[], certifications[], achievements[], skills[]
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    education_summary: Mapped[str] = mapped_column(Text, default="")
    experience_summary: Mapped[str] = mapped_column(Text, default="")
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    skill_category: Mapped[str] = mapped_column(String(40))


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    evidence: Mapped[list] = mapped_column(JSON, default=list)  # [{"section": ..., "text": ...}]
    evidence_strength: Mapped[float] = mapped_column(Float, default=0.0)
    proficiency_self_reported: Mapped[str | None] = mapped_column(String(20), nullable=True)

    skill: Mapped[Skill] = relationship()


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    careers_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_illustrative: Mapped[bool] = mapped_column(Boolean, default=False)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    team: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role_family: Mapped[str] = mapped_column(String(80), index=True)
    location: Mapped[str] = mapped_column(String(160), default="")
    work_mode: Mapped[str] = mapped_column(String(20), default="onsite")  # remote | hybrid | onsite
    job_type: Mapped[str] = mapped_column(String(30), default="full-time")  # full-time | internship | contract
    seniority: Mapped[str] = mapped_column(String(20), default="entry")  # entry | junior | mid | senior
    experience_min_years: Mapped[float] = mapped_column(Float, default=0)
    education_requirement: Mapped[str | None] = mapped_column(String(200), nullable=True)
    education_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    salary: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(60))  # e.g. "Illustrative sample", "Greenhouse", "Manual"
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_id: Mapped[str] = mapped_column(String(120))
    # live_vacancy: fetched from an official source; illustrative: example data, not an opening
    listing_type: Mapped[str] = mapped_column(String(20), default="illustrative")
    status: Mapped[str] = mapped_column(String(20), default="unverified")  # open | closed | unverified
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped[Company] = relationship()
    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    requirement_type: Mapped[str] = mapped_column(String(20))  # mandatory | preferred
    description: Mapped[str] = mapped_column(Text, default="")

    job: Mapped[Job] = relationship(back_populates="requirements")
    skill: Mapped[Skill] = relationship()


class ResumeAnalysis(Base):
    __tablename__ = "resume_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"))
    target_role: Mapped[str | None] = mapped_column(String(80), nullable=True)
    score_details: Mapped[dict] = mapped_column(JSON)
    report: Mapped[dict] = mapped_column(JSON)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    suggestions: Mapped[list["ImprovementSuggestion"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class ImprovementSuggestion(Base):
    __tablename__ = "improvement_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("resume_analysis.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # bullet | summary | keyword | project | formatting | action
    category: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    # Where the change applies, e.g. {"section": "experience", "index": 0, "bullet": 2}
    target: Mapped[dict] = mapped_column(JSON, default=dict)
    original: Mapped[str] = mapped_column(Text, default="")
    suggested: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    applicable: Mapped[bool] = mapped_column(Boolean, default=False)  # can be applied to a resume version
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | accepted | ignored
    final_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="rules")  # rules | llm

    analysis: Mapped[ResumeAnalysis] = relationship(back_populates="suggestions")


class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("resume_analysis.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float)
    score_details: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)


class SkillGap(Base):
    __tablename__ = "skill_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    priority: Mapped[float] = mapped_column(Float)
    related_job_ids: Mapped[list] = mapped_column(JSON, default=list)


class CareerRoadmap(Base):
    __tablename__ = "career_roadmaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_role: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | archived
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    steps: Mapped[list["RoadmapStep"]] = relationship(
        back_populates="roadmap", cascade="all, delete-orphan", order_by="RoadmapStep.order"
    )


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("career_roadmaps.id", ondelete="CASCADE"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    learning_focus: Mapped[str] = mapped_column(String(160))
    evidence_to_add: Mapped[str] = mapped_column(Text)
    resource_title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    resource_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned | in_progress | completed
    already_evidenced: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_to_profile: Mapped[bool] = mapped_column(Boolean, default=False)

    roadmap: Mapped[CareerRoadmap] = relationship(back_populates="steps")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("user_id", "job_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # saved | applied | interviewing | offer | rejected | withdrawn
    application_status: Mapped[str] = mapped_column(String(20), default="saved")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[Job] = relationship()
