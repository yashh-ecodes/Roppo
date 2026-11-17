"""Roppo API — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.routes import analysis, auth, career, jobs, resumes
from app.services import llm
from app.services.analysis import QUALITY_WEIGHTS
from app.services.jobsources import ensure_skills, seed_sample_jobs
from app.services.matching import MATCH_WEIGHTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.environment == "production" and settings.jwt_secret.startswith("dev-only"):
        raise RuntimeError("Set ROPPO_JWT_SECRET to a long random value in production.")
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    with SessionLocal() as db:
        ensure_skills(db)
        db.commit()
        if settings.seed_sample_jobs:
            seed_sample_jobs(db)
    yield


settings = get_settings()
app = FastAPI(
    title="Roppo API",
    description="AI-powered resume analyzer and career discovery platform. "
                "Your Skills Today. Your Opportunities Tomorrow.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, resumes, analysis, jobs, career):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/api/meta", tags=["meta"])
def meta():
    return {
        "app": settings.app_name,
        "llm_server_configured": llm.server_configured(),
        "match_weights": MATCH_WEIGHTS,
        "quality_weights": QUALITY_WEIGHTS,
        "freshness_days": settings.freshness_days,
        "max_upload_mb": settings.max_upload_mb,
        "demo_mode": settings.demo_mode,
    }


# Single-service deployment: serve the built React app (and its client-side routes) at "/".
_dist = settings.frontend_dist
if (_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        candidate = (_dist / path).resolve()
        if path and candidate.is_file() and _dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
