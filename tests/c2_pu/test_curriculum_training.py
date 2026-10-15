from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from plantaox.c2_pu.curriculum_training import (
    CurriculumData,
    compute_weighted_corrective_risk,
    train_curriculum,
)
from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import ExperimentData, PoolData
from plantaox.c2_pu.nnpu_baseline import NnPuDataset


def test_weighted_corrective_risk_uses_normalized_e1_e2_weights_and_finite_gradients():
    positive = torch.tensor([0.0, 1.0], requires_grad=True)
    unlabeled = torch.tensor([-0.5, 0.5], requires_grad=True)
    weights = torch.tensor([1.0, 0.5])
    result = compute_weighted_corrective_risk(
        positive, unlabeled, weights, prior=0.1, beta=0.0, gamma=1.0
    )
    expected_positive = torch.sum(weights * torch.nn.functional.softplus(-positive)) / weights.sum()
    assert result.positive_contribution == pytest.approx(0.1 * expected_positive.item())
    result.training_loss.backward()
    assert torch.isfinite(positive.grad).all()
    assert torch.isfinite(unlabeled.grad).all()


def _pool(name: str, prefix: str, n: int, dim: int, rng, tiers=None) -> PoolData:
    return PoolData(
        pool=name,
        peptide_ids=np.asarray([f"{prefix}{i}" for i in range(n)]),
        sequences=np.asarray(["A" * (3 + i) for i in range(n)]),
        features=rng.normal(size=(n, dim)).astype(np.float32),
        evidence_tier=np.asarray(tiers) if tiers is not None else None,
    )


def test_three_stage_smoke_preserves_checkpoint_parent_chain_and_reload(tmp_path):
    rng = np.random.default_rng(11)
    dim = 15
    train_pos = _pool("train", "p", 8, dim, rng, ["E1"] * 4 + ["E2"] * 4)
    val_pos = _pool("val", "v", 4, dim, rng, ["E1"] * 2 + ["E2"] * 2)
    held = _pool("held", "h", 3, dim, rng, ["E1", "E1", "E2"])
    c1 = _pool("C1", "c1_", 8, dim, rng)
    c2 = _pool("C2", "c2_", 6, dim, rng)
    c3 = _pool("C3", "c3_", 6, dim, rng)
    ext = _pool("external", "x", 3, dim, rng)
    data = ExperimentData(0, "descriptors", dim, train_pos, val_pos, held, c1, c2, c3, ext,
                          {"overlap_found": False})
    nnpu = NnPuDataset(
        train_pos.features, train_pos.peptide_ids, train_pos.evidence_tier,
        val_pos.features, val_pos.peptide_ids, val_pos.evidence_tier,
        c1.features[:5], c1.peptide_ids[:5], c1.features[5:], c1.peptide_ids[5:],
        4, 4, 2, 2, 0.15, 42, 0.1,
    )
    curriculum = CurriculumData(
        nnpu,
        {"C1": c1.features[:5], "C2": c2.features, "C3": c3.features},
        {"C1": c1.peptide_ids[:5], "C2": c2.peptide_ids, "C3": c3.peptide_ids},
    )
    config = ExperimentConfig(
        experiment_id="curriculum_smoke", baseline="nnPU", fold_id=0,
        feature_representation="descriptors", hidden_dims=(8, 4), batch_size=3,
        max_epochs=2, train_seed=42, device="cpu",
    )
    result = train_curriculum(config, curriculum, data, tmp_path, plateau_patience=5)
    assert [stage["stage"] for stage in result["stages"]] == ["C1", "C2", "C3"]
    assert result["stages"][0]["parent_checkpoint"] is None
    assert result["stages"][1]["parent_checkpoint_sha256"] == result["stages"][0]["best_checkpoint_sha256"]
    assert result["stages"][2]["parent_checkpoint_sha256"] == result["stages"][1]["best_checkpoint_sha256"]
    for stage in result["stages"]:
        assert Path(stage["best_checkpoint"]).exists()
        assert np.isfinite(stage["best_val_nnpu_risk"])
        summary = json.loads((Path(stage["best_checkpoint"]).parent / "stage_summary.json").read_text())
        assert summary["best_checkpoint_reload_epoch"] == stage["best_epoch"]


def test_real_diagnostic_preserves_label_orientation_and_alignment():
    path = Path("data/processed/c2_pu/fr4_external_control_diagnostic.json")
    diagnostic = json.loads(path.read_text(encoding="utf-8"))
    assert diagnostic["status"] == "NO_BLOCKING_IMPLEMENTATION_DEFECT_IDENTIFIED"
    assert diagnostic["orientation_verified"]
    assert diagnostic["label_mapping_verified"]
    assert diagnostic["feature_row_alignment_verified"]
    assert diagnostic["n_external_control"] == 38
    assert diagnostic["control_pattern"]["controls_above_0_5_in_all_five_models"] == 32
