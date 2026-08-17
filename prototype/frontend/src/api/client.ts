import axios from "axios";

const API_BASE_URL = "http://localhost:8000/api";

const client = axios.create({ baseURL: API_BASE_URL });

export const getProjectMeta = () => client.get("/project").then((r) => r.data);

export const c1Api = {
  summary: () => client.get("/c1/summary").then((r) => r.data),
  umap: () => client.get("/c1/umap").then((r) => r.data),
  prototypes: () => client.get("/c1/prototypes").then((r) => r.data),
  retrieval: () => client.get("/c1/retrieval").then((r) => r.data),
  cloudStats: () => client.get("/c1/cloud-stats").then((r) => r.data),
  dataSufficiency: () => client.get("/c1/data-sufficiency").then((r) => r.data),
  scalingAblation: () => client.get("/c1/scaling-ablation").then((r) => r.data),
  trainedSummary: () => client.get("/c1/trained-summary").then((r) => r.data),
  trainedEmbedding: () => client.get("/c1/trained-embedding").then((r) => r.data),
  trainedPrototypes: () => client.get("/c1/trained-prototypes").then((r) => r.data),
  trainedRetrieval: () => client.get("/c1/trained-retrieval").then((r) => r.data),
  ablationComparison: () => client.get("/c1/ablation-comparison").then((r) => r.data),
  trainingHistory: () => client.get("/c1/training-history").then((r) => r.data),
  statisticalTests: () => client.get("/c1/statistical-tests").then((r) => r.data),
  tier3Summary: () => client.get("/c1/tier3-summary").then((r) => r.data),
  improvementExperiment: () => client.get("/c1/improvement-experiment").then((r) => r.data),
};

export const c2Api = {
  summary: () => client.get("/c2/summary").then((r) => r.data),
  pools: () => client.get("/c2/pools").then((r) => r.data),
  rnis: () => client.get("/c2/rnis").then((r) => r.data),
  classificationMetrics: () => client.get("/c2/classification-metrics").then((r) => r.data),
  calibration: () => client.get("/c2/calibration").then((r) => r.data),
  stageComparison: () => client.get("/c2/stage-comparison").then((r) => r.data),
};

export const c3Api = {
  summary: () => client.get("/c3/summary").then((r) => r.data),
  predictors: () => client.get("/c3/predictors").then((r) => r.data),
  reliabilityFlags: () => client.get("/c3/reliability-flags").then((r) => r.data),
  bcs: (predictor: string) => client.get("/c3/bcs", { params: { predictor } }).then((r) => r.data),
  examplePerturbation: (predictor: string) =>
    client.get("/c3/example-perturbation", { params: { predictor } }).then((r) => r.data),
  perturbationResults: (predictor: string) =>
    client.get("/c3/perturbation-results", { params: { predictor } }).then((r) => r.data),
};

export const c4Api = {
  summary: () => client.get("/c4/summary").then((r) => r.data),
  candidates: () => client.get("/c4/candidates").then((r) => r.data),
  adSummary: () => client.get("/c4/ad-summary").then((r) => r.data),
  parrs: () => client.get("/c4/parrs").then((r) => r.data),
  pdss: () => client.get("/c4/pdss").then((r) => r.data),
  arr: () => client.get("/c4/arr").then((r) => r.data),
  evidenceCards: () => client.get("/c4/evidence-cards").then((r) => r.data),
};
