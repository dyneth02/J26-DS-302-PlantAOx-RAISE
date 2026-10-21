import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent, ReactNode } from "react";

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
  /** Hidden points keep their place in the axis range, so toggling a group does not rescale the map. */
  hidden?: boolean;
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
  const ordered = points.filter((p) => !p.hidden).sort((a, b) => Number(!!b.faint) - Number(!!a.faint));

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

export interface ScatterPoint3D {
  id: string;
  x: number;
  y: number;
  z: number;
  color: string;
  faint?: boolean;
  radius?: number;
  hidden?: boolean;
}

/** Resolve a CSS colour that may be a `var(--token)` so it can be used on a canvas. */
function resolveCanvasColor(el: Element, color: string): string {
  const match = /^var\((--[\w-]+)\)$/.exec(color);
  if (!match) return color;
  return getComputedStyle(el).getPropertyValue(match[1]).trim() || "#888888";
}

/**
 * 3-D version of ScatterPlot: a perspective canvas the viewer can rotate (drag) and zoom (wheel). It does not need a
 * 3-D library; at ~1.4k points a plain 2-D canvas with depth sorting is fast and keeps the bundle small.
 * All three axes use one common scale so the shape of the cloud is not distorted.
 */
export function ScatterPlot3D({
  points,
  axisLabels,
  onHover,
  ariaLabel,
}: {
  points: ScatterPoint3D[];
  axisLabels: [string, string, string];
  onHover?: (id: string | null) => void;
  ariaLabel: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const view = useRef({ yaw: 0.7, pitch: 0.35, zoom: 1 });
  const dragRef = useRef<{ x: number; y: number } | null>(null);
  const hoverRef = useRef<string | null>(null);
  const projected = useRef<{ id: string; sx: number; sy: number }[]>([]);
  const frame = useRef(0);
  const [spin, setSpin] = useState(false);

  // Robust, common scale: 1st-99th percentile of every axis, clipped just outside the box.
  const normalised = useMemo(() => {
    const q = (values: number[], p: number) => {
      const sorted = [...values].sort((a, b) => a - b);
      return sorted[Math.min(sorted.length - 1, Math.max(0, Math.round(p * (sorted.length - 1))))];
    };
    const axes = [points.map((p) => p.x), points.map((p) => p.y), points.map((p) => p.z)];
    const lo = axes.map((a) => q(a, 0.01));
    const hi = axes.map((a) => q(a, 0.99));
    const half = Math.max(...hi.map((h, i) => h - lo[i])) / 2 || 1;
    const mid = hi.map((h, i) => (h + lo[i]) / 2);
    const clip = (v: number) => Math.max(-1.15, Math.min(1.15, v));
    return points.map((p) => ({ ...p, nx: clip((p.x - mid[0]) / half), ny: clip((p.y - mid[1]) / half), nz: clip((p.z - mid[2]) / half) }));
  }, [points]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext?.("2d");
    if (!canvas || !ctx) return;
    const ratio = window.devicePixelRatio || 1;
    const W = canvas.clientWidth;
    const H = canvas.clientHeight;
    if (canvas.width !== Math.round(W * ratio) || canvas.height !== Math.round(H * ratio)) {
      canvas.width = Math.round(W * ratio);
      canvas.height = Math.round(H * ratio);
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const { yaw, pitch, zoom } = view.current;
    const scale = Math.min(W, H) * 0.3 * zoom;
    const [cy, sy, cp, sp, camera] = [Math.cos(yaw), Math.sin(yaw), Math.cos(pitch), Math.sin(pitch), 4];
    const project = (x: number, y: number, z: number) => {
      const x1 = x * cy + z * sy;
      const z1 = -x * sy + z * cy;
      const y2 = y * cp - z1 * sp;
      const z2 = y * sp + z1 * cp;
      const f = camera / (camera - z2);
      return { sx: W / 2 + x1 * scale * f, sy: H / 2 - y2 * scale * f, depth: z2 };
    };
    ctx.strokeStyle = resolveCanvasColor(canvas, "var(--color-border)");
    ctx.lineWidth = 1;
    const corners: [number, number, number][] = [];
    for (const x of [-1, 1]) for (const y of [-1, 1]) for (const z of [-1, 1]) corners.push([x, y, z]);
    const edges: [number, number][] = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6], [3, 7]];
    ctx.beginPath();
    for (const [a, b] of edges) {
      const p = project(...corners[a]);
      const q = project(...corners[b]);
      ctx.moveTo(p.sx, p.sy);
      ctx.lineTo(q.sx, q.sy);
    }
    ctx.stroke();
    ctx.fillStyle = resolveCanvasColor(canvas, "var(--color-text-muted)");
    ctx.font = "11px sans-serif";
    ([[1.18, 0, 0], [0, 1.18, 0], [0, 0, 1.18]] as const).forEach((pos, i) => {
      const p = project(pos[0], pos[1], pos[2]);
      ctx.fillText(`PC${i + 1}`, p.sx - 8, p.sy + 4);
    });

    const items = normalised
      .filter((p) => !p.hidden)
      .map((p) => ({ p, ...project(p.nx, p.ny, p.nz) }))
      .sort((a, b) => a.depth - b.depth);
    projected.current = items.map((i) => ({ id: i.p.id, sx: i.sx, sy: i.sy }));
    for (const { p, sx, sy: py, depth } of items) {
      const near = (depth + 1.7) / 3.4;
      ctx.globalAlpha = (p.faint ? 0.3 : 0.9) * (0.45 + 0.55 * near);
      ctx.fillStyle = resolveCanvasColor(canvas, p.color);
      ctx.beginPath();
      ctx.arc(sx, py, (p.radius ?? 3.2) * (0.7 + 0.6 * near) * Math.min(1.6, zoom), 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    const hit = items.find((i) => i.p.id === hoverRef.current);
    if (hit) {
      ctx.strokeStyle = resolveCanvasColor(canvas, "var(--color-text)");
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(hit.sx, hit.sy, 8, 0, Math.PI * 2);
      ctx.stroke();
    }
  }, [normalised]);

  const schedule = useCallback(() => {
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(draw);
  }, [draw]);

  useEffect(() => {
    schedule();
    const canvas = canvasRef.current;
    const observer = typeof ResizeObserver === "undefined" || !canvas ? null : new ResizeObserver(schedule);
    if (canvas) observer?.observe(canvas);
    return () => {
      observer?.disconnect();
      cancelAnimationFrame(frame.current);
    };
  }, [schedule]);

  useEffect(() => {
    if (!spin) return;
    let id = 0;
    const tick = () => {
      if (!dragRef.current) view.current.yaw += 0.004;
      draw();
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [spin, draw]);

  const onMove = (e: PointerEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    if (dragRef.current) {
      view.current.yaw += (e.clientX - dragRef.current.x) * 0.01;
      view.current.pitch = Math.max(-1.5, Math.min(1.5, view.current.pitch + (e.clientY - dragRef.current.y) * 0.01));
      dragRef.current = { x: e.clientX, y: e.clientY };
    }
    let best: string | null = null;
    let bestDist = 12;
    for (const p of projected.current) {
      const d = Math.hypot(p.sx - (e.clientX - rect.left), p.sy - (e.clientY - rect.top));
      if (d < bestDist) {
        bestDist = d;
        best = p.id;
      }
    }
    if (best !== hoverRef.current) {
      hoverRef.current = best;
      onHover?.(best);
    }
    schedule();
  };

  return (
    <div>
      <canvas
        ref={canvasRef}
        role="img"
        aria-label={ariaLabel}
        style={{ width: "100%", height: 480, display: "block", cursor: "grab", touchAction: "none", border: "1px solid var(--color-border)", borderRadius: 12 }}
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture?.(e.pointerId);
          dragRef.current = { x: e.clientX, y: e.clientY };
        }}
        onPointerUp={() => {
          dragRef.current = null;
        }}
        onPointerMove={onMove}
        onPointerLeave={() => {
          hoverRef.current = null;
          onHover?.(null);
          schedule();
        }}
        onWheel={(e) => {
          view.current.zoom = Math.max(0.5, Math.min(3, view.current.zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1)));
          schedule();
        }}
        onDoubleClick={() => {
          view.current = { yaw: 0.7, pitch: 0.35, zoom: 1 };
          schedule();
        }}
      />
      <div className="mt-2 flex flex-wrap items-center gap-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
        <span>
          {axisLabels[0]} · {axisLabels[1]} · {axisLabels[2]}
        </span>
        <span>Drag to rotate, scroll to zoom, double-click to reset.</span>
        <label className="inline-flex items-center gap-1.5">
          <input type="checkbox" checked={spin} onChange={(e) => setSpin(e.target.checked)} /> auto-rotate
        </label>
      </div>
    </div>
  );
}

