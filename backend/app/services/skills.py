"""Skill identification with evidence.

Finds taxonomy skills in text and records *where* they appear. Evidence strength follows
the concept doc's principle: a skill used in work experience or a project is stronger
evidence than a keyword appearing once in a skills list.
"""

import re
from functools import lru_cache

from app.data.skills import SKILL_INDEX, SKILLS, SkillDef

# How strongly each resume section evidences a skill.
EVIDENCE_WEIGHTS: dict[str, float] = {
    "experience": 1.0,
    "projects": 0.9,
    "certifications": 0.75,
    "roadmap": 0.7,  # completed roadmap step with attached evidence
    "education": 0.6,
    "achievements": 0.6,
    "summary": 0.5,
    "skills": 0.5,
    "manual": 0.5,
    "other": 0.4,
}


@lru_cache
def _compiled() -> list[tuple[SkillDef, list[tuple[re.Pattern, bool]]]]:
    out = []
    for skill in SKILLS:
        patterns = []
        for alias in skill.aliases or (skill.name.lower(),):
            skills_only = alias.startswith("^")
            case_sensitive = alias.startswith(("=", "^"))
            term = alias.lstrip("=^")
            # Word-ish boundaries that also work for terms like "c++", "c#", ".net", "ci/cd".
            pat = r"(?<![A-Za-z0-9+#])" + re.escape(term) + r"(?![A-Za-z0-9+#])"
            if term == "Go":  # avoid "Go-to-market", "Go live"
                pat = r"(?<![A-Za-z0-9+#])Go(?![A-Za-z0-9+#\-])(?!\s+(?:to|live|-))"
            flags = 0 if case_sensitive else re.IGNORECASE
            patterns.append((re.compile(pat, flags), skills_only))
        out.append((skill, patterns))
    return out


def find_skills(text: str, section: str = "other") -> set[str]:
    """Return canonical skill names found in a piece of text."""
    found: set[str] = set()
    if not text:
        return found
    for skill, patterns in _compiled():
        for pattern, skills_only in patterns:
            if skills_only and section != "skills":
                continue
            if pattern.search(text):
                found.add(skill.name)
                break
    return found


def canonical(name: str) -> str | None:
    """Resolve a user-typed skill name to its canonical taxonomy name (or None)."""
    name = name.strip()
    if not name:
        return None
    if name in SKILL_INDEX:
        return name
    lowered = name.lower()
    for skill in SKILLS:
        if skill.name.lower() == lowered:
            return skill.name
        for alias in skill.aliases:
            if alias.lstrip("=^").lower() == lowered:
                return skill.name
    return None


def skill_def(name: str) -> SkillDef | None:
    return SKILL_INDEX.get(name)


def build_skill_evidence(profile: dict) -> dict[str, dict]:
    """Map each skill to the places it is evidenced in a structured profile.

    Returns {skill: {"strength": float, "evidence": [{"section", "text"}], "sections": [...]}}
    Strength is the strongest single source plus a small bonus for corroboration.
    """
    evidence: dict[str, list[dict]] = {}

    def add(section: str, text: str, label: str | None = None):
        for name in find_skills(text, section):
            evidence.setdefault(name, []).append(
                {"section": section, "text": (label or text)[:220]}
            )

    for item in profile.get("experience", []):
        label = " — ".join(x for x in [item.get("title"), item.get("organization")] if x)
        add("experience", " ".join([item.get("title", "")] + item.get("bullets", [])), label or None)
    for item in profile.get("projects", []):
        add("projects", " ".join([item.get("name", ""), item.get("technologies", "")] + item.get("bullets", [])),
            item.get("name") or None)
    for item in profile.get("certifications", []):
        add("certifications", item if isinstance(item, str) else item.get("name", ""))
    for item in profile.get("education", []):
        add("education", " ".join([item.get("degree", ""), item.get("field", ""), item.get("details", "")]),
            item.get("degree") or None)
    for item in profile.get("achievements", []):
        add("achievements", item)
    add("summary", profile.get("summary", ""), "Professional summary")

    # Explicit skills list (and manually added skills) — weakest evidence on their own.
    for entry in profile.get("skills", []):
        name = entry.get("name") if isinstance(entry, dict) else entry
        source = entry.get("source", "skills") if isinstance(entry, dict) else "skills"
        canon = canonical(name) if name else None
        if canon:
            note = entry.get("evidence_note") if isinstance(entry, dict) else None
            evidence.setdefault(canon, []).append({"section": source, "text": note or "Listed in skills"})
        elif name:
            for found in find_skills(name, "skills"):
                evidence.setdefault(found, []).append({"section": "skills", "text": "Listed in skills"})

    result = {}
    for name, items in sorted(evidence.items()):
        sections = sorted({i["section"] for i in items}, key=lambda s: -EVIDENCE_WEIGHTS.get(s, 0.4))
        best = max(EVIDENCE_WEIGHTS.get(s, 0.4) for s in sections)
        bonus = 0.05 * (len(sections) - 1)
        result[name] = {
            "strength": round(min(1.0, best + bonus), 2),
            "evidence": items[:6],
            "sections": sections,
        }
    return result
