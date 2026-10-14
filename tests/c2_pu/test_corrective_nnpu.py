from __future__ import annotations

import numpy as np
import pytest
import torch

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.nnpu_baseline import NnPuDataset
from plantaox.c2_pu.nnpu_risk import compute_corrective_nnpu_risk, compute_nnpu_risk


def test_normal_branch_uses_unbiased_pu_objective():
    p = torch.tensor([-4.0, -5.0], requires_grad=True)
    u = torch.tensor([4.0, 5.0], requires_grad=True)
    result = compute_corrective_nnpu_risk(p, u, prior=0.1, beta=0.0, gamma=1.0)
    assert not result.corrective_branch
    expected = result.positive_risk_contribution + result.negative_risk_unclamped
    assert result.training_loss.item() == pytest.approx(expected)
    assert torch.isfinite(result.training_loss)


def test_corrective_branch_reverses_negative_risk_gradient():
    p = torch.tensor([0.0, 0.1], requires_grad=True)
    u = torch.tensor([-8.0, -9.0], requires_grad=True)
    result = compute_corrective_nnpu_risk(p, u, prior=0.5, beta=0.0, gamma=1.0)
    assert result.corrective_branch
    result.training_loss.backward()
    # d(-R_n)/d(unlabeled logit) < 0: gradient descent raises the logits,
    # increasing R_n (the intended corrective gradient-ascent step).
    assert (u.grad < 0).all()
    assert torch.isfinite(p.grad).all() and torch.isfinite(u.grad).all()


def test_direct_clamped_behavior_remains_zero_unlabeled_gradient():
    p = torch.tensor([0.0, 0.1], requires_grad=True)
    u = torch.tensor([-8.0, -9.0], requires_grad=True)
    direct = compute_nnpu_risk(p, u, prior=0.5)
    direct.loss.backward()
    assert direct.is_clamped
    assert torch.equal(u.grad, torch.zeros_like(u.grad))


def test_short_training_and_checkpoint_reload(tmp_path):
    from plantaox.c2_pu.corrective_nnpu import train_corrective_nnpu
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.run_recorder import load_checkpoint

    rng = np.random.default_rng(7)
    feature_dim = 15
    dataset = NnPuDataset(
        train_positive_features=rng.normal(size=(12, feature_dim)).astype(np.float32),
        train_positive_ids=np.array([f"p{i}" for i in range(12)]),
        train_positive_tiers=np.array(["E1"] * 6 + ["E2"] * 6),
        validation_positive_features=rng.normal(size=(6, feature_dim)).astype(np.float32),
        validation_positive_ids=np.array([f"vp{i}" for i in range(6)]),
        validation_positive_tiers=np.array(["E1"] * 3 + ["E2"] * 3),
        train_unlabeled_features=rng.normal(size=(20, feature_dim)).astype(np.float32),
        train_unlabeled_ids=np.array([f"u{i}" for i in range(20)]),
        validation_unlabeled_features=rng.normal(size=(8, feature_dim)).astype(np.float32),
        validation_unlabeled_ids=np.array([f"vu{i}" for i in range(8)]),
        e1_train_count=6, e2_train_count=6, e1_validation_count=3, e2_validation_count=3,
        prior=0.1, c1_validation_fraction=0.15, c1_partition_seed=42,
    )
    config = ExperimentConfig(experiment_id="corrective_smoke", baseline="nnPU", fold_id=0,
                              feature_representation="descriptors", hidden_dims=(8, 4), batch_size=5, max_epochs=2)
    summary = train_corrective_nnpu(config, dataset, tmp_path, early_stopping_patience=None)
    assert summary["executed_epochs"] == 2
    model = BinaryMlp(MlpArchitecture(input_dim=feature_dim, hidden_dims=(8, 4)))
    info = load_checkpoint(tmp_path / "checkpoint_best.pt", model)
    assert info["extra"]["nnpu_variant"] == "corrective_beta_gamma"
