"""Job data sources.

* Illustrative sample jobs (fictional companies) for demos — always labelled as such.
* Live vacancies from official, public ATS job-board APIs (Greenhouse, Lever), which
  employers publish for exactly this purpose. No scraping.
* Listings a user adds manually from an official careers page.

Each job records its source, source URL and the date it was last verified so the UI can
show freshness and distinguish live vacancies from illustrative examples.
"""

import html
import logging
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data import sample_jobs
from app.data.skills import SKILLS
from app.models import Company, Job, JobRequirement, Skill
from app.services.skills import find_skills

log = logging.getLogger("roppo.jobs")

ROLE_FAMILY_RULES: list[tuple[str, str]] = [
    (r"\b(data scientist|machine learning|ml engineer|ai engineer|applied scientist)\b", "ML Engineer"),
    (r"\bdata engineer", "Data Engineer"),
    (r"\b(data analyst|business intelligence|bi analyst|analytics)\b", "Data Analyst"),
    (r"\b(devops|site reliability|sre|platform engineer|infrastructure)\b", "DevOps Engineer"),
    (r"\bcloud\b", "Cloud Engineer"),
    (r"\b(qa|quality|test|sdet)\b", "QA Engineer"),
    (r"\b(android)\b", "Android Developer"),
    (r"\b(ios|mobile|react native|flutter)\b", "Mobile Developer"),
    (r"\b(security|soc|appsec)\b", "Security Analyst"),
    (r"\b(full[- ]?stack)\b", "Full-Stack Developer"),
    (r"\b(front[- ]?end|ui engineer|react developer)\b", "Frontend Developer"),
    (r"\b(back[- ]?end|api|server|java developer|python developer)\b", "Backend Developer"),
    (r"\b(designer|ux|ui/ux)\b", "UI/UX Designer"),
    (r"\b(business analyst|product analyst)\b", "Business Analyst"),
    (r"\b(software|developer|engineer|programmer)\b", "Software Engineer"),
]


def ensure_skills(db: Session) -> dict[str, Skill]:
    existing = {s.canonical_name: s for s in db.scalars(select(Skill))}
    for sdef in SKILLS:
        if sdef.name not in existing:
            skill = Skill(canonical_name=sdef.name, skill_category=sdef.category)
            db.add(skill)
            existing[sdef.name] = skill
    db.flush()
    return existing


def _company(db: Session, name: str, illustrative: bool, careers_url: str | None = None) -> Company:
    company = db.scalar(select(Company).where(Company.name == name))
    if company is None:
        company = Company(name=name, is_illustrative=illustrative, careers_url=careers_url)
        db.add(company)
        db.flush()
    return company


def seed_sample_jobs(db: Session) -> int:
    """Insert the fictional illustrative job set once. Returns the number of jobs added."""
    skills = ensure_skills(db)
    if db.scalar(select(Job).where(Job.listing_type == "illustrative").limit(1)):
        db.commit()
        return 0
    for name, _desc in sample_jobs.COMPANIES:
        _company(db, name, illustrative=True)
    added = 0
    for idx, row in enumerate(sample_jobs.JOBS):
        (company, title, team, family, location, mode, jtype, level, exp, edu, edu_mand, salary, summary,
         mandatory, preferred) = row
        job = Job(
            company_id=_company(db, company, True).id,
            title=title, team=team, role_family=family, location=location, work_mode=mode, job_type=jtype,
            seniority=level, experience_min_years=exp, education_requirement=edu, education_mandatory=edu_mand,
            salary=salary, description=summary, source="Illustrative sample", source_url=None,
            external_id=f"sample-{idx}", listing_type="illustrative", status="unverified",
        )
        for s in mandatory:
            job.requirements.append(JobRequirement(skill_id=skills[s].id, requirement_type="mandatory",
                                                   description=sample_jobs.WHY.get(s, "")))
        for s in preferred:
            job.requirements.append(JobRequirement(skill_id=skills[s].id, requirement_type="preferred",
                                                   description=sample_jobs.WHY.get(s, "")))
        db.add(job)
        added += 1
    db.commit()
    return added


