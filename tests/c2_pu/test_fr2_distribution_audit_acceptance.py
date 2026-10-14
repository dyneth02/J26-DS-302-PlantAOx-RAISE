"""FR2 Bucket 2.5 acceptance checks against the real, full distribution/
shortcut-bias audit artifacts. Skips cleanly if not present.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

DESCRIPTOR_TABLE_PATH = PROCESSED_DIR / "distribution_descriptor_table.csv"
AA_COMPOSITION_PATH = PROCESSED_DIR / "distribution_aa_composition.csv"
KS_COMPARISON_PATH = PROCESSED_DIR / "distribution_ks_comparison.csv"
SHORTCUT_REPORT_PATH = PROCESSED_DIR / "distribution_shortcut_report.json"

pytestmark = pytest.mark.skipif(
    not DESCRIPTOR_TABLE_PATH.exists(), reason="FR2 distribution audit not present in this checkout"
)


def test_descriptor_table_covers_every_pool_with_correct_counts():
    df = pd.read_csv(DESCRIPTOR_TABLE_PATH)
    counts = df["pool"].value_counts()
    assert counts["FR1_positives"] == 1205
    assert counts["C1_v3"] == 5000
    assert counts["C2_v2"] == 2000
    assert counts["C3_union"] == 2325


def test_aa_composition_rows_sum_to_one_per_pool():
    df = pd.read_csv(AA_COMPOSITION_PATH, index_col=0)
    sums = df.sum(axis=1)
    for pool, total in sums.items():
        assert total == pytest.approx(1.0, abs=1e-6), pool


def test_ks_comparison_covers_all_challenge_pools_and_descriptors():
    df = pd.read_csv(KS_COMPARISON_PATH)
    assert set(df["pool"].unique()) == {"C1_v3", "C2_v2", "C3_union"}
    assert set(df["descriptor"].unique()) == {
        "length", "molecular_weight", "net_charge_ph7", "gravy", "aromaticity",
    }
    assert (df["ks_statistic"] >= 0).all() and (df["ks_statistic"] <= 1).all()
    assert (df["p_value"] >= 0).all() and (df["p_value"] <= 1).all()


def test_shortcut_report_documents_fr1_organism_gap_rather_than_assuming_no_bias():
    report = json.loads(SHORTCUT_REPORT_PATH.read_text())
    assert report["fr1_positives"]["organism_metadata_available"] is False
    assert "c1_v3" in report
    assert report["c1_v3"]["n_unique_organisms"] > 1
    # No single organism should dominate so heavily it reads as a shortcut
    # on its own -- a sanity check on the number, not a claim it's safe.
    assert report["c1_v3"]["max_single_organism_share"] < 0.5
