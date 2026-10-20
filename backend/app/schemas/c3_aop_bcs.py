from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class C3HealthResponse(BaseModel):
    status: Literal["ok"]
    component: Literal["c3_aop_bcs"]
    api_version: str
    run_id: str
    artifact_count: int = Field(ge=0)


class Classification(BaseModel):
    pilot_preliminary: bool
    software_testing_only: bool
    scientific_result: bool
    real_predictor_scoring_completed: bool
    warning: str


class Configuration(BaseModel):
    seed: int
    redoxResidues: list[str]
    primaryDelta: float
    sensitivityDeltas: list[float]
    blosumMinimum: int


class Overview(BaseModel):
    pilotSubjects: int = Field(ge=0)
    pilotVariants: int = Field(ge=0)
    fullEligibleSubjects: int = Field(ge=0)
    fullVariants: int = Field(ge=0)


class DatasetStage(BaseModel):
    label: str
    count: int = Field(ge=0)
    detail: str


class Coverage(BaseModel):
    lengthRange: str
    distinctLengths: int = Field(ge=0)
    redoxResidues: list[str]
    evidenceTiers: list[str]
    maximumVariantShare: float = Field(ge=0, le=1)


class Perturbation(BaseModel):
    id: Literal["P1", "P2", "P3"]
    title: str
    subtitle: str
    question: str
    rule: str
    fullCount: int = Field(ge=0)
    pilotCount: int = Field(ge=0)
    tone: str


class Metrics(BaseModel):
    primaryDelta: float
    invarianceRate: float = Field(ge=0, le=1)
    invariantCount: int = Field(ge=0)
    invariantDenominator: int = Field(ge=0)
    falseSensitivityRate: float = Field(ge=0, le=1)
    insufficientCount: int = Field(ge=0)
    insufficientDenominator: int = Field(ge=0)
    preliminaryBcs: float = Field(ge=0, le=1)
    overallPfr: float = Field(ge=0, le=1)
    flipCount: int = Field(ge=0)
    flipDenominator: int = Field(ge=0)
    pfrByType: dict[str, float]


class SensitivityResult(BaseModel):
    delta: float
    primary: bool
    ir: float = Field(ge=0, le=1)
    fsr: float = Field(ge=0, le=1)
    bcs: float = Field(ge=0, le=1)


class VariantExample(BaseModel):
    model_config = ConfigDict(extra="allow")

    variant_id: str
    sequence_id: str
    perturbation_type: Literal["P1", "P2", "P3"]
    original_sequence: str
    position: int = Field(ge=1)
    original_residue: str
    substituted_residue: str
    mutation: str
    perturbed_sequence: str
    blosum62_score: float | None
    random_seed: int | None
    original_score: float
    perturbed_score: float
    delta_score: float
    absolute_delta_score: float = Field(ge=0)
    changed_positions: list[int]
    checks: dict[str, bool]
    inspection_status: str


class PredictorStatus(BaseModel):
    id: str
    name: str
    tier: Literal["primary", "secondary"]
    order: int = Field(ge=1)
    readiness: str
    status: str
    rationale: str


class SourceArtifact(BaseModel):
    label: str
    path: str
    sha256: str


class Provenance(BaseModel):
    runId: str
    runDate: str
    datasetVersion: str
    predictorVersion: str
    codeCommit: str
    validationStatus: str
    missingScores: int = Field(ge=0)
    sourceArtifacts: list[SourceArtifact]


class FigureEvidence(BaseModel):
    sourcePath: str
    file: str
    sha256: str


class DashboardResponse(BaseModel):
    schemaVersion: str
    apiVersion: str
    evidenceDate: str
    classification: Classification
    configuration: Configuration
    overview: Overview
    datasetFunnel: list[DatasetStage]
    coverage: Coverage
    perturbations: list[Perturbation]
    metrics: Metrics
    sensitivity: list[SensitivityResult]
    examples: list[VariantExample]
    predictors: list[PredictorStatus]
    provenance: Provenance
    figures: list[FigureEvidence]


class DashboardSectionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    section: Literal[
        "overview", "dataset", "perturbations", "metrics", "explorer", "predictors", "evidence"
    ]