# ------------------------------------------------------------------ normalisation
def _plain(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<li[^>]*>", "\n• ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def infer_role_family(title: str) -> str:
    lowered = title.lower()
    for pattern, family in ROLE_FAMILY_RULES:
        if re.search(pattern, lowered):
            return family
    return "Other"


def infer_seniority(title: str, years: float) -> str:
    t = title.lower()
    if re.search(r"\b(intern|trainee|graduate|fresher|entry)\b", t):
        return "entry"
    if re.search(r"\b(senior|sr\.?|lead|staff|principal)\b", t):
        return "senior"
    if re.search(r"\b(junior|jr\.?|associate|i)\b", t):
        return "junior"
    if years >= 5:
        return "senior"
    if years >= 3:
        return "mid"
    if years >= 1:
        return "junior"
    return "entry"


def infer_requirements(description: str) -> list[tuple[str, str, str]]:
    """Return [(skill, type, context)] from a plain-text job description.

    Skills found under 'nice to have / preferred / bonus' wording are preferred; everything
    else found in the description is treated as mandatory.
    """
    lines = description.splitlines()
    section = "mandatory"
    found: dict[str, tuple[str, str]] = {}
    for line in lines:
        low = line.lower()
        if re.search(r"nice to have|preferred|bonus|good to have|plus|desirable", low):
            section = "preferred"
        elif re.search(r"requirements|qualifications|must have|what you'll need|you have|you bring", low):
            section = "mandatory"
        for skill in find_skills(line):
            if skill not in found or (found[skill][0] == "preferred" and section == "mandatory"):
                found[skill] = (section, line.strip(" •-")[:200])
    return [(s, t, ctx) for s, (t, ctx) in found.items()]


def _years(description: str) -> float:
    m = re.search(r"(\d{1,2})\+?\s*(?:-\s*\d{1,2}\s*)?years", description, re.I)
    return float(m.group(1)) if m else 0.0


def _education(description: str) -> tuple[str | None, bool]:
    m = re.search(r"([^.\n]*(?:bachelor|master|degree|b\.?tech|b\.?e\.)[^.\n]*)", description, re.I)
    if not m:
        return None, False
    text = m.group(1).strip(" •-")[:200]
    mandatory = not re.search(r"or equivalent|preferred|nice to have", text, re.I)
    return text, mandatory


def upsert_job(db: Session, skills: dict[str, Skill], *, company: str, careers_url: str | None, source: str,
               external_id: str, title: str, location: str, work_mode: str, job_type: str, team: str | None,
               description: str, source_url: str | None) -> Job:
    now = datetime.now(timezone.utc)
    job = db.scalar(select(Job).where(Job.source == source, Job.external_id == external_id))
    years = _years(description)
    edu, edu_mand = _education(description)
    if job is None:
        job = Job(source=source, external_id=external_id,
                  company_id=_company(db, company, False, careers_url).id)
        db.add(job)
    job.title, job.team, job.location, job.work_mode, job.job_type = title, team, location, work_mode, job_type
    job.role_family = infer_role_family(title)
    job.seniority = infer_seniority(title, years)
    job.experience_min_years = years
    job.education_requirement, job.education_mandatory = edu, edu_mand
    job.description = description[:6000]
    job.source_url = source_url
    job.listing_type = "live_vacancy"
    job.status = "open"
    job.last_verified_at = now
    job.requirements.clear()
    for skill, rtype, ctx in infer_requirements(description):
        job.requirements.append(JobRequirement(skill_id=skills[skill].id, requirement_type=rtype, description=ctx))
    return job


def _work_mode(text: str) -> str:
    t = (text or "").lower()
    if "remote" in t:
        return "remote"
    if "hybrid" in t:
        return "hybrid"
    return "onsite"


def sync_greenhouse(db: Session, board: str, client: httpx.Client) -> int:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    resp = client.get(url, params={"content": "true"}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    skills = ensure_skills(db)
    seen = set()
    for item in data.get("jobs", []):
        desc = _plain(item.get("content", ""))
        location = (item.get("location") or {}).get("name", "")
        seen.add(str(item["id"]))
        upsert_job(
            db, skills, company=board.replace("-", " ").title(), careers_url=f"https://boards.greenhouse.io/{board}",
            source=f"Greenhouse:{board}", external_id=str(item["id"]), title=item.get("title", ""),
            location=location, work_mode=_work_mode(location + " " + desc[:400]), job_type="full-time",
            team=", ".join(d.get("name", "") for d in item.get("departments", [])) or None,
            description=desc, source_url=item.get("absolute_url"),
        )
    _close_missing(db, f"Greenhouse:{board}", seen)
    db.commit()
    return len(seen)


def sync_lever(db: Session, company: str, client: httpx.Client) -> int:
    url = f"https://api.lever.co/v0/postings/{company}"
    resp = client.get(url, params={"mode": "json"}, timeout=20)
    resp.raise_for_status()
    skills = ensure_skills(db)
    seen = set()
    for item in resp.json():
        cats = item.get("categories") or {}
        lists = "\n".join(f"{lst.get('text', '')}\n{_plain(lst.get('content', ''))}" for lst in item.get("lists", []))
        desc = (item.get("descriptionPlain") or "") + "\n" + lists
        seen.add(item["id"])
        commitment = (cats.get("commitment") or "").lower()
        upsert_job(
            db, skills, company=company.replace("-", " ").title(), careers_url=f"https://jobs.lever.co/{company}",
            source=f"Lever:{company}", external_id=item["id"], title=item.get("text", ""),
            location=cats.get("location", ""), work_mode=item.get("workplaceType") or _work_mode(cats.get("location", "")),
            job_type="internship" if "intern" in commitment else "contract" if "contract" in commitment else "full-time",
            team=cats.get("team"), description=desc, source_url=item.get("hostedUrl"),
        )
    _close_missing(db, f"Lever:{company}", seen)
    db.commit()
    return len(seen)


def _close_missing(db: Session, source: str, seen: set[str]) -> None:
    for job in db.scalars(select(Job).where(Job.source == source, Job.status == "open")):
        if job.external_id not in seen:
            job.status = "closed"
            job.last_verified_at = datetime.now(timezone.utc)


def sync_all(db: Session, greenhouse: list[str], lever: list[str], client: httpx.Client | None = None) -> dict:
    client = client or httpx.Client(headers={"User-Agent": "Roppo job sync"})
    results = {}
    for board in greenhouse:
        try:
            results[f"greenhouse:{board}"] = sync_greenhouse(db, board, client)
        except httpx.HTTPError as exc:
            db.rollback()
            log.warning("Greenhouse sync failed for %s: %s", board, exc)
            results[f"greenhouse:{board}"] = f"error: {exc.__class__.__name__}"
    for company in lever:
        try:
            results[f"lever:{company}"] = sync_lever(db, company, client)
        except httpx.HTTPError as exc:
            db.rollback()
            log.warning("Lever sync failed for %s: %s", company, exc)
            results[f"lever:{company}"] = f"error: {exc.__class__.__name__}"
    return results
