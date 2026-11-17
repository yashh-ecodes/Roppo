import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, BookOpen, ChevronDown, ChevronRight, Hammer, Layers, Sparkles, TrendingUp } from "lucide-react";
import { ListingBadge } from "../components/JobBits.jsx";
import { Alert, Badge, Card, CardHeader, EmptyState, Modal, PageHeader, Spinner, TagInput, scoreColor, useAsync } from "../components/ui.jsx";
import { api } from "../services/api.js";

function OpportunityDetail({ jobId, initialSkill, onClose }) {
  const [skill, setSkill] = useState(initialSkill || "");
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!jobId) return;
    setData(null);
    api.opportunityJob(jobId, skill || undefined).then(setData);
  }, [jobId, skill]);
  useEffect(() => setSkill(initialSkill || ""), [initialSkill, jobId]);

  return (
    <Modal open={!!jobId} onClose={onClose} title={data ? data.job.title : "Loading…"} wide>
      {!data ? <Spinner /> : (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
            {data.job.company.name} <ListingBadge type={data.job.listing_type} />
            <span className="text-xs text-slate-500">Requirements source: {data.job.source}</span>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="p-4">
              <div className="label">Your match today</div>
              <div className={`text-3xl font-bold ${scoreColor(data.current.score)}`}>{Math.round(data.current.score)}</div>
              <div className="text-xs text-slate-500">{data.current.band}</div>
            </Card>
            <Card className="p-4">
              <label className="label" htmlFor="skillsel">If you evidence…</label>
              <select id="skillsel" className="input" value={skill} onChange={(e) => setSkill(e.target.value)}>
                <option value="">Choose a missing skill</option>
                {data.missing_detail.map((m) => <option key={m.skill}>{m.skill}</option>)}
              </select>
              {data.after_selected_skill && (
                <div className="mt-2 text-sm">
                  Match could move to <span className={`font-bold ${scoreColor(data.after_selected_skill.score)}`}>{Math.round(data.after_selected_skill.score)}</span>
                  <span className="text-slate-500"> ({data.after_selected_skill.band})</span>
                </div>
              )}
            </Card>
          </div>
          <div>
            <div className="label">Current skills that already match</div>
            <div className="flex flex-wrap gap-1">
              {data.current.matched_skills.map((s) => <Badge key={s.skill} color="green">{s.skill} · {s.type}</Badge>)}
              {!data.current.matched_skills.length && <span className="text-sm text-slate-500">None yet</span>}
            </div>
          </div>
          <div>
            <div className="label">Additional skills not yet evidenced</div>
            <div className="divide-y divide-slate-100 rounded-xl border border-slate-200">
              {data.missing_detail.map((m) => (
                <div key={m.skill} className={`p-3 text-sm ${m.skill === skill ? "bg-brand-50/50" : ""}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{m.skill}</span>
                    <Badge color={m.type === "mandatory" ? "red" : "amber"}>{m.type}</Badge>
                  </div>
                  {m.why && <div className="mt-1 text-slate-600">Why it matters for this role: {m.why}</div>}
                  {m.also_needed && <div className="mt-0.5 text-xs text-slate-500">Usually alongside: {m.also_needed}</div>}
                  <div className="mt-1 flex flex-wrap gap-3 text-xs">
                    {m.resource && <a href={m.resource.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-brand-700 hover:underline"><BookOpen size={12} />{m.resource.title}</a>}
                    {m.project_idea && <span className="inline-flex items-center gap-1 text-slate-600"><Hammer size={12} />{m.project_idea}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
          {data.after_selected_skill && (
            <Alert kind="info">
              <div className="font-medium">Even after evidencing {data.after_selected_skill.skill}, these requirements remain:</div>
              {data.after_selected_skill.remaining_requirements.length ? data.after_selected_skill.remaining_requirements.join(", ") : "No other listed skill requirements."}
              {data.after_selected_skill.remaining_flags.length > 0 && <div className="mt-1">Other hard requirements: {data.after_selected_skill.remaining_flags.join("; ")}</div>}
            </Alert>
          )}
          <p className="text-xs text-slate-500">Requirements vary by team, location, seniority and time. Learning a skill could improve your match; it does not guarantee eligibility or an offer.</p>
        </div>
      )}
    </Modal>
  );
}

function SkillRow({ s, onOpenJob }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr className="cursor-pointer hover:bg-slate-50" onClick={() => setOpen((o) => !o)}>
        <td className="px-4 py-3 font-medium">
          <span className="inline-flex items-center gap-1">{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}{s.skill}</span>
        </td>
        <td className="px-4 py-3 text-xs text-slate-600">{(s.role_families.length ? s.role_families : s.role_families_in_jobs).slice(0, 3).join(" · ")}</td>
        <td className="px-4 py-3 text-xs text-slate-600">{s.also_needed || "—"}</td>
        <td className="px-4 py-3 text-xs">
          <div>In <strong>{s.appears_in_jobs}</strong> jobs{s.mandatory_in > 0 && <> · mandatory in <strong>{s.mandatory_in}</strong></>}</div>
          <div className="text-emerald-700">+{s.avg_score_gain} avg match</div>
        </td>
        <td className="px-4 py-3 text-xs">
          {s.jobs_reaching_good_match.length > 0 && <Badge color="green">{s.jobs_reaching_good_match.length} could reach “good match”</Badge>}
          {s.jobs_all_mandatory_met.length > 0 && <Badge color="brand" className="mt-1">{s.jobs_all_mandatory_met.length} would meet all mandatory skills</Badge>}
        </td>
      </tr>
      {open && (
        <tr className="bg-slate-50/60">
          <td colSpan={5} className="px-6 py-3 text-sm">
            <div className="flex flex-wrap gap-6">
              <div className="min-w-60 flex-1">
                <div className="label">Roles that may become a stronger match</div>
                {s.example_roles.length === 0 && <div className="text-xs text-slate-500">It improves scores, but other gaps remain — see role details on Find Companies.</div>}
                <ul className="space-y-1">
                  {s.example_roles.map((r) => (
                    <li key={r.job_id}>
                      <button className="text-left text-brand-700 hover:underline" onClick={() => onOpenJob(r.job_id, s.skill)}>{r.title}</button>
                      <span className="text-xs text-slate-500"> · {r.company} </span><ListingBadge type={r.listing_type} compact />
                    </li>
                  ))}
                </ul>
              </div>
              <div className="min-w-60 flex-1 space-y-1 text-xs">
                <div className="label">Learn & prove it</div>
                {s.resource && <a href={s.resource.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-brand-700 hover:underline"><BookOpen size={12} />{s.resource.title}</a>}
                {s.project_idea && <div className="flex items-start gap-1 text-slate-600"><Hammer size={12} className="mt-0.5" />Project idea: {s.project_idea}</div>}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function UnlockOpportunities() {
  const [params, setParams] = useSearchParams();
  const meta = useAsync(() => api.jobsMeta());
  const settings = useAsync(() => api.settings());
  const [interests, setInterests] = useState(null);
  const [detail, setDetail] = useState(null);
  const data = useAsync(() => (interests === null ? Promise.resolve(null) : api.opportunities(interests.join(",") || undefined)), [JSON.stringify(interests)]);

  useEffect(() => {
    if (settings.data && interests === null) setInterests(settings.data.preferences?.interests || []);
  }, [settings.data, interests]);
  useEffect(() => {
    const job = params.get("job");
    if (job) setDetail({ jobId: Number(job), skill: "" });
  }, [params]);

  if (data.error?.status === 404) {
    return <Card><EmptyState icon={Sparkles} title="Upload a resume first" action={<Link to="/analysis" className="text-brand-600">Go to Resume Analysis →</Link>}>Unlock Opportunities compares your profile with job requirements.</EmptyState></Card>;
  }

  const r = data.data;
  return (
    <div>
      <PageHeader
        title="Unlock Opportunities"
        subtitle="See which additional skills could expand your options: recurring gaps across job descriptions, the roles they may open up, and practical ways to build and evidence them."
      />
      <Card className="mb-5 p-4">
        <div className="label">Career interests (optional — focuses the analysis on these role families)</div>
        <TagInput value={interests || []} onChange={setInterests} placeholder="e.g. Backend Developer" suggestions={meta.data?.role_families || []} />
      </Card>

      {(data.loading || !r) ? <Spinner label="Comparing your profile with job requirements…" /> : (
        <div className="space-y-5">
          <Alert kind="info">{r.disclaimer}</Alert>

          <Card>
            <CardHeader icon={TrendingUp} title="Skill-to-opportunity pathways"
              subtitle={`Recurring skills missing or not yet evidenced across ${r.jobs_considered} job descriptions. Click a row for roles and resources.`} />
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr><th className="px-4 py-2">Additional skill</th><th className="px-4 py-2">Role families it may support</th><th className="px-4 py-2">What else may be needed</th><th className="px-4 py-2">How often it's asked</th><th className="px-4 py-2">Potential effect</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {r.skills.map((s) => <SkillRow key={s.skill} s={s} onOpenJob={(jobId, skill) => setDetail({ jobId, skill })} />)}
                </tbody>
              </table>
            </div>
            {r.skills.length === 0 && <EmptyState title="No recurring gaps found">Your profile already evidences the skills in these job descriptions.</EmptyState>}
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader icon={Layers} title="Practical learning paths" subtitle="Related skills grouped together" />
              <div className="space-y-3 p-5">
                {r.learning_paths.length === 0 && <p className="text-sm text-slate-500">No learning paths stand out for this selection.</p>}
                {r.learning_paths.map((p) => (
                  <div key={p.path} className="rounded-xl border border-slate-200 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-medium">{p.path}</div>
                      {p.jobs_reaching_good_match > 0 && <Badge color="green">{p.jobs_reaching_good_match} roles could reach “good match”</Badge>}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {p.skills_you_have.map((s) => <Badge key={s} color="green">✓ {s}</Badge>)}
                      {p.skills_to_build.map((s) => <Badge key={s} color="amber">{s}</Badge>)}
                    </div>
                    {p.role_families.length > 0 && <div className="mt-2 text-xs text-slate-500">May support: {p.role_families.join(", ")}</div>}
                  </div>
                ))}
                <Link to="/roadmap" className="inline-flex items-center gap-1 text-sm font-medium text-brand-700">Turn a path into a roadmap <ArrowRight size={14} /></Link>
              </div>
            </Card>

            <Card>
              <CardHeader icon={Sparkles} title="Role families: today vs. potential" subtitle="Average match now, and after evidencing the top 3 skills for that family" />
              <div className="space-y-4 p-5">
                {r.role_families.map((f) => (
                  <div key={f.role_family}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span className="font-medium">{f.role_family} <span className="text-xs text-slate-400">({f.jobs} jobs)</span></span>
                      <span className="text-xs text-slate-500">{f.current_average} → <span className="font-semibold text-emerald-700">{f.potential_average}</span></span>
                    </div>
                    <div className="relative h-2.5 w-full rounded-full bg-slate-100">
                      <div className="absolute h-full rounded-full bg-emerald-200" style={{ width: `${f.potential_average}%` }} />
                      <div className="absolute h-full rounded-full bg-brand-500" style={{ width: `${f.current_average}%` }} />
                    </div>
                    {f.skills_to_focus.length > 0 && <div className="mt-1 text-xs text-slate-500">Focus: {f.skills_to_focus.join(", ")}</div>}
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}
      <OpportunityDetail jobId={detail?.jobId} initialSkill={detail?.skill}
        onClose={() => { setDetail(null); if (params.get("job")) setParams({}); }} />
    </div>
  );
}
