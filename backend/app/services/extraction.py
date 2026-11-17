"""Turn raw resume text into a structured, editable candidate profile.

This is a transparent, rules-based parser: section headings are detected, then each
section is segmented into entries. Parsing is never perfect, so the result is always
shown to the user for review and correction before it is used for matching.
"""

import re
from datetime import date

from app.services.skills import find_skills

SECTION_HEADINGS: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "professional summary", "profile", "career objective", "objective", "about me",
                "professional profile", "career summary", "about"),
    "education": ("education", "academic background", "academics", "educational qualifications",
                  "qualifications", "academic qualifications", "education and training"),
    "experience": ("experience", "work experience", "professional experience", "employment history",
                   "employment", "internships", "internship", "work history", "internship experience",
                   "relevant experience", "industry experience"),
    "projects": ("projects", "academic projects", "personal projects", "key projects", "project work",
                 "selected projects", "technical projects"),
    "skills": ("skills", "technical skills", "key skills", "core competencies", "technologies",
               "skills and tools", "tools and technologies", "technical proficiency", "competencies", "tech stack"),
    "certifications": ("certifications", "certificates", "licenses and certifications", "courses",
                       "certifications and courses", "training", "online courses"),
    "achievements": ("achievements", "awards", "honors", "honours", "awards and achievements",
                     "accomplishments", "extracurricular activities", "extracurriculars", "activities",
                     "leadership", "positions of responsibility", "volunteering", "publications"),
    "other": ("languages", "interests", "hobbies", "references", "declaration", "personal details"),
}
_HEADING_LOOKUP = {h: sec for sec, hs in SECTION_HEADINGS.items() for h in hs}

BULLET_RE = re.compile(r"^\s*(?:[•\-\*▪●◦‣∙·➢►✓o]\s+|\d+[.)]\s+)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{3,5}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-%/]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", re.I)
URL_RE = re.compile(r"https?://\S+")

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_POINT = rf"(?:{_MONTH}\.?\s*,?\s*\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}})"
_PRESENT = r"(?:present|current|now|ongoing|till date|to date)"
DATE_RANGE_RE = re.compile(
    rf"(?P<start>{_POINT})\s*(?:-|–|—|‒|−|‐|·|~|to|until|till)\s*(?P<end>{_POINT}|{_PRESENT})", re.I)
SINGLE_YEAR_RE = re.compile(r"\b(19[89]\d|20\d\d)\b")

# (case-insensitive pattern, case-sensitive pattern for short ambiguous forms, level, label)
DEGREE_PATTERNS: list[tuple[str, str | None, int, str]] = [
    (r"\bph\.?\s?d\b|\bdoctor(?:ate)? of", None, 5, "Doctorate"),
    (r"\bm\.?\s?tech\b|\bm\.?\s?sc\b|\bmaster'?s?\b|\bmba\b|\bmca\b|\bm\.?\s?com\b|\bpost\s?graduate",
     r"(?<![A-Za-z])M\.?\s?(?:E|S|A)(?:\.|(?![A-Za-z]))", 4, "Master's"),
    (r"\bb\.?\s?tech\b|\bb\.?\s?sc\b|\bbachelor'?s?\b|\bbca\b|\bb\.?\s?com\b|\bbba\b|\bundergraduate\b",
     r"(?<![A-Za-z])B\.?\s?(?:E|S|A)(?:\.|(?![A-Za-z]))", 3, "Bachelor's"),
    (r"\bdiploma\b|\bassociate'?s? degree\b", None, 2, "Diploma"),
    (r"\bhigh(?:er)? (?:school|secondary)\b|\bhsc\b|\bssc\b|\b12th\b|\b10th\b|\bclass xi?i?\b|\bsecondary school\b|\bcbse\b|\bicse\b",
     None, 1, "School"),
]
GRADE_RE = re.compile(r"(?:c?gpa|cpi|sgpa)\s*[:\-]?\s*(\d{1,2}(?:\.\d{1,2})?)(?:\s*/\s*(\d{1,2}(?:\.\d)?))?|(\d{2}(?:\.\d{1,2})?)\s*%", re.I)
ORG_HINT_RE = re.compile(
    r"\b(inc|ltd|llc|limited|pvt|corp|corporation|company|technologies|technology|solutions|labs|systems|"
    r"services|software|consulting|group|university|college|institute|school|bank|foundation|studio|gmbh)\b", re.I)
INTERNSHIP_RE = re.compile(r"\bintern(ship)?\b|\btrainee\b|\bapprentice", re.I)


# --------------------------------------------------------------------------- helpers
def _clean(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace("​", "")).strip()


