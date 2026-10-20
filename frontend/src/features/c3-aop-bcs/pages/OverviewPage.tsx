import { DataState } from "@/components/research/DataState";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { ScientificBoundary } from "@/features/c3-aop-bcs/components/ScientificBoundary";
import { useDashboard } from "@/features/c3-aop-bcs/hooks/useDashboard";

export function OverviewPage() {
  const state = useDashboard();

  return (
    <DataState
      state={state}
      render={(data) => (
        <div className="space-y-6">
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <Badge tone="accent">Component 03 — AOP-BCS</Badge>
                <h2 className="mt-2 text-xl font-bold">
                  Physicochemical faithfulness audit for antioxidant peptide predictors
                </h2>
                <p className="mt-2 max-w-3xl text-sm text-muted">
                  A predictor-independent framework that tests whether model scores respond consistently to
                  controlled single-residue perturbations.
                </p>
              </div>
              <div className="flex flex-col items-end gap-1 text-right text-xs text-muted">
                <Badge tone="warning">Software pilot complete</Badge>
                <span>Dataset: {data.provenance.datasetVersion}</span>
                <span>Evidence date: {data.evidenceDate}</span>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Pilot at a glance" subtitle="Counts read from the versioned PP1 run manifest." />
            <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
              <StatTile label="Pilot peptides" value={data.overview.pilotSubjects} hint="coverage-selected" />
              <StatTile label="Pilot perturbations" value={data.overview.pilotVariants} hint="P1 + P2 + P3" />
              <StatTile label="Full eligible subjects" value={data.overview.fullEligibleSubjects} hint="redox-filtered" />
              <StatTile label="Full valid variants" value={data.overview.fullVariants.toLocaleString()} hint="zero rejected" />
            </div>
          </Card>

          <Card>
            <CardHeader title="AOP-BCS workflow" subtitle="The same frozen workflow will be rerun for each verified real predictor." />
            <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {["Prepare audit subjects", "Generate P1/P2/P3", "Validate each edit", "Score and cache", "Calculate ΔScore", "Aggregate IR/FSR/BCS"].map((step, index) => (
                <li key={step} className="flex items-center gap-3 rounded-xl border p-3" style={{ borderColor: "var(--color-border)" }}>
                  <span className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white" style={{ background: "var(--color-primary)" }}>
                    {index + 1}
                  </span>
                  <span className="text-sm font-semibold">{step}</span>
                </li>
              ))}
            </ol>
          </Card>

          <Card>
            <CardHeader title="Scientific status" subtitle="Technical reproducibility and scientific validation are separate claims." />
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <StatTile label="Perturbation pipeline" value="Verified" hint="10,036 accepted variants" />
              <StatTile label="Metric pipeline" value="Verified" hint="dummy smoke test" />
              <StatTile label="Real predictors" value="0 integrated" hint="runtime work pending" />
              <StatTile label="Scientific conclusion" value="Not established" hint="no real scores yet" />
            </div>
          </Card>
          <ScientificBoundary />
        </div>
      )}
    />
  );
}
