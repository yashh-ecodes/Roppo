"""Rules-based resume improvement suggestions.

Every suggestion is grounded in the candidate's existing content. Where a rewrite would
benefit from a fact we don't have (a metric, a result), we insert a clearly marked
[placeholder] for the user to fill in — we never invent achievements, numbers, skills,
employers or qualifications.
"""

import re
from datetime import date

from app.services.skills import build_skill_evidence, find_skills

WEAK_OPENERS: list[tuple[str, str]] = [
    (r"^(?:i\s+)?(?:was\s+)?responsible\s+for\s+", ""),
    (r"^(?:i\s+)?worked\s+on\s+", "Developed "),
    (r"^(?:i\s+)?worked\s+with\s+", "Used "),
    (r"^(?:i\s+)?(?:was\s+)?involved\s+in\s+", "Contributed to "),
    (r"^(?:i\s+)?helped\s+(?:the\s+team\s+)?(?:to\s+|in\s+|with\s+)?", "Contributed to "),
    (r"^(?:i\s+)?assisted\s+(?:in|with)\s+", "Supported "),
    (r"^(?:i\s+)?participated\s+in\s+", "Contributed to "),
    (r"^(?:i\s+)?did\s+", "Completed "),
    (r"^(?:i\s+)?tasked\s+with\s+", ""),
    (r"^duties\s+included\s+", ""),
    (r"^(?:i\s+)?handled\s+", "Managed "),
]
IRREGULAR_PAST = {
    "building": "Built", "writing": "Wrote", "leading": "Led", "making": "Made", "running": "Ran",
    "teaching": "Taught", "taking": "Took", "doing": "Did", "setting": "Set", "getting": "Got",
    "bringing": "Brought", "drawing": "Drew", "giving": "Gave", "holding": "Held", "keeping": "Kept",
    "using": "Used", "managing": "Managed", "creating": "Created", "developing": "Developed",
    "designing": "Designed", "testing": "Tested", "coding": "Coded", "debugging": "Debugged",
    "planning": "Planned", "analysing": "Analysed", "analyzing": "Analyzed", "preparing": "Prepared",
}
ACTION_VERBS = {
    "achieved", "analysed", "analyzed", "architected", "automated", "built", "collaborated", "configured",
    "contributed", "created", "cut", "decreased", "delivered", "deployed", "designed", "developed",
    "drove", "engineered", "enhanced", "established", "evaluated", "executed", "implemented", "improved",
    "increased", "integrated", "introduced", "launched", "led", "maintained", "managed", "mentored",
    "migrated", "modelled", "modeled", "optimised", "optimized", "organised", "organized", "presented",
    "produced", "programmed", "published", "redesigned", "reduced", "refactored", "researched",
    "resolved", "scaled", "shipped", "simplified", "streamlined", "supported", "tested", "trained",
    "wrote", "coded", "debugged", "documented", "conducted", "coordinated", "prepared", "performed",
    "planned", "prototyped", "secured", "monitored", "visualised", "visualized", "won", "authored",
    "used", "completed", "set", "ran", "taught", "made", "owned", "partnered", "facilitated", "earned",
}
METRIC_RE = re.compile(r"\d|%|\b(?:percent|doubled|tripled|halved|x faster|users|customers|clients)\b", re.I)
FIRST_PERSON_RE = re.compile(r"\b(?:i|me|my|mine|myself)\b", re.I)
PLACEHOLDER = "[add a measurable result — e.g. time saved, % improvement, users or records handled]"


def _gerund_to_past(word: str) -> str:
    lw = word.lower()
    if lw in IRREGULAR_PAST:
        return IRREGULAR_PAST[lw]
    if lw.endswith("ing") and len(lw) > 5:
        stem = lw[:-3]
        if stem.endswith("at") or stem.endswith("iz") or stem.endswith("is") or stem.endswith("ur"):
            stem += "e"  # creating -> create, optimizing -> optimize
        past = stem + ("d" if stem.endswith("e") else "ed")
        return past.capitalize()
    return word.capitalize()


def first_word(text: str) -> str:
    m = re.match(r"[A-Za-z]+", text.strip())
    return m.group().lower() if m else ""


