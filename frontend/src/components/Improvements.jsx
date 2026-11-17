import { useState } from "react";
import { Bot, Check, FileCheck2, KeyRound, RotateCcw, Wand2, X } from "lucide-react";
import { api } from "../services/api.js";
import { Alert, Badge, Button, Card, CardHeader, cx } from "./ui.jsx";

const GROUPS = [
  ["summary", "Professional summary"],
  ["bullet", "Bullet-point improvements"],
  ["project", "Project presentation"],
  ["formatting", "Formatting & structure feedback"],
];

function SuggestionCard({ s, onChange }) {
  const [text, setText] = useState(s.final_text ?? s.suggested);
  const [busy, setBusy] = useState(false);
  const hasPlaceholder = /\[[^\]]+\]/.test(text);

  const update = async (status) => {
    setBusy(true);
    try {
      onChange(await api.updateSuggestion(s.id, { status, final_text: text }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={cx("rounded-xl border p-4", s.status === "accepted" ? "border-emerald-300 bg-emerald-50/40" : s.status === "ignored" ? "border-slate-200 opacity-60" : "border-slate-200")}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-900">{s.title}</span>
        {s.source === "llm" && <Badge color="brand"><Bot size={11} /> AI-assisted</Badge>}
        {s.status !== "pending" && <Badge color={s.status === "accepted" ? "green" : "slate"}>{s.status}</Badge>}
      </div>
      {s.original && (
        <div className="mb-2 rounded-lg bg-slate-50 p-2 text-sm text-slate-600">
          <span className="mr-1 text-xs font-medium uppercase text-slate-400">Current</span>
          <span className="whitespace-pre-line">{s.original}</span>
        </div>
      )}
      {s.applicable ? (
        <textarea className="input" rows={Math.min(6, Math.max(2, Math.ceil(text.length / 90)))} value={text} onChange={(e) => setText(e.target.value)} />
      ) : (
        <div className="whitespace-pre-line rounded-lg border border-dashed border-slate-300 p-2 text-sm text-slate-700">{s.suggested}</div>
      )}
      <p className="mt-2 text-xs text-slate-500">{s.rationale}</p>
      {s.applicable && hasPlaceholder && (
        <p className="mt-1 text-xs text-amber-700">Replace the [bracketed placeholder] with your real details, or delete it. Roppo never fills it in for you.</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {s.applicable ? (
          <>
            <Button size="sm" variant="success" icon={Check} loading={busy} onClick={() => update("accepted")}>
              {s.status === "accepted" ? "Update" : "Accept"}
            </Button>
            <Button size="sm" variant="secondary" icon={X} disabled={busy} onClick={() => update("ignored")}>Ignore</Button>
          </>
        ) : (
          <>
            <Button size="sm" variant="secondary" icon={Check} loading={busy} onClick={() => update("accepted")}>Mark as done</Button>
            <Button size="sm" variant="ghost" icon={X} disabled={busy} onClick={() => update("ignored")}>Dismiss</Button>
          </>
        )}
        {s.status !== "pending" && (
          <Button size="sm" variant="ghost" icon={RotateCcw} disabled={busy} onClick={() => { setText(s.suggested); update("pending"); }}>Reset</Button>
        )}
      </div>
    </div>
  );
}

function KeywordGuidance({ jobs }) {
  const [jobId, setJobId] = useState("");
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.keywords(jobId ? { job_id: Number(jobId) } : { job_text: text }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader icon={KeyRound} title="Keyword guidance" subtitle="Compare your resume with a selected job description" />
      <div className="space-y-3 p-5">
        <select className="input" value={jobId} onChange={(e) => setJobId(e.target.value)}>
          <option value="">Paste a job description below…</option>
          {jobs.map((j) => <option key={j.id} value={j.id}>{j.title} — {j.company.name}</option>)}
        </select>
        {!jobId && <textarea className="input" rows={5} placeholder="Paste the job description text here" value={text} onChange={(e) => setText(e.target.value)} />}
        <Button size="sm" icon={Wand2} loading={busy} onClick={run}>Compare</Button>
        {error && <Alert kind="error">{error}</Alert>}
        {result && (
          <div className="space-y-3 text-sm">
            <div><div className="label">Evidenced in your resume</div><div className="flex flex-wrap gap-1">{result.present.map((x) => <Badge key={x.skill} color="green">{x.skill}</Badge>)}{!result.present.length && "—"}</div></div>
            <div><div className="label">Listed but not clearly evidenced</div>
              {result.weak.map((x) => <div key={x.skill} className="text-slate-600"><Badge color="blue">{x.skill}</Badge> {x.advice}</div>)}{!result.weak.length && "—"}</div>
            <div><div className="label">Not found in your resume</div><div className="flex flex-wrap gap-1">{result.missing.map((x) => <Badge key={x.skill} color={x.type === "mandatory" ? "red" : "amber"}>{x.skill} · {x.type}</Badge>)}{!result.missing.length && "—"}</div></div>
            <Alert kind="warn">{result.note}</Alert>
          </div>
        )}
      </div>
    </Card>
  );
}

export default function Improvements({ analysis, setAnalysis, jobs, onApplied }) {
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const suggestions = analysis.suggestions;
  const accepted = suggestions.filter((s) => s.status === "accepted" && s.applicable);

  const replace = (updated) => setAnalysis({ ...analysis, suggestions: suggestions.map((s) => (s.id === updated.id ? updated : s)) });

  const apply = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const res = await api.applyChanges(analysis.id, label || undefined);
      setMsg({ kind: "success", text: `Saved as “${res.version.label}”. Your original upload is unchanged and still available under Versions.` });
      onApplied?.();
    } catch (e) {
      setMsg({ kind: "error", text: e.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-5 xl:grid-cols-3">
      <div className="space-y-5 xl:col-span-2">
        <Alert kind="info">
          Suggestions are grounded in your actual experience and never add achievements, skills, employers or numbers you
          didn't provide. Review, edit and approve each change — approved changes are saved as a separate resume version.
        </Alert>
        {GROUPS.map(([cat, title]) => {
          const items = suggestions.filter((s) => s.category === cat);
          if (!items.length) return null;
          return (
            <Card key={cat}>
              <CardHeader title={title} subtitle={`${items.length} suggestion${items.length > 1 ? "s" : ""}`} />
              <div className="space-y-3 p-5">
                {items.map((s) => <SuggestionCard key={s.id} s={s} onChange={replace} />)}
              </div>
            </Card>
          );
        })}
      </div>
      <div className="space-y-5 self-start xl:sticky xl:top-6">
        <Card>
          <CardHeader icon={FileCheck2} title="Save approved changes" subtitle={`${accepted.length} accepted change(s) ready`} />
          <div className="space-y-3 p-5">
            <input className="input" placeholder="Version label (optional)" value={label} onChange={(e) => setLabel(e.target.value)} />
            <Button className="w-full" loading={busy} disabled={!accepted.length} onClick={apply}>Save as new resume version</Button>
            {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
          </div>
        </Card>
        <KeywordGuidance jobs={jobs} />
      </div>
    </div>
  );
}
