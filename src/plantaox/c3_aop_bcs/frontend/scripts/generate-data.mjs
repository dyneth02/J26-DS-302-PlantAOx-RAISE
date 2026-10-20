import { createHash } from "node:crypto";
import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const frontendDirectory = resolve(scriptDirectory, "..");
const repositoryRoot = resolve(frontendDirectory, "../../../../");
const outputDirectory = join(frontendDirectory, "assets", "generated");

const sourcePaths = {
  cleaning: "data/processed/c3_aop_bcs/sequence_cleaning_report_v1.json",
  deduplication: "data/processed/c3_aop_bcs/cd_hit_deduplication_report_v1.json",
  eligibility: "data/processed/c3_aop_bcs/redox_eligibility_report_v1.json",
  perturbations: "data/processed/c3_aop_bcs/combined_perturbation_pipeline_report_v1.json",
  pilot: "data/processed/c3_aop_bcs/pp1_pilot_report_v1.json",
  pfr: "data/processed/c3_aop_bcs/pp1_pilot_dummy_pfr_report_v1.json",
  bcs: "data/processed/c3_aop_bcs/pp1_pilot_dummy_bcs_report_v1.json",
  sensitivity: "data/processed/c3_aop_bcs/pp1_pilot_dummy_delta_sensitivity_report_v1.json",
  countReview: "data/processed/c3_aop_bcs/pp1_pilot_perturbation_count_report_v1.json",
  inspection: "data/processed/c3_aop_bcs/pp1_manual_variant_inspection_v1.json",
  manifest: "data/processed/c3_aop_bcs/pp1_pilot_run_manifest_v1.json",
  predictorPriority: "src/plantaox/c3_aop_bcs/predictor_priority_v1.json",
};

const figureSources = [
  "data/processed/c3_aop_bcs/figures/pp1_pilot_absolute_delta_distributions_v1.svg",
  "data/processed/c3_aop_bcs/figures/pp1_pilot_score_examples_v1.svg",
  "data/processed/c3_aop_bcs/figures/pp1_pilot_metric_summary_v1.svg",
  "data/processed/c3_aop_bcs/figures/pp1_pilot_prediction_flip_comparison_v1.svg",
];

function repositoryPath(relativePath) {
  return join(repositoryRoot, ...relativePath.split("/"));
}

async function loadJson(relativePath) {
  return JSON.parse(await readFile(repositoryPath(relativePath), "utf8"));
}

async function sha256(relativePath) {
  const content = await readFile(repositoryPath(relativePath));
  return createHash("sha256").update(content).digest("hex");
}

await mkdir(outputDirectory, { recursive: true });
const source = Object.fromEntries(
  await Promise.all(Object.entries(sourcePaths).map(async ([key, path]) => [key, await loadJson(path)])),
);

const pfrByType = source.pfr.pfr.by_perturbation_type;
const primarySensitivity = source.sensitivity.threshold_results.find((row) => row.is_primary);
if (!primarySensitivity) throw new Error("Primary sensitivity result is missing.");

