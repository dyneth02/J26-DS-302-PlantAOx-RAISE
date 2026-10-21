import { NavLink } from "react-router-dom";

const TABS = [
  { to: "/c2", label: "Overview", end: true },
  { to: "/c2/so1", label: "SO1 - Data Curation" },
  { to: "/c2/so2", label: "SO2 - Challenge Pools" },
  { to: "/c2/so3", label: "SO3 - Features" },
  { to: "/c2/so4", label: "SO4 - Model Comparison" },
  { to: "/c2/curriculum", label: "Curriculum" },
  { to: "/c2/evidence", label: "Evidence" },
];

export function C2Nav() {
  return (
    <nav
      className="flex flex-wrap gap-1 border-b pb-2"
      style={{ borderColor: "var(--color-border)" }}
      aria-label="Component 02 sections"
    >
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) =>
            [
              "rounded-lg px-3 py-1.5 text-sm font-medium",
              isActive ? "text-white" : "hover:bg-[var(--color-border)]/50",
            ].join(" ")
          }
          style={({ isActive }) => (isActive ? { background: "var(--color-primary)" } : undefined)}
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
