// All theme-sensitive chart styling in one place, reading the CSS custom properties
// defined per-theme in index.css so charts adapt automatically between dark and light
// without any per-page conditional logic.

export const CHART_GRID = "var(--c-line)";
// NB: `fill` must be a real color function, not the bare "R G B" triplet the --c-* variables
// hold -- `var(--c-ink-dim)` alone is invalid as a fill value and silently falls back to
// near-black. Use ink-dim (not ink-faint) here so axis labels stay legible against the panel.
export const CHART_TICK = { fill: "rgb(var(--c-ink-dim))", fontSize: 11, fontFamily: "IBM Plex Mono" };
export const CHART_LEGEND_STYLE = { fontFamily: "IBM Plex Mono", fontSize: 11, color: "rgb(var(--c-ink-dim))" };

export const TIER_COLORS: Record<string, string> = {
  Tier1_FRS: "rgb(var(--c-teal))",
  Tier2_MC: "rgb(var(--c-amber))",
  Tier_Dual: "rgb(var(--c-violet))",
  Tier3_GEN: "rgb(var(--c-ink-faint))",
};

export const AD_TIER_COLORS: Record<string, string> = {
  Tier1: "rgb(var(--c-lime))",
  Tier2: "rgb(var(--c-amber))",
  Tier3_abstain: "rgb(var(--c-coral))",
};

export const FLAG_STYLES: Record<string, string> = {
  HIGH: "bg-lime/10 text-lime ring-1 ring-lime/30",
  MEDIUM: "bg-amber/10 text-amber ring-1 ring-amber/30",
  LOW: "bg-coral/10 text-coral ring-1 ring-coral/30",
  GREEN: "bg-lime/10 text-lime ring-1 ring-lime/30",
  AMBER: "bg-amber/10 text-amber ring-1 ring-amber/30",
  RED_ABSTAIN: "bg-coral/10 text-coral ring-1 ring-coral/30",
};

// Recharts' <Tooltip> only honours `contentStyle` for the box itself -- the value rows
// inside are styled by a separate `itemStyle` (defaulting, in practice, to a low-contrast
// color meant for light backgrounds) and the header by `labelStyle`. Skipping either of
// the latter two is what made tooltip text unreadable on the dark theme: explicit,
// theme-aware colors for all three, every time a <Tooltip> is used.
export function tooltipContentStyle() {
  return {
    background: "rgb(var(--c-surface))",
    border: "1px solid var(--c-line-strong)",
    borderRadius: 10,
    fontSize: 12,
    fontFamily: "IBM Plex Mono, monospace",
    boxShadow: "0 20px 40px -24px rgba(0,0,0,0.45)",
    padding: "8px 12px",
  };
}

export function tooltipLabelStyle() {
  return { color: "rgb(var(--c-ink-dim))", marginBottom: 4, fontWeight: 500 };
}

export function tooltipItemStyle() {
  return { color: "rgb(var(--c-ink))", padding: 0 };
}
