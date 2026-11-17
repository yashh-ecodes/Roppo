import { useState } from "react";
import { Plus, Save, Trash2 } from "lucide-react";
import { Alert, Badge, Button, Card, CardHeader, TagInput } from "./ui.jsx";

const lines = (arr) => (arr || []).join("\n");
const unlines = (s) => s.split("\n").map((x) => x.trim()).filter(Boolean);

function Field({ label, value, onChange, placeholder, textarea, rows = 3 }) {
  return (
    <div>
      <label className="label">{label}</label>
      {textarea ? (
        <textarea className="input" rows={rows} value={value || ""} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input className="input" value={value || ""} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      )}
    </div>
  );
}

function ListSection({ title, items, onChange, empty, render, subtitle }) {
  return (
    <Card>
      <CardHeader title={title} subtitle={subtitle}
        action={<Button size="sm" variant="secondary" icon={Plus} onClick={() => onChange([...items, { ...empty }])}>Add</Button>} />
      <div className="divide-y divide-slate-100">
        {items.length === 0 && <p className="px-5 py-4 text-sm text-slate-500">Nothing extracted. Add entries if they're missing.</p>}
        {items.map((item, i) => (
          <div key={i} className="relative p-5">
            <button className="absolute right-4 top-4 rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label="Remove"
              onClick={() => onChange(items.filter((_, j) => j !== i))}>
              <Trash2 size={16} />
            </button>
            {render(item, (patch) => onChange(items.map((x, j) => (j === i ? { ...x, ...patch } : x))))}
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function ProfileEditor({ profile, onSave }) {
  const [data, setData] = useState(() => structuredClone(profile.data));
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const set = (patch) => setData((d) => ({ ...d, ...patch }));
  const contact = data.contact || {};
  const evidence = profile.skill_evidence || {};

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await onSave(data);
      setMsg({ kind: "success", text: "Profile saved and confirmed. It will be used for analysis and matching." });
    } catch (e) {
      setMsg({ kind: "error", text: e.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <Alert kind={profile.confirmed ? "success" : "warn"}>
        {profile.confirmed
          ? "This profile has been reviewed. You can keep editing it at any time."
          : "Resume parsing can be imperfect. Please review what was extracted and correct any mistakes before it is used for matching."}
        {data.meta?.warnings?.map((w) => <div key={w} className="mt-1 font-medium">{w}</div>)}
      </Alert>

      <Card>
        <CardHeader title="Contact & profile details" subtitle="Keep only what you need. You control what is stored." />
        <div className="grid gap-4 p-5 sm:grid-cols-2">
          {[["name", "Name"], ["headline", "Headline"], ["email", "Email"], ["phone", "Phone"], ["location", "Location"], ["linkedin", "LinkedIn"], ["github", "GitHub / portfolio"]].map(([k, l]) => (
            <Field key={k} label={l} value={contact[k]} onChange={(v) => set({ contact: { ...contact, [k]: v } })} />
          ))}
          <div className="sm:col-span-2">
            <Field label="Professional summary" textarea value={data.summary} onChange={(v) => set({ summary: v })} />
          </div>
        </div>
      </Card>

      <ListSection title="Education" items={data.education || []} onChange={(v) => set({ education: v })}
        empty={{ degree: "", institution: "", field: "", start: "", end: "", grade: "" }}
        render={(e, up) => (
          <div className="grid gap-3 pr-8 sm:grid-cols-2">
            <Field label="Degree / qualification" value={e.degree} onChange={(v) => up({ degree: v })} />
            <Field label="Institution" value={e.institution} onChange={(v) => up({ institution: v })} />
            <Field label="Field of study" value={e.field} onChange={(v) => up({ field: v })} />
            <div className="grid grid-cols-3 gap-2">
              <Field label="Start" value={e.start} onChange={(v) => up({ start: v })} />
              <Field label="End" value={e.end} onChange={(v) => up({ end: v })} />
              <Field label="Grade" value={e.grade} onChange={(v) => up({ grade: v })} />
            </div>
          </div>
        )} />

      <ListSection title="Experience & internships" items={data.experience || []} onChange={(v) => set({ experience: v })}
        subtitle="Dates are used to estimate experience (internships count at half weight)."
        empty={{ title: "", organization: "", start: "", end: "", type: "job", bullets: [] }}
        render={(e, up) => (
          <div className="grid gap-3 pr-8 sm:grid-cols-2">
            <Field label="Title" value={e.title} onChange={(v) => up({ title: v })} />
            <Field label="Organization" value={e.organization} onChange={(v) => up({ organization: v })} />
            <div className="grid grid-cols-3 gap-2 sm:col-span-2">
              <Field label="Start (e.g. Jun 2024)" value={e.start} onChange={(v) => up({ start: v })} />
              <Field label="End (or Present)" value={e.end} onChange={(v) => up({ end: v })} />
              <div>
                <label className="label">Type</label>
                <select className="input" value={e.type} onChange={(ev) => up({ type: ev.target.value })}>
                  <option value="job">Job</option>
                  <option value="internship">Internship</option>
                </select>
              </div>
            </div>
            <div className="sm:col-span-2">
              <Field label="Responsibilities & achievements (one per line)" textarea rows={4}
                value={lines(e.bullets)} onChange={(v) => up({ bullets: unlines(v) })} />
            </div>
          </div>
        )} />

      <ListSection title="Projects" items={data.projects || []} onChange={(v) => set({ projects: v })}
        empty={{ name: "", technologies: "", link: "", bullets: [] }}
        render={(p, up) => (
          <div className="grid gap-3 pr-8 sm:grid-cols-3">
            <Field label="Project name" value={p.name} onChange={(v) => up({ name: v })} />
            <Field label="Technologies" value={p.technologies} onChange={(v) => up({ technologies: v })} />
            <Field label="Link" value={p.link} onChange={(v) => up({ link: v })} />
            <div className="sm:col-span-3">
              <Field label="What you built and the result (one per line)" textarea rows={3}
                value={lines(p.bullets)} onChange={(v) => up({ bullets: unlines(v) })} />
            </div>
          </div>
        )} />

      <Card>
        <CardHeader title="Skills" subtitle="Skills backed by experience or projects count as stronger evidence than a list entry." />
        <div className="space-y-3 p-5">
          <TagInput
            value={(data.skills || []).map((s) => s.name)}
            onChange={(names) => set({ skills: names.map((n) => data.skills.find((s) => s.name === n) || { name: n, source: "manual" }) })}
            placeholder="Type a skill and press Enter"
          />
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(evidence).sort((a, b) => b[1].strength - a[1].strength).map(([s, e]) => (
              <Badge key={s} color={e.strength >= 0.9 ? "green" : e.strength >= 0.7 ? "brand" : "slate"} title={`Evidenced in: ${e.sections.join(", ")}`}>
                {s} · {Math.round(e.strength * 100)}%
              </Badge>
            ))}
          </div>
          <p className="text-xs text-slate-400">Badges show recognised skills and how strongly your resume evidences each one (after saving).</p>
        </div>
      </Card>

      <div className="grid gap-5 md:grid-cols-2">
        <Card>
          <CardHeader title="Certifications" />
          <div className="p-5"><Field label="One per line" textarea value={lines(data.certifications)} onChange={(v) => set({ certifications: unlines(v) })} /></div>
        </Card>
        <Card>
          <CardHeader title="Achievements" />
          <div className="p-5"><Field label="One per line" textarea value={lines(data.achievements)} onChange={(v) => set({ achievements: unlines(v) })} /></div>
        </Card>
      </div>

      <div className="sticky bottom-4 z-10 flex flex-col items-end gap-2">
        {msg && <Alert kind={msg.kind} className="shadow">{msg.text}</Alert>}
        <Button icon={Save} loading={saving} onClick={save} className="shadow-lg">Save & confirm profile</Button>
      </div>
    </div>
  );
}
