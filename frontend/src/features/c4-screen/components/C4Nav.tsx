import { NavLink } from "react-router-dom";

const tabs = [
  ["/c4", "Overview", true],
  ["/c4/pipeline", "Pipeline"],
  ["/c4/ad", "AD explorer"],
  ["/c4/candidates", "Candidate explorer"],
  ["/c4/cards", "Evidence cards"],
  ["/c4/abstained", "Abstained"],
  ["/c4/about", "About"],
] as const;

export function C4Nav() {
  return (
    <nav className="flex flex-wrap gap-1 border-b pb-2" style={{ borderColor: "var(--color-border)" }} aria-label="Component 04 sections">
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
