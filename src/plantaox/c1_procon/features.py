"""Simple sequence features used as baselines against ESM-2: amino-acid composition and length."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

AA = "ACDEFGHIKLMNPQRSTVWY"
TRIPEPTIDE_LENGTH = 3


def composition(sequence: str) -> np.ndarray:
    """AAC-20: the share of each of the 20 amino acids in the peptide (the vector sums to 1)."""
    if not sequence:
        raise ValueError("empty sequence")
    unknown = set(sequence) - set(AA)
    if unknown:
        raise ValueError(f"non-canonical residues: {''.join(sorted(unknown))}")
    return np.array([sequence.count(a) / len(sequence) for a in AA], dtype=float)


def composition_matrix(sequences: Iterable[str]) -> np.ndarray:
    return np.stack([composition(s) for s in sequences])


def length_features(sequences: Iterable[str]) -> np.ndarray:
    """LENGTH baseline: the length and its logarithm."""
    lengths = np.array([len(s) for s in sequences], dtype=float)
    return np.column_stack([lengths, np.log(lengths)])


def tripeptide_share(sequences: Iterable[str]) -> float:
    """Fraction of peptides that are exactly three amino acids long (a length confound found in Step 8)."""
    lengths = np.array([len(s) for s in sequences])
    return float((lengths == TRIPEPTIDE_LENGTH).mean())
