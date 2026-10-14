"""Unit tests for pn_baseline.py (Bucket 4, Task 4.2) -- dataset
construction, leakage checks, and the training loop, all against small,
fully synthetic fixtures (no real cached artifacts required; a separate
acceptance test exercises the real fold-0 data -- see
test_fr4_pn_baseline_acceptance.py)."""

from __future__ import annotations

import copy

import numpy as np
import torch
import pytest

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import DataLeakageError, ExperimentData, PoolData
from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
from plantaox.c2_pu.pn_baseline import (
    InsufficientDataError,
    build_pn_dataset,
    compute_pos_weight,
    render_loss_curve_svg,
    select_positive_evidence_tier,
    split_c1_train_validation,
    train_pn_baseline,
)

FEATURE_DIM = 495


def _pool(pool, peptide_ids, seed_offset=0, evidence_tier=None):
    n = len(peptide_ids)
    rng = np.random.default_rng(seed_offset + len(pool))
    features = rng.normal(size=(n, FEATURE_DIM)).astype(np.float32)
    sequences = np.array([f"SEQ_{pool}_{pid}" for pid in peptide_ids])
    tier = np.array(evidence_tier) if evidence_tier is not None else None
    return PoolData(pool=pool, peptide_ids=np.array(peptide_ids), sequences=sequences, features=features, evidence_tier=tier)


