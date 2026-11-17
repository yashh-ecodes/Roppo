import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

_tmp = tempfile.mkdtemp(prefix="roppo-tests-")
os.environ["ROPPO_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ROPPO_STORAGE_DIR"] = f"{_tmp}/storage"
os.environ["ROPPO_JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256-signing"
os.environ.pop("ANTHROPIC_API_KEY", None)  # tests never call an external LLM

SAMPLES = ROOT / "samples"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth(client):
    """Register a fresh user and return auth headers."""
    import uuid

    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={"name": "Test User", "email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def sample_bytes():
    def _read(name: str) -> bytes:
        return (SAMPLES / name).read_bytes()

    return _read


@pytest.fixture
def java_profile():
    from app.services.extraction import extract_profile
    from app.services.parsing import extract_text

    content = (SAMPLES / "aarav_mehta_java_fresher.docx").read_bytes()
    return extract_profile(extract_text("docx", content).text)
