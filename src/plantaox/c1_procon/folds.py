"""Homology-grouped cross-validation folds.

The fold code is self-contained on purpose: scikit-learn's grouped splitters changed between releases (the same recipe gave
0.59 to 0.66 AUROC), so the probe in Step 5 uses this deterministic assignment instead.
"""

from __future__ import annotations

import numpy as np


def group_folds(y: np.ndarray, g: np.ndarray, k: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Split whole homology groups into ``k`` folds; returns ``(train_index, test_index)`` per fold.

    Groups that contain positives balance the number of positives across folds; the other groups balance the fold size.
    Deterministic for a given ``seed``.
    """
    y, g = np.asarray(y), np.asarray(g)
    rng = np.random.RandomState(seed)
    groups = np.unique(g)
    rng.shuffle(groups)
    positives = {u: int(y[g == u].sum()) for u in groups}
    sizes = {u: int((g == u).sum()) for u in groups}
    groups = sorted(groups, key=lambda u: -(positives[u] * 10_000 + sizes[u]))
    fold_pos, fold_size = np.zeros(k), np.zeros(k)
    where = {}
    for u in groups:
        j = int(np.lexsort((fold_size, fold_pos))[0]) if positives[u] > 0 else int(np.argmin(fold_size))
        where[u] = j
        fold_pos[j] += positives[u]
        fold_size[j] += sizes[u]
    assigned = np.array([where[x] for x in g])
    return [(np.where(assigned != j)[0], np.where(assigned == j)[0]) for j in range(k)]


def assert_no_group_spans_folds(g: np.ndarray, folds: list[tuple[np.ndarray, np.ndarray]]) -> None:
    """Raise if any homology group has members in more than one test fold (that would be a leak)."""
    g = np.asarray(g)
    seen: dict = {}
    for j, (_, test) in enumerate(folds):
        for group in np.unique(g[test]):
            if seen.setdefault(group, j) != j:
                raise AssertionError(f"homology group {group} appears in test folds {seen[group]} and {j}")
