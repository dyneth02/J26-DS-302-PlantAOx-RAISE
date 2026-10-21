import { LimitationsPanel } from "@/components/research/LimitationsPanel";

export const SCIENTIFIC_LIMITATIONS = [
  "Every score and metric shown was produced by the deterministic software smoke-test dummy.",
  "These values validate software flow only; they do not measure biological or predictor reliability.",
  "All five scientific predictors remain not integrated until a retained real score is verified.",
];

export function ScientificBoundary() {
  return <LimitationsPanel items={SCIENTIFIC_LIMITATIONS} />;
}
