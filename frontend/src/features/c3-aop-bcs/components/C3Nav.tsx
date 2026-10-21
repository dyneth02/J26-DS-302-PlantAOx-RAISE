import { NavLink } from "react-router-dom";

const tabs = [
  ["/c3", "Overview", true],
  ["/c3/dataset", "Dataset"],
  ["/c3/perturbations", "Perturbations"],
  ["/c3/metrics", "Pilot metrics"],
  ["/c3/explorer", "Variant explorer"],
  ["/c3/predictors", "Predictors"],
  ["/c3/evidence", "Evidence"],
] as const;

export function C3Nav() {
  return (
    <nav className="flex flex-wrap gap-1 border-b pb-2" style={{ borderColor: "var(--color-border)" }} aria-label="Component 03 sections">
      {tabs.map(([to, label, end]) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => [
            "rounded-lg px-3 py-1.5 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2",
            isActive ? "text-white" : "hover:bg-[var(--color-border)]/50",
          ].join(" ")}
          style={({ isActive }) => (isActive ? { background: "var(--color-primary)" } : undefined)}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
