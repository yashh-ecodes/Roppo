# API reference

Interactive OpenAPI docs are served at **`/docs`** when the backend runs (for example <http://localhost:8000/docs>).
Every endpoint except register, login, health and meta needs `Authorization: Bearer <token>`.

## Auth
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Create an account → `{access_token, user}` |
| POST | `/api/auth/login` | Sign in → `{access_token, user}` |
| POST | `/api/auth/demo` | Create a pre-filled demo account with fictional data (when `ROPPO_DEMO_MODE=true`) |
| GET | `/api/auth/me` | Current user |

## Resumes & profile
| Method | Path | Description |
|---|---|---|
| POST | `/api/resumes` | Upload a PDF/DOCX (multipart `file`). Extracts an **unconfirmed** profile and creates version 1 |
| GET | `/api/resumes` | List resumes with their versions |
| DELETE | `/api/resumes/{id}` | Delete a resume, its files and its versions |
| GET | `/api/resumes/{id}/versions/{vid}` | Version content, applied changes and plain text |
| GET | `/api/resumes/{id}/versions/{vid}/export?format=docx\|txt` | Download a version |
| POST | `/api/resumes/{id}/versions/{vid}/restore` | Use a version as the working profile |
| GET | `/api/profile` | Candidate profile plus skill evidence |
| PUT | `/api/profile` | Save corrections `{data, confirmed}` |
| POST | `/api/profile/skills` | Add a skill manually |

## Analysis & improvements
| Method | Path | Description |
|---|---|---|
| POST | `/api/analysis` | Run analysis `{target_role?, use_ai}` → report, quality score, suggestions |
| GET | `/api/analysis` · `/api/analysis/latest` · `/api/analysis/{id}` | History, latest, one analysis |
| PATCH | `/api/suggestions/{id}` | `{status: pending\|accepted\|ignored, final_text?}` |
| POST | `/api/analysis/{id}/apply` | Save accepted changes as a **new resume version** (rejects unresolved `[placeholders]`) |
| POST | `/api/analysis/keywords` | Keyword guidance against `{job_id}` or `{job_text}` |

## Jobs
| Method | Path | Description |
|---|---|---|
| GET | `/api/jobs/meta` | Filter options and live/illustrative counts |
| GET | `/api/jobs` | Scored listings. Query: `q, role_family, location, work_mode[], job_type[], seniority[], min_score, hide_mandatory_gaps, listing=all\|live\|illustrative, preferences_only, sort=score\|company\|recent` |
| GET | `/api/jobs/{id}?explain=true` | Detail with match breakdown. `explain` adds an AI explanation when consented |
| POST | `/api/jobs` | Add a listing from an official careers page |
| POST | `/api/jobs/sync` | Refresh live vacancies from the configured Greenhouse/Lever boards |
| GET/POST | `/api/saved-jobs` | List / save `{job_id}` |
| PATCH/DELETE | `/api/saved-jobs/{id}` | Update `{application_status, notes}` / remove |

## Opportunities & roadmap
| Method | Path | Description |
|---|---|---|
| GET | `/api/opportunities?interests=A,B` | Recurring gaps, learning paths and role-family uplift |
| GET | `/api/opportunities/jobs/{id}?skill=X` | Opportunity detail: what matches, what's missing, what remains after X |
| GET | `/api/roadmaps/roles` | Available target roles |
| GET/POST | `/api/roadmaps` | List / create `{target_role}` |
| PATCH | `/api/roadmaps/steps/{id}` | `{status, evidence_url, evidence_note}` |
| POST | `/api/roadmaps/steps/{id}/add-to-profile` | Add a completed step's evidence to the profile |
| DELETE | `/api/roadmaps/{id}` | Remove a roadmap |

## Dashboard, settings & privacy
| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard` | Aggregated dashboard data |
| GET/PUT | `/api/settings` | Name, AI consent, preferences |
| GET | `/api/settings/export` | Export all of your data as JSON |
| DELETE | `/api/settings/analysis-history` | Delete analyses, suggestions and stored matches |
| POST | `/api/settings/delete-account` | `{password}` → permanently delete the account and its files |
| GET | `/api/health` · `/api/meta` | Health check and public config (weights, AI availability) |
