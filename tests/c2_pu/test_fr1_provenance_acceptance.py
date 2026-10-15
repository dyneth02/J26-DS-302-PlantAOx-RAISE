"""FR1 Bucket 1.7 acceptance: every retained sequence has full source
provenance, and peptide IDs form an unbroken, duplicate-free chain from the
raw-source merge through CD-HIT clustering to the final GraphPart split.

Validates the already-produced files directly (does not re-run the
pipeline -- see test_fr1_reproducibility.py for that). Skips cleanly if
those files aren't present.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = REPO_ROOT / "data" / "interim" / "c2_pu"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

PROVISIONAL_POOL_PATH = PROCESSED_DIR / "aop_positives_provisional.parquet"
CDHIT_POOL_PATH = PROCESSED_DIR / "aop_positives_cdhit90.parquet"
CDHIT_CLUSTERS_PATH = PROCESSED_DIR / "cdhit_clusters.tsv"
GRAPHPART_SPLITS_PATH = PROCESSED_DIR / "graphpart_splits.csv"
GRAPHPART_EXCLUDED_PATH = PROCESSED_DIR / "graphpart_excluded_for_homology.csv"
CONFLICT_LOG_PATH = INTERIM_DIR / "label_conflicts_anox_vs_multiaop.csv"
EXTERNAL_CONTROL_PATH = PROCESSED_DIR / "anoxpepred_inactives_clean.csv"

_REQUIRED_FILES = [
    PROVISIONAL_POOL_PATH,
    CDHIT_POOL_PATH,
    CDHIT_CLUSTERS_PATH,
    GRAPHPART_SPLITS_PATH,
    GRAPHPART_EXCLUDED_PATH,
]

pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in _REQUIRED_FILES), reason="FR1 pipeline outputs not present in this checkout"
)


@pytest.fixture(scope="module")
def provisional_pool():
    return pd.read_parquet(PROVISIONAL_POOL_PATH)


@pytest.fixture(scope="module")
def cdhit_pool():
    return pd.read_parquet(CDHIT_POOL_PATH)


@pytest.fixture(scope="module")
def cdhit_clusters():
    return pd.read_csv(CDHIT_CLUSTERS_PATH, sep="\t")


@pytest.fixture(scope="module")
def graphpart_splits():
    df = pd.read_csv(GRAPHPART_SPLITS_PATH)
    return df.rename(columns={df.columns[0]: "peptide_id"})


@pytest.fixture(scope="module")
def graphpart_excluded():
    return pd.read_csv(GRAPHPART_EXCLUDED_PATH)


# ---------------------------------------------------------------------------
# Provenance completeness: every row traces to a named, typed evidence source
# ---------------------------------------------------------------------------


def test_every_e1_row_has_anoxpepred_assay_fields(provisional_pool):
    e1 = provisional_pool[provisional_pool["evidence_tier"] == "E1"]
    assert len(e1) > 0
    assert e1["in_anoxpepred"].all()
    assert e1["anoxpepred_frs"].notna().all()
    assert e1["anoxpepred_chelator"].notna().all()
    assert e1["anoxpepred_source"].notna().all()
    assert (e1["evidence_basis"] == "anoxpepred_assay").all()


def test_every_e2_row_has_multiaop_fields_and_no_anoxpepred_row(provisional_pool):
    e2 = provisional_pool[provisional_pool["evidence_tier"] == "E2"]
    assert len(e2) > 0
    assert e2["in_multiaop"].all()
    assert (~e2["in_anoxpepred"]).all()
    assert (e2["multiaop_label"] == 1).all()
    assert (e2["evidence_basis"] == "benchmark_positive_annotation").all()
    assert (e2["assay_verified"] == "unknown").all()


def test_every_row_is_either_e1_or_e2_no_untiered_rows(provisional_pool):
    assert set(provisional_pool["evidence_tier"].unique()) <= {"E1", "E2"}
    assert provisional_pool["evidence_tier"].notna().all()


def test_no_row_is_sourceless(provisional_pool):
    # Every accepted positive must trace to at least one named raw source.
    assert (provisional_pool["in_multiaop"] | provisional_pool["in_anoxpepred"]).all()


# ---------------------------------------------------------------------------
# Chain of custody: peptide IDs match exactly at every stage boundary
# ---------------------------------------------------------------------------


def test_cdhit_clusters_cover_exactly_the_provisional_pool(provisional_pool, cdhit_clusters):
    assert set(cdhit_clusters["peptide_id"]) == set(provisional_pool["peptide_id"])


def test_cdhit_representatives_match_the_reduced_pool(cdhit_pool, cdhit_clusters):
    rep_ids = set(cdhit_clusters.loc[cdhit_clusters["is_representative"], "peptide_id"])
    assert rep_ids == set(cdhit_pool["peptide_id"])


def test_graphpart_splits_plus_excluded_cover_exactly_the_cdhit_pool(
    cdhit_pool, graphpart_splits, graphpart_excluded
):
    covered = set(graphpart_splits["peptide_id"]) | set(graphpart_excluded["peptide_id"])
    assert covered == set(cdhit_pool["peptide_id"])


@pytest.mark.parametrize(
    "fixture_name",
    ["provisional_pool", "cdhit_pool", "cdhit_clusters", "graphpart_splits", "graphpart_excluded"],
)
def test_no_duplicate_peptide_ids_at_any_stage(fixture_name, request):
    df = request.getfixturevalue(fixture_name)
    if fixture_name == "cdhit_clusters":
        # cdhit_clusters.tsv is a cluster MEMBERSHIP map (one row per member,
        # many members per cluster) -- the invariant there is "every
        # (cluster_id, peptide_id) pair is unique", not "every peptide_id is
        # unique", since a peptide_id appears exactly once as a member of
        # exactly one cluster.
        assert not df.duplicated(subset=["cluster_id", "peptide_id"]).any()
        assert df["peptide_id"].is_unique  # still true: no peptide in 2 clusters
    else:
        assert df["peptide_id"].is_unique


# ---------------------------------------------------------------------------
# No contamination: excluded/conflicted sequences never resurface downstream
# ---------------------------------------------------------------------------


def test_conflicts_and_external_control_absent_from_final_graphpart_pool(
    cdhit_pool, graphpart_splits, graphpart_excluded
):
    conflict_seqs = set(pd.read_csv(CONFLICT_LOG_PATH)["sequence"])
    control_seqs = set(pd.read_csv(EXTERNAL_CONTROL_PATH)["sequence"])
    # graphpart_splits.csv only carries peptide_id -- join back to cdhit_pool
    # for sequences; graphpart_excluded already carries its own.
    id_to_seq = dict(zip(cdhit_pool["peptide_id"], cdhit_pool["sequence"]))
    final_seqs = {id_to_seq[pid] for pid in graphpart_splits["peptide_id"]} | set(
        graphpart_excluded["sequence"]
    )
    assert final_seqs.isdisjoint(conflict_seqs)
    assert final_seqs.isdisjoint(control_seqs)
