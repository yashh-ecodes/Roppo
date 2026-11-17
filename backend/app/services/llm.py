"""Optional LLM layer (Claude via the Anthropic SDK).

Responsibilities are deliberately narrow (concept doc, sections 5, 11 and 16):
  * Explain and contextualise the matching engine's findings — never invent job
    requirements or decide a candidate's suitability.
  * Suggest clearer wording grounded in the candidate's actual content — never fabricate
    achievements, numbers, skills, employers or qualifications.
  * Only runs when the server has an API key AND the user has given explicit consent.
  * Contact details are removed before anything is sent.

Every LLM rewrite passes a grounding check; anything that introduces new numbers or new
skills is discarded and the rules-based suggestion is kept instead.
"""

import json
import logging
import os
import re

from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.skills import find_skills

log = logging.getLogger("roppo.llm")

SYSTEM_PROMPT = """You are the writing assistant inside Roppo, a career discovery tool.
You help candidates present their REAL experience more clearly. Hard rules:
- Use only facts present in the candidate profile you are given. Never invent achievements,
  metrics, numbers, skills, tools, employers, job titles, dates or qualifications.
- If a stronger bullet would need a fact you don't have (e.g. a metric), insert a short
  placeholder in square brackets, e.g. "[add % improvement]", for the candidate to fill in.
- Keep shared work honest: if the original says the candidate "helped" or "contributed", do not
  rewrite it as sole ownership.
- Do not judge whether the candidate is suitable for any job and do not predict hiring outcomes.
- Write in plain, professional English. No first-person pronouns in bullets."""


class BulletRewrite(BaseModel):
    id: str = Field(description="The id of the bullet being rewritten, copied exactly")
    suggested: str = Field(description="Improved bullet text grounded only in the original")
    rationale: str = Field(description="One short sentence on what changed and why")


class AnalysisEnhancement(BaseModel):
    overview: str = Field(description="2-3 sentence neutral overview of the candidate's profile")
    summary: str = Field(description="A concise professional summary built only from verified details")
    bullet_rewrites: list[BulletRewrite]


class MatchExplanation(BaseModel):
    explanation: str = Field(description="3-5 sentences explaining the engine's findings in plain language")
    next_steps: list[str] = Field(description="2-4 practical, honest next steps")


def available(user) -> bool:
    settings = get_settings()
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    return bool(settings.llm_enabled and has_key and getattr(user, "ai_consent", False))


def server_configured() -> bool:
    return bool(get_settings().llm_enabled and (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")))


def redact_profile(profile: dict) -> dict:
    """Remove contact details and links before sending anything to an external provider."""
    clean = {k: v for k, v in profile.items() if k not in {"contact", "sections_found"}}
    headline = (profile.get("contact") or {}).get("headline")
    if headline:
        clean["headline"] = headline
    text = json.dumps(clean)
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text)
    text = re.sub(r"https?://\S+|(?:www\.)?(?:linkedin|github)\.com/\S+", "[link]", text)
    return json.loads(text)


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def is_grounded(original: str, suggested: str, profile_skills: set[str]) -> bool:
    """Reject rewrites that add numbers or skills not present in the original/profile."""
    suggested_wo_placeholders = re.sub(r"\[[^\]]*\]", "", suggested)
    if _numbers(suggested_wo_placeholders) - _numbers(original):
        return False
    new_skills = find_skills(suggested_wo_placeholders) - find_skills(original) - profile_skills
    return not new_skills


def _call(user_content: str, schema):
    """One structured call. Returns a parsed model or None on any failure/refusal."""
    import anthropic

    settings = get_settings()
    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.parse(
            model=settings.llm_model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=schema,
            output_config={"effort": settings.llm_effort},
            # Server-side fallback if the primary model declines a request.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.RateLimitError:
        log.warning("LLM rate limited; using rules-based output")
        return None
    except anthropic.APIStatusError as exc:
        log.warning("LLM API error %s; using rules-based output", exc.status_code)
        return None
    except anthropic.APIConnectionError:
        log.warning("LLM connection error; using rules-based output")
        return None
    if response.stop_reason == "refusal":
        log.info("LLM declined the request; using rules-based output")
        return None
    return response.parsed_output


def enhance_analysis(profile: dict, suggestions: list[dict], target_role: str | None) -> dict | None:
    """Ask Claude for an overview, a summary and grounded bullet rewrites."""
    from app.services.skills import build_skill_evidence

    bullets = [s for s in suggestions if s["category"] == "bullet"][:15]
    payload = {
        "target_role": target_role,
        "profile": redact_profile(profile),
        "bullets_to_improve": [{"id": str(i), "original": s["original"]} for i, s in enumerate(bullets)],
    }
    content = (
        "Here is a candidate profile extracted from their resume (contact details removed) and the bullets "
        "our rules engine flagged for improvement. Return an overview, a professional summary and a "
        "rewrite for each bullet id.\n\n" + json.dumps(payload, indent=1)
    )
    result = _call(content, AnalysisEnhancement)
    if result is None:
        return None
    profile_skills = set(build_skill_evidence(profile))
    rewrites = {}
    for rw in result.bullet_rewrites:
        if not rw.id.isdigit() or int(rw.id) >= len(bullets):
            continue
        original = bullets[int(rw.id)]["original"]
        if is_grounded(original, rw.suggested, profile_skills):
            rewrites[int(rw.id)] = {"suggested": rw.suggested, "rationale": rw.rationale}
    summary_ok = is_grounded(json.dumps(redact_profile(profile)), result.summary, profile_skills)
    return {
        "overview": result.overview,
        "summary": result.summary if summary_ok else None,
        "bullet_rewrites": rewrites,
        "bullet_suggestions": bullets,
    }


def explain_match(profile: dict, job: dict, match: dict) -> dict | None:
    payload = {
        "job": {k: job.get(k) for k in ("title", "role_family", "seniority", "experience_min_years",
                                         "education_requirement", "requirements")},
        "engine_findings": {k: match[k] for k in ("score", "band", "components", "matched_skills", "missing_skills",
                                                  "hard_requirement_flags")},
        "profile": redact_profile(profile),
    }
    content = (
        "Explain these matching-engine findings to the candidate in plain language. Use only the findings "
        "and the job requirements given; do not add requirements or judge suitability.\n\n"
        + json.dumps(payload, indent=1)
    )
    result = _call(content, MatchExplanation)
    return result.model_dump() if result else None