def _experiment_data(
    train_ids=("P1", "P2", "P3", "P4"),
    train_tiers=("E1", "E1", "E2", "E2"),
    val_ids=("P5", "P6"),
    val_tiers=("E1", "E2"),
    held_out_ids=("P7", "P8"),
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
    base = {"experiment_id": "pn_test", "baseline": "PN", "fold_id": 0, "validation_fraction": 0.2, "eval_seed": 1}
    base.update(overrides)
    return ExperimentConfig(**base)


# ---------------------------------------------------------------------------
# E1-only selection / E2 exclusion (tests 1, 2)
# ---------------------------------------------------------------------------


def test_select_positive_evidence_tier_keeps_only_e1():
    pool = _pool("FR1_positives_train", ["P1", "P2", "P3", "P4"], evidence_tier=["E1", "E2", "E1", "E2"])
    e1_only = select_positive_evidence_tier(pool)
    assert set(e1_only.peptide_ids.tolist()) == {"P1", "P3"}
    assert set(e1_only.evidence_tier.tolist()) == {"E1"}


def test_select_positive_evidence_tier_excludes_e2_entirely():
    pool = _pool("FR1_positives_train", ["P1", "P2"], evidence_tier=["E1", "E2"])
    e1_only = select_positive_evidence_tier(pool)
    assert "P2" not in e1_only.peptide_ids.tolist()


def test_select_positive_evidence_tier_raises_without_evidence_info():
    pool = _pool("C1", ["C1-1", "C1-2"])  # no evidence_tier
    with pytest.raises(ValueError, match="evidence_tier"):
        select_positive_evidence_tier(pool)


# ---------------------------------------------------------------------------
# C1 train/validation partition (deterministic, sequence-disjoint)
# ---------------------------------------------------------------------------


def test_split_c1_train_validation_is_disjoint_and_covers_all_ids():
    c1 = _pool("C1", [f"C1-{i}" for i in range(20)])
    train, val = split_c1_train_validation(c1, validation_fraction=0.2, seed=42)
    train_ids = set(train.peptide_ids.tolist())
    val_ids = set(val.peptide_ids.tolist())
    assert train_ids.isdisjoint(val_ids)
    assert train_ids | val_ids == set(c1.peptide_ids.tolist())
    assert set(train.sequences.tolist()).isdisjoint(set(val.sequences.tolist()))


def test_split_c1_train_validation_is_deterministic():
    c1 = _pool("C1", [f"C1-{i}" for i in range(20)])
    train1, val1 = split_c1_train_validation(c1, 0.2, seed=7)
    train2, val2 = split_c1_train_validation(c1, 0.2, seed=7)
    assert train1.peptide_ids.tolist() == train2.peptide_ids.tolist()
    assert val1.peptide_ids.tolist() == val2.peptide_ids.tolist()


def test_split_c1_train_validation_different_seeds_differ():
    c1 = _pool("C1", [f"C1-{i}" for i in range(20)])
    _, val_a = split_c1_train_validation(c1, 0.2, seed=1)
    _, val_b = split_c1_train_validation(c1, 0.2, seed=2)
    assert val_a.peptide_ids.tolist() != val_b.peptide_ids.tolist()


# ---------------------------------------------------------------------------
# build_pn_dataset: E1-only, C1-only, leakage checks (tests 1-7)
# ---------------------------------------------------------------------------


def test_build_pn_dataset_uses_e1_only_and_excludes_e2():
    data = _experiment_data()
    config = _config()
    dataset = build_pn_dataset(data, config)
    assert set(dataset.e1_train_ids) == {"P1", "P2"}  # only the E1-tagged training positives
    assert set(dataset.e1_validation_ids) == {"P5"}  # only the E1-tagged validation positive
    assert "P3" not in dataset.e1_train_ids and "P4" not in dataset.e1_train_ids  # E2 excluded


def test_build_pn_dataset_only_draws_negatives_from_c1():
    data = _experiment_data()
    config = _config()
    dataset = build_pn_dataset(data, config)
    all_negative_ids = set(dataset.c1_train_ids) | set(dataset.c1_validation_ids)
    assert all_negative_ids <= set(data.c1.peptide_ids.tolist())
    # Structurally impossible for C2/C3/external to appear -- PnDataset has no field for them.
    assert not hasattr(dataset, "c2_ids")
    assert not hasattr(dataset, "external_control_ids")


def test_build_pn_dataset_class_counts_are_correct():
    data = _experiment_data()
    config = _config()
    dataset = build_pn_dataset(data, config)
    assert dataset.class_counts["train_positive"] == 2
    assert dataset.class_counts["validation_positive"] == 1
    assert dataset.class_counts["train_negative"] + dataset.class_counts["validation_negative"] == 20


def _pool_with_sequences(pool, peptide_ids, sequences, seed_offset=0, evidence_tier=None):
    n = len(peptide_ids)
    rng = np.random.default_rng(seed_offset + len(pool))
    features = rng.normal(size=(n, FEATURE_DIM)).astype(np.float32)
    tier = np.array(evidence_tier) if evidence_tier is not None else None
    return PoolData(pool=pool, peptide_ids=np.array(peptide_ids), sequences=np.array(sequences), features=features, evidence_tier=tier)


def test_build_pn_dataset_rejects_sequence_shared_with_external_control():
    # Built at construction time (not via post-hoc numpy element mutation,
    # which can silently truncate under fixed-width string dtypes) so the
    # C1 pool's first sequence is IDENTICAL to the external control's.
    data = _experiment_data()
    shared_sequence = "SHARED_SEQUENCE_WITH_EXTERNAL_CONTROL"
    c1_ids = data.c1.peptide_ids.tolist()
    c1_sequences = [shared_sequence] + data.c1.sequences.tolist()[1:]
    leaky_c1 = _pool_with_sequences("C1", c1_ids, c1_sequences, seed_offset=3)
    leaky_external = _pool_with_sequences(
        "external_control", data.external_control.peptide_ids.tolist(), [shared_sequence], seed_offset=6
    )
    data = ExperimentData(
        fold_id=data.fold_id, feature_representation=data.feature_representation, feature_dim=data.feature_dim,
        train_positive=data.train_positive, validation_positive=data.validation_positive,
        held_out_positive=data.held_out_positive, c1=leaky_c1, c2=data.c2,
        c3_fold_challenges=data.c3_fold_challenges, external_control=leaky_external, leakage_report=data.leakage_report,
    )
    with pytest.raises(DataLeakageError, match="repeated-sequence leakage"):
        build_pn_dataset(data, _config())


def test_build_pn_dataset_rejects_sequence_shared_with_held_out_positive():
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
        build_pn_dataset(data, _config())


def test_build_pn_dataset_raises_on_zero_e1_training_positives():
    data = _experiment_data(train_ids=("P1", "P2"), train_tiers=("E2", "E2"))
    with pytest.raises(InsufficientDataError, match="E1 training"):
        build_pn_dataset(data, _config())


def test_build_pn_dataset_raises_on_zero_c1_rows():
    data = _experiment_data(c1_ids=())
    with pytest.raises(InsufficientDataError):
        build_pn_dataset(data, _config())


def test_build_pn_dataset_features_are_495_dim_float32_and_finite():
    data = _experiment_data()
    dataset = build_pn_dataset(data, _config())
    assert dataset.train_features.shape[1] == FEATURE_DIM
    assert dataset.train_features.dtype == np.float32
    assert np.isfinite(dataset.train_features).all()
    assert np.isfinite(dataset.validation_features).all()


def test_build_pn_dataset_labels_are_1_for_positive_0_for_c1():
    data = _experiment_data()
    dataset = build_pn_dataset(data, _config())
    n_pos = dataset.class_counts["train_positive"]
    assert (dataset.train_labels[:n_pos] == 1.0).all()
    assert (dataset.train_labels[n_pos:] == 0.0).all()


# ---------------------------------------------------------------------------
# Training-only class weight (test 11)
# ---------------------------------------------------------------------------


def test_compute_pos_weight_uses_training_counts_only():
    counts = {"train_positive": 10, "train_negative": 100, "validation_positive": 999, "validation_negative": 1}
    weight = compute_pos_weight(counts, use_class_weight=True)
    assert weight == pytest.approx(10.0)  # 100/10, ignoring the wildly different validation counts


def test_compute_pos_weight_disabled_returns_none():
    counts = {"train_positive": 10, "train_negative": 100}
    assert compute_pos_weight(counts, use_class_weight=False) is None


def test_compute_pos_weight_raises_on_zero_training_positives():
    counts = {"train_positive": 0, "train_negative": 100}
    with pytest.raises(InsufficientDataError):
        compute_pos_weight(counts, use_class_weight=True)


# ---------------------------------------------------------------------------
# Training loop: BCE-with-logits sanity, optimizer updates, finiteness,
# checkpoint best/last distinction (tests 9, 10, 12, 13, 15, 16)
# ---------------------------------------------------------------------------


def _tiny_dataset(n_train_pos=6, n_train_neg=12, n_val_pos=3, n_val_neg=6, seed=0):
    from plantaox.c2_pu.pn_baseline import PnDataset

    rng = np.random.default_rng(seed)
    train_features = rng.normal(size=(n_train_pos + n_train_neg, FEATURE_DIM)).astype(np.float32)
    train_labels = np.concatenate([np.ones(n_train_pos, dtype=np.float32), np.zeros(n_train_neg, dtype=np.float32)])
    val_features = rng.normal(size=(n_val_pos + n_val_neg, FEATURE_DIM)).astype(np.float32)
    val_labels = np.concatenate([np.ones(n_val_pos, dtype=np.float32), np.zeros(n_val_neg, dtype=np.float32)])
    return PnDataset(
        train_features=train_features,
        train_labels=train_labels,
        train_peptide_ids=np.array([f"T{i}" for i in range(len(train_labels))]),
        validation_features=val_features,
        validation_labels=val_labels,
        validation_peptide_ids=np.array([f"V{i}" for i in range(len(val_labels))]),
        class_counts={
            "train_positive": n_train_pos,
            "train_negative": n_train_neg,
            "validation_positive": n_val_pos,
            "validation_negative": n_val_neg,
        },
        e1_train_ids=[f"T{i}" for i in range(n_train_pos)],
        e1_validation_ids=[f"V{i}" for i in range(n_val_pos)],
        c1_train_ids=[f"T{i}" for i in range(n_train_pos, n_train_pos + n_train_neg)],
        c1_validation_ids=[f"V{i}" for i in range(n_val_pos, n_val_pos + n_val_neg)],
        c1_validation_fraction=0.2,
        c1_partition_seed=42,
    )


def test_bce_with_logits_matches_sigmoid_then_bce_numerically():
    torch.manual_seed(0)
    logits = torch.randn(10, 1)
    targets = torch.randint(0, 2, (10, 1)).float()
    direct = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets)
    via_sigmoid = torch.nn.functional.binary_cross_entropy(torch.sigmoid(logits), targets)
    torch.testing.assert_close(direct, via_sigmoid, atol=1e-6, rtol=1e-6)


