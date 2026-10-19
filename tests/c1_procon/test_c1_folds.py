from __future__ import annotations

import numpy as np
import pytest

from plantaox.c1_procon.benchmark import load_benchmark, strict_pool
from plantaox.c1_procon.folds import assert_no_group_spans_folds, group_folds


@pytest.fixture(scope="module")
def pool():
    return strict_pool(load_benchmark())


def test_folds_partition_the_peptides_and_never_split_a_group(pool):
    y, g = pool["y"].to_numpy(), pool["homology_group"].to_numpy().astype(int)
    folds = group_folds(y, g, k=5, seed=1000)
    assert len(folds) == 5
    all_test = np.concatenate([te for _, te in folds])
    assert sorted(all_test) == list(range(len(pool)))  # every peptide is tested exactly once
    for tr, te in folds:
        assert not set(tr) & set(te)
    assert_no_group_spans_folds(g, folds)


def test_positives_are_spread_over_the_folds(pool):
    y, g = pool["y"].to_numpy(), pool["homology_group"].to_numpy().astype(int)
    per_fold = [int(y[te].sum()) for _, te in group_folds(y, g, k=5, seed=1000)]
    assert sum(per_fold) == 104 and min(per_fold) >= 10  # 104 MC-active peptides, none of the folds starved


def test_the_same_seed_gives_the_same_folds_and_other_seeds_differ(pool):
    y, g = pool["y"].to_numpy(), pool["homology_group"].to_numpy().astype(int)
    a, b, c = group_folds(y, g, 5, 7), group_folds(y, g, 5, 7), group_folds(y, g, 5, 8)
    assert all(np.array_equal(x[1], z[1]) for x, z in zip(a, b))
    assert not all(np.array_equal(x[1], z[1]) for x, z in zip(a, c))


def test_a_leaky_assignment_is_detected():
    g = np.array([0, 0, 1, 1])
    leaky = [(np.array([2, 3]), np.array([0, 2])), (np.array([0, 1]), np.array([1, 3]))]  # groups 0 and 1 both split
    with pytest.raises(AssertionError):
        assert_no_group_spans_folds(g, leaky)
