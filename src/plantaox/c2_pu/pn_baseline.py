"""Bucket 4, Task 4.2 -- PN (Positive-Negative) supervised baseline.

Builds entirely on Task 4.1's shared infrastructure: ``models.BinaryMlp``
(architecture), ``experiment_data.build_experiment_data`` (fold-aware
pools), ``common/seeding`` (reproducibility), and ``run_recorder``
(checkpoints/logs/manifests). No second MLP, no second checkpointing
system, no second data loader.

**Scientific framing, never to be weakened:** C1 is this project's
assumed-negative (PU-unlabeled) pool -- peptides with no reported
antioxidant activity, not peptides experimentally confirmed inactive.
Training a conventional binary classifier on E1-positive-vs-C1 is the
field's standard practice and exactly the methodological weakness this
project's proposal (abstract, §1.2.1) names and sets out to audit: "no
AOP classifier has been trained without confirmed negative labels."
The PN baseline implemented here is that conventional-practice REFERENCE
POINT -- a supervised control for comparison against the project's own
PU-learning baselines (Task 4.3+), not a claim that C1 is confirmed
biologically inactive, and not itself a scientifically validated
antioxidant-activity predictor. Every docstring, log record, and run
manifest in this module says so explicitly rather than leaving it
implied.

Heavy (torch) imports are deferred inside functions that need them, so
this module can still be imported from a torch-free context (its own
dataset-construction helpers below need only numpy/pandas) -- the
training loop itself imports torch lazily, mirroring run.py's own
lazy-import discipline for Bucket 4.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import (
    DataLeakageError,
    ExperimentData,
    PoolData,
    assert_no_cross_subset_overlap,
    split_ids_train_validation,
)

PN_POSITIVE_EVIDENCE_TIER = "E1"


class InsufficientDataError(ValueError):
    """Raised when a PN dataset would have zero positives or zero
    negatives in either the training or validation split -- a training
    run on such a split would be meaningless, so this fails loudly before
    any model is even constructed."""


@dataclass(frozen=True)
class PnDataset:
    """Exactly what PN training needs -- C2, C3, and the external control
    are never referenced by this module at all, so they cannot leak into
    a PN run even by accident."""

    train_features: np.ndarray  # (n_train, feature_dim) float32
    train_labels: np.ndarray  # (n_train,) float32, 1.0=E1 positive, 0.0=C1 assumed-negative
    train_peptide_ids: np.ndarray
    validation_features: np.ndarray
    validation_labels: np.ndarray
    validation_peptide_ids: np.ndarray
    class_counts: dict
    e1_train_ids: list[str]
    e1_validation_ids: list[str]
    c1_train_ids: list[str]
    c1_validation_ids: list[str]
    c1_validation_fraction: float
    c1_partition_seed: int


def select_positive_evidence_tier(pool: PoolData, evidence_tier: str = PN_POSITIVE_EVIDENCE_TIER) -> PoolData:
    """Filters an already fold-partitioned positive pool (e.g.
    ``ExperimentData.train_positive``) down to one evidence tier --
    E2/E3 rows are dropped, never relabeled or reweighted. The input
    pool's own train/validation/held-out partition boundary (Task 4.1) is
    untouched: this only removes rows from within whichever partition it
    is given.
    """
    if pool.evidence_tier is None:
        raise ValueError(f"{pool.pool}: no evidence_tier info available to filter by {evidence_tier!r}")
    mask = pool.evidence_tier == evidence_tier
    return PoolData(
        pool=f"{pool.pool}_{evidence_tier}",
        peptide_ids=pool.peptide_ids[mask],
        sequences=pool.sequences[mask],
        features=pool.features[mask],
        evidence_tier=pool.evidence_tier[mask],
    )


def split_c1_train_validation(c1: PoolData, validation_fraction: float, seed: int) -> tuple[PoolData, PoolData]:
    """Deterministic, sequence-disjoint C1 train/validation partition.

    C1's cache rows are already deduplicated to one row per unique
    sequence (Task 3.1/3.4) -- partitioning by ``peptide_id`` is therefore
    equivalent to partitioning by unique sequence; this function still
    asserts that invariant rather than assuming it, and reuses
    ``experiment_data.split_ids_train_validation`` (the identical
    algorithm Task 4.1 uses for the positive-pool validation split) so
    there is exactly one shuffle-split implementation in this project,
    not two.
    """
    ids = c1.peptide_ids.tolist()
    if len(set(ids)) != len(ids):
        raise DataLeakageError(
            f"C1 pool passed to split_c1_train_validation contains duplicate peptide_ids -- "
            "the Task 3.1/3.4 dedup-to-unique-sequence invariant has been violated."
        )
    train_ids, validation_ids = split_ids_train_validation(ids, validation_fraction, seed)

    id_to_row = {pid: i for i, pid in enumerate(ids)}

    def _subset(label: str, subset_ids: list[str]) -> PoolData:
        idx = [id_to_row[pid] for pid in subset_ids]
        return PoolData(
            pool=label,
            peptide_ids=c1.peptide_ids[idx],
            sequences=c1.sequences[idx],
            features=c1.features[idx],
        )

    return _subset("C1_train", train_ids), _subset("C1_validation", validation_ids)


def build_pn_dataset(data: ExperimentData, config: ExperimentConfig) -> PnDataset:
    """Assembles the PN training/validation arrays from an already-built
    ``ExperimentData`` (Task 4.1), for ``config.fold_id``. Positive class
    is E1-only, drawn from ``data.train_positive``/``data.validation_positive``
    (GraphPart's own fold-aware partition, untouched); negative class is
    a fresh C1 train/validation partition, split by this function using
    ``config.validation_fraction``/``config.eval_seed`` -- the SAME
    authoritative fraction and seed Task 4.1 already uses for the
    positive-pool split (no new config field introduced for this).

    Independently re-verifies (does not just trust Task 4.1's own
    ``data.leakage_report``) that none of the four PN subsets overlap
    with each other, with GraphPart's held-out fold, or with C2/C3/the
    external control -- by peptide_id AND by sequence.
    """
    e1_train = select_positive_evidence_tier(data.train_positive)
    e1_validation = select_positive_evidence_tier(data.validation_positive)

    if len(e1_train.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero E1 training positives.")
    if len(e1_validation.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero E1 validation positives.")
    if len(data.c1.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero C1 rows -- nothing to partition.")

    c1_train, c1_validation = split_c1_train_validation(data.c1, config.validation_fraction, config.eval_seed)

    if len(c1_train.peptide_ids) == 0 or len(c1_validation.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero C1 train or validation rows.")

    assert_no_cross_subset_overlap(
        {
            "e1_train": e1_train,
            "e1_validation": e1_validation,
            "c1_train": c1_train,
            "c1_validation": c1_validation,
            "held_out_positive": data.held_out_positive,
            "c2": data.c2,
            "c3_fold_challenges": data.c3_fold_challenges,
            "external_control": data.external_control,
        }
    )

    train_features = np.concatenate([e1_train.features, c1_train.features], axis=0)
    train_labels = np.concatenate(
        [np.ones(len(e1_train.peptide_ids), dtype=np.float32), np.zeros(len(c1_train.peptide_ids), dtype=np.float32)]
    )
    train_peptide_ids = np.concatenate([e1_train.peptide_ids, c1_train.peptide_ids])

    validation_features = np.concatenate([e1_validation.features, c1_validation.features], axis=0)
    validation_labels = np.concatenate(
        [
            np.ones(len(e1_validation.peptide_ids), dtype=np.float32),
            np.zeros(len(c1_validation.peptide_ids), dtype=np.float32),
        ]
    )
    validation_peptide_ids = np.concatenate([e1_validation.peptide_ids, c1_validation.peptide_ids])

    if not np.isfinite(train_features).all() or not np.isfinite(validation_features).all():
        raise ValueError("Non-finite value(s) in PN train/validation features -- refusing to build a dataset.")

    class_counts = {
        "train_positive": int(len(e1_train.peptide_ids)),
        "train_negative": int(len(c1_train.peptide_ids)),
        "validation_positive": int(len(e1_validation.peptide_ids)),
        "validation_negative": int(len(c1_validation.peptide_ids)),
    }

    return PnDataset(
        train_features=train_features,
        train_labels=train_labels,
        train_peptide_ids=train_peptide_ids,
        validation_features=validation_features,
        validation_labels=validation_labels,
        validation_peptide_ids=validation_peptide_ids,
        class_counts=class_counts,
        e1_train_ids=e1_train.peptide_ids.tolist(),
        e1_validation_ids=e1_validation.peptide_ids.tolist(),
        c1_train_ids=c1_train.peptide_ids.tolist(),
        c1_validation_ids=c1_validation.peptide_ids.tolist(),
        c1_validation_fraction=config.validation_fraction,
        c1_partition_seed=config.eval_seed,
    )


def compute_pos_weight(class_counts: dict, use_class_weight: bool) -> float | None:
    """``BCEWithLogitsLoss(pos_weight=...)``, derived from TRAINING-set
    class counts only (never validation/held-out) -- returns ``None`` when
    ``use_class_weight`` is False (ablation support), in which case the
    loss is unweighted.
    """
    if not use_class_weight:
        return None
    n_pos = class_counts["train_positive"]
    n_neg = class_counts["train_negative"]
    if n_pos == 0:
        raise InsufficientDataError("Zero training positives -- cannot compute a class weight.")
    return n_neg / n_pos


def render_loss_curve_svg(
    history: list[dict],
    path: Path,
    train_key: str = "train_bce_loss",
    val_key: str = "val_bce_loss",
    title: str = "PN baseline: train (blue) vs validation (red) BCE loss",
) -> Path:
    """A minimal, dependency-free SVG line chart of train/validation loss
    per epoch -- matplotlib is not an existing project dependency
    (confirmed: not installed, not in requirements.txt) and this project
    has already deliberately avoided adding it for a single chart once
    before (see IMPLEMENTATION_STATUS.md, Task 2.5's decision log); a
    hand-rolled SVG keeps that precedent rather than adding a new
    dependency for this one plot.

    ``train_key``/``val_key``/``title`` are overridable (default to the
    original PN-specific BCE keys/title, so every existing PN caller is
    unaffected) so Task 4.3's nnPU baseline can reuse this exact plotting
    routine for its own ``train_nnpu_risk``/``val_nnpu_risk`` history
    keys instead of a second, duplicated SVG writer.
    """
    width, height, pad = 640, 360, 48
    epochs = [h["epoch"] for h in history]
    train_losses = [h[train_key] for h in history]
    val_losses = [h[val_key] for h in history]
    all_losses = train_losses + val_losses
    min_loss, max_loss = min(all_losses), max(all_losses)
    loss_range = max(max_loss - min_loss, 1e-9)
    min_epoch, max_epoch = min(epochs), max(epochs)
    epoch_range = max(max_epoch - min_epoch, 1)

    def _x(epoch: int) -> float:
        return pad + (epoch - min_epoch) / epoch_range * (width - 2 * pad)

    def _y(loss: float) -> float:
        return height - pad - (loss - min_loss) / loss_range * (height - 2 * pad)

    def _polyline(values: list[float], color: str) -> str:
        points = " ".join(f"{_x(e):.2f},{_y(v):.2f}" for e, v in zip(epochs, values))
        return f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>'

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" stroke="black"/>',
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}" stroke="black"/>',
        _polyline(train_losses, "#1f77b4"),
        _polyline(val_losses, "#d62728"),
        f'<text x="{pad}" y="20" font-size="14">{title}</text>',
        f'<text x="{pad}" y="{height - 10}" font-size="11">epoch</text>',
        f'<text x="4" y="{pad}" font-size="11">loss</text>',
        "</svg>",
    ]
    path = Path(path)
    path.write_text("\n".join(svg), encoding="utf-8", newline="\n")
    return path


def train_pn_baseline(
    config: ExperimentConfig,
    dataset: PnDataset,
    run_dir: Path,
    use_class_weight: bool = True,
    early_stopping_patience: int | None = 10,
    min_improvement: float = 1e-4,
) -> dict:
    """The PN supervised training loop: BCE-with-logits on raw logits
    (sigmoid is never applied before the loss), mini-batch Adam/SGD,
    per-epoch train/validation loss, best-vs-last checkpointing via
    ``run_recorder``, and optional validation-loss-only early stopping.
    No curriculum-stage transition logic (Task 4.6's job).
    """
    import torch

    from plantaox.c2_pu.common.seeding import resolve_device, set_global_seed
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.run_recorder import append_epoch_metrics, save_checkpoint

    seed_context = set_global_seed(config.train_seed)
    device = resolve_device(config.device)

    model = BinaryMlp(MlpArchitecture(input_dim=config.feature_dim, hidden_dims=config.hidden_dims)).to(device)
    if config.optimizer == "adam":
        optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    elif config.optimizer == "sgd":
        optimizer = torch.optim.SGD(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    else:
        raise ValueError(f"Unsupported optimizer {config.optimizer!r}")

    pos_weight_value = compute_pos_weight(dataset.class_counts, use_class_weight)
    pos_weight_tensor = torch.tensor([pos_weight_value], device=device, dtype=torch.float32) if pos_weight_value is not None else None
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight_tensor)

    train_x = torch.from_numpy(dataset.train_features).to(device)
    train_y = torch.from_numpy(dataset.train_labels).to(device).unsqueeze(1)
    val_x = torch.from_numpy(dataset.validation_features).to(device)
    val_y = torch.from_numpy(dataset.validation_labels).to(device).unsqueeze(1)

    if not torch.isfinite(train_x).all() or not torch.isfinite(val_x).all():
        raise RuntimeError("Non-finite input feature(s) detected -- refusing to train.")

    shuffle_rng = np.random.default_rng(config.train_seed)
    n_train = train_x.shape[0]

    best_val_loss = float("inf")
    best_epoch: int | None = None
    epochs_without_improvement = 0
    history: list[dict] = []
    executed_epochs = 0

    start_time = time.time()
    for epoch in range(config.max_epochs):
        model.train()
        indices = np.arange(n_train)
        shuffle_rng.shuffle(indices)
        batch_loss_sum = 0.0
        for start in range(0, n_train, config.batch_size):
            batch_idx = indices[start : start + config.batch_size]
            batch_idx_t = torch.from_numpy(batch_idx).long().to(device)
            batch_x = train_x[batch_idx_t]
            batch_y = train_y[batch_idx_t]

            optimizer.zero_grad()
            logits = model(batch_x)
            if not torch.isfinite(logits).all():
                raise RuntimeError(f"Non-finite training logit(s) at epoch {epoch}.")
            loss = loss_fn(logits, batch_y)
            if not torch.isfinite(loss):
                raise RuntimeError(f"Non-finite training loss at epoch {epoch}: {loss.item()}")
            loss.backward()
            for name, param in model.named_parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():
                    raise RuntimeError(f"Non-finite gradient in {name!r} at epoch {epoch}.")
            optimizer.step()
            batch_loss_sum += loss.item() * len(batch_idx)
        train_loss = batch_loss_sum / n_train

        model.eval()
        with torch.no_grad():
            val_logits = model(val_x)
            if not torch.isfinite(val_logits).all():
                raise RuntimeError(f"Non-finite validation logit(s) at epoch {epoch}.")
            val_loss = loss_fn(val_logits, val_y).item()
        if not np.isfinite(val_loss):
            raise RuntimeError(f"Non-finite validation loss at epoch {epoch}: {val_loss}")

        executed_epochs = epoch + 1
        is_best = val_loss < (best_val_loss - min_improvement)
        if is_best:
            best_val_loss = val_loss
            best_epoch = epoch
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        metrics = {
            "train_bce_loss": train_loss,
            "val_bce_loss": val_loss,
            "learning_rate": config.learning_rate,
            "train_positive_count": dataset.class_counts["train_positive"],
            "train_negative_count": dataset.class_counts["train_negative"],
            "validation_positive_count": dataset.class_counts["validation_positive"],
            "validation_negative_count": dataset.class_counts["validation_negative"],
            "is_best": is_best,
        }
        append_epoch_metrics(run_dir, epoch, metrics)
        history.append({"epoch": epoch, **metrics})

        save_checkpoint(run_dir, model, epoch=epoch, metrics=metrics, is_best=False)
        if is_best:
            save_checkpoint(run_dir, model, epoch=epoch, metrics=metrics, is_best=True)

        if early_stopping_patience is not None and epochs_without_improvement >= early_stopping_patience:
            break

    elapsed_seconds = time.time() - start_time
    curve_path = render_loss_curve_svg(history, Path(run_dir) / "learning_curve.svg")

    return {
        "seed_context": seed_context,
        "device": str(device),
        "executed_epochs": executed_epochs,
        "max_epochs": config.max_epochs,
        "early_stopping_patience": early_stopping_patience,
        "min_improvement": min_improvement,
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss if best_epoch is not None else None,
        "final_train_loss": history[-1]["train_bce_loss"] if history else None,
        "final_val_loss": history[-1]["val_bce_loss"] if history else None,
        "class_counts": dataset.class_counts,
        "pos_weight": pos_weight_value,
        "use_class_weight": use_class_weight,
        "elapsed_seconds": elapsed_seconds,
        "history": history,
        "learning_curve_path": str(curve_path),
    }
