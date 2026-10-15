"""Bucket 2.5 -- Biological Distribution and Shortcut-Bias Checks.

Compares FR1's accepted positives against C1/C2/C3 on length, amino-acid
composition, and a small set of analytically-computed physicochemical
descriptors. **This is NOT Bucket 3.1's 15-descriptor feature-extraction
pipeline** -- this is a narrower 4-descriptor set used only for this
comparison. As of Bucket 3.1, the 4 formulas below are imported from
``common/descriptors.py`` (the canonical, frozen 15-descriptor schema)
rather than defined here a second time, so the two modules can never
silently diverge; this module still only *uses* 4 of the 15 for its own
comparison purpose.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from plantaox.c2_pu.common.descriptors import (
    AROMATIC_RESIDUES,
    STANDARD_AMINO_ACIDS,
    aromaticity,
    gravy,
    molecular_weight,
    net_charge_at_ph,
)

__all__ = [
    "AROMATIC_RESIDUES",
    "STANDARD_AMINO_ACIDS",
    "aromaticity",
    "gravy",
    "molecular_weight",
    "net_charge_at_ph",
    "amino_acid_composition",
    "pool_descriptor_table",
    "compare_pools_ks",
]


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
