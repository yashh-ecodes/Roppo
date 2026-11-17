import { AlertTriangle, CheckCircle2, CircleDashed, Clock, ExternalLink, Radio } from "lucide-react";
import { Badge, Meter, scoreColor } from "./ui.jsx";

export function ListingBadge({ type, compact }) {
  if (type === "live_vacancy") {
    return <Badge color="green" title="Fetched from an official source"><Radio size={11} /> {compact ? "Live" : "Live vacancy"}</Badge>;
  }
  return (
    <Badge color="slate" title="Example data for demonstration — not a live vacancy">
      <CircleDashed size={11} /> {compact ? "Illustrative" : "Illustrative example"}
    </Badge>
  );
}

export function Freshness({ job }) {
  const f = job.freshness;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
      <span className="inline-flex items-center gap-1">
        <Clock size={12} /> Source: {job.source}
      </span>
      {f.last_checked && <span>Last checked {new Date(f.last_checked).toLocaleDateString()}</span>}
      <span className={f.stale ? "text-amber-700" : ""}>{f.label}</span>
    </div>
  );
}

export function SkillChips({ items, kind }) {
  if (!items?.length) return <span className="text-xs text-slate-400">None</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((s) => {
        if (kind === "matched") {
          return (
            <Badge key={s.skill} color={s.listed_only ? "blue" : "green"}
              title={s.listed_only ? "Only listed in your skills section — weaker evidence" : `Evidenced in ${s.sections.join(", ")}`}>
              <CheckCircle2 size={11} /> {s.skill}{s.listed_only && " (listed)"}
            </Badge>
          );
        }
        return (
          <Badge key={s.skill} color={s.type === "mandatory" ? "red" : "amber"} title={s.why || ""}>
            {s.skill} · {s.type}
          </Badge>
        );
      })}
    </div>
  );
}

const COMPONENT_LABELS = {
  skill_coverage: "Skill coverage",
  evidence_quality: "Evidence quality",
  experience: "Experience",
  education: "Education",
  seniority: "Seniority fit",
};

export function MatchBreakdown({ match }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className={`text-4xl font-bold ${scoreColor(match.score)}`}>{Math.round(match.score)}</div>
        <div>
          <div className="font-semibold text-slate-900">{match.band}</div>
          <div className="text-xs text-slate-500">Transparent compatibility indicator — not a hiring prediction</div>
        </div>
      </div>
      <p className="text-sm text-slate-700">{match.explanation}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {Object.entries(match.components).map(([k, v]) => (
          <div key={k}>
            <div className="mb-1 flex justify-between text-xs">
              <span className="text-slate-600">{COMPONENT_LABELS[k] || k} <span className="text-slate-400">(weight {Math.round(match.weights[k] * 100)}%)</span></span>
              <span className="font-medium">{v}</span>
            </div>
            <Meter value={v} />
          </div>
        ))}
      </div>
      {match.hard_requirement_flags.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-sm font-medium text-amber-900"><AlertTriangle size={14} /> Hard requirements to check</div>
          <ul className="list-disc space-y-0.5 pl-5 text-sm text-amber-900">
            {match.hard_requirement_flags.map((f) => <li key={f}>{f}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

export function ApplyLink({ job }) {
  if (job.listing_type === "illustrative") {
    return <span className="text-xs text-slate-500">No application link — this is an illustrative example, not a live vacancy.</span>;
  }
  const href = job.source_url || job.company.careers_url;
  if (!href) return null;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
      Apply on official site <ExternalLink size={14} />
    </a>
  );
}
