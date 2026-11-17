"""Render a resume version (structured profile snapshot) as DOCX or plain text."""

import io

from docx import Document
from docx.shared import Pt


def _lines(profile: dict) -> list[tuple[str, str]]:
    """Return [(kind, text)] where kind is title|subtitle|heading|entry|bullet|text."""
    c = profile.get("contact", {})
    out: list[tuple[str, str]] = []
    if c.get("name"):
        out.append(("title", c["name"]))
    if c.get("headline"):
        out.append(("subtitle", c["headline"]))
    contact = " | ".join(x for x in [c.get("location"), c.get("email"), c.get("phone"), c.get("linkedin"), c.get("github")] if x)
    if contact:
        out.append(("text", contact))
    if profile.get("summary"):
        out += [("heading", "Summary"), ("text", profile["summary"])]
    if profile.get("education"):
        out.append(("heading", "Education"))
        for e in profile["education"]:
            line = ", ".join(x for x in [e.get("degree"), e.get("institution")] if x)
            tail = " | ".join(x for x in [" – ".join(y for y in [e.get("start"), e.get("end")] if y), e.get("grade")] if x)
            out.append(("entry", line + (f" | {tail}" if tail else "")))
    for key, label in (("experience", "Experience"), ("projects", "Projects")):
        if profile.get(key):
            out.append(("heading", label))
            for item in profile[key]:
                if key == "experience":
                    head = " | ".join(x for x in [item.get("title"), item.get("organization"),
                                                  " – ".join(y for y in [item.get("start"), item.get("end")] if y)] if x)
                else:
                    head = " | ".join(x for x in [item.get("name"), item.get("technologies"), item.get("link")] if x)
                out.append(("entry", head))
                out += [("bullet", b) for b in item.get("bullets", [])]
    if profile.get("skills"):
        names = [s.get("name") if isinstance(s, dict) else s for s in profile["skills"]]
        out += [("heading", "Skills"), ("text", ", ".join(n for n in names if n))]
    for key, label in (("certifications", "Certifications"), ("achievements", "Achievements")):
        if profile.get(key):
            out.append(("heading", label))
            out += [("bullet", x if isinstance(x, str) else x.get("name", "")) for x in profile[key]]
    return out


def to_text(profile: dict) -> str:
    rows = []
    for kind, text in _lines(profile):
        if kind == "heading":
            rows += ["", text.upper()]
        elif kind == "bullet":
            rows.append(f"• {text}")
        else:
            rows.append(text)
    return "\n".join(rows).strip() + "\n"


def to_docx(profile: dict) -> bytes:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    for kind, text in _lines(profile):
        if kind == "title":
            doc.add_heading(text, level=0)
        elif kind == "subtitle":
            doc.add_paragraph(text).runs[0].italic = True
        elif kind == "heading":
            doc.add_heading(text, level=1)
        elif kind == "entry":
            doc.add_paragraph().add_run(text).bold = True
        elif kind == "bullet":
            doc.add_paragraph(text, style="List Bullet")
        else:
            doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
