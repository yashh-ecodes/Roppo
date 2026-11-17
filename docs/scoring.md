# Matching & scoring

Roppo uses a **transparent, rules-based baseline**. AI is only used, optionally, to explain those results.

## Job compatibility (Find Companies)

Defined in `backend/app/services/matching.py` (`MATCH_WEIGHTS`).

| Component | Weight | How it's computed |
|---|---|---|
| Skill coverage | 45% | 70% × share of mandatory skills evidenced + 30% × share of preferred skills evidenced |
| Evidence quality | 15% | Average evidence strength of the matched skills (see below) |
| Experience | 20% | Profile years ÷ required minimum, capped at 1. +0.1 if a past title matches the role family |
| Education | 10% | 1.0 if the stated degree level is met. 0.3 if not met. 0.5 if no education was found in the profile |
| Seniority fit | 10% | 1.0 same level, 0.6 one level apart, 0.2 two or more |

**Bands:** ≥75 Strong match (only if no mandatory gaps) · ≥60 Good · ≥40 Partial · otherwise Stretch.

### Hard requirements are never averaged away
These are listed separately as flags on every match, and you can filter on them:
- each mandatory skill that isn't evidenced
- a minimum-experience requirement that isn't met
- mandatory education that isn't met, or can't be verified from the profile

### Evidence strength
Where a skill appears determines how much it counts:

| Section | Strength |
|---|---|
| Work experience | 1.0 |
| Projects | 0.9 |
| Certifications | 0.75 |
| Completed roadmap step with evidence | 0.7 |
| Education, achievements | 0.6 |
| Summary, skills list, manually added | 0.5 |

Each extra section that corroborates the skill adds +0.05 (capped at 1.0). A skill that appears **only** in the skills list is
marked "listed only" in the UI.

### Related skills
The taxonomy records related skills, such as MySQL ↔ PostgreSQL and React ↔ Vue.js. When a requirement is missing and you have a
related skill, Roppo tells you so you can review whether it applies. **It is never counted as a match.**

## Resume-quality indicator (Resume Analysis)

Defined in `backend/app/services/analysis.py` (`QUALITY_WEIGHTS`). The total is 100 points.

| Factor | Points | Measures |
|---|---|---|
| Completeness | 20 | Contact, education, skills, experience or projects, summary |
| Skill evidence | 20 | Share of skills backed by experience, projects or certifications |
| Measurable outcomes | 20 | Share of bullets with a quantified result (50%+ earns full marks) |
| Action language | 15 | Share of bullets that start with an action verb |
| Clarity | 15 | Share of bullets that are 8–35 words and free of first-person pronouns |
| Contact & links | 10 | Email, phone, and a LinkedIn or GitHub link |

This is a resume-quality indicator, not a measure of a person's worth or a prediction of hiring success.

## Unlock Opportunities

`services/opportunities.py` re-scores jobs with a *hypothetical* profile in which the selected skill is evidenced at
strength 0.7. It uses the same engine as above. For each recurring missing skill it reports:
- the number of jobs that ask for it, and how many of those list it as mandatory
- the average change in match score
- jobs where it would complete the mandatory skills, and jobs that would cross the "Good match" threshold

The wording is always conditional: a skill "could improve your match" or "may open up relevant roles". It never guarantees eligibility or an offer.

## Changing weights
Edit `MATCH_WEIGHTS` / `QUALITY_WEIGHTS` and run `pytest`. The weights must sum to 1.0 and 100 respectively, and the tests
check this. `GET /api/meta` returns the active weights.

## Evaluating quality
Before changing the rules, build a small set of manually reviewed profile-and-job pairs, then track false positives
(irrelevant roles ranked highly) and false negatives (relevant roles ranked low) across changes.
