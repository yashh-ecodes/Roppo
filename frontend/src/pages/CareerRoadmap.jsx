import { useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, CheckCircle2, Circle, CircleDot, Map, Plus, Trash2, UserPlus } from "lucide-react";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, Meter, PageHeader, Spinner, cx, useAsync } from "../components/ui.jsx";
import { api } from "../services/api.js";

const STATUS_ICON = { planned: Circle, in_progress: CircleDot, completed: CheckCircle2 };
const STATUS_LABEL = { planned: "Planned", in_progress: "In progress", completed: "Completed" };

function Step({ step, onChanged }) {
  const [url, setUrl] = useState(step.evidence_url || "");
  const [note, setNote] = useState(step.evidence_note || "");
  const [msg, setMsg] = useState(null);
  const Icon = STATUS_ICON[step.status];

  const patch = async (body) => {
    await api.updateStep(step.id, body);
    onChanged();
  };
  const toProfile = async () => {
    setMsg(null);
    try {
      await api.updateStep(step.id, { evidence_url: url, evidence_note: note });
      const r = await api.stepToProfile(step.id);
      setMsg({ kind: "success", text: r.message });
      onChanged();
    } catch (e) {
      setMsg({ kind: "error", text: e.message });
    }
  };

  return (
    <li className="relative flex gap-4 pb-8 last:pb-0">
      <div className="flex flex-col items-center">
        <div className={cx("flex h-9 w-9 items-center justify-center rounded-full border-2 bg-white",
          step.status === "completed" ? "border-emerald-500 text-emerald-600" : step.status === "in_progress" ? "border-brand-500 text-brand-600" : "border-slate-300 text-slate-400")}>
          <Icon size={18} />
        </div>
        <div className="mt-1 w-0.5 flex-1 bg-slate-200" />
      </div>
      <Card className="flex-1 p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="text-xs font-medium text-slate-400">STEP {step.order}</div>
            <div className="font-semibold text-slate-900">{step.learning_focus}</div>
            <div className="mt-1 flex flex-wrap gap-1">{step.skills.map((s) => <Badge key={s} color="brand">{s}</Badge>)}</div>
          </div>
          <select className="input w-auto py-1 text-xs" value={step.status} onChange={(e) => patch({ status: e.target.value })}>
            {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div className="mt-3 text-sm text-slate-600"><span className="font-medium text-slate-700">Evidence to add:</span> {step.evidence_to_add}</div>
        {step.resource_url && (
          <a href={step.resource_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs text-brand-700 hover:underline">
            <BookOpen size={12} /> {step.resource_title}
          </a>
        )}
        {step.already_evidenced && <div className="mt-2"><Badge color="green">Already evidenced in your resume</Badge></div>}
        {!step.already_evidenced && step.status !== "planned" && (
          <div className="mt-3 space-y-2 rounded-lg bg-slate-50 p-3">
            <div className="label">Attach project evidence</div>
            <input className="input" placeholder="Link to repository, demo or certificate" value={url} onChange={(e) => setUrl(e.target.value)}
              onBlur={() => url !== (step.evidence_url || "") && api.updateStep(step.id, { evidence_url: url })} />
            <textarea className="input" rows={2} placeholder="What you built, how, and the result (this becomes a project bullet)" value={note} onChange={(e) => setNote(e.target.value)}
              onBlur={() => note !== (step.evidence_note || "") && api.updateStep(step.id, { evidence_note: note })} />
            {step.added_to_profile ? (
              <Badge color="green">Added to your profile</Badge>
            ) : (
              <Button size="sm" icon={UserPlus} disabled={step.status !== "completed"} onClick={toProfile}
                title={step.status !== "completed" ? "Mark the step completed first" : ""}>Add to my profile & refresh matches</Button>
            )}
            {msg && <Alert kind={msg.kind}>{msg.text} {msg.kind === "success" && <Link className="font-medium underline" to="/companies">See updated matches</Link>}</Alert>}
          </div>
        )}
      </Card>
    </li>
  );
}

export default function CareerRoadmap() {
  const roles = useAsync(() => api.roadmapRoles());
  const roadmaps = useAsync(() => api.roadmaps());
  const [role, setRole] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const create = async () => {
    setBusy(true);
    setError(null);
    try { await api.createRoadmap(role); setRole(""); roadmaps.reload(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const remove = async (id) => {
    if (!window.confirm("Remove this roadmap?")) return;
    await api.deleteRoadmap(id);
    roadmaps.reload();
  };

  if (roles.loading || roadmaps.loading) return <Spinner />;

  return (
    <div>
      <PageHeader
        title="My Career Roadmap"
        subtitle="Choose a target role and turn skill gaps into manageable learning goals, each with evidence to add to your profile."
        action={
          <div className="flex gap-2">
            <select className="input w-64" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="">Choose a target role…</option>
              {roles.data.map((r) => <option key={r.role}>{r.role}</option>)}
            </select>
            <Button icon={Plus} disabled={!role} loading={busy} onClick={create}>Create</Button>
          </div>
        }
      />
      {error && <Alert kind="error" className="mb-4">{error}</Alert>}
      {roadmaps.data.length === 0 && (
        <Card><EmptyState icon={Map} title="No roadmap yet">
          Pick a target role above. Steps you already evidence are marked as done; for the rest you can track progress,
          attach project evidence and add it to your profile so your matches refresh.
        </EmptyState></Card>
      )}
      <div className="space-y-8">
        {roadmaps.data.map((r) => (
          <Card key={r.id}>
            <CardHeader icon={Map} title={`Target: ${r.target_role}`} subtitle={`Created ${new Date(r.created_at).toLocaleDateString()}`}
              action={<Button size="sm" variant="ghost" icon={Trash2} onClick={() => remove(r.id)}>Remove</Button>} />
            <div className="px-5 pt-4">
              <div className="mb-1 flex justify-between text-sm"><span className="text-slate-600">Progress</span><span className="font-medium">{r.progress}%</span></div>
              <Meter value={r.progress} color="bg-emerald-500" />
            </div>
            <ol className="p-5">
              {r.steps.map((s) => <Step key={s.id} step={s} onChanged={roadmaps.reload} />)}
            </ol>
          </Card>
        ))}
      </div>
    </div>
  );
}