def _strip_bullet(line: str) -> str:
    return BULLET_RE.sub("", line).strip()


def _heading_of(line: str) -> str | None:
    text = _clean(line).rstrip(":").strip().lower()
    text = re.sub(r"[^a-z &/]", "", text).replace("&", "and").strip()
    if not text or len(text.split()) > 5:
        return None
    return _HEADING_LOOKUP.get(text)


def _parse_point(token: str, is_end: bool) -> date | None:
    token = token.strip().lower().rstrip(".")
    if re.fullmatch(_PRESENT, token, re.I):
        return date.today()
    m = re.match(r"(\d{1,2})/(\d{4})", token)
    if m:
        return date(int(m.group(2)), max(1, min(12, int(m.group(1)))), 1)
    m = re.match(r"([a-z]+)\.?\s*,?\s*(\d{4})", token)
    if m:
        return date(int(m.group(2)), MONTHS.get(m.group(1)[:3], 1), 1)
    m = re.match(r"(\d{4})", token)
    if m:
        return date(int(m.group(1)), 12 if is_end else 1, 1)
    return None


def parse_date_range(text: str) -> tuple[str | None, str | None, int]:
    """Return (start_label, end_label, months) for the first date range in text."""
    m = DATE_RANGE_RE.search(text)
    if not m:
        return None, None, 0
    start, end = _parse_point(m.group("start"), False), _parse_point(m.group("end"), True)
    months = 0
    if start and end and end >= start:
        months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return m.group("start").strip(), m.group("end").strip(), months


