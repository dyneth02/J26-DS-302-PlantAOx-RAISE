from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
import torch

from plantaox.c2_pu.curriculum_training import (
    CurriculumData,
    _positive_weights,
    build_curriculum_data,
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


@pytest.mark.parametrize("unlabeled_values,corrective", [([0.0, 1.0, -0.5], False), ([-5.0, -4.0, -6.0], True)])
def test_weighted_risk_matches_independent_reference_in_both_branches(unlabeled_values, corrective):
    positive_values = [0.0, 1.0]
    weights = [1.0, 0.5]
    prior = 0.1
    softplus = lambda x: math.log1p(math.exp(x))
    p_plus = sum(w * softplus(-x) for w, x in zip(weights, positive_values)) / sum(weights)
    p_minus = sum(w * softplus(x) for w, x in zip(weights, positive_values)) / sum(weights)
    u_minus = sum(softplus(x) for x in unlabeled_values) / len(unlabeled_values)
    negative = u_minus - prior * p_minus
    expected_optimizer = -negative if corrective else prior * p_plus + negative
    expected_reported = prior * p_plus + max(0.0, negative)

    positive = torch.tensor(positive_values, dtype=torch.float64, requires_grad=True)
    unlabeled = torch.tensor(unlabeled_values, dtype=torch.float64, requires_grad=True)
    result = compute_weighted_corrective_risk(
        positive, unlabeled, torch.tensor(weights, dtype=torch.float64), prior=prior, beta=0.0, gamma=1.0
    )
    assert result.corrective_branch is corrective
    assert result.positive_contribution == pytest.approx(prior * p_plus)
    assert result.positive_as_negative == pytest.approx(p_minus)
    assert result.unlabeled_as_negative == pytest.approx(u_minus)
    assert result.negative_unclamped == pytest.approx(negative)
    assert result.training_loss.item() == pytest.approx(expected_optimizer)
    assert result.reported_risk.item() == pytest.approx(expected_reported)
    result.training_loss.backward()
    expected_u_gradient = (1 if not corrective else -1) * torch.sigmoid(unlabeled.detach()) / len(unlabeled_values)
    assert torch.allclose(unlabeled.grad, expected_u_gradient)


def test_evidence_weights_are_exact_and_e3_is_rejected():
    assert _positive_weights(np.asarray(["E1", "E2", "E1"])).tolist() == [1.0, 0.5, 1.0]
    with pytest.raises(ValueError, match="unsupported positive evidence tier"):
        _positive_weights(np.asarray(["E1", "E3"]))


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


def test_real_curriculum_membership_parent_chain_and_final_reload():
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.run_recorder import load_checkpoint

    summary = json.loads(Path("data/processed/c2_pu/fr4_curriculum_fold0_summary.json").read_text(encoding="utf-8"))
    stages = summary["training"]["stages"]
    assert [stage["stage"] for stage in stages] == ["C1", "C2", "C3"]
    assert [stage["n_train_unlabeled"] for stage in stages] == [3220, 2000, 2000]
    assert all(stage["n_train_positive"] == 604 for stage in stages)
    assert all(stage["n_train_E1"] == 331 and stage["n_train_E2"] == 273 for stage in stages)
    assert stages[1]["parent_checkpoint_sha256"] == stages[0]["best_checkpoint_sha256"]
    assert stages[2]["parent_checkpoint_sha256"] == stages[1]["best_checkpoint_sha256"]
    assert summary["leakage_report"]["overlap_found"] is False

    model = BinaryMlp(MlpArchitecture(495, (128, 64)))
    info = load_checkpoint(Path(stages[-1]["best_checkpoint"]), model)
    scores = model.predict_proba(torch.zeros((3, 495))).detach().numpy()
    assert info["extra"]["stage"] == "C3"
    assert np.isfinite(scores).all()
    assert ((scores >= 0) & (scores <= 1)).all()


def test_real_c3_epoch_zero_checkpoint_follows_c3_updates():
    summary = json.loads(Path("data/processed/c2_pu/fr4_curriculum_fold0_summary.json").read_text(encoding="utf-8"))
    c2, c3 = summary["training"]["stages"][1:]
    parent = torch.load(c2["best_checkpoint"], map_location="cpu", weights_only=False)
    selected = torch.load(c3["best_checkpoint"], map_location="cpu", weights_only=False)
    epoch_log = [json.loads(line) for line in (Path(c3["best_checkpoint"]).parent / "epoch_metrics.jsonl").read_text().splitlines()]
    assert c3["best_epoch"] == selected["epoch"] == c3["best_checkpoint_reload_epoch"] == 0
    assert c3["history"][0]["n_optimizer_updates_this_epoch"] == epoch_log[0]["n_optimizer_updates_this_epoch"] == 63
    assert selected["metrics"] == c3["history"][0]
    assert all(not torch.equal(selected["state_dict"][key], value) for key, value in parent["state_dict"].items())


def test_real_stage_membership_and_fixed_validation_are_fold_safe():
    from plantaox.c2_pu.run import C3_RANKING_PATH, _build_fold0_task4_data

    summary = json.loads(Path("data/processed/c2_pu/fr4_curriculum_fold0_summary.json").read_text(encoding="utf-8"))
    config = ExperimentConfig.from_dict(summary["resolved_config"])
    data = _build_fold0_task4_data(config)
    curriculum = build_curriculum_data(data, config, C3_RANKING_PATH, prior=0.10)
    nnpu = curriculum.nnpu
    assert (nnpu.e1_train_count, nnpu.e2_train_count, nnpu.e1_validation_count, nnpu.e2_validation_count) == (331, 273, 48, 58)
    assert len(nnpu.train_unlabeled_ids) == 3220 and len(nnpu.validation_unlabeled_ids) == 568
    assert len(curriculum.stage_unlabeled_ids["C3"]) == 2000
    assert data.leakage_report["overlap_found"] is False
    assert all(stage["n_validation_positive"] == len(nnpu.validation_positive_ids)
               and stage["n_validation_c1"] == len(nnpu.validation_unlabeled_ids)
               for stage in summary["training"]["stages"])


def test_matched_comparison_is_derived_from_accepted_stage_summary():
    source = Path("data/processed/c2_pu/fr4_curriculum_fold0_summary.json")
    summary = json.loads(source.read_text(encoding="utf-8"))
    with Path("data/processed/c2_pu/fr4_pp1_matched_curriculum_fold0.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["condition"] for row in rows] == [
        "weighted_c1_only_curriculum_reference", "after_c2", "after_c3"
    ]
    for row, stage in zip(rows, summary["training"]["stages"]):
        assert row["source_summary_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
        assert row["best_checkpoint_sha256"] == stage["best_checkpoint_sha256"]
        assert float(row["positive_recovery"]) == stage["score_summaries"]["held_out_positive"]["fraction_gt_0_5"]
        assert float(row["c2_fraction_gt_0_5"]) == stage["score_summaries"]["C2"]["fraction_gt_0_5"]
        assert float(row["external_mcc"]) == stage["external_assay_supported_evaluation"]["mcc"]


def test_cli_help_lists_diagnostic_and_curriculum_stages(capsys):
    from plantaox.c2_pu.run import main

    with pytest.raises(SystemExit) as stopped:
        main(["--help"])
    assert stopped.value.code == 0
    help_text = capsys.readouterr().out
    assert "fr4-external-control-diagnostic" in help_text
    assert "fr4-curriculum" in help_text
