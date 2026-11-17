import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Building2, FileSearch, Map, PlayCircle, Sparkles } from "lucide-react";
import { api } from "../services/api.js";
import { Logo } from "../components/Layout.jsx";
import { Alert, Button } from "../components/ui.jsx";
import { useAuth } from "../services/auth.jsx";

const QUESTIONS = [
  { icon: FileSearch, q: "What should I improve?", a: "Evidence-based resume feedback and suggestions you approve." },
  { icon: Building2, q: "Where can I apply today?", a: "Openings matched to your confirmed profile, with clear reasons." },
  { icon: Sparkles, q: "What could I unlock next?", a: "See which skills could expand the roles you match." },
  { icon: Map, q: "What practical steps next?", a: "A learning roadmap with evidence to add to your profile." },
];

export default function AuthPage({ mode }) {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const isRegister = mode === "register";
  const [demoEnabled, setDemoEnabled] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);

  useEffect(() => {
    api.meta().then((m) => setDemoEnabled(Boolean(m.demo_mode))).catch(() => {});
  }, []);

  const startDemo = async () => {
    setError(null);
    setDemoBusy(true);
    try {
      await signIn("demo");
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setDemoBusy(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signIn(mode, isRegister ? form : { email: form.email, password: form.password });
      navigate(isRegister ? "/analysis" : "/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-brand-900 p-12 text-white lg:flex">
        <Logo light />
        <div>
          <h1 className="text-4xl font-bold leading-tight">
            Your skills today.
            <br />
            <span className="text-brand-200">Your opportunities tomorrow.</span>
          </h1>
          <p className="mt-4 max-w-md text-brand-100">
            Roppo turns your resume into a structured profile, explains what it shows, and connects it to real
            opportunities and practical next steps.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            {QUESTIONS.map(({ icon: Icon, q, a }) => (
              <div key={q} className="rounded-xl bg-white/5 p-4">
                <Icon size={18} className="text-brand-200" />
                <div className="mt-2 font-semibold">{q}</div>
                <div className="mt-1 text-sm text-brand-200">{a}</div>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-brand-200">An assistive career tool — it never promises interviews or offers.</p>
      </div>

      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">{isRegister ? "Create your account" : "Welcome back"}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {isRegister ? "Start by uploading your resume." : "Sign in to continue your career discovery."}
          </p>
          <div className="mt-6 space-y-4">
            {isRegister && (
              <div>
                <label className="label" htmlFor="name">Name</label>
                <input id="name" className="input" required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
            )}
            <div>
              <label className="label" htmlFor="email">Email</label>
              <input id="email" type="email" className="input" required autoComplete="email" value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="password">Password</label>
              <input id="password" type="password" className="input" required minLength={isRegister ? 8 : undefined}
                autoComplete={isRegister ? "new-password" : "current-password"} value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} />
              {isRegister && <p className="mt-1 text-xs text-slate-400">At least 8 characters.</p>}
            </div>
            {error && <Alert kind="error">{error}</Alert>}
            <Button type="submit" loading={busy} className="w-full">
              {isRegister ? "Create account" : "Sign in"}
            </Button>
          </div>
          {demoEnabled && (
            <div className="mt-6 rounded-xl border border-brand-200 bg-brand-50 p-4">
              <div className="text-sm font-medium text-brand-900">Just looking around?</div>
              <p className="mt-0.5 text-xs text-brand-700">
                Open a ready-made demo account with a fictional resume, analysis, matches and roadmap. Nothing to fill in.
              </p>
              <Button type="button" variant="secondary" icon={PlayCircle} loading={demoBusy} onClick={startDemo} className="mt-3 w-full">
                Explore the demo
              </Button>
            </div>
          )}
          <p className="mt-6 text-center text-sm text-slate-500">
            {isRegister ? "Already have an account? " : "New to Roppo? "}
            <Link className="font-medium text-brand-600 hover:underline" to={isRegister ? "/login" : "/register"}>
              {isRegister ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
