import io
import zipfile

import pytest

from app.services.parsing import DocumentError, extract_text, validate_upload


def test_rejects_unsupported_extension():
    with pytest.raises(DocumentError):
        validate_upload("resume.exe", b"MZ....", 5)


def test_rejects_renamed_binary_as_pdf():
    with pytest.raises(DocumentError, match="valid PDF"):
        validate_upload("resume.pdf", b"MZ\x90\x00not a pdf", 5)


def test_rejects_empty_and_oversized():
    with pytest.raises(DocumentError, match="empty"):
        validate_upload("resume.pdf", b"", 5)
    with pytest.raises(DocumentError, match="5 MB"):
        validate_upload("resume.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024), 5)


def test_rejects_docx_without_body_and_macros():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("hello.txt", "hi")
    with pytest.raises(DocumentError, match="document body"):
        validate_upload("resume.docx", buf.getvalue(), 5)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<xml/>")
        zf.writestr("word/vbaProject.bin", "macro")
    with pytest.raises(DocumentError, match="Macro"):
        validate_upload("resume.docx", buf.getvalue(), 5)


@pytest.mark.parametrize("name", ["aarav_mehta_java_fresher.pdf", "priya_nair_data_analyst.docx"])
def test_extracts_text_from_samples(sample_bytes, name):
    content = sample_bytes(name)
    kind = validate_upload(name, content, 5)
    doc = extract_text(kind, content)
    assert len(doc.text) > 200
    assert doc.page_count >= 1
    assert not doc.warnings
