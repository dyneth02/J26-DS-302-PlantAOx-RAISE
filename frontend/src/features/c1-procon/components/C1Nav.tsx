import { NavLink } from "react-router-dom";

const TABS = [
  { to: "/c1", label: "Overview", end: true },
  { to: "/c1/dataset", label: "Benchmark & leakage" },
  { to: "/c1/retrieval", label: "Retrieval results" },
  { to: "/c1/confounds", label: "Shortcut checks" },
  { to: "/c1/map", label: "3-D map & lookup" },
  { to: "/c1/evidence", label: "Evidence" },
];

export function C1Nav() {
  return (
    <nav
      className="flex flex-wrap gap-1 border-b pb-2"
      style={{ borderColor: "var(--color-border)" }}
      aria-label="Component 01 sections"
    >
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) =>
            ["rounded-lg px-3 py-1.5 text-sm font-medium", isActive ? "text-white" : "hover:bg-[var(--color-border)]/50"].join(" ")
          }
          style={({ isActive }) => (isActive ? { background: "var(--color-primary)" } : undefined)}
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