def test_training_updates_model_parameters(tmp_path):
    config = _config(max_epochs=2, batch_size=4)
    dataset = _tiny_dataset()
    from plantaox.c2_pu.run_recorder import create_run_dir

    run_dir = create_run_dir(tmp_path, "t1")
    model_before = BinaryMlp(MlpArchitecture(input_dim=FEATURE_DIM, hidden_dims=config.hidden_dims))
    initial_params = [p.clone() for p in model_before.parameters()]

    train_pn_baseline(config, dataset, run_dir, early_stopping_patience=None)

    from plantaox.c2_pu.run_recorder import load_checkpoint

    reloaded = BinaryMlp(MlpArchitecture(input_dim=FEATURE_DIM, hidden_dims=config.hidden_dims))
    load_checkpoint(run_dir / "checkpoint_last.pt", reloaded)
    changed = any(not torch.equal(a, b) for a, b in zip(initial_params, reloaded.parameters()))
    assert changed, "optimizer did not change any model parameter after training"


def test_training_produces_finite_losses_and_valid_checkpoints(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=3, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t2")
    summary = train_pn_baseline(config, dataset, run_dir, early_stopping_patience=None)
    assert summary["executed_epochs"] == 3
    for record in summary["history"]:
        assert np.isfinite(record["train_bce_loss"])
        assert np.isfinite(record["val_bce_loss"])
    assert (run_dir / "checkpoint_last.pt").exists()
    assert (run_dir / "checkpoint_best.pt").exists()
    assert (run_dir / "learning_curve.svg").exists()


def test_best_checkpoint_corresponds_to_minimum_validation_loss(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir, load_checkpoint

    config = _config(max_epochs=5, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t3")
    summary = train_pn_baseline(config, dataset, run_dir, early_stopping_patience=None)

    val_losses = [r["val_bce_loss"] for r in summary["history"]]
    assert summary["best_val_loss"] == pytest.approx(min(val_losses))

    reloaded = BinaryMlp(MlpArchitecture(input_dim=FEATURE_DIM, hidden_dims=config.hidden_dims))
    info = load_checkpoint(run_dir / "checkpoint_best.pt", reloaded)
    assert info["epoch"] == summary["best_epoch"]


def test_last_checkpoint_is_the_final_executed_epoch(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir, load_checkpoint

    config = _config(max_epochs=4, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t4")
    summary = train_pn_baseline(config, dataset, run_dir, early_stopping_patience=None)

    reloaded = BinaryMlp(MlpArchitecture(input_dim=FEATURE_DIM, hidden_dims=config.hidden_dims))
    info = load_checkpoint(run_dir / "checkpoint_last.pt", reloaded)
    assert info["epoch"] == summary["executed_epochs"] - 1


def test_non_finite_training_features_are_rejected(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=1, batch_size=4)
    dataset = _tiny_dataset()
    dataset.train_features[0, 0] = np.inf
    run_dir = create_run_dir(tmp_path, "t5")
    with pytest.raises(RuntimeError, match="Non-finite"):
        train_pn_baseline(config, dataset, run_dir, early_stopping_patience=None)


# ---------------------------------------------------------------------------
# Same-seed CPU reproducibility (test 19)
# ---------------------------------------------------------------------------


def test_same_seed_training_is_bit_identical_on_cpu(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=3, batch_size=4, train_seed=5)
    dataset = _tiny_dataset()
    run_dir_a = create_run_dir(tmp_path, "repro_a")
    run_dir_b = create_run_dir(tmp_path, "repro_b")
    summary_a = train_pn_baseline(config, dataset, run_dir_a, early_stopping_patience=None)
    summary_b = train_pn_baseline(config, dataset, run_dir_b, early_stopping_patience=None)
    assert summary_a["history"] == summary_b["history"]
    assert summary_a["best_epoch"] == summary_b["best_epoch"]


# ---------------------------------------------------------------------------
# Early stopping / optional disabling
# ---------------------------------------------------------------------------


def test_early_stopping_disabled_runs_full_max_epochs(tmp_path):
    from plantaox.c2_pu.run_recorder import create_run_dir

    config = _config(max_epochs=3, batch_size=4)
    dataset = _tiny_dataset()
    run_dir = create_run_dir(tmp_path, "t6")
    summary = train_pn_baseline(config, dataset, run_dir, early_stopping_patience=None)
    assert summary["executed_epochs"] == 3


# ---------------------------------------------------------------------------
# Learning curve artifact
# ---------------------------------------------------------------------------


def test_render_loss_curve_svg_writes_a_valid_svg_file(tmp_path):
    history = [
        {"epoch": 0, "train_bce_loss": 0.9, "val_bce_loss": 0.8},
        {"epoch": 1, "train_bce_loss": 0.6, "val_bce_loss": 0.65},
        {"epoch": 2, "train_bce_loss": 0.4, "val_bce_loss": 0.7},
    ]
    path = render_loss_curve_svg(history, tmp_path / "curve.svg")
    content = path.read_text(encoding="utf-8")
    assert content.startswith("<svg")
    assert content.strip().endswith("</svg>")
    assert "polyline" in content