/**
 * Colour key. When `onToggle` is given every entry becomes a button that shows or hides that group in the chart
 * (`hidden` holds the labels currently switched off).
 */
export function Legend({
  entries,
  hidden,
  onToggle,
}: {
  entries: [string, string][];
  hidden?: ReadonlySet<string>;
  onToggle?: (label: string) => void;
}) {
  return (
    <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
      {entries.map(([color, label]) => {
        const off = hidden?.has(label) ?? false;
        const swatch = <span style={{ background: off ? "transparent" : color, border: `2px solid ${color}`, width: 11, height: 11, borderRadius: 3, display: "inline-block", flexShrink: 0 }} />;
        if (!onToggle) {
          return (
            <span key={label} className="inline-flex items-center gap-1.5">
              {swatch}
              {label}
            </span>
          );
        }
        return (
          <button
            key={label}
            type="button"
            onClick={() => onToggle(label)}
            aria-pressed={!off}
            title={off ? `Show ${label}` : `Hide ${label}`}
            className="inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5"
            style={{ opacity: off ? 0.55 : 1, textDecoration: off ? "line-through" : "none", cursor: "pointer", background: "transparent", color: "inherit" }}
          >
            {swatch}
            {label}
          </button>
        );
      })}
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

/** Plain-language note that opens on click. Closed by default so the page stays short in a demo. */
export function Callout({ title, tone = "info", children, defaultOpen = false }: { title: string; tone?: Tone; children: ReactNode; defaultOpen?: boolean }) {
  const t = CALLOUT[tone];
  return (
    <details className="group rounded-xl border p-4" style={{ background: t.bg, borderColor: t.border }} open={defaultOpen}>
      <summary className="flex cursor-pointer list-none items-center gap-3">
        <span
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
          style={{ background: t.border === "var(--color-primary)" ? "var(--color-primary)" : t.text }}
          aria-hidden
        >
          {t.icon}
        </span>
        <span className="flex-1 text-sm font-semibold" style={{ color: t.text }}>
          {title}
        </span>
        <span className="text-xs transition-transform group-open:rotate-90" style={{ color: t.text }} aria-hidden>
          ▸
        </span>
      </summary>
      <div className="mt-2 pl-9 text-sm" style={{ color: tone === "info" ? "var(--color-text-muted)" : t.text }}>
        {children}
      </div>
    </details>
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
