import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Building2, FileSearch, LayoutDashboard, LogOut, Map, Menu, Sparkles, UserCog, X } from "lucide-react";
import { useAuth } from "../services/auth.jsx";
import { cx } from "./ui.jsx";

// Suggested navigation order from the concept doc.
const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/analysis", label: "Resume Analysis", icon: FileSearch },
  { to: "/companies", label: "Find Companies", icon: Building2 },
  { to: "/opportunities", label: "Unlock Opportunities", icon: Sparkles },
  { to: "/roadmap", label: "Career Roadmap", icon: Map },
  { to: "/profile", label: "Profile & Settings", icon: UserCog },
];

export function Logo({ light }) {
  return (
    <div className="flex items-center gap-2.5">
      <img src="/favicon.svg" alt="" className="h-8 w-8" />
      <div>
        <div className={cx("text-lg font-bold leading-none tracking-tight", light ? "text-white" : "text-slate-900")}>Roppo</div>
        <div className={cx("text-[10px] leading-tight", light ? "text-brand-200" : "text-slate-500")}>
          Your skills today. Your opportunities tomorrow.
        </div>
      </div>
    </div>
  );
}

export default function Layout() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);

  const nav = (
    <nav className="flex flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            cx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
              isActive ? "bg-white/10 text-white" : "text-brand-100 hover:bg-white/5 hover:text-white",
            )
          }
        >
          <Icon size={18} /> {label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-64 shrink-0 flex-col justify-between bg-brand-900 p-4 lg:flex lg:fixed lg:inset-y-0">
        <div>
          <div className="mb-8 px-2 pt-2">
            <Logo light />
          </div>
          {nav}
        </div>
        <div className="rounded-xl bg-white/5 p-3">
          <div className="truncate text-sm font-medium text-white">{user.name}</div>
          <div className="truncate text-xs text-brand-200">{user.email}</div>
          <button onClick={signOut} className="mt-2 flex items-center gap-1.5 text-xs text-brand-200 hover:text-white">
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <Logo />
        <button onClick={() => setOpen(true)} aria-label="Open menu" className="rounded-lg p-2 hover:bg-slate-100">
          <Menu size={20} />
        </button>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 bg-slate-900/50 lg:hidden" onClick={() => setOpen(false)}>
          <div className="h-full w-72 bg-brand-900 p-4" onClick={(e) => e.stopPropagation()}>
            <div className="mb-6 flex items-center justify-between">
              <Logo light />
              <button onClick={() => setOpen(false)} className="text-white" aria-label="Close menu">
                <X size={20} />
              </button>
            </div>
            {nav}
            <button onClick={signOut} className="mt-6 flex items-center gap-1.5 px-3 text-sm text-brand-200">
              <LogOut size={14} /> Sign out
            </button>
          </div>
        </div>
      )}

      <main className="min-w-0 flex-1 lg:ml-64">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
        <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-slate-400 sm:px-6 lg:px-8">
          Roppo is an assistive career tool. Scores are explainable indicators, not hiring decisions or guarantees of
          interviews, offers or eligibility.
        </footer>
      </main>
    </div>
  );
}
