import { NavLink } from "react-router-dom";
import { COMPONENT_REGISTRY } from "@/config/components";
import { FlaskConical, LayoutDashboard } from "lucide-react";

export function Sidebar({ onNavigate, className = "" }: { onNavigate?: () => void; className?: string }) {
  return (
    <aside
      className={`flex w-64 shrink-0 flex-col border-r px-4 py-6 ${className}`}
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      <div className="mb-8 px-2">
        <p className="text-base font-bold" style={{ color: "var(--color-text)" }}>
          PlantAOx-RAISE
        </p>
        <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
          PP1 research demonstration
        </p>
      </div>

      <nav className="flex flex-col gap-1" aria-label="Platform navigation">
        <NavLink to="/" end className={({ isActive }) => navLinkClass(isActive)} onClick={onNavigate}>
          <LayoutDashboard size={16} />
          Platform overview
        </NavLink>
      </nav>

      <p className="mt-6 mb-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--color-text-muted)" }}>
        Components
      </p>
      <nav className="flex flex-col gap-1" aria-label="Component navigation">
        {COMPONENT_REGISTRY.map((component) => (
          <NavLink
            key={component.id}
            to={component.basePath ?? `/not-integrated/${component.id}`}
            className={({ isActive }) => navLinkClass(isActive)}
            onClick={onNavigate}
          >
            <FlaskConical size={16} />
            <span className="flex-1">{component.shortTitle}</span>
            {component.status === "not_integrated" && (
              <span
                className="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                style={{ background: "var(--color-border)", color: "var(--color-text-muted)" }}
              >
                N/A
              </span>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

function navLinkClass(isActive: boolean) {
  return [
    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive ? "bg-[var(--color-primary)]/10" : "hover:bg-[var(--color-border)]/50",
  ].join(" ");
}
