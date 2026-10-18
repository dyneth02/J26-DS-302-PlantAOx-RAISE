import { useParams } from "react-router-dom";
import { COMPONENT_REGISTRY } from "@/config/components";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export function NotIntegratedPage() {
  const { componentId } = useParams();
  const component = COMPONENT_REGISTRY.find((c) => c.id === componentId);

  return (
    <Card>
      <CardHeader title={component?.title ?? "Component"} subtitle={component?.ownerNote} />
      <Badge tone="neutral">Not integrated</Badge>
      <p className="mt-3 text-sm" style={{ color: "var(--color-text-muted)" }}>
        This component is owned by a different team member and has not been integrated into the
        shared platform yet. This PP1 demonstration implements Component 02 (PU-AOP) only.
      </p>
    </Card>
  );
}
