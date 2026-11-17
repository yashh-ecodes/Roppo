import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bookmark, BookmarkCheck, Bot, Briefcase, Building2, MapPin, Plus, RefreshCw, Search, SlidersHorizontal, Sparkles, Trash2 } from "lucide-react";
import { ApplyLink, Freshness, ListingBadge, MatchBreakdown, SkillChips } from "../components/JobBits.jsx";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, Modal, PageHeader, Spinner, Tabs, cx, scoreColor, useAsync } from "../components/ui.jsx";
import { api } from "../services/api.js";

const STATUSES = ["saved", "applied", "interviewing", "offer", "rejected", "withdrawn"];
const DEFAULT_FILTERS = { q: "", role_family: "", location: "", work_mode: [], job_type: [], seniority: [], min_score: 0,
  hide_mandatory_gaps: false, listing: "all", preferences_only: false, sort: "score" };

function toggle(list, v) {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}

function JobCard({ job, onOpen, onSave }) {
  const m = job.match;
  return (
    <Card className="p-5 transition hover:border-brand-300 hover:shadow">
      <div className="flex gap-4">
        <div className="hidden h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-lg font-bold text-slate-500 sm:flex">
          {job.company.name[0]}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <button onClick={() => onOpen(job)} className="text-left font-semibold text-slate-900 hover:text-brand-700">{job.title}</button>
              <div className="text-sm text-slate-600">{job.company.name}{job.team && <span className="text-slate-400"> · {job.team}</span>}</div>
            </div>
            {m && (
              <div className="text-right">
                <div className={`text-2xl font-bold leading-none ${scoreColor(m.score)}`}>{Math.round(m.score)}</div>
                <div className="text-[11px] text-slate-500">{m.band}</div>
              </div>
            )}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <ListingBadge type={job.listing_type} />
            <span className="inline-flex items-center gap-1"><MapPin size={12} />{job.location || "—"}</span>
            <Badge className="capitalize">{job.work_mode}</Badge>
            <Badge className="capitalize">{job.job_type}</Badge>
            <Badge className="capitalize">{job.seniority}</Badge>
            {job.salary && <Badge>{job.salary}</Badge>}
            {job.preference_fit && !job.preference_fit.fits && <Badge color="amber" title={job.preference_fit.notes.join("; ")}>Outside your preferences</Badge>}
          </div>
          {m && (
            <>
              <p className="mt-3 text-sm text-slate-600">{m.explanation}</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div><div className="label">Matched skills</div><SkillChips items={m.matched_skills} kind="matched" /></div>
                <div><div className="label">Skill gaps</div><SkillChips items={m.missing_skills} kind="missing" /></div>
              </div>
            </>
          )}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
            <Freshness job={job} />
            <div className="flex gap-2">
              <Button size="sm" variant={job.saved_status ? "secondary" : "ghost"} icon={job.saved_status ? BookmarkCheck : Bookmark} onClick={() => onSave(job)}>
                {job.saved_status ? job.saved_status : "Save"}
              </Button>
              <Button size="sm" onClick={() => onOpen(job)}>Details</Button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function JobDetail({ jobId, onClose, onSaved }) {
  const [job, setJob] = useState(null);
  const [explaining, setExplaining] = useState(false);
  useEffect(() => {
    if (jobId) api.job(jobId).then(setJob);
    else setJob(null);
  }, [jobId]);
  const explain = async () => {
    setExplaining(true);
    try { setJob(await api.job(jobId, true)); } finally { setExplaining(false); }
  };
  return (
    <Modal open={!!jobId} onClose={onClose} title={job ? job.title : "Loading…"} wide>
      {!job ? <Spinner /> : (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
            <Building2 size={16} /> {job.company.name} {job.team && `· ${job.team}`}
            <ListingBadge type={job.listing_type} />
            <Badge className="capitalize">{job.work_mode}</Badge><Badge className="capitalize">{job.job_type}</Badge>
            <span className="inline-flex items-center gap-1"><MapPin size={14} />{job.location}</span>
          </div>
          {job.listing_type === "illustrative" && (
            <Alert kind="warn">This is an illustrative example used to demonstrate matching. It is not a confirmed vacancy at this company.</Alert>
          )}
          {job.match ? <MatchBreakdown match={job.match} /> : <Alert>Upload a resume to see how you match.</Alert>}
          {job.match && (
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="label">Matched skills (with evidence)</div>
                <ul className="space-y-1 text-sm">
                  {job.match.matched_skills.map((s) => (
                    <li key={s.skill}><span className="font-medium">{s.skill}</span> <span className="text-xs text-slate-500">· {s.type} · {s.sections.join(", ")}</span></li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="label">Requirements not evidenced</div>
                <ul className="space-y-2 text-sm">
                  {job.match.missing_skills.map((s) => (
                    <li key={s.skill}>
                      <span className="font-medium">{s.skill}</span> <Badge color={s.type === "mandatory" ? "red" : "amber"}>{s.type}</Badge>
                      {s.why && <div className="text-xs text-slate-500">Why it matters: {s.why}</div>}
                      {s.related_you_have.length > 0 && (
                        <div className="text-xs text-sky-700">Related skill you have: {s.related_you_have.join(", ")} — review whether it applies (not counted as a match).</div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
          {job.match && (
            <div>
              <div className="label">Eligibility notes</div>
              <ul className="list-disc pl-5 text-sm text-slate-600">{job.match.eligibility_notes.map((n) => <li key={n}>{n}</li>)}</ul>
            </div>
          )}
          <div>
            <div className="label">Role description</div>
            <p className="whitespace-pre-line text-sm text-slate-700">{job.description}</p>
          </div>
          {job.ai_explanation && (
            <div className="rounded-lg bg-brand-50 p-4 text-sm text-brand-900">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-medium"><Bot size={14} /> AI explanation of these findings</div>
              <p>{job.ai_explanation.explanation}</p>
              <ul className="mt-2 list-disc pl-5">{job.ai_explanation.next_steps.map((s) => <li key={s}>{s}</li>)}</ul>
            </div>
          )}
          <Freshness job={job} />
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
            <ApplyLink job={job} />
            {!job.saved_status && <Button variant="secondary" icon={Bookmark} onClick={async () => { await api.saveJob(job.id); setJob({ ...job, saved_status: "saved" }); onSaved(); }}>Save</Button>}
            {job.match && <Button variant="ghost" icon={Bot} loading={explaining} onClick={explain} title="Requires AI consent in settings">Explain with AI</Button>}
            <Link to={`/opportunities?job=${job.id}`}><Button variant="ghost" icon={Sparkles}>What could unlock this role?</Button></Link>
          </div>
        </div>
      )}
    </Modal>
  );
}

function AddListing({ open, onClose, onAdded }) {
  const [f, setF] = useState({ company: "", title: "", source_url: "", location: "", work_mode: "onsite", job_type: "full-time", description: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    setError(null);
    try { await api.addJob(f); onAdded(); onClose(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  return (
    <Modal open={open} onClose={onClose} title="Add a listing from an official careers page">
      <div className="space-y-3">
        <Alert>Copy a vacancy from the employer's official careers page or a verified listing. Requirements are inferred from the description.</Alert>
        {[["company", "Company"], ["title", "Job title"], ["source_url", "Official listing URL"], ["location", "Location"]].map(([k, l]) => (
          <div key={k}><label className="label">{l}</label><input className="input" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></div>
        ))}
        <div className="grid grid-cols-2 gap-3">
          <select className="input" value={f.work_mode} onChange={(e) => setF({ ...f, work_mode: e.target.value })}>{["onsite", "hybrid", "remote"].map((x) => <option key={x}>{x}</option>)}</select>
          <select className="input" value={f.job_type} onChange={(e) => setF({ ...f, job_type: e.target.value })}>{["full-time", "internship", "contract"].map((x) => <option key={x}>{x}</option>)}</select>
        </div>
        <div><label className="label">Job description</label><textarea className="input" rows={7} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></div>
        {error && <Alert kind="error">{error}</Alert>}
        <Button loading={busy} onClick={submit}>Add listing</Button>
      </div>
    </Modal>
  );
}

function SavedJobs({ onOpen }) {
  const { data, loading, reload } = useAsync(() => api.savedJobs());
  if (loading) return <Spinner />;
  if (!data.length) return <Card><EmptyState icon={Bookmark} title="No saved jobs yet">Save openings to build a shortlist and track your applications.</EmptyState></Card>;
  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr><th className="px-4 py-2">Role</th><th className="px-4 py-2">Match</th><th className="px-4 py-2">Status</th><th className="px-4 py-2">Notes</th><th /></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((s) => (
              <tr key={s.id}>
                <td className="px-4 py-3">
                  <button className="font-medium text-slate-900 hover:text-brand-700" onClick={() => onOpen(s.job)}>{s.job.title}</button>
                  <div className="flex items-center gap-2 text-xs text-slate-500">{s.job.company.name} <ListingBadge type={s.job.listing_type} compact /></div>
                </td>
                <td className={`px-4 py-3 font-bold ${s.job.match ? scoreColor(s.job.match.score) : ""}`}>{s.job.match ? Math.round(s.job.match.score) : "—"}</td>
                <td className="px-4 py-3">
                  <select className="input py-1" value={s.application_status} onChange={async (e) => { await api.updateSaved(s.id, { application_status: e.target.value }); reload(); }}>
                    {STATUSES.map((x) => <option key={x}>{x}</option>)}
                  </select>
                </td>
                <td className="px-4 py-3">
                  <input className="input py-1" defaultValue={s.notes || ""} placeholder="Add a note"
                    onBlur={(e) => e.target.value !== (s.notes || "") && api.updateSaved(s.id, { notes: e.target.value })} />
                </td>
                <td className="px-4 py-3 text-right">
                  <button className="rounded p-1 text-slate-400 hover:text-rose-600" aria-label="Remove" onClick={async () => { await api.deleteSaved(s.id); reload(); }}><Trash2 size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export default function FindCompanies() {
  const [tab, setTab] = useState("openings");
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [query, setQuery] = useState(DEFAULT_FILTERS);
  const [openId, setOpenId] = useState(null);
  const [adding, setAdding] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [syncMsg, setSyncMsg] = useState(null);
  const meta = useAsync(() => api.jobsMeta());
  const jobs = useAsync(() => api.jobs(query), [JSON.stringify(query)]);

  useEffect(() => {
    const t = setTimeout(() => setQuery(filters), 300);
    return () => clearTimeout(t);
  }, [filters]);

  const set = (patch) => setFilters((f) => ({ ...f, ...patch }));
  const save = async (job) => {
    if (!job.saved_status) await api.saveJob(job.id);
    jobs.reload();
  };
  const sync = async () => {
    try { const r = await api.syncJobs(); setSyncMsg({ kind: "success", text: `Synced: ${JSON.stringify(r.results)}` }); jobs.reload(); meta.reload(); }
    catch (e) { setSyncMsg({ kind: "error", text: e.message }); }
  };

  const m = meta.data;
  const filterPanel = m && (
    <Card className="space-y-4 p-4">
      <div>
        <label className="label">Role family</label>
        <select className="input" value={filters.role_family} onChange={(e) => set({ role_family: e.target.value })}>
          <option value="">All</option>{m.role_families.map((r) => <option key={r}>{r}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Location</label>
        <input className="input" list="locations" placeholder="Any" value={filters.location} onChange={(e) => set({ location: e.target.value })} />
        <datalist id="locations">{m.locations.map((l) => <option key={l} value={l} />)}</datalist>
      </div>
      {[["work_mode", "Work arrangement", m.work_modes], ["seniority", "Experience level", m.seniority], ["job_type", "Job type", m.job_types]].map(([key, label, opts]) => (
        <div key={key}>
          <div className="label">{label}</div>
          <div className="flex flex-wrap gap-1.5">
            {opts.map((o) => (
              <button key={o} onClick={() => set({ [key]: toggle(filters[key], o) })}
                className={cx("rounded-full border px-2.5 py-1 text-xs capitalize", filters[key].includes(o) ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-600")}>{o}</button>
            ))}
          </div>
        </div>
      ))}
      <div>
        <div className="label">Minimum match: {filters.min_score}</div>
        <input type="range" min="0" max="90" step="5" className="w-full accent-brand-600" value={filters.min_score} onChange={(e) => set({ min_score: Number(e.target.value) })} />
      </div>
      <div>
        <div className="label">Listings</div>
        <select className="input" value={filters.listing} onChange={(e) => set({ listing: e.target.value })}>
          <option value="all">Live + illustrative</option><option value="live">Live vacancies only ({m.counts.live})</option><option value="illustrative">Illustrative only ({m.counts.illustrative})</option>
        </select>
      </div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={filters.hide_mandatory_gaps} onChange={(e) => set({ hide_mandatory_gaps: e.target.checked })} /> Only roles where I meet all hard requirements</label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={filters.preferences_only} onChange={(e) => set({ preferences_only: e.target.checked })} /> Match my saved preferences</label>
      <Button size="sm" variant="ghost" onClick={() => setFilters(DEFAULT_FILTERS)}>Reset filters</Button>
    </Card>
  );

  return (
    <div>
      <PageHeader
        title="Find Companies You Can Target Today"
        subtitle="Openings that align with your current, confirmed profile. Every match shows matched skills, gaps, hard requirements and where the listing came from."
        action={
          <div className="flex gap-2">
            {m?.live_sources_configured && <Button variant="secondary" icon={RefreshCw} onClick={sync}>Refresh live jobs</Button>}
            <Button variant="secondary" icon={Plus} onClick={() => setAdding(true)}>Add a listing</Button>
          </div>
        }
      />
      {syncMsg && <Alert kind={syncMsg.kind} className="mb-4">{syncMsg.text}</Alert>}
      {m && m.counts.live === 0 && (
        <Alert kind="warn" className="mb-4">
          No live vacancies are loaded yet, so the listings below are <strong>illustrative examples with fictional companies</strong>.
          A company name alone is not an opportunity — connect official job-board sources or add listings from official careers pages.
        </Alert>
      )}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Tabs value={tab} onChange={setTab} tabs={[{ value: "openings", label: "Openings", count: jobs.data?.total }, { value: "saved", label: "Saved & applications" }]} />
        {tab === "openings" && (
          <div className="flex w-full gap-2 sm:w-auto">
            <div className="relative flex-1 sm:w-72">
              <Search size={16} className="absolute left-3 top-2.5 text-slate-400" />
              <input className="input pl-9" placeholder="Company, title, role or keyword" value={filters.q} onChange={(e) => set({ q: e.target.value })} />
            </div>
            <select className="input w-auto" value={filters.sort} onChange={(e) => set({ sort: e.target.value })}>
              <option value="score">Best match</option><option value="company">Company</option><option value="recent">Recently checked</option>
            </select>
            <Button variant="secondary" className="lg:hidden" icon={SlidersHorizontal} onClick={() => setShowFilters((s) => !s)} />
          </div>
        )}
      </div>

      {tab === "saved" ? <SavedJobs onOpen={(j) => setOpenId(j.id)} /> : (
        <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
          <aside className={cx(showFilters ? "block" : "hidden", "lg:block")}>{filterPanel}</aside>
          <div className="space-y-4">
            {jobs.loading && !jobs.data && <Spinner />}
            {jobs.data && !jobs.data.has_profile && (
              <Alert kind="info">Upload your resume on <Link className="font-medium underline" to="/analysis">Resume Analysis</Link> to see match scores.</Alert>
            )}
            {jobs.data?.jobs.length === 0 && <Card><EmptyState icon={Briefcase} title="No openings match these filters">Try widening your filters.</EmptyState></Card>}
            {jobs.data?.jobs.map((j) => <JobCard key={j.id} job={j} onOpen={(x) => setOpenId(x.id)} onSave={save} />)}
          </div>
        </div>
      )}
      <JobDetail jobId={openId} onClose={() => setOpenId(null)} onSaved={jobs.reload} />
      <AddListing open={adding} onClose={() => setAdding(false)} onAdded={() => { jobs.reload(); meta.reload(); }} />
    </div>
  );
}
