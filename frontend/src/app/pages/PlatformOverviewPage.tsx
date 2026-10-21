import type { ComponentType } from "react";
import { useApi } from "@/lib/api/useApi";
import { apiGet } from "@/lib/api/client";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Link } from "react-router-dom";
import { COMPONENT_REGISTRY } from "@/config/components";
import { ArrowRight, Dna, Leaf, ShieldCheck, Workflow } from "lucide-react";

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

// Per-component icon + accent. Deliberately not reused from anywhere else --
// this page is the one place all four components are shown side by side, so
// each gets a visual identity matching its domain rather than one shared
// generic "card" treatment.
const COMPONENT_VISUALS: Record<string, { icon: ComponentType<{ size?: number }>; accent: string }> = {
  c1_procon: { icon: Workflow, accent: "#3b82f6" },
  c2_pu: { icon: Dna, accent: "var(--color-primary)" },
  c3_aop_bcs: { icon: ShieldCheck, accent: "var(--color-accent)" },
  c4_plantaop_screen: { icon: Leaf, accent: "#16a34a" },
};

export function PlatformOverviewPage() {
  const state = useApi(fetchComponents, []);

  return (
    <div className="space-y-6">
      <Card className="relative overflow-hidden">
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-1"
          style={{ background: "linear-gradient(90deg, var(--color-primary), var(--color-accent))" }}
        />
        <div className="pt-1">
          <CardHeader
            title="PlantAOx-RAISE"
            subtitle="Four-component research framework for reliable computational antioxidant-peptide discovery."
          />
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
            This PP1 demonstration integrates Component 02 (PU-AOP) and Component 04 (PlantAOP-Screen) against their
            available research artifacts. C4 outputs retain explicit mock-cloud and mock-signal limitations.
          </p>
        </div>
      </Card>

      <DataState
        state={state}
        render={(components) => (
          <div className="grid gap-4 sm:grid-cols-2">
            {components.map((component) => {
              const visual = COMPONENT_VISUALS[component.id];
              const Icon = visual?.icon ?? Workflow;
              const accent = visual?.accent ?? "var(--color-text-muted)";
              // The frontend's own route registry is the source of truth for
              // navigation -- the API's `base_path` describes the backend
              // mount point (e.g. "/api/v1/c1" for some components), not a
              // frontend route, and following it directly 404s.
              const frontendRoute = COMPONENT_REGISTRY.find((entry) => entry.id === component.id)?.basePath;

              return (
                <Card key={component.id} className="group relative overflow-hidden transition-shadow hover:shadow-md">
                  <div aria-hidden="true" className="absolute inset-y-0 left-0 w-1" style={{ background: accent }} />
                  <div className="flex items-start justify-between gap-2 pl-2">
                    <div className="flex items-center gap-3">
                      <div
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border"
                        style={{ borderColor: accent, color: accent }}
                      >
                        <Icon size={20} />
                      </div>
                      <div>
                        <p className="text-xs font-semibold" style={{ color: "var(--color-text-muted)" }}>
                          {component.code}
                        </p>
                        <h3 className="text-base font-semibold">{component.title}</h3>
                      </div>
                    </div>
                    <Badge tone={component.status === "implemented" ? "success" : "neutral"}>
                      {component.status === "implemented" ? "Implemented" : "Not integrated"}
                    </Badge>
                  </div>
                  <p className="mt-3 pl-2 text-sm" style={{ color: "var(--color-text-muted)" }}>
                    {component.owner_note}
                  </p>
                  {component.status === "implemented" && frontendRoute && (
                    <Link
                      to={frontendRoute}
                      className="mt-4 inline-flex items-center gap-1 pl-2 text-sm font-medium transition-transform group-hover:translate-x-0.5"
                      style={{ color: accent }}
                    >
                      Open dashboard
                      <ArrowRight size={14} />
                    </Link>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      />
    </div>
  );
}
