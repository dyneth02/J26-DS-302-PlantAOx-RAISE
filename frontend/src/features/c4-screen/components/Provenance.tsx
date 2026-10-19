import type { ReactNode } from "react";
import type { CandidateDetail } from "@/features/c4-screen/types";

const chips = [
  { key: "d_AD", text: "d_AD: mock cloud", title: "Applicability distance to the current mock reference cloud" },
  { key: "SIM_C1", text: "SIM_C1: mock", title: "Mock C1 similarity signal; not a measured classifier result" },
  { key: "PROB_C2", text: "PROB_C2: mock", title: "Mock C2 probability signal; not a measured classifier result" },
  { key: "BCS", text: "BCS: mock · C4-provisional", title: "Mock BCS stratum; flag thresholds are C4-provisional" },
];

export function ProvenanceChips() {
  return (
    <div className="flex flex-wrap gap-2" aria-label="Data provenance">
      {chips.map((chip) => (
        <span
          key={chip.key}
          title={chip.title}
          aria-label={`${chip.text}. ${chip.title}`}
          className="rounded-full border px-2.5 py-1 text-xs font-medium"
          style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}
        >
          {chip.text}
        </span>
      ))}
    </div>
  );
}

export function TierBadge({ tier, flag }: { tier: number; flag?: string }) {
  const label = flag ?? (tier === 1 ? "GREEN" : tier === 2 ? "AMBER" : "RED");
  const tone = tier === 1 ? "success" : tier === 2 ? "warning" : "danger";
  const styles = {
    success: ["var(--color-success-bg)", "var(--color-success-border)", "var(--color-success-text)"],
    warning: ["var(--color-warning-bg)", "var(--color-warning-border)", "var(--color-warning-text)"],
    danger: ["var(--color-danger-bg)", "var(--color-danger-border)", "var(--color-danger-text)"],
  }[tone];
  return (
    <span className="inline-flex rounded-full border px-2.5 py-1 text-xs font-bold" style={{ background: styles[0], borderColor: styles[1], color: styles[2] }}>
      Tier {tier} · {label}
    </span>
  );
}

export function DemoMarker({ injected }: { injected: boolean }) {
  return injected ? (
    <span className="rounded border px-2 py-1 text-xs font-semibold" style={{ borderColor: "var(--color-accent)", color: "var(--color-accent)" }}>
      Injected demo case
    </span>
  ) : null;
}

export function ProvenanceNotice({ children }: { children?: ReactNode }) {
  return (
    <div className="space-y-3">
      <ProvenanceChips />
      {children}
    </div>
  );
}

export function CandidateProvenance({ candidate }: { candidate: CandidateDetail }) {
  return (
    <div className="space-y-2">
      <ProvenanceChips />
      <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
        Cloud: {candidate.cloud_source}; SIM_C1: {candidate.signal_sources.SIM_C1}; PROB_C2: {candidate.signal_sources.PROB_C2}; BCS: {candidate.signal_sources.BCS}.
      </p>
    </div>
  );
}
