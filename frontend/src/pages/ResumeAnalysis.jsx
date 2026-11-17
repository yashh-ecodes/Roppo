import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, Download, Eye, FileText, History, Play, RotateCcw, Trash2, UploadCloud } from "lucide-react";
import AnalysisReport from "../components/AnalysisReport.jsx";
import Improvements from "../components/Improvements.jsx";
import ProfileEditor from "../components/ProfileEditor.jsx";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, Modal, PageHeader, Spinner, Tabs, cx } from "../components/ui.jsx";
import { api, downloadResponse } from "../services/api.js";

function Uploader({ onUploaded }) {
  const input = useRef(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const send = async (file) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      onUploaded(await api.uploadResume(file));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); send(e.dataTransfer.files[0]); }}
        onClick={() => input.current?.click()}
        className={cx("flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition",
          drag ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-white hover:border-brand-400")}
      >
        <UploadCloud size={36} className="text-brand-500" />
        <div className="mt-3 font-medium text-slate-900">{busy ? "Uploading and extracting…" : "Drop your resume here, or click to browse"}</div>
        <div className="mt-1 text-sm text-slate-500">PDF or DOCX · up to 5 MB · stored privately, never shared publicly</div>
        <input ref={input} type="file" accept=".pdf,.docx" className="hidden" onChange={(e) => send(e.target.files[0])} />
      </div>
      {error && <Alert kind="error" className="mt-3">{error}</Alert>}
    </div>
  );
}

