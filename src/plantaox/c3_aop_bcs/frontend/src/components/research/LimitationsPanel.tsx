import { AlertTriangle } from "lucide-react";
import { Card } from "@/components/ui/Card";

export function LimitationsPanel({ title = "Scientific interpretation boundary", items }: { title?: string; items: string[] }) {
  return <Card style={{ background: "var(--color-warning-bg)", borderColor: "var(--color-warning-border)" }}><div className="flex items-start gap-3"><AlertTriangle size={18} className="mt-0.5 shrink-0" style={{ color: "var(--color-warning-text)" }} /><div><p className="text-sm font-semibold" style={{ color: "var(--color-warning-text)" }}>{title}</p><ul className="mt-2 list-disc space-y-1 pl-4 text-sm" style={{ color: "var(--color-warning-text)" }}>{items.map((item) => <li key={item}>{item}</li>)}</ul></div></div></Card>;
}
