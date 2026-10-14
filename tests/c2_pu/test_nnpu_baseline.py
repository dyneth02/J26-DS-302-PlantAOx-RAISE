"""Unit tests for nnpu_baseline.py (Bucket 4, Task 4.3) -- dataset
construction, leakage checks, and the training loop, all against small,
fully synthetic fixtures (no real cached artifacts required; a separate
acceptance test exercises the real fold-0 data -- see
test_fr4_nnpu_baseline_acceptance.py)."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import DataLeakageError, ExperimentData, PoolData
from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
from plantaox.c2_pu.nnpu_baseline import (
    DEFAULT_PRIOR,
    NnPuDataset,
    _CyclingIndexSampler,
    build_nnpu_dataset,
    select_e1_e2_positive_evidence,
    train_nnpu_baseline,
)
from plantaox.c2_pu.nnpu_risk import InvalidPriorError
from plantaox.c2_pu.pn_baseline import InsufficientDataError, split_c1_train_validation

FEATURE_DIM = 495


def _pool(pool, peptide_ids, seed_offset=0, evidence_tier=None):
    n = len(peptide_ids)
    rng = np.random.default_rng(seed_offset + len(pool))
    features = rng.normal(size=(n, FEATURE_DIM)).astype(np.float32)
    sequences = np.array([f"SEQ_{pool}_{pid}" for pid in peptide_ids])
    tier = np.array(evidence_tier) if evidence_tier is not None else None
    return PoolData(pool=pool, peptide_ids=np.array(peptide_ids), sequences=sequences, features=features, evidence_tier=tier)


def _experiment_data(
    train_ids=("P1", "P2", "P3", "P4", "P5"),
    train_tiers=("E1", "E1", "E2", "E2", "E3"),
    val_ids=("P6", "P7", "P8"),
    val_tiers=("E1", "E2", "E3"),
    held_out_ids=("P9", "P10"),
    c1_ids=tuple(f"C1-{i}" for i in range(20)),
    c2_ids=("C2-1",),
    c3_ids=("C3-1",),
    ext_ids=("EXT-1",),
    fold_id=0,
):
    return ExperimentData(
        fold_id=fold_id,
        feature_representation="fused",
        feature_dim=FEATURE_DIM,
        train_positive=_pool("FR1_positives_train", train_ids, evidence_tier=train_tiers),
        validation_positive=_pool("FR1_positives_validation", val_ids, seed_offset=1, evidence_tier=val_tiers),
        held_out_positive=_pool("FR1_positives_held_out", held_out_ids, seed_offset=2, evidence_tier=["E1"] * len(held_out_ids)),
        c1=_pool("C1", c1_ids, seed_offset=3),
        c2=_pool("C2", c2_ids, seed_offset=4),
        c3_fold_challenges=_pool(f"C3_fold{fold_id}", c3_ids, seed_offset=5),
        external_control=_pool("external_control", ext_ids, seed_offset=6),
        leakage_report={"pairs_checked": [], "overlap_found": False},
    )


def _config(**overrides):
    base = {"experiment_id": "nnpu_test", "baseline": "nnPU", "fold_id": 0, "validation_fraction": 0.2, "eval_seed": 1}
    base.update(overrides)
    return ExperimentConfig(**base)


# ---------------------------------------------------------------------------
# E1+E2 selection / E3 exclusion
# ---------------------------------------------------------------------------


def test_select_e1_e2_positive_evidence_keeps_e1_and_e2():
    pool = _pool("FR1_positives_train", ["P1", "P2", "P3"], evidence_tier=["E1", "E2", "E3"])
    selected = select_e1_e2_positive_evidence(pool)
    assert set(selected.peptide_ids.tolist()) == {"P1", "P2"}
    assert set(selected.evidence_tier.tolist()) == {"E1", "E2"}


def test_select_e1_e2_positive_evidence_excludes_e3_entirely():
    pool = _pool("FR1_positives_train", ["P1", "P2"], evidence_tier=["E1", "E3"])
    selected = select_e1_e2_positive_evidence(pool)
    assert "P2" not in selected.peptide_ids.tolist()


def test_select_e1_e2_positive_evidence_raises_without_evidence_info():
    pool = _pool("C1", ["C1-1", "C1-2"])  # no evidence_tier
    with pytest.raises(ValueError, match="evidence_tier"):
        select_e1_e2_positive_evidence(pool)


# ---------------------------------------------------------------------------
# build_nnpu_dataset: E1+E2 positive, C1-only unlabeled, leakage checks
# ---------------------------------------------------------------------------


def test_build_nnpu_dataset_includes_e1_and_e2_excludes_e3():
    data = _experiment_data()
    config = _config()
    dataset = build_nnpu_dataset(data, config)
    assert set(dataset.train_positive_ids.tolist()) == {"P1", "P2", "P3", "P4"}  # E3 (P5) excluded
    assert set(dataset.validation_positive_ids.tolist()) == {"P6", "P7"}  # E3 (P8) excluded
    assert dataset.e1_train_count == 2
    assert dataset.e2_train_count == 2
    assert dataset.e1_validation_count == 1
    assert dataset.e2_validation_count == 1


def test_build_nnpu_dataset_preserves_evidence_tier_provenance():
    data = _experiment_data()
    dataset = build_nnpu_dataset(data, _config())
    tier_by_id = dict(zip(dataset.train_positive_ids.tolist(), dataset.train_positive_tiers.tolist()))
    assert tier_by_id["P1"] == "E1"
    assert tier_by_id["P3"] == "E2"


def test_build_nnpu_dataset_unlabeled_group_is_c1_only_no_label_field():
    data = _experiment_data()
    dataset = build_nnpu_dataset(data, _config())
    all_unlabeled_ids = set(dataset.train_unlabeled_ids.tolist()) | set(dataset.validation_unlabeled_ids.tolist())
    assert all_unlabeled_ids <= set(data.c1.peptide_ids.tolist())
    # Structurally impossible for C2/C3/external/labels to appear.
    assert not hasattr(dataset, "train_unlabeled_labels")
    assert not hasattr(dataset, "c2_ids")
    assert not hasattr(dataset, "external_control_ids")


def test_build_nnpu_dataset_c1_partition_matches_pn_shared_splitter():
    data = _experiment_data()
    config = _config()
    dataset = build_nnpu_dataset(data, config)
    expected_train, expected_val = split_c1_train_validation(data.c1, config.validation_fraction, config.eval_seed)
    assert set(dataset.train_unlabeled_ids.tolist()) == set(expected_train.peptide_ids.tolist())
    assert set(dataset.validation_unlabeled_ids.tolist()) == set(expected_val.peptide_ids.tolist())


def test_build_nnpu_dataset_rejects_invalid_prior():
    data = _experiment_data()
    with pytest.raises(InvalidPriorError):
        build_nnpu_dataset(data, _config(), prior=1.5)


def test_build_nnpu_dataset_records_prior():
    data = _experiment_data()
    dataset = build_nnpu_dataset(data, _config(), prior=0.2)
    assert dataset.prior == pytest.approx(0.2)


def test_build_nnpu_dataset_default_prior_is_point_one():
    assert DEFAULT_PRIOR == pytest.approx(0.10)


def _pool_with_sequences(pool, peptide_ids, sequences, seed_offset=0, evidence_tier=None):
    n = len(peptide_ids)
    rng = np.random.default_rng(seed_offset + len(pool))
    features = rng.normal(size=(n, FEATURE_DIM)).astype(np.float32)
    tier = np.array(evidence_tier) if evidence_tier is not None else None
    return PoolData(pool=pool, peptide_ids=np.array(peptide_ids), sequences=np.array(sequences), features=features, evidence_tier=tier)


def test_build_nnpu_dataset_rejects_sequence_shared_with_held_out_positive():
    data = _experiment_data()
    shared_sequence = "SHARED_SEQUENCE_WITH_HELD_OUT"
    c1_ids = data.c1.peptide_ids.tolist()
    c1_sequences = [shared_sequence] + data.c1.sequences.tolist()[1:]
    leaky_c1 = _pool_with_sequences("C1", c1_ids, c1_sequences, seed_offset=3)
    held_out_ids = data.held_out_positive.peptide_ids.tolist()
    held_out_sequences = [shared_sequence] + data.held_out_positive.sequences.tolist()[1:]
    leaky_held_out = _pool_with_sequences(
        "FR1_positives_held_out", held_out_ids, held_out_sequences, seed_offset=2,
        evidence_tier=data.held_out_positive.evidence_tier.tolist(),
    )
    data = ExperimentData(
        fold_id=data.fold_id, feature_representation=data.feature_representation, feature_dim=data.feature_dim,
        train_positive=data.train_positive, validation_positive=data.validation_positive,
        held_out_positive=leaky_held_out, c1=leaky_c1, c2=data.c2,
        c3_fold_challenges=data.c3_fold_challenges, external_control=data.external_control, leakage_report=data.leakage_report,
    )
    with pytest.raises(DataLeakageError, match="repeated-sequence leakage"):
        build_nnpu_dataset(data, _config())


def test_build_nnpu_dataset_rejects_sequence_shared_with_c2():
    data = _experiment_data()
    shared_sequence = "SHARED_SEQUENCE_WITH_C2"
    c1_ids = data.c1.peptide_ids.tolist()
    c1_sequences = [shared_sequence] + data.c1.sequences.tolist()[1:]
    leaky_c1 = _pool_with_sequences("C1", c1_ids, c1_sequences, seed_offset=3)
    leaky_c2 = _pool_with_sequences("C2", data.c2.peptide_ids.tolist(), [shared_sequence], seed_offset=4)
    data = ExperimentData(
        fold_id=data.fold_id, feature_representation=data.feature_representation, feature_dim=data.feature_dim,
        train_positive=data.train_positive, validation_positive=data.validation_positive,
        held_out_positive=data.held_out_positive, c1=leaky_c1, c2=leaky_c2,
        c3_fold_challenges=data.c3_fold_challenges, external_control=data.external_control, leakage_report=data.leakage_report,
    )
    with pytest.raises(DataLeakageError, match="repeated-sequence leakage"):
        build_nnpu_dataset(data, _config())


def test_build_nnpu_dataset_raises_on_zero_e1_e2_training_positives():
    data = _experiment_data(train_ids=("P1",), train_tiers=("E3",))
    with pytest.raises(InsufficientDataError, match="E1/E2 training"):
        build_nnpu_dataset(data, _config())


def test_build_nnpu_dataset_raises_on_zero_c1_rows():
    data = _experiment_data(c1_ids=())
    with pytest.raises(InsufficientDataError):
        build_nnpu_dataset(data, _config())


def test_build_nnpu_dataset_features_are_495_dim_float32_and_finite():
    data = _experiment_data()
    dataset = build_nnpu_dataset(data, _config())
    assert dataset.train_positive_features.shape[1] == FEATURE_DIM
    assert dataset.train_positive_features.dtype == np.float32
    assert np.isfinite(dataset.train_positive_features).all()
    assert np.isfinite(dataset.train_unlabeled_features).all()


# ---------------------------------------------------------------------------
# _CyclingIndexSampler
# ---------------------------------------------------------------------------


def test_cycling_sampler_cycles_and_covers_all_indices_before_repeat():
    rng = np.random.default_rng(0)
    sampler = _CyclingIndexSampler(5, rng)
    first_cycle = sampler.next_batch(5)
    assert set(first_cycle.tolist()) == set(range(5))


def test_cycling_sampler_wraps_and_reshuffles():
    rng = np.random.default_rng(0)
    sampler = _CyclingIndexSampler(3, rng)
    batch1 = sampler.next_batch(5)  # wraps after index 3
    assert len(batch1) == 5
    assert set(batch1.tolist()) <= set(range(3))


def test_cycling_sampler_is_deterministic_given_same_seed():
    sampler_a = _CyclingIndexSampler(10, np.random.default_rng(42))
    sampler_b = _CyclingIndexSampler(10, np.random.default_rng(42))
    for _ in range(5):
        assert sampler_a.next_batch(4).tolist() == sampler_b.next_batch(4).tolist()


def test_cycling_sampler_rejects_nonpositive_n():
    with pytest.raises(ValueError):
        _CyclingIndexSampler(0, np.random.default_rng(0))


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------


def _tiny_dataset(n_train_pos=6, n_train_unlabeled=24, n_val_pos=3, n_val_unlabeled=12, seed=0, prior=0.1):
    rng = np.random.default_rng(seed)
    train_pos = rng.normal(size=(n_train_pos, FEATURE_DIM)).astype(np.float32)
    train_unlabeled = rng.normal(size=(n_train_unlabeled, FEATURE_DIM)).astype(np.float32)
    val_pos = rng.normal(size=(n_val_pos, FEATURE_DIM)).astype(np.float32)
    val_unlabeled = rng.normal(size=(n_val_unlabeled, FEATURE_DIM)).astype(np.float32)
    return NnPuDataset(
        train_positive_features=train_pos,
        train_positive_ids=np.array([f"TP{i}" for i in range(n_train_pos)]),
        train_positive_tiers=np.array(["E1"] * (n_train_pos // 2) + ["E2"] * (n_train_pos - n_train_pos // 2)),
        validation_positive_features=val_pos,
        validation_positive_ids=np.array([f"VP{i}" for i in range(n_val_pos)]),
        validation_positive_tiers=np.array(["E1"] * n_val_pos),
        train_unlabeled_features=train_unlabeled,
        train_unlabeled_ids=np.array([f"TU{i}" for i in range(n_train_unlabeled)]),
        validation_unlabeled_features=val_unlabeled,
        validation_unlabeled_ids=np.array([f"VU{i}" for i in range(n_val_unlabeled)]),
        e1_train_count=n_train_pos // 2,
        e2_train_count=n_train_pos - n_train_pos // 2,
        e1_validation_count=n_val_pos,
        e2_validation_count=0,
        c1_validation_fraction=0.2,
        c1_partition_seed=42,
        prior=prior,
    )


def test_training_updates_model_parameters(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir, load_checkpoint

    config = _config(max_epochs=2, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t1")
    model_before = BinaryMlp(MlpArchitecture(input_dim=FEATURE_DIM, hidden_dims=config.hidden_dims))
    initial_params = [p.clone() for p in model_before.parameters()]

    train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)

    reloaded = BinaryMlp(MlpArchitecture(input_dim=FEATURE_DIM, hidden_dims=config.hidden_dims))
    load_checkpoint(run_dir / "checkpoint_last.pt", reloaded)
    changed = any(not torch.equal(a, b) for a, b in zip(initial_params, reloaded.parameters()))
    assert changed, "optimizer did not change any model parameter after training"


def test_training_produces_finite_risks_and_valid_checkpoints(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=3, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t2")
    summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)
    assert summary["executed_epochs"] == 3
    for record in summary["history"]:
        assert np.isfinite(record["train_nnpu_risk"])
        assert np.isfinite(record["val_nnpu_risk"])
    assert (run_dir / "checkpoint_last.pt").exists()
    assert (run_dir / "checkpoint_best.pt").exists()
    assert (run_dir / "learning_curve.svg").exists()


def test_training_logs_every_required_risk_component(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=1, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t3")
    summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)
    required_keys = {
        "train_nnpu_risk", "train_positive_risk_contribution", "train_positive_as_negative_risk",
        "train_unlabeled_as_negative_risk", "train_negative_risk_unclamped", "train_negative_risk_contribution",
        "train_clamped_update_fraction", "val_nnpu_risk", "val_positive_risk_contribution",
        "val_positive_as_negative_risk", "val_unlabeled_as_negative_risk", "val_negative_risk_unclamped",
        "val_negative_risk_contribution", "val_is_clamped", "learning_rate", "prior",
        "n_e1e2_positive_train", "n_c1_unlabeled_train", "n_optimizer_updates_this_epoch", "is_best",
    }
    assert required_keys <= set(summary["history"][0].keys())


def test_training_uses_the_configured_prior_in_every_epoch(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=2, batch_size=4)
    dataset = _tiny_dataset(prior=0.2)
    run_dir = create_run_dir(tmp_path, "t4")
    summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)
    assert summary["prior"] == pytest.approx(0.2)
    for record in summary["history"]:
        assert record["prior"] == pytest.approx(0.2)


def test_nnpu_variant_is_recorded_as_direct_clamped(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=1, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t5")
    summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)
    assert summary["nnpu_variant"] == "direct_clamped"


def test_positive_batch_is_independently_sampled_every_step(tmp_path):
    # With only 6 training positives and an unlabeled pool of 24 at
    # batch_size=4, there are 6 unlabeled mini-batches per epoch -- the
    # cycling positive sampler must wrap around more than once; this is
    # exercised structurally (no crash, finite risk) rather than
    # inspecting internal state directly.
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=1, batch_size=4)
    dataset = _tiny_dataset(n_train_pos=6, n_train_unlabeled=24)
    run_dir = create_run_dir(tmp_path, "t6")
    summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)
    assert summary["history"][0]["n_optimizer_updates_this_epoch"] == 6  # ceil(24/4)


def test_best_checkpoint_corresponds_to_minimum_validation_risk(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir, load_checkpoint

    config = _config(max_epochs=5, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t7")
    summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)

    val_risks = [r["val_nnpu_risk"] for r in summary["history"]]
    assert summary["best_val_nnpu_risk"] == pytest.approx(min(val_risks))

    reloaded = BinaryMlp(MlpArchitecture(input_dim=FEATURE_DIM, hidden_dims=config.hidden_dims))
    info = load_checkpoint(run_dir / "checkpoint_best.pt", reloaded)
    assert info["epoch"] == summary["best_epoch"]


def test_last_checkpoint_is_the_final_executed_epoch(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir, load_checkpoint

    config = _config(max_epochs=4, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t8")
    summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)

    reloaded = BinaryMlp(MlpArchitecture(input_dim=FEATURE_DIM, hidden_dims=config.hidden_dims))
    info = load_checkpoint(run_dir / "checkpoint_last.pt", reloaded)
    assert info["epoch"] == summary["executed_epochs"] - 1


def test_checkpoint_reload_reproduces_inference(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir, load_checkpoint

    config = _config(max_epochs=2, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t9")
    train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)

    reloaded = BinaryMlp(MlpArchitecture(input_dim=FEATURE_DIM, hidden_dims=config.hidden_dims))
    load_checkpoint(run_dir / "checkpoint_best.pt", reloaded)
    sample = torch.from_numpy(dataset.validation_positive_features)
    proba = reloaded.predict_proba(sample)
    assert proba.shape == (dataset.validation_positive_features.shape[0], 1)
    assert torch.isfinite(proba).all()
    assert bool(((proba >= 0) & (proba <= 1)).all().item())


def test_non_finite_training_features_are_rejected(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=1, batch_size=4)
    dataset = _tiny_dataset()
    dataset.train_positive_features[0, 0] = np.inf
    run_dir = create_run_dir(tmp_path, "t10")
    with pytest.raises(RuntimeError, match="Non-finite"):
        train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)


def test_early_stopping_disabled_runs_full_max_epochs(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=3, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t11")
    summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)
    assert summary["executed_epochs"] == 3


def test_early_stopping_monitors_validation_risk_only(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=50, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t12")
    summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=3, min_improvement=1e-9)
    assert summary["executed_epochs"] <= 50
    # If it stopped early, it must be because validation risk stalled,
    # not an external signal -- re-derive the stopping condition.
    if summary["executed_epochs"] < 50:
        val_risks = [h["val_nnpu_risk"] for h in summary["history"]]
        best_idx = val_risks.index(min(val_risks))
        assert summary["executed_epochs"] - 1 - best_idx >= 3


def test_same_seed_training_is_bit_identical_on_cpu(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=3, batch_size=4, train_seed=5)
    dataset = _tiny_dataset()
    run_dir_a = create_run_dir(tmp_path, "repro_a")
    run_dir_b = create_run_dir(tmp_path, "repro_b")
    summary_a = train_nnpu_baseline(config, dataset, run_dir_a, early_stopping_patience=None)
    summary_b = train_nnpu_baseline(config, dataset, run_dir_b, early_stopping_patience=None)
    assert summary_a["history"] == summary_b["history"]
    assert summary_a["best_epoch"] == summary_b["best_epoch"]


def test_stability_diagnostics_are_present():
    from plantaox.c2_pu.run_recorder import create_run_dir
    import tempfile

    config = _config(max_epochs=2, batch_size=4)
    dataset = _tiny_dataset()
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = create_run_dir(tmp, "t13")
        summary = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=None)
    diag = summary["stability_diagnostics"]
    assert "persistent_negative_risk_clamping_last_5_epochs" in diag
    assert "validation_prediction_saturation" in diag
    assert "diverging_risk_detected" in diag
