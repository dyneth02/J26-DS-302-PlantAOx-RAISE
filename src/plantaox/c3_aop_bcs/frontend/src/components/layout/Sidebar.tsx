import { FlaskConical, LayoutDashboard } from "lucide-react";
import { NavLink } from "react-router-dom";

const components = ["C1 — AOP-ProCon", "C2 — PU-AOP", "C3 — AOP-BCS", "C4 — PlantAOP-Screen"];

export function Sidebar({ onNavigate, className = "" }: { onNavigate?: () => void; className?: string }) {
  return (
    <aside className={`flex w-64 shrink-0 flex-col border-r px-4 py-6 ${className}`} style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
      <div className="mb-8 px-2"><p className="text-base font-bold">PlantAOx-RAISE</p><p className="text-xs text-muted">PP1 research demonstration</p></div>
      <nav className="flex flex-col gap-1" aria-label="Platform navigation">
        <NavLink to="/" end className={({ isActive }) => navClass(isActive)} onClick={onNavigate}><LayoutDashboard size={16} />Platform overview</NavLink>
      </nav>
      <p className="mt-6 mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-muted">Components</p>
      <nav className="flex flex-col gap-1" aria-label="Component navigation">
        {components.map((name) => name.startsWith("C3") ? (
          <NavLink key={name} to="/" end className={({ isActive }) => navClass(isActive)} onClick={onNavigate}><FlaskConical size={16} /><span>{name}</span></NavLink>
        ) : (
          <span key={name} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted"><FlaskConical size={16} /><span>{name}</span></span>
        ))}
      </nav>
    </aside>
  );
}

function navClass(active: boolean) {
  return `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${active ? "bg-[var(--color-primary)]/10" : "hover:bg-[var(--color-border)]/50"}`;
}
