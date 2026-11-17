"""Initial analysis report (concept doc, section 4).

Produces: resume overview, strengths, skill coverage, content quality, potential gaps and
improvement actions, plus a resume-quality indicator whose factors are fully explained.

The score is a configurable resume-quality indicator — not a measure of a person's worth
or a prediction of hiring success.
"""

from collections import Counter

from app.data.skills import SKILL_INDEX
from app.services.extraction import summarize_education, summarize_experience, total_experience_months
from app.services.improvement import (
    FIRST_PERSON_RE,
    METRIC_RE,
    bullet_suggestions,
    formatting_feedback,
    is_action_led,
    project_suggestions,
    summary_suggestion,
)
from app.services.skills import build_skill_evidence

# Configurable weights for the resume-quality indicator (sum to 100).
QUALITY_WEIGHTS: dict[str, int] = {
    "completeness": 20,
    "skill_evidence": 20,
    "measurable_outcomes": 20,
    "action_language": 15,
    "clarity": 15,
    "contact_and_links": 10,
}

SCORE_DISCLAIMER = (
    "This is a resume-quality indicator based on the factors below. It is not a measure of "
    "your worth or a prediction of hiring success, and it should not be used for automated "
    "hiring decisions."
)


def _all_bullets(profile: dict) -> list[str]:
    return [b for sec in ("experience", "projects") for item in profile.get(sec, []) for b in item.get("bullets", [])]


def quality_score(profile: dict, evidence: dict) -> dict:
    bullets = _all_bullets(profile)
    contact = profile.get("contact", {})

    sections = {
        "contact": bool(contact.get("email") or contact.get("phone")),
        "education": bool(profile.get("education")),
        "skills": bool(profile.get("skills")),
        "experience_or_projects": bool(profile.get("experience") or profile.get("projects")),
        "summary": bool(profile.get("summary")),
    }
    completeness = sum(sections.values()) / len(sections)

    if evidence:
        backed = [s for s, e in evidence.items() if set(e["sections"]) & {"experience", "projects", "certifications"}]
        skill_evidence = len(backed) / len(evidence)
    else:
        backed, skill_evidence = [], 0.0

    with_metrics = [b for b in bullets if METRIC_RE.search(b)]
    measurable = min(1.0, (len(with_metrics) / len(bullets)) / 0.5) if bullets else 0.0  # 50%+ bullets = full marks

    action_led = [b for b in bullets if is_action_led(b)]
    action = len(action_led) / len(bullets) if bullets else 0.0

    good_length = [b for b in bullets if 8 <= len(b.split()) <= 35 and not FIRST_PERSON_RE.search(b)]
    clarity = len(good_length) / len(bullets) if bullets else 0.0

    contact_score = sum([bool(contact.get("email")), bool(contact.get("phone")),
                         bool(contact.get("linkedin") or contact.get("github"))]) / 3

    factors = {
        "completeness": (completeness, f"{sum(sections.values())} of {len(sections)} core sections present"
                         + (f" (missing: {', '.join(k.replace('_', ' ') for k, v in sections.items() if not v)})"
                            if not all(sections.values()) else "")),
        "skill_evidence": (skill_evidence, f"{len(backed)} of {len(evidence)} skills are backed by experience, "
                           "projects or certifications"),
        "measurable_outcomes": (measurable, f"{len(with_metrics)} of {len(bullets)} bullets include a measurable result"),
        "action_language": (action, f"{len(action_led)} of {len(bullets)} bullets start with an action verb"),
        "clarity": (clarity, f"{len(good_length)} of {len(bullets)} bullets are a readable length without first-person pronouns"),
        "contact_and_links": (contact_score, "Email, phone and a LinkedIn/GitHub link"),
    }
    total = round(sum(QUALITY_WEIGHTS[k] * v for k, (v, _) in factors.items()))
    return {
        "score": total,
        "label": "Resume-quality indicator",
        "disclaimer": SCORE_DISCLAIMER,
        "factors": [
            {"key": k, "weight": QUALITY_WEIGHTS[k], "value": round(v * 100), "points": round(QUALITY_WEIGHTS[k] * v, 1),
             "explanation": why}
            for k, (v, why) in factors.items()
        ],
    }


def content_quality(profile: dict) -> list[dict]:
    bullets = _all_bullets(profile)
    n = len(bullets) or 1
    vague = [b for b in bullets if len(b.split()) < 6]
    tech_named = [b for b in bullets if any(s in b for s in SKILL_INDEX)]
    return [
        {"aspect": "Clarity", "rating": _rate(sum(8 <= len(b.split()) <= 35 for b in bullets) / n),
         "detail": f"{len(vague)} very short bullet(s); {sum(len(b.split()) > 35 for b in bullets)} overly long."},
        {"aspect": "Structure", "rating": _rate(len(profile.get("sections_found", [])) / 6),
         "detail": "Sections detected: " + (", ".join(profile.get("sections_found", [])) or "none")},
        {"aspect": "Specificity", "rating": _rate(len(tech_named) / n),
         "detail": f"{len(tech_named)} of {len(bullets)} bullets name a specific tool or technology."},
        {"aspect": "Measurable outcomes", "rating": _rate(sum(bool(METRIC_RE.search(b)) for b in bullets) / n / 0.5),
         "detail": f"{sum(bool(METRIC_RE.search(b)) for b in bullets)} of {len(bullets)} bullets quantify a result."},
    ]


