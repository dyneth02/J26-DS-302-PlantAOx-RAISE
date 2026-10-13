"""Unit tests for curation.tiers conflict-resolution and evidence-tiering logic."""

from __future__ import annotations

import pandas as pd
import pytest

from plantaox.c2_pu.common.schemas import EvidenceTier
from plantaox.c2_pu.common.sequence import is_valid_peptide, make_peptide_id, normalize_sequence
from plantaox.c2_pu.curation.standardize import apply_length_filter, assign_peptide_ids
from plantaox.c2_pu.curation.tiers import build_positive_pool


@pytest.fixture
def toy_multiaop():
    return pd.DataFrame(
        {
            "sequence": ["AAAK", "HHHK", "CCCL", "DDDM", "EEEN"],
            "label": [1, 1, 1, 0, 1],
        }
    )


@pytest.fixture
def toy_anoxpepred():
    return pd.DataFrame(
        {
            # AAAK: assay-active, also claimed by Multi-AOP -> E1, corroborated
            # CCCL: assay-inactive, but Multi-AOP claims positive -> conflict
            # FFFP: assay-active, Multi-AOP-silent -> plain E1
            # FF:   assay-active but only 2 AA -> E1-eligible, length-excluded
            # GGGQ: assay-inactive, Multi-AOP-silent -> clean external control
            "sequence": ["AAAK", "CCCL", "FFFP", "FF", "GGGQ"],
            "frs": [1, 0, 1, 1, 0],
            "chelator": [0, 0, 0, 0, 0],
            "source": ["10.1/a", "10.1/b", "10.1/c", "10.1/d", "10.1/e"],
        }
    )


def test_e1_assay_confirmed_takes_precedence(toy_multiaop, toy_anoxpepred):
    positive_df, conflict_df, control_df, summary = build_positive_pool(
        toy_multiaop, toy_anoxpepred
    )
    row = positive_df.set_index("sequence").loc["AAAK"]
    assert row["evidence_tier"] == EvidenceTier.E1.value
    assert row["evidence_basis"] == "anoxpepred_assay"
    assert row["in_multiaop"] and row["in_anoxpepred"]


def test_conflict_excluded_not_reclassified_as_e3(toy_multiaop, toy_anoxpepred):
    positive_df, conflict_df, control_df, summary = build_positive_pool(
        toy_multiaop, toy_anoxpepred
    )
    assert "CCCL" not in set(positive_df["sequence"])
    assert "CCCL" in set(conflict_df["sequence"])
    row = conflict_df.set_index("sequence").loc["CCCL"]
    assert row["resolution"] == "excluded_pending_manual_review"
    assert bool(row["external_control_candidate"]) is True
    assert bool(row["manual_review_required"]) is True
    # never silently promoted to E3
    assert not (positive_df["sequence"] == "CCCL").any()


def test_multiaop_only_defaults_to_e2_provisional(toy_multiaop, toy_anoxpepred):
    positive_df, conflict_df, control_df, summary = build_positive_pool(
        toy_multiaop, toy_anoxpepred
    )
    row = positive_df.set_index("sequence").loc["EEEN"]
    assert row["evidence_tier"] == EvidenceTier.E2.value
    assert row["assay_type"] == "unknown"
    assert row["assay_verified"] == "unknown"
    assert row["provenance_status"] == "source_unresolved"


def test_multiaop_label_zero_never_enters_positive_pool(toy_multiaop, toy_anoxpepred):
    positive_df, conflict_df, control_df, summary = build_positive_pool(
        toy_multiaop, toy_anoxpepred
    )
    assert "DDDM" not in set(positive_df["sequence"])


def test_length_filter_excludes_short_and_long_sequences(toy_multiaop, toy_anoxpepred):
    positive_df, conflict_df, control_df, summary = build_positive_pool(
        toy_multiaop, toy_anoxpepred
    )
    # "FF" (len 2) is assay-active in AnOxPePred but shorter than the 3 AA floor
    assert "FF" not in set(positive_df["sequence"])
    assert summary["n_length_excluded"] == 1


def test_clean_vs_conflicted_external_control_are_disjoint(toy_multiaop, toy_anoxpepred):
    positive_df, conflict_df, control_df, summary = build_positive_pool(
        toy_multiaop, toy_anoxpepred
    )
    assert set(control_df["sequence"]).isdisjoint(set(conflict_df["sequence"]))
    assert "GGGQ" in set(control_df["sequence"])  # inactive, uncontested
    assert "CCCL" in set(conflict_df["sequence"])  # inactive, but contested


def test_summary_counts_are_internally_consistent(toy_multiaop, toy_anoxpepred):
    positive_df, conflict_df, control_df, summary = build_positive_pool(
        toy_multiaop, toy_anoxpepred
    )
    assert summary["n_accepted_positives"] == len(positive_df)
    assert summary["n_conflict_excluded"] == len(conflict_df)
    assert (
        summary["n_external_control_clean"] + summary["n_external_control_conflict_candidates"]
        >= summary["n_external_control_clean"]
    )


def test_sequence_helpers():
    assert normalize_sequence(" aak \n") == "AAK"
    assert is_valid_peptide("AAK") is True
    assert is_valid_peptide("AA") is False  # below 3 AA floor
    assert is_valid_peptide("AAX") is False  # non-standard residue
    assert make_peptide_id("AAK") == make_peptide_id("AAK")  # deterministic


def test_apply_length_filter_and_assign_ids():
    kept, dropped = apply_length_filter({"AA", "AAA", "A" * 51})
    assert kept == {"AAA"}
    assert dropped == {"AA", "A" * 51}
    ids = assign_peptide_ids(kept)
    assert set(ids.keys()) == kept
    assert all(v.startswith("AOP-") for v in ids.values())
