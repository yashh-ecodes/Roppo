import { Link } from "react-router-dom";
import { ArrowRight, Award, Bot, Gauge, ListTree, SearchX, Sparkles, Target } from "lucide-react";
import { Alert, Badge, Button, Card, CardHeader, Meter, ScoreRing } from "./ui.jsx";

const FACTOR_LABELS = {
  completeness: "Completeness",
  skill_evidence: "Skill evidence",
  measurable_outcomes: "Measurable outcomes",
  action_language: "Action-oriented language",
  clarity: "Clarity",
  contact_and_links: "Contact & links",
};
const RATING = { Strong: "green", Fair: "amber", "Needs work": "red" };

export default function AnalysisReport({ analysis }) {
  const r = analysis.report;
  const q = r.quality;
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader icon={Gauge} title="Resume-quality indicator" />
          <div className="flex flex-col items-center p-5">
            <ScoreRing score={q.score} size={120} />
            <p className="mt-3 text-center text-xs text-slate-500">{q.disclaimer}</p>
          </div>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader title="What's behind the score" subtitle="Each factor, its weight and why it scored the way it did." />
          <div className="space-y-3 p-5">
            {q.factors.map((f) => (
              <div key={f.key}>
                <div className="mb-1 flex justify-between gap-3 text-sm">
                  <span className="font-medium text-slate-700">{FACTOR_LABELS[f.key] || f.key}</span>
                  <span className="shrink-0 text-slate-500">{f.points} / {f.weight} pts</span>
                </div>
                <Meter value={f.value} color={f.value >= 70 ? "bg-emerald-500" : f.value >= 40 ? "bg-amber-500" : "bg-rose-500"} />
                <div className="mt-1 text-xs text-slate-500">{f.explanation}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="Resume overview" />
        <div className="space-y-3 p-5 text-sm leading-relaxed text-slate-700">
          <p>{r.overview}</p>
          {r.ai_overview && (
            <div className="rounded-lg bg-brand-50 p-3 text-brand-900">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-medium"><Bot size={14} /> AI explanation</div>
              {r.ai_overview}
            </div>
          )}
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader icon={Award} title="Strengths" subtitle="Supported by your resume content" />
          <ul className="space-y-2 p-5 text-sm">
            {r.strengths.length === 0 && <li className="text-slate-500">No strong evidence detected yet — see the improvement suggestions.</li>}
            {r.strengths.map((s) => <li key={s} className="flex gap-2"><span className="text-emerald-500">●</span>{s}</li>)}
          </ul>
        </Card>
        <Card>
          <CardHeader icon={ListTree} title="Content quality" />
          <div className="divide-y divide-slate-100">
            {r.content_quality.map((c) => (
              <div key={c.aspect} className="flex items-start justify-between gap-3 px-5 py-3">
                <div>
                  <div className="text-sm font-medium">{c.aspect}</div>
                  <div className="text-xs text-slate-500">{c.detail}</div>
                </div>
                <Badge color={RATING[c.rating]}>{c.rating}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader icon={Sparkles} title="Skill coverage" subtitle="Skills identified and where they appear in your resume" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="px-5 py-2">Skill</th><th className="px-5 py-2">Category</th><th className="px-5 py-2 w-48">Evidence</th><th className="px-5 py-2">Where it appears</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {r.skill_coverage.skills.map((s) => (
                <tr key={s.skill}>
                  <td className="px-5 py-2 font-medium">{s.skill}{s.listed_only && <Badge color="blue" className="ml-2">listed only</Badge>}</td>
                  <td className="px-5 py-2 capitalize text-slate-500">{s.category}</td>
                  <td className="px-5 py-2"><Meter value={s.strength * 100} color={s.strength >= 0.9 ? "bg-emerald-500" : s.strength >= 0.7 ? "bg-brand-500" : "bg-slate-400"} /></td>
                  <td className="px-5 py-2 text-xs text-slate-500" title={s.evidence.map((e) => `${e.section}: ${e.text}`).join("\n")}>{s.sections.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {r.skill_coverage.unrecognised.length > 0 && (
          <div className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
            Listed but not in Roppo's skill taxonomy (kept as written): {r.skill_coverage.unrecognised.join(", ")}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader icon={SearchX} title="Potential gaps"
          subtitle={`Requirements in ${r.potential_gaps.role} (${r.potential_gaps.jobs_considered} job descriptions) not evidenced in your resume`} />
        <div className="space-y-3 p-5">
          {r.potential_gaps.gaps.length === 0 && <p className="text-sm text-slate-500">No recurring gaps found for this selection.</p>}
          {r.potential_gaps.gaps.map((g) => (
            <div key={g.skill} className="flex items-center gap-4">
              <div className="w-40 shrink-0 text-sm font-medium">{g.skill}</div>
              <Meter value={g.share} color="bg-amber-500" />
              <div className="w-48 shrink-0 text-right text-xs text-slate-500">
                in {g.share}% of jobs{g.mandatory_in > 0 && <> · mandatory in {g.mandatory_in}</>}
              </div>
            </div>
          ))}
          <Alert kind="info">Only add a skill to your resume once you can genuinely evidence it. See <Link className="font-medium underline" to="/opportunities">Unlock Opportunities</Link> for which skills could open up more roles.</Alert>
        </div>
      </Card>

      <Card className="bg-gradient-to-r from-brand-600 to-brand-700 text-white">
        <div className="flex flex-col items-start justify-between gap-4 p-6 sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2 text-lg font-semibold"><Target size={20} /> Ready for the next step?</div>
            <p className="text-sm text-brand-100">See openings that align with your current, confirmed profile — with clear reasons for every match.</p>
          </div>
          <Link to="/companies">
            <Button variant="secondary" className="border-0">Discover Companies Where You Can Apply <ArrowRight size={16} /></Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
