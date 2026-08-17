"""Shared physicochemical descriptor computation.

Reproduces the 15-feature descriptor schema used in data/raw/descriptors.csv
(mw, gravy, aromaticity, instability, charge_ph7, aliphatic_index, 3 CTD-hydrophobicity
composition bins, 3 CTD-hydrophobicity transition bins, 2 CTD-charge composition bins)
so that any new sequence (e.g. non-AOP negatives, plant fragments) can be placed in the
same descriptor space as the curated AOP-BenchPos table.
"""
from __future__ import annotations

from Bio.SeqUtils.ProtParam import ProteinAnalysis

HYDRO_GROUPS = {
    "hydrophobic": set("AVLIPFMW"),
    "neutral": set("GHYQNST"),
    "polar": set("RKEDC"),
}
CHARGE_GROUPS = {
    "positive": set("RK"),
    "negative": set("DE"),
}

VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")


def is_valid_sequence(seq: str) -> bool:
    return len(seq) > 0 and set(seq.upper()) <= VALID_AA


def _composition(seq: str, groups: dict) -> dict:
    n = len(seq)
    out = {}
    for name, members in groups.items():
        out[name] = sum(1 for c in seq if c in members) / n
    return out


def compute_descriptors(sequence: str) -> dict:
    seq = sequence.upper().strip()
    pa = ProteinAnalysis(seq)

    hydro_comp = _composition(seq, HYDRO_GROUPS)
    charge_comp = _composition(seq, CHARGE_GROUPS)

    membership = {}
    for name, members in HYDRO_GROUPS.items():
        for c in members:
            membership[c] = name

    trans_counts = {
        "hydrophobic_neutral": 0,
        "neutral_polar": 0,
        "hydrophobic_polar": 0,
    }
    n_pairs = max(len(seq) - 1, 1)
    for i in range(len(seq) - 1):
        a, b = membership.get(seq[i]), membership.get(seq[i + 1])
        if a is None or b is None or a == b:
            continue
        pair = "_".join(sorted([a, b], key=lambda x: ["hydrophobic", "neutral", "polar"].index(x)))
        if pair in trans_counts:
            trans_counts[pair] += 1

    return {
        "sequence": seq,
        "mw": pa.molecular_weight(),
        "gravy": pa.gravy(),
        "aromaticity": pa.aromaticity(),
        "instability": pa.instability_index(),
        "charge_ph7": pa.charge_at_pH(7.0),
        "aliphatic_index": _aliphatic_index(seq),
        "ctd_hydro_C_hydrophobic": hydro_comp["hydrophobic"],
        "ctd_hydro_C_neutral": hydro_comp["neutral"],
        "ctd_hydro_C_polar": hydro_comp["polar"],
        "ctd_hydro_T_hydrophobic_neutral": trans_counts["hydrophobic_neutral"] / n_pairs,
        "ctd_hydro_T_neutral_polar": trans_counts["neutral_polar"] / n_pairs,
        "ctd_hydro_T_hydrophobic_polar": trans_counts["hydrophobic_polar"] / n_pairs,
        "ctd_charge_C_positive": charge_comp["positive"],
        "ctd_charge_C_negative": charge_comp["negative"],
    }


def _aliphatic_index(seq: str) -> float:
    n = len(seq)
    a = seq.count("A") / n * 100
    v = seq.count("V") / n * 100
    i = seq.count("I") / n * 100
    l = seq.count("L") / n * 100
    return a + 2.9 * v + 3.9 * (i + l)
