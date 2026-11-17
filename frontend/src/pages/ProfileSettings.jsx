import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, Download, FileText, ShieldCheck, SlidersHorizontal, Trash2, User } from "lucide-react";
import { Alert, Button, Card, CardHeader, Modal, PageHeader, Spinner, TagInput, useAsync } from "../components/ui.jsx";
import { api, downloadJson } from "../services/api.js";
import { useAuth } from "../services/auth.jsx";

export default function ProfileSettings() {
  const { setUser, signOut } = useAuth();
  const s = useAsync(() => api.settings());
  const meta = useAsync(() => api.jobsMeta());
  const [form, setForm] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [password, setPassword] = useState("");
  const [delError, setDelError] = useState(null);

  useEffect(() => {
    if (s.data) setForm({ name: s.data.name, ai_consent: s.data.ai_consent,
      preferences: { locations: [], work_modes: [], job_types: [], interests: [], ...s.data.preferences } });
  }, [s.data]);

  if (!form || !meta.data) return <Spinner />;
  const prefs = form.preferences;
  const setPref = (k, v) => setForm({ ...form, preferences: { ...prefs, [k]: v } });

  const save = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const res = await api.saveSettings(form);
      setUser((u) => ({ ...u, name: res.name, ai_consent: res.ai_consent, preferences: res.preferences }));
      setMsg({ kind: "success", text: "Settings saved." });
    } catch (e) {
      setMsg({ kind: "error", text: e.message });
    } finally {
      setBusy(false);
    }
  };

  const deleteAccount = async () => {
    setDelError(null);
    try {
      await api.deleteAccount(password);
      signOut();
    } catch (e) {
      setDelError(e.message);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader title="Profile & Settings" subtitle="Personal details, job preferences, AI consent, resume versions, and privacy & deletion controls." />

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader icon={User} title="Personal details" />
          <div className="space-y-4 p-5">
            <div><label className="label">Display name</label><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div><label className="label">Email</label><input className="input bg-slate-50" value={s.data.email} disabled /></div>
            <p className="text-sm text-slate-500">
              Education, experience and skills live in your candidate profile —{" "}
              <Link to="/analysis" className="font-medium text-brand-700">edit them on Resume Analysis</Link>.
            </p>
            <Link to="/analysis"><Button variant="secondary" size="sm" icon={FileText}>Manage resumes & versions</Button></Link>
          </div>
        </Card>

        <Card>
          <CardHeader icon={SlidersHorizontal} title="Job preferences" subtitle="Used to flag and filter openings" />
          <div className="space-y-4 p-5">
            <div><div className="label">Preferred locations</div><TagInput value={prefs.locations} onChange={(v) => setPref("locations", v)} placeholder="e.g. Pune" suggestions={meta.data.locations} /></div>
            <div><div className="label">Work arrangement</div><TagInput value={prefs.work_modes} onChange={(v) => setPref("work_modes", v)} suggestions={meta.data.work_modes} /></div>
            <div><div className="label">Job types</div><TagInput value={prefs.job_types} onChange={(v) => setPref("job_types", v)} suggestions={meta.data.job_types} /></div>
            <div><div className="label">Career interests</div><TagInput value={prefs.interests} onChange={(v) => setPref("interests", v)} suggestions={meta.data.role_families} /></div>
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader icon={Bot} title="AI assistance" subtitle={`Provider: ${s.data.ai.provider} · model ${s.data.ai.model}`} />
          <div className="space-y-3 p-5 text-sm text-slate-600">
            <p>
              Roppo works fully without AI using transparent rules. If you opt in, Claude is used to explain your results in
              plain language and suggest clearer wording. What is sent: the structured profile (education, experience,
              projects, skills) and the engine's findings. <strong>Your name, email, phone and links are removed first.</strong>{" "}
              AI suggestions are checked so they can't add numbers or skills that aren't in your resume, and you approve every change.
            </p>
            {!s.data.ai.server_configured && <Alert kind="warn">AI is not configured on this server (no API key), so analysis uses rules only.</Alert>}
            <label className="flex items-center gap-2 font-medium text-slate-800">
              <input type="checkbox" checked={form.ai_consent} onChange={(e) => setForm({ ...form, ai_consent: e.target.checked })} />
              I consent to my redacted profile being processed by the AI provider for these features.
            </label>
          </div>
        </Card>
      </div>

      <div className="flex items-center justify-end gap-3">
        {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
        <Button loading={busy} onClick={save}>Save settings</Button>
      </div>

      <Card>
        <CardHeader icon={ShieldCheck} title="Privacy & data" subtitle="Your resume is treated as a sensitive personal document." />
        <div className="grid gap-4 p-5 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 p-4">
            <div className="font-medium">Export my data</div>
            <p className="mt-1 text-sm text-slate-500">Download your profile, resume versions, analyses and saved jobs as JSON.</p>
            <Button size="sm" variant="secondary" icon={Download} className="mt-3" onClick={async () => downloadJson(await api.exportData(), "roppo-data.json")}>Export</Button>
          </div>
          <div className="rounded-xl border border-slate-200 p-4">
            <div className="font-medium">Delete analysis history</div>
            <p className="mt-1 text-sm text-slate-500">Removes all analyses, suggestions and stored matches. Resumes and profile are kept.</p>
            <Button size="sm" variant="secondary" icon={Trash2} className="mt-3"
              onClick={async () => { if (window.confirm("Delete all analysis history?")) { await api.deleteHistory(); setMsg({ kind: "success", text: "Analysis history deleted." }); } }}>Delete history</Button>
          </div>
          <div className="rounded-xl border border-rose-200 bg-rose-50/40 p-4">
            <div className="font-medium text-rose-800">Delete account</div>
            <p className="mt-1 text-sm text-slate-600">Permanently deletes your account, uploaded files, extracted data and everything else.</p>
            <Button size="sm" variant="danger" icon={Trash2} className="mt-3" onClick={() => setDeleting(true)}>Delete account</Button>
          </div>
        </div>
      </Card>

      <Modal open={deleting} onClose={() => setDeleting(false)} title="Delete your account">
        <div className="space-y-3">
          <Alert kind="error">This permanently deletes your resumes, profile, analyses, roadmaps and saved jobs. It cannot be undone.</Alert>
          <label className="label" htmlFor="pw">Confirm with your password</label>
          <input id="pw" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
          {delError && <Alert kind="error">{delError}</Alert>}
          <Button variant="danger" disabled={!password} onClick={deleteAccount}>Permanently delete</Button>
        </div>
      </Modal>
    </div>
  );
}
