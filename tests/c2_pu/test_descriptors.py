"""Tests for Bucket 3.1 -- src/plantaox/c2_pu/common/descriptors.py.

Covers the acceptance-checklist items from Task 3.1: exactly 15 approved
descriptors, stable names/order, reference-sequence correctness, length
boundaries, invalid-alphabet handling, batch/single equivalence, and
finite-value guarantees.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.common import descriptors as d


# ---------------------------------------------------------------------------
# Schema contract
# ---------------------------------------------------------------------------


def test_schema_has_exactly_15_descriptors():
    assert len(d.DESCRIPTOR_NAMES) == 15
    assert len(set(d.DESCRIPTOR_NAMES)) == 15  # no duplicate names


def test_compute_descriptors_returns_exactly_the_schema_keys():
    result = d.compute_descriptors("ACDEFGHIK")
    assert set(result.keys()) == set(d.DESCRIPTOR_NAMES)
    assert len(result) == 15


def test_batch_output_column_order_matches_schema_order_after_id_and_sequence():
    df = d.compute_descriptors_batch(["P1", "P2"], ["ACDEFGHIK", "KLMNPQRST"])
    assert list(df.columns) == ["peptide_id", "sequence"] + list(d.DESCRIPTOR_NAMES)


# ---------------------------------------------------------------------------
# Reference-value correctness (hand-calculated / textbook values)
# ---------------------------------------------------------------------------


def test_molecular_weight_matches_known_value_for_glycylglycine():
    assert d.molecular_weight("GG") == pytest.approx(132.1191, abs=0.01)


def test_gravy_is_mean_kyte_doolittle_hydropathy():
    assert d.gravy("AG") == pytest.approx(0.7, abs=1e-9)


def test_aromaticity_counts_only_f_w_y():
    assert d.aromaticity("FWYAG") == pytest.approx(3 / 5)
    assert d.aromaticity("AAAA") == 0.0


def test_net_charge_signs_for_charged_homopeptides():
    assert d.net_charge_at_ph("KKKK", ph=7.0) > 0
    assert d.net_charge_at_ph("DDDD", ph=7.0) < 0


def test_isoelectric_point_is_higher_for_basic_than_acidic_peptide():
    pi_basic = d.isoelectric_point("KKK")
    pi_acidic = d.isoelectric_point("DDDDD")
    assert pi_basic > 7.0
    assert pi_acidic < 7.0
    assert pi_basic > pi_acidic


def test_isoelectric_point_is_the_zero_crossing_of_net_charge():
    for seq in ["KKK", "DDDDD", "ACDEFGHIKLMNPQRSTVWY"[:10], "AAAAA"]:
        pi = d.isoelectric_point(seq)
        charge_at_pi = d.net_charge_at_ph(seq, pi)
        assert abs(charge_at_pi) < 1e-2


def test_instability_index_flags_proline_rich_peptide_as_unstable():
    # Pro-Pro is one of the most destabilizing dipeptides in the Guruprasad
    # table (20.26); a poly-proline peptide should score well above the
    # conventional ProtParam "stable" cutoff of 40.
    assert d.instability_index("PPPPPPPP") > 40


def test_aliphatic_index_is_zero_when_no_contributing_residues_present():
    assert d.aliphatic_index("KKK") == 0.0


def test_aliphatic_index_matches_hand_calculation_for_pure_leucine():
    # AI = 100 * (0 + 2.9*0 + 3.9*(1.0 + 0)) = 390
    assert d.aliphatic_index("LLLL") == pytest.approx(390.0)


def test_hydrophobic_moment_is_near_zero_for_a_uniform_sequence():
    # All-identical-residue "helix" has every per-residue vector identical
    # in magnitude but rotated by a fixed angle each step; for a long
    # enough stretch the vector sum does not grow proportionally to N, so
    # the per-residue mean moment shrinks towards 0 -- sanity check it's
    # small relative to a single residue's own hydrophobicity magnitude.
    moment = d.hydrophobic_moment("A" * 20)
    assert 0 <= moment < abs(d.EISENBERG["A"])


# ---------------------------------------------------------------------------
# Length boundaries and representative biological cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,sequence",
    [
        ("min_length_3", "ACD"),
        ("max_length_50", "A" * 50),
        ("charged", "KRDEKRDEKR"),
        ("aromatic", "FWYFWYFWY"),
        ("hydrophobic", "LLLLIIIIVVVVMMMM"),
        ("cysteine_rich", "CCCCCCCCCC"),
        ("proline_rich", "PPPPPPPPPP"),
    ],
)
def test_representative_sequences_produce_finite_values(name, sequence):
    result = d.compute_descriptors(sequence)
    assert all(math.isfinite(v) for v in result.values()), f"{name}: non-finite value in {result}"


def test_short_and_long_boundaries_are_both_valid():
    assert d.compute_descriptors("ACD")["length"] == 3.0
    assert d.compute_descriptors("A" * 50)["length"] == 50.0


# ---------------------------------------------------------------------------
# Invalid input handling
# ---------------------------------------------------------------------------


def test_sequence_below_minimum_length_is_rejected():
    with pytest.raises(d.InvalidPeptideError):
        d.compute_descriptors("AC")


def test_sequence_above_maximum_length_is_rejected():
    with pytest.raises(d.InvalidPeptideError):
        d.compute_descriptors("A" * 51)


def test_non_standard_residue_is_rejected_not_silently_dropped():
    with pytest.raises(d.InvalidPeptideError) as exc_info:
        d.compute_descriptors("ACDX")
    assert "X" in str(exc_info.value)


def test_batch_rejects_if_any_single_sequence_is_invalid():
    with pytest.raises(d.InvalidPeptideError):
        d.compute_descriptors_batch(["P1", "P2"], ["ACDEFGH", "AC"])


def test_batch_mismatched_id_and_sequence_lengths_raises():
    with pytest.raises(ValueError):
        d.compute_descriptors_batch(["P1"], ["ACDEFGH", "KLMNPQR"])


# ---------------------------------------------------------------------------
# Batch vs single equivalence, determinism, finiteness over a larger sample
# ---------------------------------------------------------------------------


def _random_valid_sequences(n, seed=42):
    rng = np.random.default_rng(seed)
    aas = list(d.STANDARD_AMINO_ACIDS)
    out = []
    for _ in range(n):
        length = rng.integers(3, 51)
        out.append("".join(rng.choice(aas) for _ in range(length)))
    return out


def test_batch_and_single_sequence_results_are_numerically_identical():
    sequences = _random_valid_sequences(50)
    ids = [f"P{i}" for i in range(len(sequences))]
    batch_df = d.compute_descriptors_batch(ids, sequences)
    for i, seq in enumerate(sequences):
        single = d.compute_descriptors(seq)
        row = batch_df.iloc[i]
        for name in d.DESCRIPTOR_NAMES:
            assert single[name] == pytest.approx(row[name], abs=1e-9)


def test_all_descriptors_finite_over_a_larger_random_sample():
    sequences = _random_valid_sequences(300)
    ids = [f"P{i}" for i in range(len(sequences))]
    df = d.compute_descriptors_batch(ids, sequences)
    values = df[list(d.DESCRIPTOR_NAMES)].to_numpy(dtype=float)
    assert np.isfinite(values).all()


def test_descriptor_extraction_is_deterministic_across_repeated_calls():
    sequences = _random_valid_sequences(20, seed=7)
    ids = [f"P{i}" for i in range(len(sequences))]
    first = d.compute_descriptors_batch(ids, sequences)
    second = d.compute_descriptors_batch(ids, sequences)
    pd.testing.assert_frame_equal(first, second)


def test_compute_descriptors_does_not_mutate_input_sequence():
    seq = "ACDEFGHIK"
    original = str(seq)
    d.compute_descriptors(seq)
    assert seq == original
