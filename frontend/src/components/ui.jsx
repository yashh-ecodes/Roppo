import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Info, Loader2, X } from "lucide-react";

export function cx(...c) {
  return c.filter(Boolean).join(" ");
}

export function Card({ className, children, ...rest }) {
  return (
    <div className={cx("rounded-2xl border border-slate-200 bg-white shadow-sm", className)} {...rest}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action, icon: Icon }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="mt-0.5 rounded-lg bg-brand-50 p-2 text-brand-600">
            <Icon size={18} />
          </div>
        )}
        <div>
          <h3 className="font-semibold text-slate-900">{title}</h3>
          {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

const BTN = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 shadow-sm",
  secondary: "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50",
  ghost: "text-slate-600 hover:bg-slate-100",
  danger: "bg-rose-600 text-white hover:bg-rose-700",
  success: "bg-emerald-600 text-white hover:bg-emerald-700",
};

export function Button({ variant = "primary", size = "md", loading, icon: Icon, className, children, ...rest }) {
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-4 py-2 text-sm",
        BTN[variant],
        className,
      )}
      disabled={loading || rest.disabled}
      {...rest}
    >
      {loading ? <Loader2 size={16} className="animate-spin" /> : Icon && <Icon size={size === "sm" ? 14 : 16} />}
      {children}
    </button>
  );
}

const BADGE = {
  slate: "bg-slate-100 text-slate-700",
  brand: "bg-brand-50 text-brand-700",
  green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-800",
  red: "bg-rose-50 text-rose-700",
  blue: "bg-sky-50 text-sky-700",
};

export function Badge({ color = "slate", className, children, title }) {
  return (
    <span
      title={title}
      className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", BADGE[color], className)}
    >
      {children}
    </span>
  );
}

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-slate-500">
      <Loader2 className="animate-spin" size={20} /> {label}
    </div>
  );
}

export function Alert({ kind = "info", children, className }) {
  const styles = {
    info: ["bg-sky-50 text-sky-800 border-sky-200", Info],
    error: ["bg-rose-50 text-rose-800 border-rose-200", AlertCircle],
    success: ["bg-emerald-50 text-emerald-800 border-emerald-200", CheckCircle2],
    warn: ["bg-amber-50 text-amber-900 border-amber-200", AlertCircle],
  }[kind];
  const Icon = styles[1];
  return (
    <div className={cx("flex items-start gap-2 rounded-lg border px-3 py-2 text-sm", styles[0], className)}>
      <Icon size={16} className="mt-0.5 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      {Icon && (
        <div className="mb-4 rounded-2xl bg-brand-50 p-4 text-brand-600">
          <Icon size={28} />
        </div>
      )}
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      <div className="mt-1 max-w-md text-sm text-slate-500">{children}</div>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function scoreColor(score) {
  if (score >= 75) return "text-emerald-600";
  if (score >= 60) return "text-brand-600";
  if (score >= 40) return "text-amber-600";
  return "text-slate-500";
}

export function ScoreRing({ score, size = 72, label }) {
  const r = 30;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox="0 0 72 72" className={scoreColor(score)}>
        <circle cx="36" cy="36" r={r} fill="none" stroke="currentColor" strokeOpacity="0.15" strokeWidth="7" />
        <circle
          cx="36" cy="36" r={r} fill="none" stroke="currentColor" strokeWidth="7" strokeLinecap="round"
          strokeDasharray={`${c * pct} ${c}`} transform="rotate(-90 36 36)"
        />
        <text x="36" y="41" textAnchor="middle" className="fill-slate-900 text-[17px] font-bold">
          {Math.round(score)}
        </text>
      </svg>
      {label && <span className="mt-1 text-xs text-slate-500">{label}</span>}
    </div>
  );
}

export function Meter({ value, className, color = "bg-brand-500" }) {
  return (
    <div className={cx("h-2 w-full overflow-hidden rounded-full bg-slate-100", className)}>
      <div className={cx("h-full rounded-full transition-all", color)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        className={cx("my-8 w-full rounded-2xl bg-white shadow-xl", wide ? "max-w-4xl" : "max-w-lg")}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-500 hover:bg-slate-100" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
      {tabs.map((t) => (
        <button
          key={t.value}
          onClick={() => onChange(t.value)}
          className={cx(
            "whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition",
            value === t.value ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900",
          )}
        >
          {t.label}
          {t.count !== undefined && <span className="ml-1.5 text-xs text-slate-400">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function TagInput({ value = [], onChange, placeholder, suggestions = [] }) {
  const [text, setText] = useState("");
  const add = (v) => {
    const t = v.trim();
    if (t && !value.includes(t)) onChange([...value, t]);
    setText("");
  };
  return (
    <div>
      <div className="flex flex-wrap gap-1.5 rounded-lg border border-slate-300 bg-white p-1.5">
        {value.map((v) => (
          <span key={v} className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
            {v}
            <button onClick={() => onChange(value.filter((x) => x !== v))} aria-label={`Remove ${v}`}>
              <X size={12} />
            </button>
          </span>
        ))}
        <input
          className="min-w-24 flex-1 px-1 text-sm outline-none"
          value={text}
          placeholder={placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              add(text);
            }
          }}
          onBlur={() => text && add(text)}
        />
      </div>
      {suggestions.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {suggestions.filter((s) => !value.includes(s)).slice(0, 12).map((s) => (
            <button key={s} onClick={() => add(s)} className="rounded-md border border-dashed border-slate-300 px-2 py-0.5 text-xs text-slate-600 hover:border-brand-400 hover:text-brand-700">
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-slate-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    fn()
      .then((data) => alive && setState({ loading: false, data, error: null }))
      .catch((error) => alive && setState({ loading: false, data: null, error }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { ...state, reload: () => setTick((t) => t + 1), setData: (data) => setState((s) => ({ ...s, data })) };
}
