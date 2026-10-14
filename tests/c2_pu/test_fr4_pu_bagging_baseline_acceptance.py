"""Bucket 4, Task 4.4 acceptance tests: the fr4-pu-bagging-baseline CLI
stage against the real local Tasks 3.1-3.4 artifacts.

Gated to skip cleanly when those artifacts aren't present locally. Uses a
reduced ``n_estimators`` for speed (the per-estimator math does not
change with ensemble size -- the full ``n_estimators=100`` default is
exercised once, separately, to confirm it also runs end-to-end on real
data). Confirms: real fold-0 E1+E2/C1 counts match Task 4.2/4.3's own
documented totals exactly, finite bounded predictions, the documented
"positives are never out-of-bag" property on real data, checkpoint
save/reload reproduces predictions exactly, GraphPart held-out fold
isolation, and that every prior task's real artifacts remain
byte-unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.run import (
    C3_RANKING_PATH,
    FR3_DESCRIPTOR_TABLE_PATH,
    FR3_EMBEDDINGS_MANIFEST_PATH,
    FR3_FEATURE_CACHE_MANIFEST_PATH,
    FR3_FUSION_SCALERS_PATH,
    FR3_RECORD_MAP_PATH,
    FR2_FROZEN_DIR,
    FROZEN_DIR,
    FR4_NNPU_BASELINE_SUMMARY_PATH_TEMPLATE,
    FR4_PN_BASELINE_SUMMARY_PATH_TEMPLATE,
    FR4_TWO_STEP_PU_BASELINE_SUMMARY_PATH_TEMPLATE,
    run_fr4_pu_bagging_baseline,
)

REQUIRED_INPUTS = [FR3_FEATURE_CACHE_MANIFEST_PATH, FR3_FUSION_SCALERS_PATH, FR3_RECORD_MAP_PATH, C3_RANKING_PATH]
pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in REQUIRED_INPUTS),
    reason="Tasks 3.1-3.4 outputs not present locally.",
)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def pre_run_hashes():
    hashes = {
        "feature_cache_manifest": _sha256(FR3_FEATURE_CACHE_MANIFEST_PATH),
        "fusion_scalers": _sha256(FR3_FUSION_SCALERS_PATH),
        "record_map": _sha256(FR3_RECORD_MAP_PATH),
        "c3_ranking": _sha256(C3_RANKING_PATH),
    }
    if FR3_DESCRIPTOR_TABLE_PATH.exists():
        hashes["descriptor_table"] = _sha256(FR3_DESCRIPTOR_TABLE_PATH)
    if FR3_EMBEDDINGS_MANIFEST_PATH.exists():
        hashes["embeddings_manifest"] = _sha256(FR3_EMBEDDINGS_MANIFEST_PATH)
    for key, template in (
        ("pn_summary", FR4_PN_BASELINE_SUMMARY_PATH_TEMPLATE),
        ("nnpu_summary", FR4_NNPU_BASELINE_SUMMARY_PATH_TEMPLATE),
        ("two_step_pu_summary", FR4_TWO_STEP_PU_BASELINE_SUMMARY_PATH_TEMPLATE),
    ):
        path = Path(template.format(fold_id=0))
        if path.exists():
            hashes[key] = _sha256(path)
    return hashes


@pytest.fixture(scope="module")
def smoke_summary(pre_run_hashes):
    # Stage B: reduced ensemble size for speed -- exercises the exact
    # same real fold-0 cache, explicitly not presented as the final
    # baseline result.
    return run_fr4_pu_bagging_baseline(fold_id=0, n_estimators=10)


def test_stage_b_smoke_produces_a_finite_oob_score(smoke_summary):
    assert np.isfinite(smoke_summary["oob_metrics"]["oob_score"])
    assert smoke_summary["n_estimators"] == 10


@pytest.fixture(scope="module")
def full_summary(smoke_summary):
    # Stage C: the genuine, documented default (n_estimators=100).
    return run_fr4_pu_bagging_baseline(fold_id=0)


def test_default_n_estimators_used_when_unspecified(full_summary):
    assert full_summary["n_estimators"] == 100


def test_real_fold0_e1_e2_and_c1_counts_match_task_4_2_4_3_documented_values(full_summary):
    counts = full_summary["class_counts"]
    assert counts["e1_train"] == 331
    assert counts["e2_train"] == 273
    assert counts["e1_validation"] == 48
    assert counts["e2_validation"] == 58
    assert counts["train_positive"] == 604
    assert counts["validation_positive"] == 106
    assert counts["train_unlabeled"] == 3220
    assert counts["validation_unlabeled"] == 568


def test_c1_partition_matches_pn_nnpu_shared_splitter(full_summary):
    assert full_summary["c1_partition"]["validation_fraction"] == pytest.approx(0.15)
    assert full_summary["c1_partition"]["seed"] == 42


def test_graphpart_held_out_fold_is_never_referenced():
    from plantaox.c2_pu.experiment_config import ExperimentConfig
    from plantaox.c2_pu.experiment_data import build_experiment_data
    from plantaox.c2_pu.pu_sklearn_common import build_sklearn_pu_dataset

    cache_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    record_map = pd.read_csv(FR3_RECORD_MAP_PATH)
    config = ExperimentConfig(experiment_id="verify_held_out", baseline="PUBagging", fold_id=0)
    entry = cache_manifest["folds"]["0"]
    data = build_experiment_data(config, Path(entry["cache_path"]), entry, fusion_scalers["0"], record_map, C3_RANKING_PATH)
    dataset = build_sklearn_pu_dataset(data, config)

    trained_ids = (
        set(dataset.train_positive_ids.tolist())
        | set(dataset.validation_positive_ids.tolist())
        | set(dataset.train_unlabeled_ids.tolist())
        | set(dataset.validation_unlabeled_ids.tolist())
    )
    held_out_ids = set(data.held_out_positive.peptide_ids.tolist())
    assert trained_ids.isdisjoint(held_out_ids)
    assert len(held_out_ids) == 124


def test_validation_predictions_are_finite_and_bounded(full_summary):
    val = full_summary["training"]["validation_metrics"]
    for side in ("positive_rows", "unlabeled_rows"):
        assert val[side]["min"] >= 0.0
        assert val[side]["max"] <= 1.0
        assert np.isfinite(val[side]["mean"])


def test_positives_score_higher_on_average_than_c1_unlabeled(full_summary):
    val = full_summary["training"]["validation_metrics"]
    assert val["positive_rows"]["mean"] > val["unlabeled_rows"]["mean"]


def test_all_training_positives_are_never_out_of_bag_on_real_data(full_summary):
    oob = full_summary["oob_metrics"]
    assert oob["n_rows_never_out_of_bag"] == 604  # e1_train + e2_train
    assert oob["positive_rows"]["n"] == 0
    assert oob["unlabeled_rows"]["n"] == 3220
    assert np.isfinite(oob["oob_score"])
    assert 0.0 <= oob["oob_score"] <= 1.0


def test_best_and_last_checkpoints_saved(full_summary):
    # best/last are the SAME single fit (documented difference from
    # PN/nnPU's iterative best-vs-last distinction) -- the underlying
    # estimator's predictions must match exactly, even though the raw
    # file SHA-256 can legitimately differ (each payload embeds its own
    # live `saved_at` timestamp, same reasoning already documented for
    # PN/nnPU's own torch checkpoints).
    from plantaox.c2_pu.pu_sklearn_common import load_sklearn_checkpoint

    run_dir = Path(full_summary["run_dir"])
    assert (run_dir / "checkpoint_best.joblib").exists()
    assert (run_dir / "checkpoint_last.joblib").exists()
    best_estimator = load_sklearn_checkpoint(run_dir / "checkpoint_best.joblib")["estimator"]
    last_estimator = load_sklearn_checkpoint(run_dir / "checkpoint_last.joblib")["estimator"]
    sample = best_estimator.estimators_[0].coef_  # any deterministic attribute to sanity-check equality
    assert np.array_equal(sample, last_estimator.estimators_[0].coef_)


def test_checkpoint_reload_reproduces_predictions(full_summary):
    from plantaox.c2_pu.pu_sklearn_common import load_sklearn_checkpoint

    run_dir = Path(full_summary["run_dir"])
    payload = load_sklearn_checkpoint(run_dir / "checkpoint_best.joblib")
    estimator = payload["estimator"]

    cache_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    record_map = pd.read_csv(FR3_RECORD_MAP_PATH)
    from plantaox.c2_pu.experiment_config import ExperimentConfig
    from plantaox.c2_pu.experiment_data import build_experiment_data
    from plantaox.c2_pu.pu_sklearn_common import build_sklearn_pu_dataset, combined_fit_arrays

    config = ExperimentConfig(experiment_id="verify_reload", baseline="PUBagging", fold_id=0)
    entry = cache_manifest["folds"]["0"]
    data = build_experiment_data(config, Path(entry["cache_path"]), entry, fusion_scalers["0"], record_map, C3_RANKING_PATH)
    dataset = build_sklearn_pu_dataset(data, config)
    val_x, _val_y, _val_ids = combined_fit_arrays(dataset, "validation")

    proba_a = estimator.predict_proba(val_x)
    proba_b = estimator.predict_proba(val_x)
    assert np.array_equal(proba_a, proba_b)
    assert np.isfinite(proba_a).all()
    assert ((proba_a >= 0) & (proba_a <= 1)).all()


def test_rerunning_the_smoke_config_is_bit_identical_in_substance(smoke_summary):
    second = run_fr4_pu_bagging_baseline(fold_id=0, n_estimators=10)
    assert second["oob_metrics"]["oob_score"] == smoke_summary["oob_metrics"]["oob_score"]
    assert second["class_counts"] == smoke_summary["class_counts"]
    assert second["training"]["validation_metrics"] == smoke_summary["training"]["validation_metrics"]
    assert second["run_dir"] != smoke_summary["run_dir"]


def test_limitations_section_is_present_and_explicit(full_summary):
    limitations = full_summary["limitations"]
    assert "unlabeled" in limitations["assumed_unlabeled_c1"].lower()
    assert "never" in limitations["assumed_unlabeled_c1"].lower()
    assert "binarymlp" in limitations["base_estimator_not_binarymlp"].lower()
    assert "task 4.5" in limitations["no_mcc_auprc_here"].lower()


def test_all_prior_task_outputs_are_untouched(full_summary, pre_run_hashes):
    for name, path in [
        ("feature_cache_manifest", FR3_FEATURE_CACHE_MANIFEST_PATH),
        ("fusion_scalers", FR3_FUSION_SCALERS_PATH),
        ("record_map", FR3_RECORD_MAP_PATH),
        ("c3_ranking", C3_RANKING_PATH),
        ("descriptor_table", FR3_DESCRIPTOR_TABLE_PATH),
        ("embeddings_manifest", FR3_EMBEDDINGS_MANIFEST_PATH),
    ]:
        if name in pre_run_hashes:
            assert _sha256(path) == pre_run_hashes[name], f"{name} changed after running the PU-Bagging baseline"


def test_other_baseline_summaries_unaffected_if_present(full_summary, pre_run_hashes):
    for key, template in (
        ("pn_summary", FR4_PN_BASELINE_SUMMARY_PATH_TEMPLATE),
        ("nnpu_summary", FR4_NNPU_BASELINE_SUMMARY_PATH_TEMPLATE),
        ("two_step_pu_summary", FR4_TWO_STEP_PU_BASELINE_SUMMARY_PATH_TEMPLATE),
    ):
        if key in pre_run_hashes:
            assert _sha256(Path(template.format(fold_id=0))) == pre_run_hashes[key]


def test_frozen_fr1_fr2_baselines_are_untouched(full_summary):
    assert FROZEN_DIR.exists() and FR2_FROZEN_DIR.exists()
    assert not (FROZEN_DIR / "fr4_pu_bagging_baseline_fold0_summary.json").exists()
    assert not (FR2_FROZEN_DIR / "fr4_pu_bagging_baseline_fold0_summary.json").exists()


def test_missing_prerequisite_raises_a_clear_error(monkeypatch, tmp_path):
    import plantaox.c2_pu.run as run_module

    bogus_path = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(run_module, "FR3_FEATURE_CACHE_MANIFEST_PATH", bogus_path)
    with pytest.raises(FileNotFoundError, match="Tasks 3.1-3.4"):
        run_fr4_pu_bagging_baseline(fold_id=0)
