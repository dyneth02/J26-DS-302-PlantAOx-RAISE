"""Bucket 4, Task 4.3 -- plain non-negative PU (nnPU) baseline.

Builds entirely on Task 4.1's shared infrastructure (``models.BinaryMlp``,
``experiment_data.build_experiment_data``, ``common/seeding``,
``run_recorder``) and reuses Task 4.2's deterministic C1 train/validation
partition (``pn_baseline.split_c1_train_validation``) and its
``InsufficientDataError``/SVG-plotting routine directly -- no second MLP,
no second checkpointing system, no second C1-splitter, no second loss
curve renderer.

**Scientific framing, never to be weakened (same invariant as PN):** C1
is this project's assumed-negative, PU-UNLABELED pool -- peptides with no
reported antioxidant activity, never experimentally confirmed inactive.
Unlike PN, this module never treats C1 as a confirmed-negative label at
all: it is passed to the non-negative PU risk estimator
(``nnpu_risk.compute_nnpu_risk``) as the unlabeled group U, with its true
composition modeled only through the assumed prior ``pi`` (Section 8).

**What differs from PN (Task 4.2), recorded explicitly so later
comparisons do not attribute every observed change to the loss function
alone):**

1. **Positive-evidence population.** PN used E1-ONLY positives (331
   train / 48 validation at fold 0). This module uses the pooled
   **E1 + E2** labeled-positive population (604 train / 106 validation at
   fold 0, per Task 4.2's own documented fold-0 counts) -- E2 is
   provisional benchmark-annotated evidence, not uniformly assay-
   confirmed (Section 6.2), and is included here per Task 4.3's explicit
   "agreed E1/E2 labeled-positive population" instruction. Each row's own
   evidence tier is preserved in ``NnPuDataset.train_positive_tiers``/
   ``validation_positive_tiers`` so E1 vs. E2 provenance stays separately
   auditable, never pooled into an anonymous "positive" count.
2. **How C1 is used.** PN labels C1 rows ``0.0`` (a conventional binary
   negative label fed to ``BCEWithLogitsLoss``). This module never
   assigns C1 a binary label at all -- it is the unlabeled group U of the
   nnPU risk estimator, whose true positive/negative composition is
   modeled only through ``pi`` (Section 8), never asserted as "confirmed
   negative."
3. **Training objective.** PN minimizes ordinary BCE-with-logits (an E1-
   vs-C1-as-negative classification loss). This module minimizes the
   non-negative PU risk (``nnpu_risk.compute_nnpu_risk``, the
   **direct-clamped** variant -- see that module's docstring for why this
   variant and not the original paper's beta/gamma corrective procedure
   was chosen as Task 4.3's explicit initial baseline).
4. **Loss comparability.** nnPU risk and PN's BCE loss are NOT the same
   quantity and must never be compared numerically as if a lower nnPU
   number means "a better classifier than PN" (Section 16.F) -- they are
   different estimators of different targets under different label
   assumptions.

Heavy (torch) imports are deferred inside functions that need them,
mirroring ``pn_baseline.py``'s own lazy-import discipline, so this module
can still be imported from a torch-free context (its dataset-construction
helpers below need only numpy/pandas) and ``run.py``'s module-level
import graph stays torch-free.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import (
    ExperimentData,
    PoolData,
    assert_no_cross_subset_overlap,
)
from plantaox.c2_pu.nnpu_risk import NNPU_VARIANT_DIRECT_CLAMPED, validate_prior
from plantaox.c2_pu.pn_baseline import (
    InsufficientDataError,
    render_loss_curve_svg,
    split_c1_train_validation,
)

NNPU_POSITIVE_EVIDENCE_TIERS = ("E1", "E2")

# Section 8.2: no pre-specified positive-class prior or estimation method
# was found in the proposal, PU_AOP_RESEARCH_CONTEXT.md,
# PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md, or the
# IMPLEMENTATION_STATUS.md decision log as of Task 4.3 (verified by
# direct inspection before writing this module, not assumed). Per
# Section 8.2's explicit fallback instruction, pi=0.10 is used as a
# clearly-labeled PROVISIONAL engineering/sensitivity-analysis anchor --
# NOT a literature-established or independently measured biological
# prevalence of true antioxidant peptides within C1 (Section 8.4: C1 was
# deliberately constructed from a different source distribution than the
# positive AOP data, so no sampling-ratio-derived number would be a valid
# substitute either -- see Section 8.1).
DEFAULT_PRIOR = 0.10
PRIOR_SENSITIVITY_GRID = (0.05, 0.10, 0.20)
PRIOR_PROVENANCE_NOTE = (
    "No positive-class prior (pi) or estimation method was found pre-specified in "
    "docs/PU_AOP_RESEARCH_CONTEXT.md, docs/PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md, the "
    "proposal's FR3/FR4 requirement table, or the IMPLEMENTATION_STATUS.md experiment-decision log "
    "(inspected directly before implementing Task 4.3). pi=0.10 is therefore a clearly-labeled "
    "PROVISIONAL modeling/sensitivity-analysis anchor, not a literature-established or "
    "independently measured biological prevalence of true antioxidant peptides within C1. C1 was "
    "deliberately constructed from a different source distribution than the positive AOP pool "
    "(UniProtKB reviewed decoys vs. Multi-AOP/AnOxPePred benchmark positives) -- the naive sampling "
    "ratio n_labeled_positive / (n_labeled_positive + n_C1) is NOT used as pi, per Section 8.1's "
    "explicit instruction that this ratio is not automatically a valid biological prior. Sensitivity "
    "support (pi in {0.05, 0.10, 0.20}) is provided via PRIOR_SENSITIVITY_GRID; full sensitivity "
    "TRAINING across the grid is deferred (Section 8.3) -- only pi=0.10's fold-0 run is the Task 4.3 "
    "genuine baseline result."
)


def select_e1_e2_positive_evidence(pool: PoolData) -> PoolData:
    """Filters an already fold-partitioned positive pool (e.g.
    ``ExperimentData.train_positive``) down to the E1+E2 evidence tiers
    ONLY -- any other tier (e.g. a future E3 row) is excluded, never
    relabeled, reweighted, or silently included by an "everything that
    isn't E1" catch-all. Mirrors ``pn_baseline.select_positive_evidence_tier``
    but keeps both evidence tiers (Section 6.1) instead of E1-only, and
    preserves each row's own tier in the returned ``PoolData.evidence_tier``
    so E1-vs-E2 provenance remains separately auditable (Section 6.2).
    """
    if pool.evidence_tier is None:
        raise ValueError(f"{pool.pool}: no evidence_tier info available to filter by {NNPU_POSITIVE_EVIDENCE_TIERS}")
    mask = np.isin(pool.evidence_tier, NNPU_POSITIVE_EVIDENCE_TIERS)
    return PoolData(
        pool=f"{pool.pool}_E1E2",
        peptide_ids=pool.peptide_ids[mask],
        sequences=pool.sequences[mask],
        features=pool.features[mask],
        evidence_tier=pool.evidence_tier[mask],
    )


@dataclass(frozen=True)
class NnPuDataset:
    """Exactly what nnPU training needs -- C2, C3, and the external
    control are never referenced by this module at all (structurally
    absent, same discipline as ``PnDataset``), so they cannot leak into
    an nnPU run even by accident. C1 rows carry NO binary label field
    anywhere in this dataclass -- they are the unlabeled group U, never a
    labeled negative.
    """

    train_positive_features: np.ndarray  # (n_p_train, feature_dim) float32, E1+E2
    train_positive_ids: np.ndarray
    train_positive_tiers: np.ndarray  # "E1"/"E2" per row, preserved for auditability
    validation_positive_features: np.ndarray
    validation_positive_ids: np.ndarray
    validation_positive_tiers: np.ndarray
    train_unlabeled_features: np.ndarray  # (n_u_train, feature_dim) float32, C1 train
    train_unlabeled_ids: np.ndarray
    validation_unlabeled_features: np.ndarray
    validation_unlabeled_ids: np.ndarray
    e1_train_count: int
    e2_train_count: int
    e1_validation_count: int
    e2_validation_count: int
    c1_validation_fraction: float
    c1_partition_seed: int
    prior: float


def build_nnpu_dataset(data: ExperimentData, config: ExperimentConfig, prior: float = DEFAULT_PRIOR) -> NnPuDataset:
    """Assembles the nnPU train/validation arrays from an already-built
    ``ExperimentData`` (Task 4.1), for ``config.fold_id``. Positive group
    is E1+E2 (Section 6.1), drawn from ``data.train_positive``/
    ``data.validation_positive`` (GraphPart's own fold-aware partition,
    untouched); unlabeled group is C1, partitioned via
    ``pn_baseline.split_c1_train_validation`` -- the IDENTICAL
    deterministic C1 split Task 4.2 uses (same
    ``config.validation_fraction``/``config.eval_seed``), reused rather
    than re-implemented (Section 7).

    Independently re-verifies (does not just trust Task 4.1's own
    ``data.leakage_report``) that none of the four nnPU subsets overlap
    with each other, with GraphPart's held-out fold, or with C2/C3/the
    external control -- by peptide_id AND by sequence (Section 7's
    required leakage checks).
    """
    prior = validate_prior(prior)

    positive_train = select_e1_e2_positive_evidence(data.train_positive)
    positive_validation = select_e1_e2_positive_evidence(data.validation_positive)

    if len(positive_train.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero E1/E2 training positives.")
    if len(positive_validation.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero E1/E2 validation positives.")
    if len(data.c1.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero C1 rows -- nothing to partition as unlabeled data.")

    c1_train, c1_validation = split_c1_train_validation(data.c1, config.validation_fraction, config.eval_seed)

    if len(c1_train.peptide_ids) == 0 or len(c1_validation.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero C1 train or validation rows.")

    assert_no_cross_subset_overlap(
        {
            "e1e2_positive_train": positive_train,
            "e1e2_positive_validation": positive_validation,
            "c1_unlabeled_train": c1_train,
            "c1_unlabeled_validation": c1_validation,
            "held_out_positive": data.held_out_positive,
            "c2": data.c2,
            "c3_fold_challenges": data.c3_fold_challenges,
            "external_control": data.external_control,
        }
    )

    for name, pool in (
        ("train_positive", positive_train),
        ("validation_positive", positive_validation),
        ("c1_train", c1_train),
        ("c1_validation", c1_validation),
    ):
        if not np.isfinite(pool.features).all():
            raise ValueError(f"Non-finite value(s) in nnPU {name} features -- refusing to build a dataset.")

    train_tier_counts = Counter(positive_train.evidence_tier.tolist())
    validation_tier_counts = Counter(positive_validation.evidence_tier.tolist())

    return NnPuDataset(
        train_positive_features=positive_train.features,
        train_positive_ids=positive_train.peptide_ids,
        train_positive_tiers=positive_train.evidence_tier,
        validation_positive_features=positive_validation.features,
        validation_positive_ids=positive_validation.peptide_ids,
        validation_positive_tiers=positive_validation.evidence_tier,
        train_unlabeled_features=c1_train.features,
        train_unlabeled_ids=c1_train.peptide_ids,
        validation_unlabeled_features=c1_validation.features,
        validation_unlabeled_ids=c1_validation.peptide_ids,
        e1_train_count=int(train_tier_counts.get("E1", 0)),
        e2_train_count=int(train_tier_counts.get("E2", 0)),
        e1_validation_count=int(validation_tier_counts.get("E1", 0)),
        e2_validation_count=int(validation_tier_counts.get("E2", 0)),
        c1_validation_fraction=config.validation_fraction,
        c1_partition_seed=config.eval_seed,
        prior=prior,
    )


class _CyclingIndexSampler:
    """Deterministic infinite cycle over ``range(n)`` -- reshuffles (via
    the SAME seeded ``numpy.random.Generator`` passed in, consumed in a
    fixed, call-order-determined sequence, so same-seed reruns are
    bit-identical) every time it wraps.

    Used for the SMALLER group (E1+E2 training positives, ~604 rows at
    fold 0) so every larger-group (C1 unlabeled, ~3,220 rows) mini-batch
    step still gets a full-size, independently-shuffled positive
    mini-batch -- Task 4.3 Section 10.1's "each optimizer update requires
    a positive batch and an unlabeled batch, independently sampled" and
    "document whether ... full positive passes with cycling unlabeled
    batches, or another explicitly justified paired-batch design"
    requirements. The design here is the SYMMETRIC case: a full pass over
    the LARGER unlabeled pool defines one epoch, and the smaller positive
    pool cycles (reshuffling on wraparound) to supply a same-size batch
    for every unlabeled mini-batch step.
    """

    def __init__(self, n: int, rng: np.random.Generator):
        if n <= 0:
            raise ValueError("_CyclingIndexSampler: n must be positive.")
        self._n = n
        self._rng = rng
        self._indices = np.array([], dtype=np.int64)
        self._pos = 0

    def _refill(self) -> None:
        self._indices = np.arange(self._n)
        self._rng.shuffle(self._indices)
        self._pos = 0

    def next_batch(self, batch_size: int) -> np.ndarray:
        if batch_size <= 0:
            raise ValueError(f"_CyclingIndexSampler.next_batch: batch_size must be positive, got {batch_size}")
        collected: list[int] = []
        while len(collected) < batch_size:
            if self._pos >= len(self._indices):
                self._refill()
            take = min(batch_size - len(collected), len(self._indices) - self._pos)
            collected.extend(self._indices[self._pos : self._pos + take].tolist())
            self._pos += take
        return np.array(collected, dtype=np.int64)


def train_nnpu_baseline(
    config: ExperimentConfig,
    dataset: NnPuDataset,
    run_dir: Path,
    early_stopping_patience: int | None = 10,
    min_improvement: float = 1e-4,
) -> dict:
    """The nnPU training loop: paired positive/unlabeled mini-batches
    (``_CyclingIndexSampler``, Section 10.1), the non-negative PU risk
    estimator (``nnpu_risk.compute_nnpu_risk``, direct-clamped variant),
    mini-batch Adam/SGD, per-epoch train/validation risk + EVERY risk
    component required by Section 10.3, best-vs-last checkpointing via
    ``run_recorder`` (byte-identical filenames/behavior to PN), and
    optional early stopping that monitors validation nnPU risk ONLY
    (never the held-out GraphPart fold or C2/C3 -- Section 11).

    Validation nnPU risk is computed once per epoch over the FULL
    validation positive + validation C1 sets (no mini-batching needed at
    this scale) and is explicitly a surrogate: "validation nnPU surrogate
    risk under assumed pi and the C1 sampling model" -- not an
    independently measured biological classification error (Section 11).
    """
    import torch

    from plantaox.c2_pu.common.seeding import resolve_device, set_global_seed
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.nnpu_risk import compute_nnpu_risk
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

    train_pos_x = torch.from_numpy(dataset.train_positive_features).to(device)
    train_unlabeled_x = torch.from_numpy(dataset.train_unlabeled_features).to(device)
    val_pos_x = torch.from_numpy(dataset.validation_positive_features).to(device)
    val_unlabeled_x = torch.from_numpy(dataset.validation_unlabeled_features).to(device)

    for name, tensor in (
        ("train_positive", train_pos_x),
        ("train_unlabeled", train_unlabeled_x),
        ("validation_positive", val_pos_x),
        ("validation_unlabeled", val_unlabeled_x),
    ):
        if not torch.isfinite(tensor).all():
            raise RuntimeError(f"Non-finite input feature(s) detected in {name} -- refusing to train.")

    n_unlabeled_train = train_unlabeled_x.shape[0]
    n_positive_train = train_pos_x.shape[0]

    unlabeled_shuffle_rng = np.random.default_rng(config.train_seed)
    # Independent RNG stream (distinct seed) so the positive-cycling
    # sequence is not coupled to the unlabeled shuffle's own draws --
    # still fully determined by config.train_seed, so same-seed reruns
    # remain bit-identical.
    positive_cycle_rng = np.random.default_rng(config.train_seed + 1_000_003)
    positive_sampler = _CyclingIndexSampler(n_positive_train, positive_cycle_rng)

    best_val_risk = float("inf")
    best_epoch: int | None = None
    epochs_without_improvement = 0
    history: list[dict] = []
    executed_epochs = 0
    total_optimizer_updates = 0

    start_time = time.time()
    for epoch in range(config.max_epochs):
        model.train()
        unlabeled_indices = np.arange(n_unlabeled_train)
        unlabeled_shuffle_rng.shuffle(unlabeled_indices)

        sums = {
            "loss": 0.0,
            "positive_term": 0.0,
            "positive_as_negative": 0.0,
            "unlabeled_as_negative": 0.0,
            "negative_unclamped": 0.0,
            "negative_contribution": 0.0,
        }
        epoch_clamped_updates = 0
        epoch_updates = 0

        for start in range(0, n_unlabeled_train, config.batch_size):
            unlabeled_batch_idx = unlabeled_indices[start : start + config.batch_size]
            unlabeled_batch_idx_t = torch.from_numpy(unlabeled_batch_idx).long().to(device)
            unlabeled_batch_x = train_unlabeled_x[unlabeled_batch_idx_t]

            positive_batch_idx = positive_sampler.next_batch(len(unlabeled_batch_idx))
            positive_batch_idx_t = torch.from_numpy(positive_batch_idx).long().to(device)
            positive_batch_x = train_pos_x[positive_batch_idx_t]

            optimizer.zero_grad()
            positive_logits = model(positive_batch_x)
            unlabeled_logits = model(unlabeled_batch_x)
            if not torch.isfinite(positive_logits).all() or not torch.isfinite(unlabeled_logits).all():
                raise RuntimeError(f"Non-finite training logit(s) at epoch {epoch}.")

            risk = compute_nnpu_risk(positive_logits, unlabeled_logits, prior)
            if not torch.isfinite(risk.loss):
                raise RuntimeError(f"Non-finite training nnPU risk at epoch {epoch}: {risk.loss.item()}")

            risk.loss.backward()
            for name, param in model.named_parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():
                    raise RuntimeError(f"Non-finite gradient in {name!r} at epoch {epoch}.")
            optimizer.step()

            batch_n = len(unlabeled_batch_idx)
            sums["loss"] += float(risk.loss.item()) * batch_n
            sums["positive_term"] += risk.positive_risk_contribution * batch_n
            sums["positive_as_negative"] += risk.positive_as_negative_risk * batch_n
            sums["unlabeled_as_negative"] += risk.unlabeled_as_negative_risk * batch_n
            sums["negative_unclamped"] += risk.negative_risk_unclamped * batch_n
            sums["negative_contribution"] += risk.negative_risk_contribution * batch_n
            epoch_clamped_updates += int(risk.is_clamped)
            epoch_updates += 1
            total_optimizer_updates += 1

        # Epoch-level training metrics: a per-batch-size-weighted average
        # across this epoch's mini-batches (weighted by the UNLABELED
        # batch size, which defines each step) -- an approximation of a
        # full-pool recomputation, not a second exact forward pass over
        # the whole training set; identical convention to
        # pn_baseline.train_pn_baseline's own epoch-loss averaging.
        train_risk = sums["loss"] / n_unlabeled_train
        train_positive_term = sums["positive_term"] / n_unlabeled_train
        train_positive_as_negative = sums["positive_as_negative"] / n_unlabeled_train
        train_unlabeled_as_negative = sums["unlabeled_as_negative"] / n_unlabeled_train
        train_negative_unclamped = sums["negative_unclamped"] / n_unlabeled_train
        train_negative_contribution = sums["negative_contribution"] / n_unlabeled_train
        train_clamped_fraction = epoch_clamped_updates / epoch_updates if epoch_updates else 0.0

        model.eval()
        with torch.no_grad():
            val_positive_logits = model(val_pos_x)
            val_unlabeled_logits = model(val_unlabeled_x)
            if not torch.isfinite(val_positive_logits).all() or not torch.isfinite(val_unlabeled_logits).all():
                raise RuntimeError(f"Non-finite validation logit(s) at epoch {epoch}.")
            val_risk = compute_nnpu_risk(val_positive_logits, val_unlabeled_logits, prior)
        val_risk_value = float(val_risk.loss.item())
        if not np.isfinite(val_risk_value):
            raise RuntimeError(f"Non-finite validation nnPU risk at epoch {epoch}: {val_risk_value}")

        executed_epochs = epoch + 1
        is_best = val_risk_value < (best_val_risk - min_improvement)
        if is_best:
            best_val_risk = val_risk_value
            best_epoch = epoch
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        metrics = {
            "train_nnpu_risk": train_risk,
            "train_positive_risk_contribution": train_positive_term,
            "train_positive_as_negative_risk": train_positive_as_negative,
            "train_unlabeled_as_negative_risk": train_unlabeled_as_negative,
            "train_negative_risk_unclamped": train_negative_unclamped,
            "train_negative_risk_contribution": train_negative_contribution,
            "train_clamped_update_fraction": train_clamped_fraction,
            "val_nnpu_risk": val_risk_value,
            "val_positive_risk_contribution": val_risk.positive_risk_contribution,
            "val_positive_as_negative_risk": val_risk.positive_as_negative_risk,
            "val_unlabeled_as_negative_risk": val_risk.unlabeled_as_negative_risk,
            "val_negative_risk_unclamped": val_risk.negative_risk_unclamped,
            "val_negative_risk_contribution": val_risk.negative_risk_contribution,
            "val_is_clamped": val_risk.is_clamped,
            "learning_rate": config.learning_rate,
            "prior": prior,
            "n_e1e2_positive_train": n_positive_train,
            "n_c1_unlabeled_train": n_unlabeled_train,
            "n_optimizer_updates_this_epoch": epoch_updates,
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

    # Section 10.4: monitor and DOCUMENT (never silently hide) diverging
    # risk, persistent zero-clamped negative risk, and saturated
    # predictions -- these are reportable modeling observations, not
    # hard failures like the NaN/Inf checks above, so they do not raise.
    clamped_fractions = [h["train_clamped_update_fraction"] for h in history]
    tail = clamped_fractions[-min(5, len(clamped_fractions)):] if clamped_fractions else []
    with torch.no_grad():
        final_val_proba = model.predict_proba(torch.cat([val_pos_x, val_unlabeled_x], dim=0))
    stability_diagnostics = {
        "persistent_negative_risk_clamping_last_5_epochs": bool(tail) and all(f >= 0.999 for f in tail),
        "mean_train_clamped_fraction_last_5_epochs": float(np.mean(tail)) if tail else None,
        "validation_prediction_saturation": {
            "fraction_near_zero": float((final_val_proba < 0.01).float().mean().item()),
            "fraction_near_one": float((final_val_proba > 0.99).float().mean().item()),
        },
        "diverging_risk_detected": bool(
            len(history) >= 2 and history[0]["train_nnpu_risk"] > 0 and history[-1]["train_nnpu_risk"] > history[0]["train_nnpu_risk"] * 10
        ),
    }

    curve_path = render_loss_curve_svg(
        history,
        Path(run_dir) / "learning_curve.svg",
        train_key="train_nnpu_risk",
        val_key="val_nnpu_risk",
        title="nnPU baseline: train (blue) vs validation (red) non-negative PU risk",
    )

    return {
        "seed_context": seed_context,
        "device": str(device),
        "executed_epochs": executed_epochs,
        "max_epochs": config.max_epochs,
        "early_stopping_patience": early_stopping_patience,
        "min_improvement": min_improvement,
        "best_epoch": best_epoch,
        "best_val_nnpu_risk": best_val_risk if best_epoch is not None else None,
        "final_train_nnpu_risk": history[-1]["train_nnpu_risk"] if history else None,
        "final_val_nnpu_risk": history[-1]["val_nnpu_risk"] if history else None,
        "prior": prior,
        "nnpu_variant": NNPU_VARIANT_DIRECT_CLAMPED,
        "e1_train_count": dataset.e1_train_count,
        "e2_train_count": dataset.e2_train_count,
        "e1_validation_count": dataset.e1_validation_count,
        "e2_validation_count": dataset.e2_validation_count,
        "n_c1_unlabeled_train": n_unlabeled_train,
        "n_c1_unlabeled_validation": int(dataset.validation_unlabeled_features.shape[0]),
        "total_optimizer_updates": total_optimizer_updates,
        "elapsed_seconds": elapsed_seconds,
        "stability_diagnostics": stability_diagnostics,
        "history": history,
        "learning_curve_path": str(curve_path),
    }
