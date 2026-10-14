"""Focused beta/gamma corrective-nnPU follow-up to accepted Task 4.3."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.nnpu_baseline import NnPuDataset, _CyclingIndexSampler
from plantaox.c2_pu.nnpu_risk import NNPU_VARIANT_CORRECTIVE_BETA_GAMMA, validate_prior
from plantaox.c2_pu.pn_baseline import render_loss_curve_svg


def train_corrective_nnpu(
    config: ExperimentConfig,
    dataset: NnPuDataset,
    run_dir: Path,
    *,
    beta: float = 0.0,
    gamma: float = 1.0,
    early_stopping_patience: int | None = 10,
    min_improvement: float = 1e-4,
) -> dict:
    """Train with Kiryo's corrective step; select checkpoints by reported validation nnPU risk."""
    import torch

    from plantaox.c2_pu.common.seeding import resolve_device, set_global_seed
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.nnpu_risk import compute_corrective_nnpu_risk, compute_nnpu_risk
    from plantaox.c2_pu.run_recorder import append_epoch_metrics, save_checkpoint

    prior = validate_prior(dataset.prior)
    seed_context = set_global_seed(config.train_seed)
    device = resolve_device(config.device)
    model = BinaryMlp(MlpArchitecture(input_dim=config.feature_dim, hidden_dims=config.hidden_dims)).to(device)
    if config.optimizer == "adam":
        optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    elif config.optimizer == "sgd":
        optimizer = torch.optim.SGD(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    else:
        raise ValueError(f"Unsupported optimizer {config.optimizer!r}")

    train_pos = torch.from_numpy(dataset.train_positive_features).to(device)
    train_unlabeled = torch.from_numpy(dataset.train_unlabeled_features).to(device)
    val_pos = torch.from_numpy(dataset.validation_positive_features).to(device)
    val_unlabeled = torch.from_numpy(dataset.validation_unlabeled_features).to(device)
    for name, tensor in (("train_positive", train_pos), ("train_unlabeled", train_unlabeled),
                         ("validation_positive", val_pos), ("validation_unlabeled", val_unlabeled)):
        if not torch.isfinite(tensor).all():
            raise RuntimeError(f"Non-finite input feature(s) detected in {name}.")

    n_u, n_p = train_unlabeled.shape[0], train_pos.shape[0]
    u_rng = np.random.default_rng(config.train_seed)
    p_sampler = _CyclingIndexSampler(n_p, np.random.default_rng(config.train_seed + 1_000_003))
    best_val, best_epoch, stale = float("inf"), None, 0
    history: list[dict] = []
    total_updates = 0
    started = time.time()

    for epoch in range(config.max_epochs):
        model.train()
        u_indices = np.arange(n_u)
        u_rng.shuffle(u_indices)
        sums = {k: 0.0 for k in ("reported", "optimizer", "positive", "p_as_n", "u_as_n", "negative", "negative_contribution")}
        corrections = updates = 0
        for start in range(0, n_u, config.batch_size):
            u_idx = u_indices[start:start + config.batch_size]
            p_idx = p_sampler.next_batch(len(u_idx))
            optimizer.zero_grad()
            p_logits = model(train_pos[torch.from_numpy(p_idx).long().to(device)])
            u_logits = model(train_unlabeled[torch.from_numpy(u_idx).long().to(device)])
            risk = compute_corrective_nnpu_risk(p_logits, u_logits, prior, beta, gamma)
            risk.training_loss.backward()
            for name, param in model.named_parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():
                    raise RuntimeError(f"Non-finite gradient in {name!r} at epoch {epoch}.")
            optimizer.step()
            batch_n = len(u_idx)
            sums["reported"] += float(risk.reported_nnpu_risk.item()) * batch_n
            sums["optimizer"] += float(risk.training_loss.item()) * batch_n
            sums["positive"] += risk.positive_risk_contribution * batch_n
            sums["p_as_n"] += risk.positive_as_negative_risk * batch_n
            sums["u_as_n"] += risk.unlabeled_as_negative_risk * batch_n
            sums["negative"] += risk.negative_risk_unclamped * batch_n
            sums["negative_contribution"] += risk.negative_risk_contribution * batch_n
            corrections += int(risk.corrective_branch)
            updates += 1
            total_updates += 1

        model.eval()
        with torch.no_grad():
            val = compute_nnpu_risk(model(val_pos), model(val_unlabeled), prior)
        val_value = float(val.loss.item())
        is_best = val_value < best_val - min_improvement
        if is_best:
            best_val, best_epoch, stale = val_value, epoch, 0
        else:
            stale += 1
        metrics = {
            "train_nnpu_risk": sums["reported"] / n_u,
            "train_optimizer_loss": sums["optimizer"] / n_u,
            "train_positive_risk_contribution": sums["positive"] / n_u,
            "train_positive_as_negative_risk": sums["p_as_n"] / n_u,
            "train_unlabeled_as_negative_risk": sums["u_as_n"] / n_u,
            "train_negative_risk_unclamped": sums["negative"] / n_u,
            "train_negative_risk_contribution": sums["negative_contribution"] / n_u,
            "train_corrective_branch_fraction": corrections / updates,
            "val_nnpu_risk": val_value,
            "val_positive_risk_contribution": val.positive_risk_contribution,
            "val_positive_as_negative_risk": val.positive_as_negative_risk,
            "val_unlabeled_as_negative_risk": val.unlabeled_as_negative_risk,
            "val_negative_risk_unclamped": val.negative_risk_unclamped,
            "val_negative_risk_contribution": val.negative_risk_contribution,
            "prior": prior, "beta": beta, "gamma": gamma,
            "n_optimizer_updates_this_epoch": updates, "is_best": is_best,
        }
        append_epoch_metrics(run_dir, epoch, metrics)
        history.append({"epoch": epoch, **metrics})
        save_checkpoint(run_dir, model, epoch, metrics, is_best=False,
                        extra={"nnpu_variant": NNPU_VARIANT_CORRECTIVE_BETA_GAMMA, "beta": beta, "gamma": gamma})
        if is_best:
            save_checkpoint(run_dir, model, epoch, metrics, is_best=True,
                            extra={"nnpu_variant": NNPU_VARIANT_CORRECTIVE_BETA_GAMMA, "beta": beta, "gamma": gamma})
        if early_stopping_patience is not None and stale >= early_stopping_patience:
            break

    fractions = [row["train_corrective_branch_fraction"] for row in history]
    curve = render_loss_curve_svg(history, Path(run_dir) / "learning_curve.svg",
                                  train_key="train_nnpu_risk", val_key="val_nnpu_risk",
                                  title="Corrective nnPU: reported train vs validation nnPU risk")
    return {
        "seed_context": seed_context, "device": str(device), "executed_epochs": len(history),
        "best_epoch": best_epoch, "best_val_nnpu_risk": best_val if best_epoch is not None else None,
        "final_train_nnpu_risk": history[-1]["train_nnpu_risk"],
        "final_val_nnpu_risk": history[-1]["val_nnpu_risk"],
        "final_train_optimizer_loss": history[-1]["train_optimizer_loss"],
        "mean_corrective_branch_fraction": float(np.mean(fractions)),
        "final_five_corrective_branch_fraction": float(np.mean(fractions[-5:])),
        "prior": prior, "beta": beta, "gamma": gamma,
        "nnpu_variant": NNPU_VARIANT_CORRECTIVE_BETA_GAMMA,
        "total_optimizer_updates": total_updates, "elapsed_seconds": time.time() - started,
        "history": history, "learning_curve_path": str(curve),
    }
