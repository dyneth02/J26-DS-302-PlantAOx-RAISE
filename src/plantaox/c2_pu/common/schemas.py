"""Record/row schemas for the positive pool, conflict log, and data registry (FR1)."""

from __future__ import annotations

from enum import Enum


class EvidenceTier(str, Enum):
    """E1/E2/E3 + CONFLICT per PU_AOP_RESEARCH_CONTEXT.md and the proposal's SO1."""

    E1 = "E1"  # AOP-specific experimental assay documented (AnOxPePred FRS/Chelator readout)
    E2 = "E2"  # antioxidant-annotated positive with no per-record assay documentation
    E3 = "E3"  # bioactivity-adjacent; excluded from positives, treated as unlabeled
    CONFLICT = "CONFLICT"  # contradictory cross-source evidence; excluded pending manual review


# Columns written to data/processed/c2_pu/aop_positives_provisional.csv
POSITIVE_POOL_COLUMNS = [
    "peptide_id",
    "sequence",
    "length",
    "evidence_tier",
    "evidence_basis",
    "assay_type",
    "assay_verified",
    "provenance_status",
    "in_multiaop",
    "in_anoxpepred",
    "multiaop_label",
    "anoxpepred_frs",
    "anoxpepred_chelator",
    "anoxpepred_source",
]

# Columns written to data/interim/c2_pu/label_conflicts_anox_vs_multiaop.csv
CONFLICT_LOG_COLUMNS = [
    "peptide_id",
    "sequence",
    "length",
    "multiaop_label",
    "anoxpepred_frs",
    "anoxpepred_chelator",
    "anoxpepred_source",
    "conflict_type",
    "evidence_status",
    "resolution",
    "resolution_reason",
    "external_control_candidate",
    "manual_review_required",
]

# Columns written to data/processed/c2_pu/anoxpepred_inactives_clean.csv
EXTERNAL_CONTROL_COLUMNS = [
    "peptide_id",
    "sequence",
    "length",
    "anoxpepred_source",
    "evidence_status",
]
