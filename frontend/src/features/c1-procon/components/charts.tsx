import { useState } from "react";
import type { ReactNode } from "react";

/**
 * Small SVG chart primitives for Component 01. They are written for this feature (not shared) so the
 * dashboard can show confidence whiskers, chance lines and noise bands, which the stock bar chart cannot.
 */

// One colour language across all C1 pages.
export const C1_COLORS = {
  frs: "var(--color-primary)", // radical scavenging (teal)
  mc: "var(--color-accent)", // metal chelation (purple)
  dual: "#f59e0b", // both mechanisms
  gen: "#94a3b8", // mechanism not established
  baseline: "var(--color-primary)",
  trained: "var(--color-accent)",
  bad: "var(--color-danger-text)",
  muted: "var(--color-text-muted)",
} as const;

export interface BarItem {
  label: string;
  value: number;
  lo?: number | null;
  hi?: number | null;
  color?: string;
  faint?: boolean;
  note?: string;
}

export interface RefLine {
  value: number;
  label: string;
  color?: string;
}

export interface Band {
  lo: number;
  hi: number;
  label: string;
}

export function HBarChart({
  items,
  min = 0,
  max,
  refs = [],
  bands = [],
  decimals = 3,
  labelWidth = 230,
  ariaLabel,
}: {
  items: BarItem[];
  min?: number;
  max: number;
  refs?: RefLine[];
  bands?: Band[];
  decimals?: number;
  labelWidth?: number;
  ariaLabel: string;
}) {
  const W = 900;
  const rowH = 28;
  const legendRows = bands.length + refs.length;
  const top = 18 + legendRows * 13;
  const right = 70;
  const H = top + items.length * rowH + 34;
  const x = (v: number) => labelWidth + ((v - min) / (max - min)) * (W - labelWidth - right);
  const ticks = Array.from({ length: 5 }, (_, i) => min + ((max - min) * i) / 4);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={ariaLabel} style={{ display: "block" }}>
      {bands.map((b) => (
        <g key={b.label}>
          <rect x={x(b.lo)} y={top - 8} width={x(b.hi) - x(b.lo)} height={items.length * rowH + 10} fill="var(--color-danger-text)" opacity={0.1} />
          <text x={x(b.lo)} y={12 + bands.indexOf(b) * 13} fontSize={10.5} fill="var(--color-danger-text)">
            {b.label}
          </text>
        </g>
      ))}
      {ticks.map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1={top - 8} y2={top + items.length * rowH + 2} stroke="var(--color-border)" />
          <text x={x(t)} y={H - 10} fontSize={11} textAnchor="middle" fill="var(--color-text-muted)">
            {t.toFixed(decimals > 2 ? 2 : decimals)}
          </text>
        </g>
      ))}
      {items.map((item, i) => {
        const y = top + i * rowH;
        const x0 = x(Math.max(min, 0));
        const barEnd = x(item.value);
        return (
          <g key={`${item.label}-${i}`}>
            <text x={labelWidth - 10} y={y + 15} fontSize={12} textAnchor="end" fill="var(--color-text)">
              {item.label}
            </text>
            <rect
              x={Math.min(x0, barEnd)}
              y={y + 3}
              width={Math.max(2, Math.abs(barEnd - x0))}
              height={17}
              rx={3}
              fill={item.color ?? C1_COLORS.baseline}
              opacity={item.faint ? 0.45 : 1}
            >
              <title>{`${item.label}: ${item.value.toFixed(decimals)}${item.lo != null && item.hi != null ? ` [${item.lo.toFixed(decimals)}, ${item.hi.toFixed(decimals)}]` : ""}`}</title>
            </rect>
            {item.lo != null && item.hi != null && (
              <g stroke="var(--color-text)" strokeWidth={1.4}>
                <line x1={x(item.lo)} x2={x(item.hi)} y1={y + 11.5} y2={y + 11.5} />
                <line x1={x(item.lo)} x2={x(item.lo)} y1={y + 6.5} y2={y + 16.5} />
                <line x1={x(item.hi)} x2={x(item.hi)} y1={y + 6.5} y2={y + 16.5} />
              </g>
            )}
            <text x={x(item.hi ?? item.value) + 7} y={y + 15} fontSize={11.5} fill="var(--color-text-muted)">
              {item.value.toFixed(decimals)}
              {item.note ? `  ${item.note}` : ""}
            </text>
          </g>
        );
      })}
      {refs.map((r, i) => (
        <g key={r.label}>
          <line x1={x(r.value)} x2={x(r.value)} y1={top - 8} y2={top + items.length * rowH + 2} stroke={r.color ?? C1_COLORS.bad} strokeWidth={1.6} strokeDasharray="5 4" />
          <text x={x(r.value) + 4} y={12 + (bands.length + i) * 13} fontSize={10.5} fill={r.color ?? C1_COLORS.bad}>
            {r.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

export interface ScatterPoint {
  id: string;
  x: number;
  y: number;
  color: string;
  faint?: boolean;
  radius?: number;
}

export function ScatterPlot({
  points,
  xLabel,
  yLabel,
  onHover,
  ariaLabel,
}: {
  points: ScatterPoint[];
  xLabel: string;
  yLabel: string;
  onHover?: (id: string | null) => void;
  ariaLabel: string;
}) {
  const W = 900;
  const H = 520;
  const pad = { l: 56, r: 16, t: 14, b: 46 };
  // Robust axis range (1st-99th percentile) so a few extreme peptides do not squash the dense core; points beyond
  // the range are drawn on the edge of the plot instead of being dropped.
  const quantile = (values: number[], q: number) => {
    const sorted = [...values].sort((a, b) => a - b);
    return sorted[Math.min(sorted.length - 1, Math.max(0, Math.round(q * (sorted.length - 1))))];
  };
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const [x0, x1] = [quantile(xs, 0.01), quantile(xs, 0.99)];
  const [y0, y1] = [quantile(ys, 0.01), quantile(ys, 0.99)];
  const dx = (x1 - x0) * 0.06 || 1;
  const dy = (y1 - y0) * 0.06 || 1;
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
  const X = (v: number) => pad.l + clamp((v - (x0 - dx)) / (x1 - x0 + 2 * dx), 0.005, 0.995) * (W - pad.l - pad.r);
  const Y = (v: number) => H - pad.b - clamp((v - (y0 - dy)) / (y1 - y0 + 2 * dy), 0.005, 0.995) * (H - pad.t - pad.b);
  // faint points first so highlighted classes are drawn on top
  const ordered = [...points].sort((a, b) => Number(!!b.faint) - Number(!!a.faint));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={ariaLabel} style={{ display: "block" }}>
      <rect x={pad.l} y={pad.t} width={W - pad.l - pad.r} height={H - pad.t - pad.b} fill="none" stroke="var(--color-border)" />
      {ordered.map((p) => (
        <circle
          key={p.id}
          cx={X(p.x)}
          cy={Y(p.y)}
          r={p.radius ?? 3.4}
          fill={p.color}
          opacity={p.faint ? 0.28 : 0.85}
          onMouseEnter={() => onHover?.(p.id)}
          onMouseLeave={() => onHover?.(null)}
        />
      ))}
      <text x={W / 2} y={H - 10} fontSize={12} textAnchor="middle" fill="var(--color-text-muted)">
        {xLabel}
      </text>
      <text x={16} y={H / 2} fontSize={12} textAnchor="middle" fill="var(--color-text-muted)" transform={`rotate(-90 16 ${H / 2})`}>
        {yLabel}
      </text>
    </svg>
  );
}

export function Legend({ entries }: { entries: [string, string][] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
      {entries.map(([color, label]) => (
        <span key={label} className="inline-flex items-center gap-1.5">
          <span style={{ background: color, width: 11, height: 11, borderRadius: 3, display: "inline-block" }} />
          {label}
        </span>
      ))}
    </div>
  );
}

type Tone = "info" | "warn" | "good" | "bad";
const CALLOUT: Record<Tone, { bg: string; border: string; text: string; icon: string }> = {
  info: { bg: "var(--color-surface)", border: "var(--color-primary)", text: "var(--color-text)", icon: "ℹ" },
  warn: { bg: "var(--color-warning-bg)", border: "var(--color-warning-border)", text: "var(--color-warning-text)", icon: "!" },
  good: { bg: "var(--color-success-bg)", border: "var(--color-success-border)", text: "var(--color-success-text)", icon: "✓" },
  bad: { bg: "var(--color-danger-bg)", border: "var(--color-danger-border)", text: "var(--color-danger-text)", icon: "✕" },
};

/** Plain-language "what this shows" box that sits above or below a chart. */
export function Callout({ title, tone = "info", children }: { title: string; tone?: Tone; children: ReactNode }) {
  const t = CALLOUT[tone];
  return (
    <div className="flex gap-3 rounded-xl border p-4" style={{ background: t.bg, borderColor: t.border }}>
      <span
        className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
        style={{ background: t.border === "var(--color-primary)" ? "var(--color-primary)" : t.text }}
        aria-hidden
      >
        {t.icon}
      </span>
      <div>
        <p className="text-sm font-semibold" style={{ color: t.text }}>
          {title}
        </p>
        <div className="mt-1 text-sm" style={{ color: tone === "info" ? "var(--color-text-muted)" : t.text }}>
          {children}
        </div>
      </div>
    </div>
  );
}

/** Large headline number used on the overview. */
export function HeroStat({ value, label, hint, accent }: { value: string; label: string; hint?: string; accent?: string }) {
  return (
    <div className="rounded-xl border p-5" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
      <p className="text-3xl font-bold" style={{ color: accent ?? "var(--color-text)" }}>
        {value}
      </p>
      <p className="mt-1 text-sm font-semibold">{label}</p>
      {hint && (
        <p className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
          {hint}
        </p>
      )}
    </div>
  );
}

/** Pill-style toggle group. */
export function Toggle<T extends string>({ options, value, onChange }: { options: [T, string][]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="flex flex-wrap gap-2" role="group">
      {options.map(([key, label]) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key)}
          aria-pressed={value === key}
          className="rounded-full border px-3 py-1 text-xs font-medium"
          style={{
            borderColor: "var(--color-border)",
            background: value === key ? "var(--color-primary)" : "transparent",
            color: value === key ? "white" : "var(--color-text)",
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/** Hover read-out used under scatter plots. */
export function useHover() {
  return useState<string | null>(null);
}
