import { Card } from "@/components/ui/Card";
import { AlertTriangle } from "lucide-react";

export function LimitationsPanel({ title = "Known limitations", items }: { title?: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <Card style={{ background: "var(--color-warning-bg)", borderColor: "var(--color-warning-border)" }}>
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center gap-3">
          <AlertTriangle size={18} style={{ color: "var(--color-warning-text)" }} className="shrink-0" />
          <span className="flex-1 text-sm font-semibold" style={{ color: "var(--color-warning-text)" }}>
            {title}
          </span>
          <span className="text-xs transition-transform group-open:rotate-90" style={{ color: "var(--color-warning-text)" }} aria-hidden>
            ▸
          </span>
        </summary>
        <ul className="mt-3 list-disc space-y-1 pl-9 text-sm" style={{ color: "var(--color-warning-text)" }}>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </details>
    </Card>
  );
}