def is_action_led(bullet: str) -> bool:
    return first_word(bullet) in ACTION_VERBS


def improve_bullet(bullet: str) -> tuple[str, list[str]] | None:
    """Return (suggested_text, reasons) or None when the bullet is already strong."""
    text = bullet.strip().rstrip(".")
    reasons: list[str] = []
    new = text
    for pattern, replacement in WEAK_OPENERS:
        if re.match(pattern, new, re.I):
            rest = re.sub(pattern, "", new, count=1, flags=re.I)
            words = rest.split(" ", 1)
            if replacement == "" and words and words[0].lower().endswith("ing"):
                new = _gerund_to_past(words[0]) + (" " + words[1] if len(words) > 1 else "")
            elif replacement == "":
                new = "Managed " + rest
            elif replacement == "Contributed to " and words and not words[0].lower().endswith("ing"):
                # "Helped write X" -> "Contributed to writing X": keeps the shared ownership honest.
                verb = words[0].lower()
                if verb.isalpha() and verb not in {"the", "a", "an", "in", "with", "on", "my", "our"}:
                    gerund = (verb[:-1] if verb.endswith("e") and not verb.endswith("ee") else verb) + "ing"
                    new = "Contributed to " + gerund + (" " + words[1] if len(words) > 1 else "")
                else:
                    new = "Contributed to " + rest
            else:
                new = replacement + rest
            reasons.append("Starts with a passive or vague phrase; leading with a specific action verb is clearer.")
            break
    if FIRST_PERSON_RE.search(new):
        new = re.sub(r"^(?:i|we)\s+", "", new, flags=re.I)
        if FIRST_PERSON_RE.search(new):
            reasons.append("Avoid first-person pronouns in resume bullets.")
        else:
            reasons.append("Removed the first-person pronoun.")
    if not is_action_led(new) and not reasons:
        w = first_word(new)
        if w.endswith("ing") and len(w) > 5:
            rest = new.split(" ", 1)
            new = _gerund_to_past(rest[0]) + (" " + rest[1] if len(rest) > 1 else "")
            reasons.append("Use past-tense action verbs for completed work.")
    word_count = len(new.split())
    if word_count > 35:
        reasons.append(f"This bullet is {word_count} words long; aim for one idea in roughly 12–30 words.")
    if not METRIC_RE.search(new):
        new = f"{new} — {PLACEHOLDER}"
        reasons.append("No measurable outcome. If you know one, add it; if not, describe the result qualitatively.")
    if not reasons:
        return None
    new = new[0].upper() + new[1:]
    return new.rstrip(".") + ("" if new.endswith("]") else "."), reasons


def bullet_suggestions(profile: dict) -> list[dict]:
    out = []
    for section in ("experience", "projects"):
        for i, item in enumerate(profile.get(section, [])):
            label = item.get("title") or item.get("name") or f"{section[:-1]} {i + 1}"
            for j, bullet in enumerate(item.get("bullets", [])):
                result = improve_bullet(bullet)
                if not result:
                    continue
                suggested, reasons = result
                out.append({
                    "category": "bullet",
                    "title": f"Strengthen a bullet in “{label}”",
                    "target": {"section": section, "index": i, "bullet": j},
                    "original": bullet,
                    "suggested": suggested,
                    "rationale": " ".join(reasons),
                    "applicable": True,
                })
    return out