def _rate(x: float) -> str:
    return "Strong" if x >= 0.7 else "Fair" if x >= 0.4 else "Needs work"


def strengths(profile: dict, evidence: dict) -> list[str]:
    out = []
    top = sorted(((s, e) for s, e in evidence.items() if e["strength"] >= 0.9), key=lambda kv: (-kv[1]["strength"], kv[0]))
    for skill, e in top[:5]:
        where = ", ".join(e["sections"][:2])
        out.append(f"{skill} — evidenced in {where}")
    metrics = [b for b in _all_bullets(profile) if METRIC_RE.search(b)]
    if metrics:
        out.append(f"Quantified impact: “{metrics[0][:120]}”")
    for c in profile.get("certifications", [])[:2]:
        out.append(f"Certification: {c if isinstance(c, str) else c.get('name')}")
    for a in profile.get("achievements", [])[:2]:
        out.append(f"Achievement: {a}")
    return out


def skill_coverage(profile: dict, evidence: dict) -> dict:
    rows = []
    for skill, e in sorted(evidence.items(), key=lambda kv: (-kv[1]["strength"], kv[0])):
        sdef = SKILL_INDEX.get(skill)
        rows.append({
            "skill": skill,
            "category": sdef.category if sdef else "other",
            "strength": e["strength"],
            "sections": e["sections"],
            "evidence": e["evidence"],
            "listed_only": e["sections"] == ["skills"],
        })
    recognised = {r["skill"].lower() for r in rows}
    unrecognised = []
    for s in profile.get("skills", []):
        name = s.get("name") if isinstance(s, dict) else s
        if name and name.lower() not in recognised and not any(name.lower() in r.lower() for r in recognised):
            unrecognised.append(name)
    return {"skills": rows, "unrecognised": unrecognised}


def potential_gaps(evidence: dict, jobs: list[dict], target_role: str | None) -> dict:
    """Requirements common in the target role family that the resume doesn't evidence."""
    pool = [j for j in jobs if not target_role or j["role_family"] == target_role]
    if not pool:
        return {"role": target_role, "gaps": [], "jobs_considered": 0}
    counts: Counter = Counter()
    mandatory_counts: Counter = Counter()
    for j in pool:
        for r in j["requirements"]:
            if r["skill"] not in evidence:
                counts[r["skill"]] += 1
                if r["type"] == "mandatory":
                    mandatory_counts[r["skill"]] += 1
    gaps = [
        {"skill": s, "share": round(100 * c / len(pool)), "mandatory_in": mandatory_counts[s], "jobs": c}
        for s, c in counts.most_common(8)
    ]
    return {"role": target_role or "all roles in the job set", "gaps": gaps, "jobs_considered": len(pool)}


def overview(profile: dict) -> str:
    contact = profile.get("contact", {})
    parts = []
    name = contact.get("name") or "This candidate"
    edu = summarize_education(profile)
    exp = summarize_experience(profile)
    parts.append(f"{name}{' — ' + contact['headline'] if contact.get('headline') else ''}.")
    if edu:
        parts.append(f"Highest qualification: {edu}.")
    if exp:
        parts.append(exp[0].upper() + exp[1:] + ".")
    n_skills = len(profile.get("skills", []))
    if n_skills:
        parts.append(f"{n_skills} skills listed.")
    return " ".join(parts)


def build_report(profile: dict, text: str, page_count: int, jobs: list[dict], target_role: str | None,
                 warnings: list[str] | None = None) -> tuple[dict, list[dict]]:
    """Return (report, suggestions)."""
    evidence = build_skill_evidence(profile)
    suggestions = []
    summary = summary_suggestion(profile, target_role)
    if summary:
        suggestions.append(summary)
    suggestions += bullet_suggestions(profile)
    suggestions += project_suggestions(profile)
    suggestions += formatting_feedback(profile, text, page_count, warnings)

    report = {
        "overview": overview(profile),
        "strengths": strengths(profile, evidence),
        "skill_coverage": skill_coverage(profile, evidence),
        "content_quality": content_quality(profile),
        "potential_gaps": potential_gaps(evidence, jobs, target_role),
        "experience_months": total_experience_months(profile.get("experience", [])),
        "quality": quality_score(profile, evidence),
    }
    return report, suggestions
