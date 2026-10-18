import type { CSSProperties, ReactNode } from "react";

export function Card({
  children,
  className = "",
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={`rounded-xl border p-5 shadow-sm ${className}`}
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)", ...style }}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-semibold tracking-wide uppercase" style={{ color: "var(--color-text-muted)" }}>
        {title}
      </h3>
      {subtitle && (
        <p className="mt-1 text-sm" style={{ color: "var(--color-text-muted)" }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

export function StatTile({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--color-text-muted)" }}>
        {label}
      </span>
      <span className="text-2xl font-semibold" style={{ color: "var(--color-text)" }}>
        {value}
      </span>
      {hint && (
        <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
          {hint}
        </span>
      )}
    </div>
  );
}
