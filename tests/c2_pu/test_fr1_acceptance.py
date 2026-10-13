"""FR1 acceptance checks against the FULL raw data files (not a sample), per
AGENTS.md's validation rule #1. Skips cleanly if the raw files aren't present
(e.g. a teammate's checkout without the data placed yet).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from plantaox.c2_pu.curation.adapters import load_anoxpepred, load_multiaop
from plantaox.c2_pu.curation.tiers import build_positive_pool

REPO_ROOT = Path(__file__).resolve().parents[2]
MULTIAOP_PATH = REPO_ROOT / "data" / "raw" / "c2_pu" / "Multi-AOP" / "combined_data.csv"
ANOXPEPRED_PATH = (
    REPO_ROOT / "data" / "raw" / "c2_pu" / "AnOxPePred" / "Supplementary_Data_S1_Marcatili.csv"
)

pytestmark = pytest.mark.skipif(
    not (MULTIAOP_PATH.exists() and ANOXPEPRED_PATH.exists()),
    reason="raw FR1 source files not present in this checkout",
)


@pytest.fixture(scope="module")
def built_pool():
    mo_df = load_multiaop(MULTIAOP_PATH)
    an_df = load_anoxpepred(ANOXPEPRED_PATH)
    return build_positive_pool(mo_df, an_df)


def test_known_conflict_count_on_full_file(built_pool):
    # Pinned against the full dataset on 2026-10-14: 179 Multi-AOP-positive
    # sequences contradicted by AnOxPePred's own FRS=0/Chelator=0 assay call.
    _, conflict_df, _, summary = built_pool
    assert summary["n_conflict_excluded"] == 179
    assert len(conflict_df) == 179


def test_known_external_control_split_on_full_file(built_pool):
    # 217 total AnOxPePred true-inactives; 179 of those are also contested by
    # Multi-AOP, leaving only 38 as uncontested external-control candidates.
    _, conflict_df, control_df, summary = built_pool
    assert summary["n_external_control_clean"] == 38
    assert len(control_df) == 38


def test_no_conflict_sequence_leaks_into_positive_pool_or_control(built_pool):
    positive_df, conflict_df, control_df, _ = built_pool
    conflict_seqs = set(conflict_df["sequence"])
    assert conflict_seqs.isdisjoint(set(positive_df["sequence"]))
    assert conflict_seqs.isdisjoint(set(control_df["sequence"]))


def test_positive_pool_size_meets_so1_floor(built_pool):
    # SO1 target: >= 800 verified AOP sequences (pre-CD-HIT; see run.py docstring).
    positive_df, _, _, summary = built_pool
    assert summary["n_accepted_positives"] >= 800
    assert len(positive_df) == summary["n_accepted_positives"]


def test_all_positive_sequences_are_within_shared_length_window(built_pool):
    positive_df, _, _, _ = built_pool
    assert positive_df["length"].between(3, 50).all()


def test_no_duplicate_peptide_ids(built_pool):
    positive_df, conflict_df, control_df, _ = built_pool
    for df in (positive_df, conflict_df, control_df):
        assert df["peptide_id"].is_unique


def test_two_builds_from_the_same_input_agree_on_content(built_pool):
    # build_positive_pool uses set operations internally; this guards against
    # Python's per-process hash-seed randomization silently changing which
    # rows come out (content, not just order -- run.py's sort_values handles
    # order separately). Rebuild once more from the same inputs and diff.
    mo_df = load_multiaop(MULTIAOP_PATH)
    an_df = load_anoxpepred(ANOXPEPRED_PATH)
    positive_df, conflict_df, control_df, summary = built_pool
    positive_df2, conflict_df2, control_df2, summary2 = build_positive_pool(mo_df, an_df)
    assert summary == summary2
    assert set(positive_df["sequence"]) == set(positive_df2["sequence"])
    assert set(conflict_df["sequence"]) == set(conflict_df2["sequence"])
    assert set(control_df["sequence"]) == set(control_df2["sequence"])
