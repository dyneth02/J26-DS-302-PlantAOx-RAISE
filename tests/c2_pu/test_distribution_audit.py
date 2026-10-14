"""Tests for curation/distribution_audit.py (Bucket 2.5)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.curation.distribution_audit import (
    amino_acid_composition,
    aromaticity,
    compare_pools_ks,
    gravy,
    molecular_weight,
    net_charge_at_ph,
    pool_descriptor_table,
)


def test_molecular_weight_matches_known_value_for_a_simple_peptide():
    # Glycylglycine (GG): 2*57.0519 + 18.0153 = 132.1191, a textbook value.
    assert molecular_weight("GG") == pytest.approx(132.1191, abs=0.01)


def test_gravy_is_mean_kyte_doolittle_hydropathy():
    # A=1.8, G=-0.4 -> mean = 0.7
    assert gravy("AG") == pytest.approx(0.7, abs=1e-9)


def test_aromaticity_counts_only_f_w_y():
    assert aromaticity("FWYAG") == pytest.approx(3 / 5)
    assert aromaticity("AAAA") == 0.0


def test_net_charge_at_ph7_is_positive_for_a_lysine_rich_peptide():
    # Lysine-rich short peptide should be net positive at pH 7.
    assert net_charge_at_ph("KKKK", ph=7.0) > 0


def test_net_charge_at_ph7_is_negative_for_an_aspartate_rich_peptide():
    assert net_charge_at_ph("DDDD", ph=7.0) < 0


def test_amino_acid_composition_sums_to_one_and_counts_correctly():
    comp = amino_acid_composition(["AAG", "GG"])
    # 5 residues total: A=2, G=3
    assert comp["A"] == pytest.approx(2 / 5)
    assert comp["G"] == pytest.approx(3 / 5)
    assert sum(comp.values()) == pytest.approx(1.0)


def test_amino_acid_composition_handles_empty_input_without_crashing():
    comp = amino_acid_composition([])
    assert all(v == 0.0 for v in comp.values())


def test_pool_descriptor_table_has_one_row_per_sequence_with_expected_columns():
    df = pool_descriptor_table("test_pool", ["AAAA", "GGGGG"])
    assert len(df) == 2
    assert set(df.columns) >= {"pool", "sequence", "length", "molecular_weight", "net_charge_ph7", "gravy", "aromaticity"}
    assert list(df["length"]) == [4, 5]
    assert (df["pool"] == "test_pool").all()


def test_compare_pools_ks_detects_an_obviously_different_distribution():
    reference = pool_descriptor_table("FR1_positives", ["AAAA"] * 20)  # all identical, length 4
    similar = pool_descriptor_table("similar_pool", ["AAAA"] * 20)
    different = pool_descriptor_table("different_pool", ["WWWWWWWWWW"] * 20)  # very different
    result = compare_pools_ks(reference, {"similar": similar, "different": different}, columns=["length", "gravy"])

    similar_rows = result[result["pool"] == "similar"]
    different_rows = result[result["pool"] == "different"]
    # Identical distributions -> KS statistic 0, p-value 1.
    assert (similar_rows["ks_statistic"] == 0).all()
    # Very different distributions -> KS statistic should be large (close to 1).
    assert (different_rows["ks_statistic"] > 0.9).all()
