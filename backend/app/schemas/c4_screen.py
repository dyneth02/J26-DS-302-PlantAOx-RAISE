from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class C4MetaResponse(BaseModel):
    ad_params: dict[str, Any]
    cloud: dict[str, Any]
    signal_sources: dict[str, str]
    spec_version: str | None
    embedding_manifest_summary: dict[str, Any]
    output_manifest_hash: str
    tag: str | None
    warnings: list[str]


class FunnelRow(BaseModel):
    plant: str
    proteins: int
    protein_exclusions: int = 0
    raw_fragments: int
    length_filtered: int
    composition_filtered: int
    deduplicated: int
    embedded: int = 0


class TierFraction(BaseModel):
    tier: int = Field(ge=1, le=3)
    fraction: float = Field(ge=0, le=1)
    n: int = Field(ge=0)


class TierBin(BaseModel):
    plant: str
    length_bin: Literal["3-10", "11-20"]
    tier: int = Field(ge=1, le=3)
    fraction: float = Field(ge=0, le=1)
    n: int = Field(ge=0)


class SensitivityFraction(TierFraction):
    label: str = "sensitivity, not production"


class TierSummaryResponse(BaseModel):
    plant: str | None
    overall: list[dict[str, Any]]
    by_length_bin: list[TierBin]
    mean_centering_sensitivity: list[dict[str, Any]] | None
    sensitivity_label: str = "sensitivity, not production"


class HistogramSeries(BaseModel):
    source: str
    counts: list[int]


class HistogramResponse(BaseModel):
    plant: str | None
    bins: int
    edges: list[float]
    cloud: HistogramSeries
    candidates: HistogramSeries
    t1: float
    t2: float
    cloud_source: str


class LengthCount(BaseModel):
    length: int
    candidate_count: int
    cloud_count: int


class LengthsResponse(BaseModel):
    candidate_source: str
    cloud_source: str
    distributions: list[LengthCount]


class CandidateRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    peptide_id: str
    sequence: str
    plant: str
    tier: int = Field(ge=1, le=3)
    d_AD: float
    CS: float
    rank: int | None = None
    length: int


class CandidatePage(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class CandidateDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    sequence: str
    peptide_id: str
    species: str
    plant: str
    provenance: list[dict[str, Any]]
    parent_accessions: list[str]
    enzymes: list[str]
    physicochemical: dict[str, float]
    SIM_C1: float | None
    PROB_C2: float | None
    evidence_tier: str | None
    tier: int
    d_AD: float
    CS: float
    rank: int | None
    BCS: float | None
    BCS_flag: str | None
    BCS_threshold_status: str = "C4-provisional"
    signal_sources: dict[str, str]
    cloud_source: str
    injected_demo_case: bool
    notice: str


class CandidateCardsResponse(BaseModel):
    plant: str
    cards: list[CandidateDetail]


class AbstainedCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    peptide_id: str
    sequence: str
    plant: str
    tier: Literal[3] = 3
    flag: Literal["RED"] = "RED"
    CS: Literal[0] = 0
    injected_demo_case: bool = False


class AbstainedPage(BaseModel):
    items: list[AbstainedCandidate]
    total: int
    page: int
    page_size: int