def _split_sections(lines: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    header: list[str] = []
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in lines:
        heading = _heading_of(raw)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        if current is None:
            header.append(raw)
        else:
            sections[current].append(raw)
    return header, sections


def _group_entries(lines: list[str]) -> list[dict]:
    """Group lines into entries of {"header": [...], "bullets": [...]}.

    A non-bullet line after bullets starts a new entry; wrapped bullet lines that start
    in lower case are joined to the previous bullet.
    """
    entries: list[dict] = []
    cur = {"header": [], "bullets": []}
    for raw in lines:
        line = _clean(raw)
        if not line:
            if cur["bullets"]:
                entries.append(cur)
                cur = {"header": [], "bullets": []}
            continue
        if BULLET_RE.match(raw) or BULLET_RE.match(line):
            cur["bullets"].append(_strip_bullet(line))
        elif cur["bullets"] and (line[0].islower() or line[0] in ",;&(") :
            cur["bullets"][-1] += " " + line
        elif cur["bullets"] and len(line.split()) > 12 and not DATE_RANGE_RE.search(line):
            # long sentence-like line inside an entry: treat as a description bullet
            cur["bullets"].append(line)
        else:
            if cur["bullets"]:
                entries.append(cur)
                cur = {"header": [], "bullets": []}
            cur["header"].append(line)
    if cur["header"] or cur["bullets"]:
        entries.append(cur)
    # Entries with headers but no bullets and very long header lines: move to bullets.
    for e in entries:
        if not e["bullets"] and len(e["header"]) > 2:
            e["bullets"] = [h for h in e["header"][1:] if len(h.split()) > 6]
            e["header"] = [h for h in e["header"] if h not in e["bullets"]]
    return [e for e in entries if e["header"] or e["bullets"]]


def _split_title_org(text: str) -> tuple[str, str]:
    text = DATE_RANGE_RE.sub("", text)
    text = re.sub(r"\s*[|•·]\s*$", "", text).strip(" ,|-–—")
    parts = [p.strip(" ,|-–—") for p in re.split(r"\s+(?:at|@)\s+|\s*\|\s*|\s+[-–—]\s+|,\s+", text) if p.strip(" ,|-–—")]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    first, second = parts[0], parts[1]
    if ORG_HINT_RE.search(first) and not ORG_HINT_RE.search(second):
        first, second = second, first
    return first, second


# --------------------------------------------------------------------------- sections
def _parse_contact(header: list[str], full_text: str) -> dict:
    lines = [_clean(line) for line in header if _clean(line)]
    email = EMAIL_RE.search(full_text)
    linkedin = LINKEDIN_RE.search(full_text)
    github = GITHUB_RE.search(full_text)
    phone = None
    for line in lines[:8] or full_text.splitlines()[:8]:
        for m in PHONE_RE.finditer(line):
            digits = re.sub(r"\D", "", m.group())
            if 10 <= len(digits) <= 13 and not DATE_RANGE_RE.search(m.group()):
                phone = m.group().strip()
                break
        if phone:
            break
    name = ""
    for line in lines[:4]:
        if EMAIL_RE.search(line) or re.search(r"\d", line) or "http" in line.lower():
            continue
        words = line.replace(",", " ").split()
        if 1 < len(words) <= 5 and all(w[0].isupper() for w in words if w[0].isalpha()):
            name = line
            break
    headline = ""
    if name:
        idx = lines.index(name)
        for line in lines[idx + 1: idx + 3]:
            if not EMAIL_RE.search(line) and not re.search(r"\d{5,}", line) and len(line.split()) <= 10:
                headline = line
                break
    location = ""
    for line in lines[:6]:
        m = re.search(r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?,\s?[A-Z][a-zA-Z]+)\b", line)
        if m and not EMAIL_RE.search(m.group()):
            location = m.group(1)
            break
    return {
        "name": name,
        "email": email.group() if email else "",
        "phone": phone or "",
        "location": location,
        "linkedin": linkedin.group() if linkedin else "",
        "github": github.group() if github else "",
        "headline": headline,
    }


def degree_level(text: str) -> tuple[int, str]:
    for pattern, cs_pattern, level, label in DEGREE_PATTERNS:
        if re.search(pattern, text, re.I) or (cs_pattern and re.search(cs_pattern, text)):
            return level, label
    return 0, ""


def _parse_education(lines: list[str]) -> list[dict]:
    blocks: list[list[str]] = []
    cur: list[str] = []
    for raw in lines:
        line = _clean(_strip_bullet(raw))
        if not line:
            if cur:
                blocks.append(cur)
                cur = []
            continue
        if cur and degree_level(line)[0] and any(degree_level(c)[0] for c in cur):
            blocks.append(cur)
            cur = []
        cur.append(line)
    if cur:
        blocks.append(cur)

    out = []
    for block in blocks:
        joined = " ".join(block)
        level, label = degree_level(joined)
        degree_line = next((b for b in block if degree_level(b)[0]), block[0])
        institution = next((b for b in block if re.search(r"universit|college|institute|school|iit|nit|academy", b, re.I)), "")
        field = ""
        m = re.search(r"\b(?:in|of)\s+([A-Z][A-Za-z &]+?)(?:\s*[,|(\-–]|\s+\d|$)", degree_line)
        if m:
            field = m.group(1).strip()
        grade = ""
        g = GRADE_RE.search(joined)
        if g:
            grade = g.group(0).strip()
        start, end, _ = parse_date_range(joined)
        years = SINGLE_YEAR_RE.findall(joined)
        degree_text = DATE_RANGE_RE.sub("", degree_line).strip(" ,|-–")
        if institution == degree_line:
            parts = [p.strip() for p in re.split(r",|\||\s[-–—]\s", degree_text) if p.strip()]
            inst_parts = [p for p in parts if re.search(r"universit|college|institute|school|iit|nit|academy", p, re.I)]
            institution = inst_parts[0] if inst_parts else ""
            degree_text = next((p for p in parts if degree_level(p)[0]), parts[0] if parts else degree_text)
        degree_text = GRADE_RE.sub("", SINGLE_YEAR_RE.sub("", degree_text)).strip(" ,|-–")
        out.append({
            "degree": degree_text,
            "level": level,
            "level_label": label,
            "field": field,
            "institution": DATE_RANGE_RE.sub("", institution).strip(" ,|-–"),
            "start": start or "",
            "end": end or (years[-1] if years else ""),
            "grade": grade,
            "details": " ".join(b for b in block if b not in (degree_line, institution))[:300],
        })
    return out


def _parse_experience(lines: list[str]) -> list[dict]:
    out = []
    for entry in _group_entries(lines):
        header = " | ".join(entry["header"])
        start, end, months = parse_date_range(header + " " + " ".join(entry["bullets"][:1]))
        title, org = "", ""
        if entry["header"]:
            title, org = _split_title_org(entry["header"][0])
            if not org and len(entry["header"]) > 1:
                second_title, second_org = _split_title_org(entry["header"][1])
                org = second_title if second_title else second_org
        if not title and not entry["bullets"]:
            continue
        out.append({
            "title": title,
            "organization": org,
            "start": start or "",
            "end": end or "",
            "months": months,
            "type": "internship" if INTERNSHIP_RE.search(header) else "job",
            "bullets": entry["bullets"],
        })
    return out


def _parse_projects(lines: list[str]) -> list[dict]:
    out = []
    for entry in _group_entries(lines):
        header = " | ".join(entry["header"])
        name = entry["header"][0] if entry["header"] else (entry["bullets"][0][:60] if entry["bullets"] else "")
        tech = ""
        m = re.search(r"(?:tech(?:nologies)?|stack|tools|built with)\s*[:\-]\s*(.+)", header + " " + " ".join(entry["bullets"]), re.I)
        if m:
            tech = m.group(1).split(".")[0][:200]
        elif "|" in name:
            name, tech = name.split("|", 1)
        elif "(" in name and name.endswith(")"):
            name, tech = name.split("(", 1)
            tech = tech.rstrip(")")
        link = URL_RE.search(header)
        name = DATE_RANGE_RE.sub("", name)
        name = re.sub(r"(?:tech(?:nologies)?|stack|tools)\s*[:\-].*$", "", name, flags=re.I).strip(" ,|-–—:")
        bullets = [b for b in entry["bullets"] if not re.match(r"(?:tech(?:nologies)?|stack|tools)\s*[:\-]", b, re.I)]
        out.append({
            "name": name.strip(),
            "technologies": tech.strip(" ,|-–—:"),
            "link": link.group() if link else "",
            "bullets": bullets,
        })
    return [p for p in out if p["name"] or p["bullets"]]


def _parse_list(lines: list[str]) -> list[str]:
    items = []
    for raw in lines:
        line = _clean(_strip_bullet(raw))
        if line:
            items.append(line)
    return items


def _parse_skills(lines: list[str]) -> list[dict]:
    names: list[str] = []
    for raw in lines:
        line = _clean(_strip_bullet(raw))
        if not line:
            continue
        if ":" in line:  # "Languages: Java, Python"
            line = line.split(":", 1)[1]
        line = re.sub(r"\((?:basic|beginner|intermediate|advanced|familiar|learning)[^)]*\)", "", line, flags=re.I)
        for part in re.split(r"[,|;•·/]|\s{2,}|\band\b", line):
            part = part.strip(" .-–()")
            if part and len(part) <= 40:
                names.append(part)
    # Keep the user's own wording, de-duplicated case-insensitively.
    seen, out = set(), []
    for n in names:
        if n.lower() not in seen:
            seen.add(n.lower())
            out.append({"name": n, "source": "skills"})
    return out


# --------------------------------------------------------------------------- public API
def total_experience_months(experience: list[dict], include_internships: bool = True) -> int:
    """Months of experience, merging overlapping ranges is approximated by summing
    non-internship roles and counting internships at half weight."""
    total = 0.0
    for item in experience:
        months = item.get("months") or 0
        if item.get("type") == "internship":
            total += months * 0.5 if include_internships else 0
        else:
            total += months
    return int(total)


def extract_profile(text: str) -> dict:
    lines = text.splitlines()
    header, sections = _split_sections(lines)
    contact = _parse_contact(header, text)

    profile = {
        "contact": contact,
        "summary": " ".join(_parse_list(sections.get("summary", []))),
        "education": _parse_education(sections.get("education", [])),
        "experience": _parse_experience(sections.get("experience", [])),
        "projects": _parse_projects(sections.get("projects", [])),
        "skills": _parse_skills(sections.get("skills", [])),
        "certifications": _parse_list(sections.get("certifications", [])),
        "achievements": _parse_list(sections.get("achievements", [])),
        "sections_found": sorted(sections.keys()),
    }

    # If there is no explicit skills section, fall back to skills found anywhere.
    if not profile["skills"]:
        profile["skills"] = [{"name": s, "source": "skills"} for s in sorted(find_skills(text))]

    return profile


def summarize_education(profile: dict) -> str:
    edu = profile.get("education", [])
    if not edu:
        return ""
    best = max(edu, key=lambda e: e.get("level", 0))
    bits = [best.get("degree", "")]
    if best.get("institution"):
        bits.append(best["institution"])
    if best.get("end"):
        bits.append(str(best["end"]))
    return ", ".join(b for b in bits if b)


def _duration(months: int) -> str:
    if months >= 12:
        years = months / 12
        return f"~{years:.1f} year{'s' if years >= 1.05 else ''}"
    return f"{months} month{'s' if months != 1 else ''}"


def summarize_experience(profile: dict) -> str:
    exp = profile.get("experience", [])
    roles = [e.get("title") for e in exp if e.get("title")]
    parts = []
    job_months = sum(e.get("months") or 0 for e in exp if e.get("type") != "internship")
    intern_months = sum(e.get("months") or 0 for e in exp if e.get("type") == "internship")
    if job_months:
        parts.append(_duration(job_months) + " of work experience")
    if intern_months:
        parts.append(_duration(intern_months) + " of internship experience")
    if roles:
        parts.append("roles: " + ", ".join(roles[:3]))
    if profile.get("projects"):
        parts.append(f"{len(profile['projects'])} project(s)")
    return "; ".join(parts)