def summary_suggestion(profile: dict, target_role: str | None = None) -> dict | None:
    """Draft a concise summary strictly from verified profile details."""
    evidence = build_skill_evidence(profile)
    strong = [s for s, e in sorted(evidence.items(), key=lambda kv: (-kv[1]["strength"], kv[0]))
              if e["strength"] >= 0.75][:5]
    edu = max(profile.get("education", []), key=lambda e: e.get("level", 0), default=None)
    exp = profile.get("experience", [])
    projects = profile.get("projects", [])

    who = ""
    if edu and edu.get("level", 0) >= 3:
        field = f" in {edu['field']}" if edu.get("field") else ""
        end_year = re.search(r"\d{4}", str(edu.get("end", "")))
        finished = bool(end_year) and int(end_year.group()) <= date.today().year
        who = f"{edu.get('level_label', 'Degree')} {'graduate' if finished else 'student'}{field}"
    else:
        who = "Candidate"
    bits = [who]
    jobs = [e for e in exp if e.get("type") != "internship"]
    interns = [e for e in exp if e.get("type") == "internship"]
    if jobs:
        bits.append(f"with professional experience as {jobs[0].get('title') or 'a team member'}")
    elif interns:
        bits.append(f"with internship experience{(' at ' + interns[0]['organization']) if interns[0].get('organization') else ''}")
    sentence1 = " ".join(bits)
    if strong:
        sentence1 += f", with hands-on work in {', '.join(strong[:-1]) + ' and ' + strong[-1] if len(strong) > 1 else strong[0]}"
    sentence1 += "."
    sentence2 = ""
    if projects:
        sentence2 = f" Built {len(projects)} project{'s' if len(projects) > 1 else ''}, including {projects[0].get('name') or 'a personal project'}."
    goal = f" Seeking {target_role} roles." if target_role else " [Add the type of role you are targeting.]"
    draft = (sentence1 + sentence2 + goal).replace("  ", " ")
    current = profile.get("summary", "")
    return {
        "category": "summary",
        "title": "Professional summary" + (" (draft)" if not current else " (alternative draft)"),
        "target": {"section": "summary"},
        "original": current,
        "suggested": draft,
        "rationale": "Drafted only from details verified in your profile. Edit the wording so it sounds like you.",
        "applicable": True,
    }


def keyword_guidance(profile: dict, job_text: str, job_requirements: list[dict] | None = None) -> dict:
    """Compare a selected job description with the profile.

    Returns present / weak (listed only) / missing keywords. Missing keywords are guidance
    only: they should be added ONLY if the candidate genuinely has that experience.
    """
    evidence = build_skill_evidence(profile)
    if job_requirements:
        wanted = {r["skill"]: r["type"] for r in job_requirements}
    else:
        wanted = {}
        lowered = job_text.lower()
        for skill in find_skills(job_text):
            # Heuristic: requirement is mandatory when it appears near "required"/"must".
            idx = lowered.find(skill.lower())
            window = lowered[max(0, idx - 160): idx + 40] if idx >= 0 else ""
            wanted[skill] = "preferred" if re.search(r"nice to have|preferred|bonus|plus|good to have", window) else "mandatory"
    present, weak, missing = [], [], []
    for skill, rtype in sorted(wanted.items(), key=lambda kv: (kv[1] != "mandatory", kv[0])):
        ev = evidence.get(skill)
        row = {"skill": skill, "type": rtype}
        if not ev:
            missing.append(row)
        elif ev["sections"] == ["skills"]:
            weak.append({**row, "advice": f"Show where you used {skill} in a project or role bullet."})
        else:
            present.append({**row, "sections": ev["sections"]})
    return {
        "present": present,
        "weak": weak,
        "missing": missing,
        "note": "Only add a missing keyword if you have genuinely used it. Never list skills you don't have.",
    }


PROBLEM_RE = re.compile(r"\b(?:to|for|so that|allow|allows|allowing|enable|enables|help|helps|solve|problem|automate|track|manage)\b", re.I)
IMPLEMENT_RE = re.compile(r"\b(?:built|developed|implemented|designed|created|architected|engineered|wrote|integrated|trained|deployed)\b", re.I)
RESULT_RE = re.compile(r"\d|%|\b(?:users|reduced|improved|increased|deployed|live|adopted|won|award|accuracy|faster|saved)\b", re.I)


