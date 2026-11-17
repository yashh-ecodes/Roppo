"""Unlock Opportunities — the forward-looking skill-gap engine (concept doc, section 7).

1. Compare the profile with a broad set of job descriptions.
2. Find recurring skills that are missing or not yet evidenced.
3. Group related skills into practical learning paths.
4. Estimate which roles may become a stronger match if those skills are evidenced
   (by re-scoring with a hypothetical profile — the same transparent engine).
5. Show companies with relevant roles, distinguishing live vacancies from illustrative ones.

Language is deliberately careful: skills "could improve your match" or "may open up
relevant roles". Nothing here guarantees eligibility or an offer.
"""

from collections import defaultdict

from app.data.skills import LEARNING_PATHS, SKILL_INDEX
from app.services.matching import CandidateSnapshot, score_job, with_added_skills

GOOD_MATCH = 60


def _skill_meta(skill: str) -> dict:
    sdef = SKILL_INDEX.get(skill)
    if not sdef:
        return {"category": "other", "role_families": [], "also_needed": "", "resource": None, "project_idea": ""}
    return {
        "category": sdef.category,
        "role_families": list(sdef.role_families),
        "also_needed": sdef.also_needed,
        "resource": {"title": sdef.resource[0], "url": sdef.resource[1]} if sdef.resource else None,
        "project_idea": sdef.project_idea or "",
    }


def analyse(snap: CandidateSnapshot, jobs: list[dict], interests: list[str] | None = None) -> dict:
    interests = [i for i in (interests or []) if i]
    pool = [j for j in jobs if not interests or j["role_family"] in interests] or jobs
    baseline = {j["id"]: score_job(snap, j) for j in pool}

    freq: dict[str, dict] = defaultdict(lambda: {"jobs": [], "mandatory_in": 0, "families": set()})
    for j in pool:
        for miss in baseline[j["id"]]["missing_skills"]:
            row = freq[miss["skill"]]
            row["jobs"].append(j["id"])
            row["families"].add(j["role_family"])
            if miss["type"] == "mandatory":
                row["mandatory_in"] += 1

    ranked = sorted(freq.items(), key=lambda kv: (-(kv[1]["mandatory_in"] * 2 + len(kv[1]["jobs"])), kv[0]))[:15]

    skills_out = []
    for skill, row in ranked:
        sim = with_added_skills(snap, [skill])
        gains, improved, unblocked, crossing = [], [], [], []
        for jid in row["jobs"]:
            job = next(j for j in pool if j["id"] == jid)
            before = baseline[jid]
            after = score_job(sim, job)
            gains.append(after["score"] - before["score"])
            if after["score"] > before["score"]:
                improved.append(jid)
            if before["mandatory"]["matched"] < before["mandatory"]["total"] and \
                    after["mandatory"]["matched"] == after["mandatory"]["total"]:
                unblocked.append(jid)
            if before["score"] < GOOD_MATCH <= after["score"]:
                crossing.append(jid)
        skills_out.append({
            "skill": skill,
            "appears_in_jobs": len(row["jobs"]),
            "mandatory_in": row["mandatory_in"],
            "role_families_in_jobs": sorted(row["families"]),
            "avg_score_gain": round(sum(gains) / len(gains), 1) if gains else 0,
            "jobs_improved": len(improved),
            "jobs_all_mandatory_met": unblocked,
            "jobs_reaching_good_match": crossing,
            **_skill_meta(skill),
        })

    # Learning paths: bundles of related missing skills.
    paths_out = []
    missing_all = set(freq)
    for path, skills in LEARNING_PATHS.items():
        missing = [s for s in skills if s in missing_all]
        have = [s for s in skills if s in snap.skills]
        if not missing:
            continue
        sim = with_added_skills(snap, missing)
        rescored = {j["id"]: score_job(sim, j) for j in pool}
        crossing = [jid for jid, r in rescored.items() if baseline[jid]["score"] < GOOD_MATCH <= r["score"]]
        families = sorted({j["role_family"] for j in pool if j["id"] in crossing})
        if not crossing and not have:
            continue
        paths_out.append({
            "path": path,
            "skills_you_have": have,
            "skills_to_build": missing,
            "jobs_reaching_good_match": len(crossing),
            "role_families": families,
        })
    paths_out.sort(key=lambda p: (-p["jobs_reaching_good_match"], -len(p["skills_you_have"])))

    # Role families: where you are now vs. after the top missing skills for that family.
    families: dict[str, list[dict]] = defaultdict(list)
    for j in pool:
        families[j["role_family"]].append(j)
    family_out = []
    for fam, fjobs in families.items():
        current = [baseline[j["id"]]["score"] for j in fjobs]
        fam_missing: dict[str, int] = defaultdict(int)
        for j in fjobs:
            for m in baseline[j["id"]]["missing_skills"]:
                fam_missing[m["skill"]] += 2 if m["type"] == "mandatory" else 1
        top_missing = [s for s, _ in sorted(fam_missing.items(), key=lambda kv: -kv[1])[:3]]
        sim = with_added_skills(snap, top_missing)
        potential = [score_job(sim, j)["score"] for j in fjobs]
        family_out.append({
            "role_family": fam,
            "jobs": len(fjobs),
            "current_best": max(current),
            "current_average": round(sum(current) / len(current), 1),
            "skills_to_focus": top_missing,
            "potential_best": max(potential),
            "potential_average": round(sum(potential) / len(potential), 1),
        })
    family_out.sort(key=lambda f: -(f["potential_average"] - f["current_average"]))

    return {
        "skills": skills_out,
        "learning_paths": paths_out[:6],
        "role_families": family_out,
        "jobs_considered": len(pool),
        "interests_applied": interests,
        "disclaimer": "Estimates use the same transparent matching rules as Find Companies, with the selected skill "
                      "treated as evidenced. Learning a skill could improve your match or open up relevant roles; it "
                      "does not guarantee eligibility, an interview or an offer. Requirements vary by team, location, "
                      "seniority and time.",
    }


def opportunity_detail(snap: CandidateSnapshot, job: dict, selected_skill: str | None = None) -> dict:
    """Opportunity detail view: current matches, gaps, why each matters, what remains."""
    current = score_job(snap, job)
    missing = []
    for m in current["missing_skills"]:
        missing.append({**m, **_skill_meta(m["skill"])})
    after = None
    if selected_skill:
        after_result = score_job(with_added_skills(snap, [selected_skill]), job)
        after = {
            "skill": selected_skill,
            "score": after_result["score"],
            "band": after_result["band"],
            "remaining_requirements": [m["skill"] + f" ({m['type']})" for m in after_result["missing_skills"]],
            "remaining_flags": [f for f in after_result["hard_requirement_flags"] if selected_skill not in f],
        }
    return {"current": current, "missing_detail": missing, "after_selected_skill": after}
