type Tone = "neutral" | "warning" | "danger" | "success" | "accent";

const TONE_STYLES: Record<Tone, { bg: string; border: string; text: string }> = {
  neutral: { bg: "var(--color-surface)", border: "var(--color-border)", text: "var(--color-text-muted)" },
  warning: { bg: "var(--color-warning-bg)", border: "var(--color-warning-border)", text: "var(--color-warning-text)" },
  danger: { bg: "var(--color-danger-bg)", border: "var(--color-danger-border)", text: "var(--color-danger-text)" },
  success: { bg: "var(--color-success-bg)", border: "var(--color-success-border)", text: "var(--color-success-text)" },
  accent: { bg: "var(--color-surface)", border: "var(--color-accent)", text: "var(--color-accent)" },
};

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) {
  const style = TONE_STYLES[tone];
  return (
    <span
      className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ background: style.bg, borderColor: style.border, color: style.text }}
    >
      {children}
    </span>
  );
}
