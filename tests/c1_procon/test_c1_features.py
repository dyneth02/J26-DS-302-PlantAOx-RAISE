from __future__ import annotations

import numpy as np
import pytest

from plantaox.c1_procon.benchmark import load_benchmark, strict_pool
from plantaox.c1_procon.features import AA, composition, composition_matrix, length_features, tripeptide_share


def test_composition_of_a_known_peptide():
    vec = composition("HYY")
    assert vec.sum() == pytest.approx(1.0)
    assert vec[AA.index("H")] == pytest.approx(1 / 3) and vec[AA.index("Y")] == pytest.approx(2 / 3)
    assert np.count_nonzero(vec) == 2


def test_composition_ignores_order_but_not_content():
    assert np.allclose(composition("HYY"), composition("YHY")) and np.allclose(composition("HYY"), composition("YYH"))
    assert not np.allclose(composition("HYY"), composition("HHY"))


@pytest.mark.parametrize("bad", ["", "AXZ", "ab1"])
def test_composition_rejects_empty_and_non_canonical_input(bad):
    with pytest.raises(ValueError):
        composition(bad)


def test_composition_matrix_has_one_unit_row_per_peptide():
    m = composition_matrix(["AAA", "GGGGG", "WYH"])
    assert m.shape == (3, 20) and np.allclose(m.sum(axis=1), 1.0)


def test_length_features_are_length_and_its_log():
    f = length_features(["AAA", "AAAAAAAAAA"])
    assert f.tolist() == [[3.0, pytest.approx(np.log(3))], [10.0, pytest.approx(np.log(10))]]


def test_tripeptide_share_shows_the_length_confound_of_the_strict_pool():
    pool = strict_pool(load_benchmark())
    frs = tripeptide_share(pool.loc[pool["y"] == 0, "sequence"])
    mc = tripeptide_share(pool.loc[pool["y"] == 1, "sequence"])
    assert frs == pytest.approx(0.428, abs=0.001) and mc == pytest.approx(0.163, abs=0.001)
