"""Document validation and text extraction for PDF and DOCX resumes.

Files are validated by size, extension AND content signature (magic bytes / DOCX zip
structure). Uploaded content is only ever read as data — it is never executed.
"""

import io
import zipfile
from dataclasses import dataclass

import pymupdf as fitz  # PyMuPDF
from docx import Document

ALLOWED_TYPES = {"pdf", "docx"}


class DocumentError(ValueError):
    """Raised for files that fail validation or cannot be parsed."""


@dataclass
class ExtractedDocument:
    text: str
    file_type: str
    page_count: int
    warnings: list[str]


def detect_file_type(filename: str, content: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_TYPES:
        raise DocumentError("Only PDF and DOCX resumes are supported.")
    if ext == "pdf":
        if not content.startswith(b"%PDF-"):
            raise DocumentError("The file does not look like a valid PDF.")
        return "pdf"
    # DOCX is a zip container with a word/document.xml part.
    if not content.startswith(b"PK"):
        raise DocumentError("The file does not look like a valid DOCX document.")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if "word/document.xml" not in names:
                raise DocumentError("The DOCX file is missing its document body.")
            if any(n.lower().endswith("vbaproject.bin") for n in names):
                raise DocumentError("Macro-enabled documents are not accepted.")
            total = sum(i.file_size for i in zf.infolist())
            if total > 50 * 1024 * 1024:  # zip-bomb guard
                raise DocumentError("The DOCX file expands to an unexpectedly large size.")
    except zipfile.BadZipFile as exc:
        raise DocumentError("The DOCX file is corrupted.") from exc
    return "docx"


def validate_upload(filename: str, content: bytes, max_mb: int) -> str:
    if not content:
        raise DocumentError("The uploaded file is empty.")
    if len(content) > max_mb * 1024 * 1024:
        raise DocumentError(f"Files must be {max_mb} MB or smaller.")
    return detect_file_type(filename, content)


def _extract_pdf(content: bytes) -> ExtractedDocument:
    warnings: list[str] = []
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises several exception types
        raise DocumentError("The PDF could not be opened.") from exc
    if doc.needs_pass:
        raise DocumentError("Password-protected PDFs are not supported.")
    pages = []
    for page in doc:
        # sort=True gives natural reading order for multi-column layouts.
        pages.append(page.get_text("text", sort=True))
    page_count = doc.page_count
    doc.close()
    text = "\n".join(pages)
    if len(text.strip()) < 50:
        warnings.append(
            "Very little text could be extracted. The PDF may be a scanned image; "
            "please upload a text-based PDF or DOCX for accurate results."
        )
    return ExtractedDocument(text=text, file_type="pdf", page_count=page_count, warnings=warnings)


def _extract_docx(content: bytes) -> ExtractedDocument:
    try:
        document = Document(io.BytesIO(content))
    except Exception as exc:
        raise DocumentError("The DOCX file could not be read.") from exc
    lines: list[str] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            lines.append("")
            continue
        style = (para.style.name or "").lower() if para.style is not None else ""
        if "list" in style and not text.startswith(("•", "-", "*")):
            text = f"• {text}"
        lines.append(text)
    # Tables are common in resume templates (e.g. skills grids).
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                lines.append(" | ".join(dict.fromkeys(cells)))
    text = "\n".join(lines)
    warnings = []
    if len(text.strip()) < 50:
        warnings.append("Very little text could be extracted from this document.")
    # Rough page estimate (~500 words per page) for length feedback.
    page_count = max(1, round(len(text.split()) / 500))
    return ExtractedDocument(text=text, file_type="docx", page_count=page_count, warnings=warnings)


def extract_text(file_type: str, content: bytes) -> ExtractedDocument:
    if file_type == "pdf":
        return _extract_pdf(content)
    if file_type == "docx":
        return _extract_docx(content)
    raise DocumentError("Unsupported file type.")
