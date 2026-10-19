"""Weighted AUROC and group-bootstrap weights used for the confidence intervals in Steps 5 and 8."""

from __future__ import annotations

import numpy as np


def boot_weights(g: np.ndarray, n: int, seed: int = 0) -> np.ndarray:
    """Group bootstrap as multiplicity weights of shape ``(n, n_samples)``.

    Whole homology groups are resampled (peptides of one group are not independent), so every peptide inherits the draw
    count of its group.
    """
    g = np.asarray(g)
    unique, inverse = np.unique(g, return_inverse=True)
    draws = np.random.RandomState(seed).multinomial(len(unique), np.full(len(unique), 1 / len(unique)), size=n)
    return draws[:, inverse].astype(float)


def wauc(scores: np.ndarray, y: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Weighted AUROC (ties count 1/2) for every row of ``weights``.

    Returns NaN for a resample with no positive or no negative weight. With all weights equal to 1 this is the ordinary
    AUROC.
    """
    scores, y = np.asarray(scores), np.asarray(y)
    weights = np.atleast_2d(np.asarray(weights, dtype=float))
    unique, inverse = np.unique(scores, return_inverse=True)
    onehot = np.zeros((len(scores), len(unique)))
    onehot[np.arange(len(scores)), inverse] = 1
    pos, neg = (weights * y) @ onehot, (weights * (1 - y)) @ onehot
    num = (pos * (np.cumsum(neg, 1) - neg + 0.5 * neg)).sum(1)
    den = pos.sum(1) * neg.sum(1)
    return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
