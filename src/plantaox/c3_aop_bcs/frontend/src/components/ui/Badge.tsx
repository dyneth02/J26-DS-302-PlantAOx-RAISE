import type { ReactNode } from "react";

type Tone = "neutral" | "warning" | "danger" | "success" | "accent";
const tones = {
  neutral: ["var(--color-surface)", "var(--color-border)", "var(--color-text-muted)"],
  warning: ["var(--color-warning-bg)", "var(--color-warning-border)", "var(--color-warning-text)"],
  danger: ["var(--color-danger-bg)", "var(--color-danger-border)", "var(--color-danger-text)"],
  success: ["var(--color-success-bg)", "var(--color-success-border)", "var(--color-success-text)"],
  accent: ["var(--color-surface)", "var(--color-accent)", "var(--color-accent)"],
} satisfies Record<Tone, [string, string, string]>;

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  const [background, borderColor, color] = tones[tone];
  return <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium" style={{ background, borderColor, color }}>{children}</span>;
}
