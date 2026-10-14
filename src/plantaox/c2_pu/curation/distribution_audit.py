"""Bucket 2.5 -- Biological Distribution and Shortcut-Bias Checks.

Compares FR1's accepted positives against C1/C2/C3 on length, amino-acid
composition, and a small set of analytically-computed physicochemical
descriptors. **This is NOT Bucket 3.1's 15-descriptor feature-extraction
pipeline** (that module, ``common/descriptors.py``, is still an empty
scaffold stub) -- this is a narrower, independently-computed set used only
for this comparison, so Task 2.5 doesn't silently do Bucket 3.1's job or
create two divergent descriptor implementations.

All formulas below are standard, textbook/tool-reference values (Kyte-
Doolittle hydropathy; a common Expasy/EMBOSS-style pKa table for net
charge), not novel -- and are used only for *relative, cross-pool*
comparison here, not claimed as publication-grade absolute values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

# Average residue masses (Da) within a peptide chain (free amino acid mass
# minus one water, 18.0153 Da -- added back once per peptide below).
_RESIDUE_MASS = {
    "A": 71.0788, "R": 156.1875, "N": 114.1038, "D": 115.0886, "C": 103.1388,
    "E": 129.1155, "Q": 128.1307, "G": 57.0519, "H": 137.1411, "I": 113.1594,
    "L": 113.1594, "K": 128.1741, "M": 131.1926, "F": 147.1766, "P": 97.1167,
    "S": 87.0782, "T": 101.1051, "W": 186.2132, "Y": 163.1760, "V": 99.1326,
}
_WATER_MASS = 18.0153

# Kyte & Doolittle (1982) hydropathy index, for GRAVY.
_KYTE_DOOLITTLE = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

# Common Expasy/EMBOSS-style pKa table (side chains + termini) for an
# approximate net-charge-at-pH calculation (Henderson-Hasselbalch). Used
# consistently across every pool, so it is valid for relative comparison
# even though it is not the one canonical pKa set the field uses.
_PKA_POSITIVE = {"Nterm": 9.69, "K": 10.53, "R": 12.48, "H": 6.0}
_PKA_NEGATIVE = {"Cterm": 2.34, "D": 3.65, "E": 4.25, "C": 8.3, "Y": 10.07}

AROMATIC_RESIDUES = {"F", "W", "Y"}
STANDARD_AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"


def molecular_weight(sequence: str) -> float:
    return sum(_RESIDUE_MASS[r] for r in sequence) + _WATER_MASS


def gravy(sequence: str) -> float:
    return sum(_KYTE_DOOLITTLE[r] for r in sequence) / len(sequence)


def aromaticity(sequence: str) -> float:
    return sum(1 for r in sequence if r in AROMATIC_RESIDUES) / len(sequence)


def net_charge_at_ph(sequence: str, ph: float = 7.0) -> float:
    """Approximate net charge via Henderson-Hasselbalch, evaluated once at
    ``ph`` (not a full isoelectric-point solve -- we only need a single,
    consistently-computed value per sequence for cross-pool comparison)."""
    positive = 1.0 / (1.0 + 10 ** (ph - _PKA_POSITIVE["Nterm"]))
    positive += sum(
        1.0 / (1.0 + 10 ** (ph - _PKA_POSITIVE[r])) for r in sequence if r in _PKA_POSITIVE
    )
    negative = 1.0 / (1.0 + 10 ** (_PKA_NEGATIVE["Cterm"] - ph))
    negative += sum(
        1.0 / (1.0 + 10 ** (_PKA_NEGATIVE[r] - ph)) for r in sequence if r in _PKA_NEGATIVE
    )
    return positive - negative


def amino_acid_composition(sequences: list[str]) -> dict[str, float]:
    """Fractional frequency of each of the 20 standard residues, pooled
    across every residue in every sequence (not averaged per-sequence)."""
    counts = {aa: 0 for aa in STANDARD_AMINO_ACIDS}
    total = 0
    for seq in sequences:
        for r in seq:
            counts[r] += 1
            total += 1
    if total == 0:
        return {aa: 0.0 for aa in STANDARD_AMINO_ACIDS}
    return {aa: count / total for aa, count in counts.items()}


def pool_descriptor_table(pool_name: str, sequences: list[str]) -> pd.DataFrame:
    """One row per sequence: length + the 4 analytically-computed
    descriptors above."""
    return pd.DataFrame(
        {
            "pool": pool_name,
            "sequence": sequences,
            "length": [len(s) for s in sequences],
            "molecular_weight": [molecular_weight(s) for s in sequences],
            "net_charge_ph7": [net_charge_at_ph(s) for s in sequences],
            "gravy": [gravy(s) for s in sequences],
            "aromaticity": [aromaticity(s) for s in sequences],
        }
    )


def compare_pools_ks(
    reference: pd.DataFrame, other_pools: dict[str, pd.DataFrame], columns: list[str]
) -> pd.DataFrame:
    """Two-sample Kolmogorov-Smirnov test, FR1 positives (``reference``)
    vs. each challenge pool, for every numeric column in ``columns``.
    Quantifies distributional mismatch rather than relying on eyeballing
    plots -- a small p-value means the two pools' distributions for that
    descriptor are statistically distinguishable, i.e. a potential
    shortcut signal a classifier could exploit instead of real antioxidant
    chemistry.
    """
    rows = []
    for pool_name, pool_df in other_pools.items():
        for column in columns:
            statistic, p_value = stats.ks_2samp(reference[column], pool_df[column])
            rows.append(
                {
                    "pool": pool_name,
                    "descriptor": column,
                    "ks_statistic": statistic,
                    "p_value": p_value,
                    "reference_mean": reference[column].mean(),
                    "reference_std": reference[column].std(),
                    "pool_mean": pool_df[column].mean(),
                    "pool_std": pool_df[column].std(),
                }
            )
    return pd.DataFrame(rows)
