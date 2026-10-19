import { useApi } from "@/lib/api/useApi";
import { apiGet } from "@/lib/api/client";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Link } from "react-router-dom";

// Matches backend/app/schemas/common.py::ComponentInfo (snake_case, as the
// API actually returns it) -- intentionally separate from
// config/components.ts's camelCase ComponentDescriptor, which is the
// frontend's own navigation registry, not a response type.
interface ComponentInfoResponse {
  id: string;
  code: string;
  title: string;
  owner_note: string;
  status: "implemented" | "not_integrated";
  base_path: string | null;
}

function fetchComponents() {
  return apiGet<ComponentInfoResponse[]>("/components");
}

export function PlatformOverviewPage() {
  const state = useApi(fetchComponents, []);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="PlantAOx-RAISE"
          subtitle="Four-component research framework for reliable computational antioxidant-peptide discovery."
        />
        <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
          This PP1 demonstration integrates Component 02 (PU-AOP) and Component 04 (PlantAOP-Screen) against their
          available research artifacts. C4 outputs retain explicit mock-cloud and mock-signal limitations.
        </p>
      </Card>

      <DataState
        state={state}
        render={(components) => (
          <div className="grid gap-4 sm:grid-cols-2">
            {components.map((component) => (
              <Card key={component.id}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs font-semibold" style={{ color: "var(--color-text-muted)" }}>
                      {component.code}
                    </p>
                    <h3 className="text-base font-semibold">{component.title}</h3>
                  </div>
                  <Badge tone={component.status === "implemented" ? "success" : "neutral"}>
                    {component.status === "implemented" ? "Implemented" : "Not integrated"}
                  </Badge>
                </div>
                <p className="mt-2 text-sm" style={{ color: "var(--color-text-muted)" }}>
                  {component.owner_note}
                </p>
                {component.status === "implemented" && component.base_path && (
                  <Link
                    to={component.base_path}
                    className="mt-3 inline-block text-sm font-medium"
                    style={{ color: "var(--color-primary)" }}
                  >
                    Open dashboard →
                  </Link>
                )}
              </Card>
            ))}
          </div>
        )}
      />
    </div>
  );
}