def project_suggestions(profile: dict) -> list[dict]:
    out = []
    for i, p in enumerate(profile.get("projects", [])):
        text = " ".join([p.get("name", ""), p.get("technologies", "")] + p.get("bullets", []))
        has = {
            "problem": bool(PROBLEM_RE.search(" ".join(p.get("bullets", [])))),
            "implementation": bool(IMPLEMENT_RE.search(text)),
            "technology": bool(p.get("technologies") or find_skills(text)),
            "result": bool(RESULT_RE.search(" ".join(p.get("bullets", [])))),
        }
        missing = [k for k, v in has.items() if not v]
        if not missing:
            continue
        tech = p.get("technologies") or ", ".join(sorted(find_skills(text))) or "[technologies used]"
        template = [
            f"Problem: {'[what problem or need did this project address, and for whom?]' if not has['problem'] else 'keep your current description'}",
            f"Implementation: {'[what you built and your role in it]' if not has['implementation'] else 'keep your current description'}",
            f"Technology: {tech}",
            f"Result: {'[outcome — e.g. users, accuracy, performance, deployment link]' if not has['result'] else 'keep your current result'}",
        ]
        out.append({
            "category": "project",
            "title": f"Present “{p.get('name') or 'project ' + str(i + 1)}” more completely",
            "target": {"section": "projects", "index": i},
            "original": "\n".join(p.get("bullets", [])),
            "suggested": "\n".join(template),
            "rationale": "Strong project entries cover the problem, implementation, technology and result. "
                         f"Missing: {', '.join(missing)}.",
            "applicable": False,
        })
    return out


DATE_STYLE_RES = {
    "Mon YYYY": re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}\b", re.I),
    "MM/YYYY": re.compile(r"\b\d{1,2}/\d{4}\b"),
}


def formatting_feedback(profile: dict, text: str, page_count: int, warnings: list[str] | None = None) -> list[dict]:
    """Flag readability/structure issues that can be detected reliably."""
    issues: list[tuple[str, str]] = []
    contact = profile.get("contact", {})
    words = len(text.split())
    months = sum(e.get("months", 0) for e in profile.get("experience", []))

    for w in warnings or []:
        issues.append(("Text extraction", w))
    if not contact.get("email"):
        issues.append(("Contact details", "No email address was found. Recruiters need a way to reach you."))
    if not contact.get("phone"):
        issues.append(("Contact details", "No phone number was found (optional, but commonly expected)."))
    if not contact.get("linkedin") and not contact.get("github"):
        issues.append(("Links", "Consider adding a LinkedIn or GitHub link so reviewers can verify your work."))
    for sec, label in (("education", "Education"), ("skills", "Skills")):
        if not profile.get(sec):
            issues.append(("Structure", f"No {label} section was detected. Use a clear “{label}” heading."))
    if not profile.get("experience") and not profile.get("projects"):
        issues.append(("Structure", "No Experience or Projects section was detected; add at least one with concrete bullets."))
    if words < 200:
        issues.append(("Length", f"The resume is short ({words} words). Add detail to projects and experience."))
    if page_count > 2 or (page_count > 1 and months < 36):
        issues.append(("Length", f"The resume is {page_count} pages. For under ~3 years of experience, one page is usually enough."))
    all_bullets = [b for sec in ("experience", "projects") for item in profile.get(sec, []) for b in item.get("bullets", [])]
    long_bullets = [b for b in all_bullets if len(b.split()) > 35]
    if long_bullets:
        issues.append(("Readability", f"{len(long_bullets)} bullet(s) are over 35 words. Split them into focused points."))
    for sec in ("experience", "projects"):
        for item in profile.get(sec, []):
            n = len(item.get("bullets", []))
            label = item.get("title") or item.get("name") or sec
            if n == 0:
                issues.append(("Structure", f"“{label}” has no bullet points describing what you did."))
            elif n > 7:
                issues.append(("Readability", f"“{label}” has {n} bullets; keep the 3–6 most relevant."))
    pronoun_bullets = [b for b in all_bullets if FIRST_PERSON_RE.search(b)]
    if pronoun_bullets:
        issues.append(("Tone", f"{len(pronoun_bullets)} bullet(s) use first-person pronouns (I/my)."))
    styles = [name for name, rx in DATE_STYLE_RES.items() if rx.search(text)]
    if len(styles) > 1:
        issues.append(("Consistency", "Dates use more than one format (e.g. “Jun 2024” and “06/2024”). Pick one."))
    caps_lines = [line for line in text.splitlines() if len(line.split()) > 6 and line.isupper()]
    if caps_lines:
        issues.append(("Readability", "Some long lines are in ALL CAPS, which is harder to read."))

    return [
        {
            "category": "formatting",
            "title": title,
            "target": {},
            "original": "",
            "suggested": detail,
            "rationale": "Detected automatically from the document structure.",
            "applicable": False,
        }
        for title, detail in issues
    ]
