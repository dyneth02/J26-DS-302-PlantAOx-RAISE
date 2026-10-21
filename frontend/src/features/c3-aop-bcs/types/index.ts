export interface HealthResponse { status: "ok"; component: "c3_aop_bcs"; api_version: string; run_id: string; artifact_count: number }
export interface Classification { pilot_preliminary: boolean; software_testing_only: boolean; scientific_result: boolean; real_predictor_scoring_completed: boolean; warning: string }
export interface Configuration { seed: number; redoxResidues: string[]; primaryDelta: number; sensitivityDeltas: number[]; blosumMinimum: number }
export interface Overview { pilotSubjects: number; pilotVariants: number; fullEligibleSubjects: number; fullVariants: number }
export interface DatasetStage { label: string; count: number; detail: string }
export interface Coverage { lengthRange: string; distinctLengths: number; redoxResidues: string[]; evidenceTiers: string[]; maximumVariantShare: number }
export interface Perturbation { id: "P1" | "P2" | "P3"; title: string; subtitle: string; question: string; rule: string; fullCount: number; pilotCount: number; tone: string }
export interface Metrics { primaryDelta: number; invarianceRate: number; invariantCount: number; invariantDenominator: number; falseSensitivityRate: number; insufficientCount: number; insufficientDenominator: number; preliminaryBcs: number; overallPfr: number; flipCount: number; flipDenominator: number; pfrByType: Record<string, number> }
export interface SensitivityResult { delta: number; primary: boolean; ir: number; fsr: number; bcs: number }
export interface VariantExample { variant_id: string; sequence_id: string; perturbation_type: "P1" | "P2" | "P3"; original_sequence: string; position: number; original_residue: string; substituted_residue: string; mutation: string; perturbed_sequence: string; blosum62_score: number | null; random_seed: number | null; original_score: number; perturbed_score: number; delta_score: number; absolute_delta_score: number; inspection_status: string }
export interface PredictorStatus { id: string; name: string; tier: "primary" | "secondary"; order: number; readiness: string; status: string; rationale: string }
export interface SourceArtifact { label: string; path: string; sha256: string }
export interface Provenance { runId: string; runDate: string; datasetVersion: string; predictorVersion: string; codeCommit: string; validationStatus: string; missingScores: number; sourceArtifacts: SourceArtifact[] }
export interface FigureEvidence { sourcePath: string; file: string; sha256: string }
export interface DeltaDistributionBin { label: string; binStart: number; binEnd: number; binMidpoint: number; P1: number; P2: number; P3: number }
export interface ScoreExamplePoint { label: string; perturbationType: "P1" | "P2" | "P3"; original: number; perturbed: number }
export interface MetricChartPoint { metric: "IR" | "FSR" | "BCS" | "PFR"; value: number }
export interface PredictionFlipPoint { type: "P1" | "P2" | "P3"; rate: number; flips: number; total: number }
export interface ChartSource { path: string; sha256: string; recordCount: number }
export interface ChartData { absoluteDeltaDistribution: DeltaDistributionBin[]; scoreExamples: ScoreExamplePoint[]; metricSummary: MetricChartPoint[]; predictionFlips: PredictionFlipPoint[]; source: ChartSource }

export interface DashboardPayload {
  schemaVersion: string;
  apiVersion: string;
  evidenceDate: string;
  classification: Classification;
  configuration: Configuration;
  overview: Overview;
  datasetFunnel: DatasetStage[];
  coverage: Coverage;
  perturbations: Perturbation[];
  metrics: Metrics;
  sensitivity: SensitivityResult[];
  examples: VariantExample[];
  predictors: PredictorStatus[];
  provenance: Provenance;
  figures: FigureEvidence[];
  chartData: ChartData;
}
