"""Request schemas. The candidate profile schema doubles as input sanitisation for edits."""

from pydantic import BaseModel, Field


class Contact(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    headline: str = ""


class Education(BaseModel):
    degree: str = ""
    level: int = 0
    level_label: str = ""
    field: str = ""
    institution: str = ""
    start: str = ""
    end: str = ""
    grade: str = ""
    details: str = ""


class Experience(BaseModel):
    title: str = ""
    organization: str = ""
    start: str = ""
    end: str = ""
    months: int = 0
    type: str = "job"
    bullets: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str = ""
    technologies: str = ""
    link: str = ""
    bullets: list[str] = Field(default_factory=list)


class SkillEntry(BaseModel):
    name: str
    source: str = "skills"  # skills | manual | roadmap
    proficiency: str | None = None  # beginner | intermediate | advanced (self-reported)
    evidence_note: str | None = None


class ProfileData(BaseModel):
    contact: Contact = Field(default_factory=Contact)
    summary: str = ""
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skills: list[SkillEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    sections_found: list[str] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    data: ProfileData
    confirmed: bool = True
