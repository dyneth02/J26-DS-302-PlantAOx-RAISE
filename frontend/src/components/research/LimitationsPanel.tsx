import { Card } from "@/components/ui/Card";
import { AlertTriangle } from "lucide-react";

export function LimitationsPanel({ title = "Known limitations", items }: { title?: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <Card style={{ background: "var(--color-warning-bg)", borderColor: "var(--color-warning-border)" }}>
      <div className="flex items-start gap-3">
        <AlertTriangle size={18} style={{ color: "var(--color-warning-text)" }} className="mt-0.5 shrink-0" />
        <div>
          <p className="text-sm font-semibold" style={{ color: "var(--color-warning-text)" }}>
            {title}
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm" style={{ color: "var(--color-warning-text)" }}>
            {items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