const data = {
  schemaVersion: "1.0",
  presentationId: "c3_aop_bcs_pp1_progress_presentation_v1",
  evidenceDate: source.manifest.run_date,
  classification: source.manifest.classification,
  configuration: {
    seed: source.manifest.configuration.random_seed,
    redoxResidues: source.manifest.configuration.redox_residues,
    primaryDelta: source.manifest.configuration.primary_delta,
    sensitivityDeltas: source.manifest.configuration.sensitivity_deltas,
    blosumMinimum: source.manifest.configuration.blosum62.minimum_score,
  },
  overview: {
    pilotSubjects: source.manifest.counts.peptides,
    pilotVariants: source.manifest.counts.perturbations_total,
    fullEligibleSubjects: source.perturbations.counts.input_peptide_count,
    fullVariants: source.perturbations.counts.accepted_variant_count,
  },
  datasetFunnel: [
    { label: "Standardized candidates", count: source.cleaning.counts.original_count, detail: "merged source records" },
    { label: "Clean unique sequences", count: source.cleaning.counts.retained_count, detail: "valid 3–50 aa peptides" },
    { label: "CD-HIT representatives", count: source.deduplication.counts.representative_count, detail: "90% identity clusters" },
    { label: "Redox-eligible subjects", count: source.eligibility.counts.eligible_count, detail: "contains W, Y, H, M or C" },
    { label: "PP1 pilot subjects", count: source.pilot.coverage.selected_subject_count, detail: "seeded coverage sample" },
  ],
  coverage: {
    lengthRange: `${source.pilot.coverage.sequence_length_min}–${source.pilot.coverage.sequence_length_max} aa`,
    distinctLengths: source.pilot.coverage.distinct_sequence_lengths,
    redoxResidues: Object.keys(source.pilot.coverage.redox_residue_subject_counts),
    evidenceTiers: Object.keys(source.pilot.coverage.evidence_tier_counts),
    maximumVariantShare: source.countReview.dominance_review.maximum_contributor.variant_share,
  },
  perturbations: [
    {
      id: "P1",
      title: "Redox disruption",
      subtitle: "Alanine scanning",
      question: "Does the score change when a redox-active residue is removed?",
      rule: "Replace each W/Y/H/M/C position with alanine.",
      fullCount: source.perturbations.counts.accepted_by_perturbation_type.P1,
      pilotCount: source.manifest.counts.perturbations_by_type.P1,
      tone: "coral",
    },
    {
      id: "P2",
      title: "Conservative control",
      subtitle: "BLOSUM62-guided",
      question: "Does the score remain stable under a similar-residue edit?",
      rule: `Use the highest eligible BLOSUM62 replacement with score ≥ ${source.manifest.configuration.blosum62.minimum_score}.`,
      fullCount: source.perturbations.counts.accepted_by_perturbation_type.P2,
      pilotCount: source.manifest.counts.perturbations_by_type.P2,
      tone: "teal",
    },
    {
      id: "P3",
      title: "Random control",
      subtitle: "Seeded substitution",
      question: "How does the response compare with a reproducible random edit?",
      rule: `Choose a different standard residue using master seed ${source.manifest.configuration.random_seed}.`,
      fullCount: source.perturbations.counts.accepted_by_perturbation_type.P3,
      pilotCount: source.manifest.counts.perturbations_by_type.P3,
      tone: "violet",
    },
  ],
  metrics: {
    primaryDelta: source.manifest.configuration.primary_delta,
    invarianceRate: source.bcs.components.invariance_rate.value,
    invariantCount: source.bcs.components.invariance_rate.invariant_p2_count,
    invariantDenominator: source.bcs.components.invariance_rate.evaluated_p2_count,
    falseSensitivityRate: source.bcs.components.false_sensitivity_rate.value,
    insufficientCount: source.bcs.components.false_sensitivity_rate.insufficient_response_p1_count,
    insufficientDenominator: source.bcs.components.false_sensitivity_rate.evaluated_p1_count,
    preliminaryBcs: source.bcs.result.preliminary_bcs,
    overallPfr: source.pfr.pfr.overall.prediction_flip_rate,
    flipCount: source.pfr.pfr.overall.flip_count,
    flipDenominator: source.pfr.pfr.overall.perturbation_count,
    pfrByType: Object.fromEntries(Object.entries(pfrByType).map(([key, value]) => [key, value.prediction_flip_rate])),
  },
  sensitivity: source.sensitivity.threshold_results.map((row) => ({
    delta: row.delta,
    primary: row.is_primary,
    ir: row.invariance_rate,
    fsr: row.false_sensitivity_rate,
    bcs: row.preliminary_bcs,
  })),
  examples: source.inspection.examples,
  predictors: source.predictorPriority.priorities.map((predictor) => ({
    id: predictor.predictor_id,
    name: predictor.display_name,
    tier: predictor.tier,
    order: predictor.integration_order,
    readiness: predictor.readiness,
    status: predictor.integration_status,
    rationale: predictor.rationale,
  })),
  provenance: {
    runId: source.manifest.run_id,
    runDate: source.manifest.run_date,
    datasetVersion: source.manifest.dataset.version,
    predictorVersion: `${source.manifest.predictor.predictor_id}@${source.manifest.predictor.version}`,
    codeCommit: source.manifest.code.git_commit,
    validationStatus: source.manifest.validation.status,
    missingScores: source.manifest.failures_and_missing_scores.pilot_perturbations_without_finite_scores,
    sourceArtifacts: await Promise.all(Object.entries(sourcePaths).map(async ([label, path]) => ({
      label,
      path,
      sha256: await sha256(path),
    }))),
  },
  figures: [],
};

for (const relativePath of figureSources) {
  const fileName = relativePath.split("/").at(-1);
  const destination = join(outputDirectory, fileName);
  await copyFile(repositoryPath(relativePath), destination);
  data.figures.push({
    sourcePath: relativePath,
    file: `assets/generated/${fileName}`,
    sha256: await sha256(relativePath),
  });
}

const outputPath = join(outputDirectory, "presentation-data.json");
await writeFile(outputPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
console.log(`Generated ${relative(repositoryRoot, outputPath)} from ${Object.keys(sourcePaths).length} versioned reports.`);
