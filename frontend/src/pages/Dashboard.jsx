import { Link } from "react-router-dom";
import { ArrowRight, Bookmark, Building2, FileSearch, ListChecks, Map, Sparkles, Upload } from "lucide-react";
import { ListingBadge } from "../components/JobBits.jsx";
import { Badge, Button, Card, CardHeader, EmptyState, Meter, PageHeader, ScoreRing, Spinner, scoreColor, useAsync } from "../components/ui.jsx";
import { api } from "../services/api.js";

export default function Dashboard() {
  const { data, loading, error } = useAsync(() => api.dashboard());
  if (loading) return <Spinner />;
  if (error) return <p className="text-rose-600">{error.message}</p>;

  if (!data.has_profile) {
    return (
      <Card>
        <EmptyState
          icon={Upload}
          title={`Welcome to Roppo, ${data.user.name.split(" ")[0]}`}
          action={<Link to="/analysis"><Button icon={Upload}>Upload your resume</Button></Link>}
        >
          Upload a PDF or DOCX resume. Roppo extracts a structured profile you can review and correct, explains what it
          shows, and connects it to opportunities and practical next steps.
        </EmptyState>
      </Card>
    );
  }

  const a = data.latest_analysis;
  const p = data.profile;
  return (
    <div>
      <PageHeader
        title={`Hi ${data.user.name.split(" ")[0]} 👋`}
        subtitle="Your latest analysis, top matches, recommended actions and progress at a glance."
      />

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader icon={FileSearch} title="Latest analysis"
            subtitle={a ? `Run ${new Date(a.created_at).toLocaleString()}${a.target_role ? ` · target: ${a.target_role}` : ""}` : "Not run yet"}
            action={<Link to="/analysis"><Button size="sm" variant="secondary">Open</Button></Link>} />
          <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center">
            {a ? (
              <>
                <ScoreRing score={a.score} size={96} label="Resume-quality indicator" />
                <p className="text-sm leading-relaxed text-slate-600">{a.overview}</p>
              </>
            ) : (
              <div className="text-sm text-slate-600">
                Your profile is ready. <Link className="font-medium text-brand-600" to="/analysis">Run your first analysis →</Link>
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader icon={ListChecks} title="Recommended actions" />
          <ul className="divide-y divide-slate-100">
            {data.recommended_actions.length === 0 && <li className="px-5 py-4 text-sm text-slate-500">You're all caught up.</li>}
            {data.recommended_actions.map((r, i) => (
              <li key={i}>
                <Link to="/analysis" className="flex items-center justify-between gap-3 px-5 py-3 text-sm hover:bg-slate-50">
                  <span className="text-slate-700">{r.title}</span>
                  <ArrowRight size={14} className="shrink-0 text-slate-400" />
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardHeader title="Profile summary" />
          <dl className="space-y-3 p-5 text-sm">
            <div><dt className="label">Name</dt><dd>{p.name || "—"}{p.headline && <span className="text-slate-500"> · {p.headline}</span>}</dd></div>
            <div><dt className="label">Education</dt><dd>{p.education || "—"}</dd></div>
            <div><dt className="label">Experience</dt><dd>{p.experience || "—"}</dd></div>
            <div>
              <dt className="label">Strongly evidenced skills ({p.skills} total)</dt>
              <dd className="mt-1 flex flex-wrap gap-1">{p.strong_skills.map((s) => <Badge key={s} color="green">{s}</Badge>)}</dd>
            </div>
          </dl>
          {!data.profile_confirmed && (
            <div className="border-t border-slate-100 px-5 py-3 text-xs text-amber-700">
              Review and confirm your extracted profile for accurate matching.
            </div>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader icon={Building2} title="Top matches right now"
            action={<Link to="/companies"><Button size="sm" variant="secondary">Find companies</Button></Link>} />
          <ul className="divide-y divide-slate-100">
            {data.top_matches.map((m) => (
              <li key={m.job_id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-slate-900">{m.title}</div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    {m.company} <ListingBadge type={m.listing_type} compact />
                    {m.mandatory_gaps > 0 && <Badge color="amber">{m.mandatory_gaps} mandatory gap{m.mandatory_gaps > 1 ? "s" : ""}</Badge>}
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-lg font-bold ${scoreColor(m.score)}`}>{Math.round(m.score)}</div>
                  <div className="text-[10px] text-slate-400">{m.band}</div>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardHeader icon={Bookmark} title="Saved jobs" subtitle={`${data.saved_jobs.total} saved`} />
          <div className="flex flex-wrap gap-2 p-5">
            {Object.entries(data.saved_jobs.by_status).map(([k, v]) => (
              <Badge key={k} color="brand">{k}: {v}</Badge>
            ))}
            {data.saved_jobs.total === 0 && <span className="text-sm text-slate-500">Save jobs from Find Companies to track applications.</span>}
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader icon={Map} title="Roadmap progress"
            action={<Link to="/roadmap"><Button size="sm" variant="secondary">Open roadmap</Button></Link>} />
          <div className="space-y-4 p-5">
            {data.roadmaps.length === 0 && (
              <p className="text-sm text-slate-500">
                No roadmap yet. Pick a target role on <Link to="/roadmap" className="text-brand-600">Career Roadmap</Link> or
                explore <Link to="/opportunities" className="text-brand-600">Unlock Opportunities <Sparkles className="inline" size={12} /></Link>.
              </p>
            )}
            {data.roadmaps.map((r) => (
              <div key={r.id}>
                <div className="mb-1 flex justify-between text-sm"><span className="font-medium">{r.target_role}</span><span className="text-slate-500">{r.progress}%</span></div>
                <Meter value={r.progress} />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
