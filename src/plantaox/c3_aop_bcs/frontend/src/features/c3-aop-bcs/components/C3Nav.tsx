import { NavLink } from "react-router-dom";

const tabs = [
  ["/", "Overview", true], ["/dataset", "Dataset"], ["/perturbations", "Perturbations"], ["/metrics", "Pilot metrics"],
  ["/explorer", "Variant explorer"], ["/predictors", "Predictors"], ["/evidence", "Evidence"],
] as const;

export function C3Nav() {
  return <nav className="flex flex-wrap gap-1 border-b pb-2" style={{ borderColor: "var(--color-border)" }} aria-label="Component 03 sections">
    {tabs.map(([to, label, end]) => <NavLink key={to} to={to} end={end} className={({ isActive }) => `rounded-lg px-3 py-1.5 text-sm font-medium ${isActive ? "text-white" : "hover:bg-[var(--color-border)]/50"}`} style={({ isActive }) => isActive ? { background: "var(--color-primary)" } : undefined}>{label}</NavLink>)}
  </nav>;
}
