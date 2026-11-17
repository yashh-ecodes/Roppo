"""Transparent, rules-based job matching.

Design principles (concept doc, section 11):
  * The score is an explainable compatibility indicator, not a hiring prediction.
  * Weights are configurable and documented (MATCH_WEIGHTS, docs/scoring.md).
  * Hard requirements (mandatory skills, mandatory education, minimum experience) are
    flagged separately and never hidden inside an average.
  * Evidence matters: a skill used in experience/projects counts more than a skills-list
    keyword.
  * Related skills are surfaced for the user to review, never counted as a match.
"""

from dataclasses import dataclass, field

from app.data.skills import SKILL_INDEX
from app.services.extraction import degree_level, total_experience_months
from app.services.skills import build_skill_evidence

# Configurable component weights (must sum to 1.0).
MATCH_WEIGHTS: dict[str, float] = {
    "skill_coverage": 0.45,  # share of required skills evidenced (mandatory weighted higher)
    "evidence_quality": 0.15,  # how strongly matched skills are evidenced
    "experience": 0.20,  # years vs. job minimum, plus relevant-role bonus
    "education": 0.10,  # stated education requirement
    "seniority": 0.10,  # candidate level vs. role level
}
MANDATORY_SHARE = 0.7  # within skill coverage: mandatory vs preferred
SENIORITY_ORDER = ["entry", "junior", "mid", "senior"]

BANDS = [
    (75, "Strong match"),
    (60, "Good match"),
    (40, "Partial match"),
    (0, "Stretch"),
]


@dataclass
class CandidateSnapshot:
    skills: dict[str, dict]  # skill -> {"strength", "sections", "evidence"}
    experience_months: int
    education_level: int
    titles: list[str]
    seniority: str
    preferences: dict = field(default_factory=dict)

    @property
    def years(self) -> float:
        return round(self.experience_months / 12, 1)


def seniority_for_months(months: int) -> str:
    years = months / 12
    if years < 1:
        return "entry"
    if years < 3:
        return "junior"
    if years < 6:
        return "mid"
    return "senior"


def snapshot_from_profile(profile: dict, preferences: dict | None = None) -> CandidateSnapshot:
    months = total_experience_months(profile.get("experience", []))
    levels = [e.get("level") or degree_level(e.get("degree", ""))[0] for e in profile.get("education", [])]
    return CandidateSnapshot(
        skills=build_skill_evidence(profile),
        experience_months=months,
        education_level=max(levels, default=0),
        titles=[e.get("title", "") for e in profile.get("experience", []) if e.get("title")],
        seniority=seniority_for_months(months),
        preferences=preferences or {},
    )


def with_added_skills(snap: CandidateSnapshot, skills: list[str], strength: float = 0.7) -> CandidateSnapshot:
    """Hypothetical snapshot used by Unlock Opportunities: 'what if I evidenced these skills?'"""
    new_skills = dict(snap.skills)
    for s in skills:
        if s not in new_skills:
            new_skills[s] = {"strength": strength, "sections": ["planned"], "evidence": []}
    return CandidateSnapshot(new_skills, snap.experience_months, snap.education_level, snap.titles,
                             snap.seniority, snap.preferences)


def band_for(score: float, mandatory_gaps: int) -> str:
    for threshold, label in BANDS:
        if score >= threshold:
            if label == "Strong match" and mandatory_gaps:
                return "Good match"
            return label
    return "Stretch"


def _related_evidence(skill: str, snap: CandidateSnapshot) -> list[str]:
    sdef = SKILL_INDEX.get(skill)
    related = set(sdef.related) if sdef else set()
    # Relations are symmetric for review purposes.
    for name, other in SKILL_INDEX.items():
        if skill in other.related:
            related.add(name)
    return sorted(r for r in related if r in snap.skills)


