"""FR1 Bucket 1.5/1.6 acceptance checks against the real pipeline outputs.

Unlike test_fr1_acceptance.py these do not re-run the pipeline (CD-HIT/
GraphPart need the WSL pu_aop conda env, not just pip installs) -- they
validate the frozen-for-now output files directly. Skips cleanly if those
files aren't present (e.g. a teammate's checkout before WSL setup).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"
INTERIM_DIR = REPO_ROOT / "data" / "interim" / "c2_pu"

CDHIT_CLUSTERS_PATH = PROCESSED_DIR / "cdhit_clusters.tsv"
CDHIT_POOL_PATH = PROCESSED_DIR / "aop_positives_cdhit90.parquet"
GRAPHPART_SPLITS_PATH = PROCESSED_DIR / "graphpart_splits.csv"
GRAPHPART_EXCLUDED_PATH = PROCESSED_DIR / "graphpart_excluded_for_homology.csv"
GRAPHPART_REPORT_PATH = PROCESSED_DIR / "graphpart_splits_report.json"

pytestmark = pytest.mark.skipif(
    not (CDHIT_CLUSTERS_PATH.exists() and GRAPHPART_SPLITS_PATH.exists()),
    reason="CD-HIT/GraphPart outputs not present in this checkout",
)


def test_cdhit_output_sizes():
    clusters = pd.read_csv(CDHIT_CLUSTERS_PATH, sep="\t")
    pool = pd.read_parquet(CDHIT_POOL_PATH)
    assert clusters["peptide_id"].is_unique
    assert len(pool) == clusters["cluster_id"].nunique()
    # Pinned against the 2026-10-14 run: 1,205 provisional positives -> 925 clusters.
    assert len(pool) == 925


def test_cdhit_dropped_nothing():
    report = json.loads((PROCESSED_DIR / "cdhit_before_after_report.json").read_text())
    assert report["n_sequences_dropped_by_cdhit"] == 0


def test_graphpart_splits_cover_only_non_excluded_sequences():
    splits = pd.read_csv(GRAPHPART_SPLITS_PATH)
    excluded = pd.read_csv(GRAPHPART_EXCLUDED_PATH)
    pool = pd.read_parquet(CDHIT_POOL_PATH)

    ac_col = splits.columns[0]
    split_ids = set(splits[ac_col])
    excluded_ids = set(excluded["peptide_id"])
    pool_ids = set(pool["peptide_id"])

    assert split_ids.isdisjoint(excluded_ids)
    assert split_ids | excluded_ids == pool_ids


def test_graphpart_converged_with_zero_residual_homology_violations():
    report = json.loads(GRAPHPART_REPORT_PATH.read_text())
    rounds = report["removal_step_1"]
    last_round = rounds[sorted(rounds.keys(), key=int)[-1]]
    assert last_round["Connectivity"] == 0
    assert last_round["#Problematics"] == 0


def test_all_five_folds_present_and_nonempty():
    splits = pd.read_csv(GRAPHPART_SPLITS_PATH)
    fold_counts = splits["cluster"].value_counts()
    assert len(fold_counts) == 5
    assert (fold_counts > 0).all()
