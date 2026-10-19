from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from plantaox.c1_procon.metrics import boot_weights, wauc


def test_unit_weights_give_the_ordinary_auroc():
    rng = np.random.RandomState(1)
    scores, y = rng.rand(50).round(1), rng.randint(0, 2, 50)  # rounded on purpose: many ties
    assert wauc(scores, y, np.ones((1, 50)))[0] == pytest.approx(roc_auc_score(y, scores), abs=1e-12)


def test_perfect_and_reversed_rankings():
    y = np.array([0, 0, 1, 1])
    assert wauc(np.array([0.1, 0.2, 0.8, 0.9]), y, np.ones((1, 4)))[0] == pytest.approx(1.0)
    assert wauc(np.array([0.9, 0.8, 0.2, 0.1]), y, np.ones((1, 4)))[0] == pytest.approx(0.0)
    assert wauc(np.full(4, 0.5), y, np.ones((1, 4)))[0] == pytest.approx(0.5)  # all ties


def test_integer_weights_equal_repeating_the_peptides():
    rng = np.random.RandomState(3)
    scores, y = rng.rand(20), rng.randint(0, 2, 20)
    w = rng.randint(0, 4, 20).astype(float)
    repeated = np.repeat(np.arange(20), w.astype(int))
    assert wauc(scores, y, w[None, :])[0] == pytest.approx(roc_auc_score(y[repeated], scores[repeated]), abs=1e-12)


def test_a_resample_without_positives_gives_nan():
    out = wauc(np.array([0.1, 0.9, 0.5]), np.array([0, 1, 1]), np.array([[1.0, 0.0, 0.0]]))
    assert np.isnan(out[0])


def test_boot_weights_resample_whole_groups():
    g = np.array([0, 0, 1, 1, 1, 2])
    w = boot_weights(g, n=200, seed=0)
    assert w.shape == (200, 6)
    assert np.all(w[:, 0] == w[:, 1]) and np.all(w[:, 2] == w[:, 3]) and np.all(w[:, 3] == w[:, 4])  # same draw count within a group
    assert (w[:, [0, 2, 5]].sum(axis=1) == 3).all()  # 3 groups drawn 3 times in total