def score_job(snap: CandidateSnapshot, job: dict) -> dict:
    """Score one job. `job` is a plain dict (see job_to_dict) so this stays easy to test."""
    reqs = job.get("requirements", [])
    mandatory = [r for r in reqs if r["type"] == "mandatory"]
    preferred = [r for r in reqs if r["type"] == "preferred"]

    def evaluate(items):
        matched, missing = [], []
        for r in items:
            ev = snap.skills.get(r["skill"])
            if ev:
                matched.append({
                    "skill": r["skill"], "type": r["type"], "strength": ev["strength"],
                    "sections": ev["sections"], "listed_only": ev["sections"] == ["skills"],
                })
            else:
                missing.append({
                    "skill": r["skill"], "type": r["type"], "why": r.get("description", ""),
                    "related_you_have": _related_evidence(r["skill"], snap),
                })
        return matched, missing

    m_matched, m_missing = evaluate(mandatory)
    p_matched, p_missing = evaluate(preferred)

    # --- skill coverage
    m_cov = len(m_matched) / len(mandatory) if mandatory else 1.0
    p_cov = len(p_matched) / len(preferred) if preferred else 1.0
    skill_coverage = MANDATORY_SHARE * m_cov + (1 - MANDATORY_SHARE) * p_cov

    # --- evidence quality
    all_matched = m_matched + p_matched
    evidence_quality = (sum(m["strength"] for m in all_matched) / len(all_matched)) if all_matched else 0.0

    # --- experience
    required_years = float(job.get("experience_min_years") or 0)
    if required_years <= 0:
        experience = 1.0
    else:
        experience = min(1.0, snap.years / required_years)
    family = (job.get("role_family") or "").lower()
    family_words = {w for w in family.replace("-", " ").split() if w not in {"developer", "engineer"}}
    relevant_role = any(family_words & set(t.lower().replace("-", " ").split()) for t in snap.titles)
    if relevant_role and required_years > 0:
        experience = min(1.0, experience + 0.1)
    experience_ok = snap.years >= required_years or required_years <= 0

    # --- education
    req_text = job.get("education_requirement") or ""
    req_level = degree_level(req_text)[0] if req_text else 0
    if not req_level:
        education, education_ok = 1.0, True
    elif snap.education_level >= req_level:
        education, education_ok = 1.0, True
    elif snap.education_level == 0:
        education, education_ok = 0.5, None  # unknown: education not found in profile
    else:
        education, education_ok = 0.3, False

    # --- seniority
    try:
        gap = abs(SENIORITY_ORDER.index(snap.seniority) - SENIORITY_ORDER.index(job.get("seniority", "entry")))
    except ValueError:
        gap = 1
    seniority = {0: 1.0, 1: 0.6}.get(gap, 0.2)

    components = {
        "skill_coverage": skill_coverage,
        "evidence_quality": evidence_quality,
        "experience": experience,
        "education": education,
        "seniority": seniority,
    }
    score = round(100 * sum(MATCH_WEIGHTS[k] * v for k, v in components.items()), 1)

    hard_flags = []
    for m in m_missing:
        hard_flags.append(f"Mandatory skill not evidenced: {m['skill']}")
    if not experience_ok:
        hard_flags.append(f"Asks for {required_years:g}+ years of experience (profile shows ~{snap.years:g})")
    if job.get("education_mandatory") and education_ok is False:
        hard_flags.append(f"Education requirement: {req_text}")
    elif job.get("education_mandatory") and education_ok is None:
        hard_flags.append(f"Education requirement could not be verified from your profile: {req_text}")

    eligibility = []
    if req_text:
        eligibility.append(f"Education: {req_text}" + (" (mandatory)" if job.get("education_mandatory") else ""))
    eligibility.append(
        f"Experience: {required_years:g}+ years" if required_years > 0 else "Experience: open to freshers")
    eligibility.append(f"Level: {job.get('seniority', 'entry')}")

    result = {
        "score": score,
        "band": band_for(score, len(m_missing)),
        "components": {k: round(v * 100) for k, v in components.items()},
        "weights": MATCH_WEIGHTS,
        "mandatory": {"total": len(mandatory), "matched": len(m_matched)},
        "preferred": {"total": len(preferred), "matched": len(p_matched)},
        "matched_skills": all_matched,
        "missing_skills": m_missing + p_missing,
        "hard_requirement_flags": hard_flags,
        "meets_hard_requirements": not hard_flags,
        "eligibility_notes": eligibility,
    }
    result["explanation"] = explain(result, job)
    return result


def explain(result: dict, job: dict) -> str:
    parts = []
    m, p = result["mandatory"], result["preferred"]
    if m["total"]:
        parts.append(f"You evidence {m['matched']} of {m['total']} mandatory skills")
    if p["total"]:
        parts.append(f"{p['matched']} of {p['total']} preferred skills")
    sentence = (" and ".join(parts) + ".") if parts else ""
    missing_m = [x["skill"] for x in result["missing_skills"] if x["type"] == "mandatory"]
    if missing_m:
        sentence += f" Not yet evidenced (mandatory): {', '.join(missing_m)}."
    weak = [x["skill"] for x in result["matched_skills"] if x["listed_only"]]
    if weak:
        sentence += f" Only listed in your skills section (weaker evidence): {', '.join(weak)}."
    if result["components"]["experience"] < 100:
        sentence += " Experience is below the stated minimum."
    return sentence.strip()


def preference_fit(job: dict, prefs: dict) -> dict:
    """How a job fits the user's stated preferences (shown, and usable as a filter)."""
    notes = []
    locs = [loc.lower() for loc in prefs.get("locations", []) if loc]
    modes = prefs.get("work_modes", [])
    types = prefs.get("job_types", [])
    loc_ok = not locs or job.get("work_mode") == "remote" or any(loc in (job.get("location") or "").lower() for loc in locs)
    mode_ok = not modes or job.get("work_mode") in modes
    type_ok = not types or job.get("job_type") in types
    if not loc_ok:
        notes.append("Outside your preferred locations")
    if not mode_ok:
        notes.append("Different work arrangement from your preference")
    if not type_ok:
        notes.append("Different job type from your preference")
    return {"fits": loc_ok and mode_ok and type_ok, "notes": notes}


def job_to_dict(job) -> dict:
    """Convert a Job ORM object into the plain dict the engine expects."""
    return {
        "id": job.id,
        "title": job.title,
        "team": job.team,
        "role_family": job.role_family,
        "location": job.location,
        "work_mode": job.work_mode,
        "job_type": job.job_type,
        "seniority": job.seniority,
        "experience_min_years": job.experience_min_years,
        "education_requirement": job.education_requirement,
        "education_mandatory": job.education_mandatory,
        "requirements": [
            {"skill": r.skill.canonical_name, "type": r.requirement_type, "description": r.description}
            for r in job.requirements
        ],
    }
