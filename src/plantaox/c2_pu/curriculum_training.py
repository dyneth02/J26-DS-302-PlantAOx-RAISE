"""Task 4.6 fold-0 corrective-nnPU curriculum: C1 -> C2 -> C3."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from plantaox.c2_pu.baseline_evaluation import classification_metrics, score_summary
from plantaox.c2_pu.common.feature_cache import sha256_of
from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import ExperimentData
from plantaox.c2_pu.nnpu_baseline import NnPuDataset, _CyclingIndexSampler, build_nnpu_dataset
from plantaox.c2_pu.nnpu_risk import NNPU_VARIANT_CORRECTIVE_BETA_GAMMA, validate_prior

CURRICULUM_VARIANT = "corrective_beta_gamma_curriculum"
EVIDENCE_WEIGHTS = {"E1": 1.0, "E2": 0.5}


@dataclass(frozen=True)
class CurriculumData:
    nnpu: NnPuDataset
    stage_unlabeled_features: dict[str, np.ndarray]
    stage_unlabeled_ids: dict[str, np.ndarray]


@dataclass(frozen=True)
class WeightedCorrectiveRisk:
    training_loss: object
    reported_risk: object
    positive_contribution: float
    positive_as_negative: float
    unlabeled_as_negative: float
    negative_unclamped: float
    negative_contribution: float
    corrective_branch: bool


def build_curriculum_data(
    data: ExperimentData,
    config: ExperimentConfig,
    c3_ranking_path: Path,
    prior: float = 0.10,
) -> CurriculumData:
    """Assemble stage pools and independently verify sanctioned fold-0 C3 membership."""
    from plantaox.c2_pu.curation.c3 import load_fold_challenges

    nnpu = build_nnpu_dataset(data, config, prior=prior)
    sanctioned = load_fold_challenges(c3_ranking_path, config.fold_id)
    sanctioned_ids = sanctioned["peptide_id"].astype(str).tolist()
    observed_ids = data.c3_fold_challenges.peptide_ids.astype(str).tolist()
    if sanctioned_ids != observed_ids:
        raise ValueError("C3 feature rows do not match load_fold_challenges(ranking_path, fold_id) order/membership")
    return CurriculumData(
        nnpu=nnpu,
        stage_unlabeled_features={
            "C1": nnpu.train_unlabeled_features,
            "C2": data.c2.features,
            "C3": data.c3_fold_challenges.features,
        },
        stage_unlabeled_ids={
            "C1": nnpu.train_unlabeled_ids,
            "C2": data.c2.peptide_ids,
            "C3": data.c3_fold_challenges.peptide_ids,
        },
    )


def compute_weighted_corrective_risk(
    positive_logits,
    unlabeled_logits,
    positive_weights,
    *,
    prior: float,
    beta: float,
    gamma: float,
) -> WeightedCorrectiveRisk:
    """Corrective nnPU with normalized E1/E2 weights in both positive expectations."""
    import torch
    import torch.nn.functional as functional

    prior = validate_prior(prior)
    if positive_logits.numel() == 0 or unlabeled_logits.numel() == 0:
        raise ValueError("positive and unlabeled batches must both be non-empty")
    weights = positive_weights.reshape(-1).to(positive_logits)
    if len(weights) != positive_logits.numel() or not torch.isfinite(weights).all() or torch.any(weights <= 0):
        raise ValueError("positive weights must be finite, positive, and match positive logits")
    p = positive_logits.reshape(-1)
    u = unlabeled_logits.reshape(-1)
    p_positive = torch.sum(weights * functional.softplus(-p)) / torch.sum(weights)
    p_negative = torch.sum(weights * functional.softplus(p)) / torch.sum(weights)
    u_negative = functional.softplus(u).mean()
    negative = u_negative - prior * p_negative
    positive = prior * p_positive
    corrective = bool(negative.detach().item() < -beta)
    optimizer_loss = -gamma * negative if corrective else positive + negative
    reported = positive + torch.clamp(negative, min=0.0)
    values = (optimizer_loss, reported, p_positive, p_negative, u_negative, negative)
    if not all(torch.isfinite(value).all() for value in values):
        raise RuntimeError("non-finite weighted corrective nnPU risk")
    return WeightedCorrectiveRisk(
        training_loss=optimizer_loss,
        reported_risk=reported,
        positive_contribution=float(positive.detach().item()),
        positive_as_negative=float(p_negative.detach().item()),
        unlabeled_as_negative=float(u_negative.detach().item()),
        negative_unclamped=float(negative.detach().item()),
        negative_contribution=float(max(0.0, negative.detach().item())),
        corrective_branch=corrective,
    )


def _positive_weights(tiers: np.ndarray) -> np.ndarray:
    try:
        return np.asarray([EVIDENCE_WEIGHTS[str(tier)] for tier in tiers], dtype=np.float32)
    except KeyError as exc:
        raise ValueError(f"unsupported positive evidence tier {exc.args[0]!r}") from exc


def _optimizer(config: ExperimentConfig, model):
    import torch
    if config.optimizer == "adam":
        return torch.optim.Adam(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    if config.optimizer == "sgd":
        return torch.optim.SGD(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    raise ValueError(f"unsupported optimizer {config.optimizer!r}")


def _score_model(model, features: np.ndarray) -> np.ndarray:
    import torch
    model.eval()
    with torch.no_grad():
        result = model.predict_proba(torch.from_numpy(features.astype(np.float32))).cpu().numpy().reshape(-1)
    if not np.isfinite(result).all() or np.any((result < 0) | (result > 1)):
        raise RuntimeError("invalid curriculum inference score")
    return result


def train_curriculum(
    config: ExperimentConfig,
    curriculum: CurriculumData,
    data: ExperimentData,
    run_dir: Path,
    *,
    prior: float = 0.10,
    beta: float = 0.0,
    gamma: float = 1.0,
    plateau_patience: int = 5,
    min_improvement: float = 1e-4,
) -> dict:
    """Train one seeded model through C1, C2, C3; reset optimizer at transitions."""
    import torch

    from plantaox.c2_pu.common.seeding import resolve_device, set_global_seed
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.run_recorder import append_epoch_metrics, load_checkpoint, save_checkpoint

    if plateau_patience != 5:
        raise ValueError("Task 4.6 Planner requires plateau_patience=5")
    prior = validate_prior(prior)
    seed_context = set_global_seed(config.train_seed)
    device = resolve_device(config.device)
    model = BinaryMlp(MlpArchitecture(config.feature_dim, config.hidden_dims)).to(device)
    nnpu = curriculum.nnpu
    train_positive = torch.from_numpy(nnpu.train_positive_features).to(device)
    train_weights = torch.from_numpy(_positive_weights(nnpu.train_positive_tiers)).to(device)
    val_positive = torch.from_numpy(nnpu.validation_positive_features).to(device)
    val_weights = torch.from_numpy(_positive_weights(nnpu.validation_positive_tiers)).to(device)
    val_unlabeled = torch.from_numpy(nnpu.validation_unlabeled_features).to(device)
    stage_results = []
    parent_checkpoint = None
    global_epoch = 0
    started = time.time()

    for stage_index, stage_name in enumerate(("C1", "C2", "C3"), start=1):
        stage_dir = Path(run_dir) / f"stage_{stage_index}_{stage_name.lower()}"
        stage_dir.mkdir(parents=True, exist_ok=False)
        unlabeled_np = curriculum.stage_unlabeled_features[stage_name]
        unlabeled = torch.from_numpy(unlabeled_np).to(device)
        optimizer = _optimizer(config, model)  # weights continue; optimizer state intentionally resets.
        u_rng = np.random.default_rng(config.train_seed + stage_index * 10_007)
        p_sampler = _CyclingIndexSampler(
            len(train_positive), np.random.default_rng(config.train_seed + stage_index * 10_007 + 1_000_003)
        )
        best_val, best_epoch, stale = float("inf"), None, 0
        total_updates = corrections = 0
        history = []

        for stage_epoch in range(config.max_epochs):
            model.train()
            order = np.arange(len(unlabeled_np))
            u_rng.shuffle(order)
            sums = {key: 0.0 for key in ("reported", "optimizer", "positive", "p_as_n", "u_as_n", "negative")}
            epoch_updates = epoch_corrections = 0
            for start in range(0, len(order), config.batch_size):
                u_idx = order[start:start + config.batch_size]
                p_idx = p_sampler.next_batch(len(u_idx))
                p_index = torch.from_numpy(p_idx).long().to(device)
                u_index = torch.from_numpy(u_idx).long().to(device)
                optimizer.zero_grad()
                risk = compute_weighted_corrective_risk(
                    model(train_positive[p_index]), model(unlabeled[u_index]), train_weights[p_index],
                    prior=prior, beta=beta, gamma=gamma,
                )
                risk.training_loss.backward()
                for name, parameter in model.named_parameters():
                    if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                        raise RuntimeError(f"non-finite gradient in {name} at {stage_name} epoch {stage_epoch}")
                optimizer.step()
                n = len(u_idx)
                sums["reported"] += float(risk.reported_risk.item()) * n
                sums["optimizer"] += float(risk.training_loss.item()) * n
                sums["positive"] += risk.positive_contribution * n
                sums["p_as_n"] += risk.positive_as_negative * n
                sums["u_as_n"] += risk.unlabeled_as_negative * n
                sums["negative"] += risk.negative_unclamped * n
                epoch_corrections += int(risk.corrective_branch)
                epoch_updates += 1
            total_updates += epoch_updates
            corrections += epoch_corrections

            model.eval()
            with torch.no_grad():
                validation = compute_weighted_corrective_risk(
                    model(val_positive), model(val_unlabeled), val_weights,
                    prior=prior, beta=beta, gamma=gamma,
                )
            val_value = float(validation.reported_risk.item())
            is_best = val_value < best_val - min_improvement
            if is_best:
                best_val, best_epoch, stale = val_value, stage_epoch, 0
            else:
                stale += 1
            metrics = {
                "stage": stage_name, "stage_index": stage_index, "stage_epoch": stage_epoch,
                "global_epoch": global_epoch, "train_nnpu_risk": sums["reported"] / len(order),
                "train_optimizer_loss": sums["optimizer"] / len(order),
                "train_positive_risk_contribution": sums["positive"] / len(order),
                "train_positive_as_negative_risk": sums["p_as_n"] / len(order),
                "train_unlabeled_as_negative_risk": sums["u_as_n"] / len(order),
                "train_negative_risk_unclamped": sums["negative"] / len(order),
                "train_corrective_branch_fraction": epoch_corrections / epoch_updates,
                "val_nnpu_risk": val_value,
                "val_negative_risk_unclamped": validation.negative_unclamped,
                "n_optimizer_updates_this_epoch": epoch_updates, "is_best": is_best,
            }
            append_epoch_metrics(stage_dir, stage_epoch, metrics)
            history.append(metrics)
            extra = {
                "variant": CURRICULUM_VARIANT, "stage": stage_name, "stage_index": stage_index,
                "parent_checkpoint": str(parent_checkpoint) if parent_checkpoint else None,
                "parent_checkpoint_sha256": sha256_of(parent_checkpoint) if parent_checkpoint else None,
                "prior": prior, "beta": beta, "gamma": gamma, "positive_weights": EVIDENCE_WEIGHTS,
                "optimizer_state_policy": "reset_each_stage_model_weights_warm_started",
            }
            save_checkpoint(stage_dir, model, stage_epoch, metrics, is_best=False, extra=extra)
            if is_best:
                save_checkpoint(stage_dir, model, stage_epoch, metrics, is_best=True, extra=extra)
            global_epoch += 1
            if stale >= plateau_patience:
                break

        best_checkpoint = stage_dir / "checkpoint_best.pt"
        load_info = load_checkpoint(best_checkpoint, model)
        model.to(device)
        validation_scores = _score_model(model, nnpu.validation_positive_features)
        c1_scores = _score_model(model, data.c1.features)
        c2_scores = _score_model(model, data.c2.features)
        c3_scores = _score_model(model, data.c3_fold_challenges.features)
        held_scores = _score_model(model, data.held_out_positive.features)
        control_scores = _score_model(model, data.external_control.features)
        labels = np.concatenate([np.ones(len(held_scores)), np.zeros(len(control_scores))])
        external_metrics = classification_metrics(
            labels, np.concatenate([held_scores, control_scores]), np.concatenate([held_scores, control_scores])
        )
        stage_result = {
            "stage": stage_name, "stage_index": stage_index,
            "parent_checkpoint": str(parent_checkpoint) if parent_checkpoint else None,
            "parent_checkpoint_sha256": sha256_of(parent_checkpoint) if parent_checkpoint else None,
            "best_checkpoint": str(best_checkpoint), "best_checkpoint_sha256": sha256_of(best_checkpoint),
            "last_checkpoint": str(stage_dir / "checkpoint_last.pt"),
            "last_checkpoint_sha256": sha256_of(stage_dir / "checkpoint_last.pt"),
            "best_checkpoint_reload_epoch": load_info["epoch"],
            "unlabeled_pool": stage_name,
            "n_train_positive": int(len(nnpu.train_positive_ids)),
            "n_train_E1": nnpu.e1_train_count, "n_train_E2": nnpu.e2_train_count,
            "n_train_unlabeled": int(len(unlabeled_np)),
            "validation_protocol": "fixed weighted E1+E2 positive validation plus fixed C1 validation surrogate risk",
            "n_validation_positive": int(len(nnpu.validation_positive_ids)),
            "n_validation_c1": int(len(nnpu.validation_unlabeled_ids)),
            "executed_epochs": len(history), "best_epoch": best_epoch,
            "best_val_nnpu_risk": best_val, "final_val_nnpu_risk": history[-1]["val_nnpu_risk"],
            "mean_corrective_branch_fraction": corrections / total_updates,
            "total_optimizer_updates": total_updates,
            "history": history,
            "score_summaries": {
                "positive_validation": score_summary(validation_scores),
                "C1": score_summary(c1_scores), "C2": score_summary(c2_scores), "C3_fold0": score_summary(c3_scores),
                "held_out_positive": score_summary(held_scores), "external_control": score_summary(control_scores),
            },
            "external_assay_supported_evaluation": external_metrics,
        }
        (stage_dir / "stage_summary.json").write_text(json.dumps(stage_result, indent=2), encoding="utf-8")
        stage_results.append(stage_result)
        parent_checkpoint = best_checkpoint

    return {
        "variant": CURRICULUM_VARIANT, "learner": NNPU_VARIANT_CORRECTIVE_BETA_GAMMA,
        "seed_context": seed_context, "device": str(device), "prior": prior, "beta": beta, "gamma": gamma,
        "positive_evidence_weights": EVIDENCE_WEIGHTS, "plateau_patience": plateau_patience,
        "min_improvement": min_improvement, "optimizer_state_policy": "reset_each_stage_model_weights_warm_started",
        "stage_order": ["C1", "C2", "C3"], "stages": stage_results,
        "elapsed_seconds": time.time() - started,
    }


def render_curriculum_trajectory_svg(path: Path, rows: list[dict]) -> None:
    width, height, margin = 900, 460, 70
    labels = [row["condition"] for row in rows]
    series = (("positive_recovery", "Positive recovery", "#2563eb"),
              ("c1_fraction_gt_0_5", "C1 > 0.5", "#10b981"),
              ("c2_fraction_gt_0_5", "C2 > 0.5", "#f59e0b"),
              ("c3_fraction_gt_0_5", "C3 > 0.5", "#dc2626"))
    x_step = (width - 2 * margin) / (len(rows) - 1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{width/2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">Curriculum score trajectory (fold 0)</text>']
    for tick in range(6):
        value = tick / 5
        y = height - margin - value * (height - 2 * margin)
        parts.append(f'<line x1="{margin}" y1="{y:.1f}" x2="{width-margin}" y2="{y:.1f}" stroke="#ddd"/>')
    for key, title, color in series:
        points = []
        for i, row in enumerate(rows):
            x = margin + i * x_step
            y = height - margin - float(row[key]) * (height - 2 * margin)
            points.append(f"{x:.1f},{y:.1f}")
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
    for i, label in enumerate(labels):
        parts.append(f'<text x="{margin+i*x_step:.1f}" y="{height-margin+20}" text-anchor="middle" font-family="sans-serif" font-size="11">{label}</text>')
    for i, (_, title, color) in enumerate(series):
        parts.append(f'<rect x="{margin+i*190}" y="{height-25}" width="12" height="12" fill="{color}"/>')
        parts.append(f'<text x="{margin+18+i*190}" y="{height-15}" font-family="sans-serif" font-size="11">{title}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8", newline="\n")
