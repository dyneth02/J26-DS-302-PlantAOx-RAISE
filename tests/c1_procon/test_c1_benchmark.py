from __future__ import annotations

import pandas as pd
import pytest

from plantaox.c1_procon.benchmark import (
    EXPECTED_FINGERPRINT,
    BenchmarkMismatchError,
    load_benchmark,
    s2_fingerprint,
)


@pytest.fixture(scope="module")
def s2():
    return load_benchmark()


def test_benchmark_matches_the_frozen_fingerprint(s2):
    assert s2_fingerprint(s2) == EXPECTED_FINGERPRINT == "47d9c2a2fff63eb1"


def test_benchmark_has_one_row_per_sequence_and_the_documented_label_counts(s2):
    assert len(s2) == 1389 and s2["sequence"].is_unique
    assert s2["labels"].value_counts().to_dict() == {"GEN": 675, "FRS": 565, "FRS;MC": 86, "MC": 63}


def test_homology_groups_and_folds_are_defined_for_every_mechanism_active_peptide(s2):
    mech = s2[s2["labels"].str.contains("FRS|MC")]
    assert len(mech) == 714 and mech["homology_group"].notna().all()
    assert mech["homology_group"].nunique() == 573
    assert mech["lso_fold"].isin([0, 1]).all()


def test_no_homology_group_spans_both_folds(s2):
    mech = s2[s2["labels"].str.contains("FRS|MC")]
    assert mech.groupby("homology_group")["lso_fold"].nunique().max() == 1


def test_a_changed_benchmark_is_refused(tmp_path, s2):
    altered = s2.copy()
    altered.loc[altered.index[0], "labels"] = "FRS"  # one label flipped
    path = tmp_path / "changed.csv"
    altered.to_csv(path, index=False)
    with pytest.raises(BenchmarkMismatchError):
        load_benchmark(path)
    assert len(load_benchmark(path, verify=False)) == len(s2)


def test_duplicate_sequences_are_refused(tmp_path, s2):
    path = tmp_path / "duplicated.csv"
    pd.concat([s2, s2.iloc[[0]]]).to_csv(path, index=False)
    with pytest.raises(BenchmarkMismatchError):
        load_benchmark(path)


def test_strict_pool_has_the_documented_size_and_target(s2):
    from plantaox.c1_procon.benchmark import strict_pool

    pool = strict_pool(s2)
    assert len(pool) == 669
    assert int(pool["y"].sum()) == 104 and int((pool["y"] == 0).sum()) == 565
    assert not pool["labels"].eq("GEN").any()


def test_every_frs_only_peptide_comes_from_one_source_database(s2):
    from plantaox.c1_procon.benchmark import strict_pool

    pool = strict_pool(s2)
    assert pool.loc[pool["y"] == 0, "source_group"].nunique() == 1  # the source confound found in Step 8
    assert (pool.loc[pool["y"] == 1, "source_group"] == "external_literature").sum() == 29