function Versions({ resumes, reload, onRestored }) {
  const [view, setView] = useState(null);
  const open = async (r, v) => setView({ ...(await api.version(r.id, v.id)), resume: r });
  const restore = async (r, v) => {
    await api.restoreVersion(r.id, v.id);
    onRestored();
  };
  const remove = async (r) => {
    if (!window.confirm(`Delete “${r.filename}” and all its versions? This cannot be undone.`)) return;
    await api.deleteResume(r.id);
    reload();
  };
  if (!resumes.length) return <Card><EmptyState icon={History} title="No resumes yet">Upload a resume to start.</EmptyState></Card>;
  return (
    <div className="space-y-5">
      {resumes.map((r) => (
        <Card key={r.id}>
          <CardHeader icon={FileText} title={r.filename} subtitle={`Uploaded ${new Date(r.created_at).toLocaleString()} · ${(r.size_bytes / 1024).toFixed(0)} KB`}
            action={<Button size="sm" variant="ghost" icon={Trash2} onClick={() => remove(r)}>Delete</Button>} />
          <ul className="divide-y divide-slate-100">
            {r.versions.map((v) => (
              <li key={v.id} className="flex flex-col gap-2 px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-sm font-medium">v{v.version_number} · {v.label}</div>
                  <div className="text-xs text-slate-500">{new Date(v.created_at).toLocaleString()} {v.source === "original" && <Badge className="ml-1">original</Badge>}</div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" icon={Eye} onClick={() => open(r, v)}>View</Button>
                  <Button size="sm" variant="secondary" icon={Download} onClick={async () => downloadResponse(await api.exportVersion(r.id, v.id, "docx"), "resume.docx")}>DOCX</Button>
                  <Button size="sm" variant="secondary" icon={Download} onClick={async () => downloadResponse(await api.exportVersion(r.id, v.id, "txt"), "resume.txt")}>TXT</Button>
                  <Button size="sm" variant="ghost" icon={RotateCcw} onClick={() => restore(r, v)} title="Use this version as your working profile">Use this version</Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ))}
      <Modal open={!!view} onClose={() => setView(null)} title={view ? `v${view.version_number} · ${view.label}` : ""} wide>
        {view?.applied_changes?.length > 0 && (
          <div className="mb-4 space-y-2">
            <div className="label">Changes in this version</div>
            {view.applied_changes.map((c, i) => (
              <div key={i} className="rounded-lg border border-slate-200 p-2 text-sm">
                <div className="text-rose-700 line-through decoration-rose-300">{c.before || "(empty)"}</div>
                <div className="text-emerald-700">{c.after}</div>
              </div>
            ))}
          </div>
        )}
        <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm">{view?.text}</pre>
      </Modal>
    </div>
  );
}

export default function ResumeAnalysis() {
  const [tab, setTab] = useState("profile");
  const [profile, setProfile] = useState(undefined);
  const [analysis, setAnalysis] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [roles, setRoles] = useState([]);
  const [settings, setSettings] = useState(null);
  const [target, setTarget] = useState("");
  const [useAi, setUseAi] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [editorKey, setEditorKey] = useState(0);

  const load = useCallback(async () => {
    const [p, a, r, meta, s] = await Promise.all([
      api.profile().catch(() => null),
      api.latestAnalysis().catch(() => null),
      api.resumes(),
      api.jobsMeta(),
      api.settings(),
    ]);
    setProfile(p);
    setAnalysis(a);
    setResumes(r);
    setRoles(meta.role_families);
    setSettings(s);
    if (a) setTab((t) => (t === "profile" && p?.confirmed ? "report" : t));
    if (p) api.jobs({ sort: "score" }).then((j) => setJobs(j.jobs));
  }, []);

  useEffect(() => { load(); }, [load]);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      setAnalysis(await api.runAnalysis({ target_role: target || null, use_ai: useAi }));
      setTab("report");
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  if (profile === undefined) return <Spinner />;
  const aiReady = settings?.ai?.server_configured && settings?.ai_consent;

  return (
    <div>
      <PageHeader
        title="Resume Analysis"
        subtitle="Upload a resume, confirm what was extracted, then get an explainable analysis with practical improvements you approve."
        action={profile && (
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className="label">Target role (optional)</label>
              <select className="input w-56" value={target} onChange={(e) => setTarget(e.target.value)}>
                <option value="">All roles</option>
                {roles.map((r) => <option key={r}>{r}</option>)}
              </select>
            </div>
            <label className={cx("flex items-center gap-1.5 pb-2 text-xs", aiReady ? "text-slate-600" : "text-slate-400")}
              title={aiReady ? "Use Claude to explain results and polish wording" : "Enable AI in Profile & Settings (requires your consent and a server API key)"}>
              <input type="checkbox" checked={useAi && aiReady} disabled={!aiReady} onChange={(e) => setUseAi(e.target.checked)} />
              <Bot size={14} /> AI-assisted
            </label>
            <Button icon={Play} loading={running} onClick={run}>{analysis ? "Re-run analysis" : "Run analysis"}</Button>
          </div>
        )}
      />
      {error && <Alert kind="error" className="mb-4">{error}</Alert>}

      {!profile ? (
        <Uploader onUploaded={() => { load(); setTab("profile"); }} />
      ) : (
        <>
          <div className="mb-5">
            <Tabs value={tab} onChange={setTab} tabs={[
              { value: "profile", label: "1 · Review profile" },
              { value: "report", label: "2 · Analysis report" },
              { value: "improve", label: "3 · Improvements", count: analysis?.suggestions.filter((s) => s.status === "pending").length },
              { value: "versions", label: "Versions & uploads" },
            ]} />
          </div>
          {tab === "profile" && (
            <ProfileEditor key={editorKey} profile={profile}
              onSave={async (data) => { setProfile(await api.saveProfile(data, true)); }} />
          )}
          {tab === "report" && (analysis ? <AnalysisReport analysis={analysis} /> : (
            <Card><EmptyState icon={Play} title="No analysis yet" action={<Button icon={Play} loading={running} onClick={run}>Run analysis</Button>}>
              {profile.confirmed ? "Your profile is confirmed. Run the analysis to see strengths, gaps and suggestions." : "Tip: review and confirm your profile first so the analysis uses accurate information."}
            </EmptyState></Card>
          ))}
          {tab === "improve" && (analysis
            ? <Improvements analysis={analysis} setAnalysis={setAnalysis} jobs={jobs} onApplied={() => { load(); setEditorKey((k) => k + 1); }} />
            : <Card><EmptyState title="Run an analysis to get suggestions" /></Card>)}
          {tab === "versions" && (
            <div className="space-y-5">
              <Uploader onUploaded={() => { load(); setEditorKey((k) => k + 1); setTab("profile"); }} />
              <Versions resumes={resumes} reload={load} onRestored={() => { load(); setEditorKey((k) => k + 1); setTab("profile"); }} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
