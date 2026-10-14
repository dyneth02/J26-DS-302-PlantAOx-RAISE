"""Bucket 4, Task 4.3 POST-ACCEPTANCE DIAGNOSTIC -- positive-prior (pi)
sensitivity and negative-risk clamping investigation.

**This module is diagnostic-only.** It does NOT replace, modify, or
re-implement the accepted Task 4.3 estimator (``nnpu_risk.py``) or
training loop (``nnpu_baseline.py::train_nnpu_baseline``) -- both are
imported and reused UNCHANGED. What this module adds is purely
additional INSTRUMENTATION the accepted training loop does not collect:

1. Real PER-UPDATE (per-mini-batch) values of the unclamped negative
   risk ``R_n = R_u^- - pi*R_p^-``, not only the accepted loop's
   batch-size-weighted EPOCH aggregate -- so min/max/percentiles across
   actual optimizer updates can be reported (Section 5 of the Task 4.3
   post-acceptance diagnostic brief), distinct from the epoch-level
   aggregate and from the full-validation-set R_n.
2. Best-checkpoint prediction-distribution diagnostics, broken out by
   E1/E2/C1 and train/validation (Section 6).

``train_nnpu_with_diagnostics`` below deliberately mirrors
``nnpu_baseline.train_nnpu_baseline``'s training loop EXACTLY (same
optimizer, same ``_CyclingIndexSampler`` RNG streams, same batch
construction, same ``compute_nnpu_risk`` call) -- it is not a rewritten
or "improved" training loop, only the original loop with extra
bookkeeping appended after each already-existing step. A regression test
(``tests/c2_pu/test_nnpu_prior_diagnostics.py``) confirms that, run at
the SAME prior (pi=0.10) with the SAME seeds, this function reproduces
the accepted loop's own per-epoch aggregate history exactly -- i.e. the
added instrumentation changes nothing about what is actually trained.

Never writes to, imports from, or depends on the accepted pi=0.10 run's
own output files (``data/processed/c2_pu/fr4_nnpu_baseline_fold0_*``) --
those remain the historical, immutable reference. All new runs this
module performs go to a separate run-directory tree and separate
committed-summary filenames (``run.py``'s
``FR4_NNPU_PRIOR_SENSITIVITY_*`` constants), so a pi=0.10 sensitivity
replicate run through this module can never collide with or overwrite
the accepted baseline.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.nnpu_baseline import NnPuDataset, _CyclingIndexSampler
from plantaox.c2_pu.nnpu_risk import NNPU_VARIANT_DIRECT_CLAMPED, validate_prior
from plantaox.c2_pu.pn_baseline import render_loss_curve_svg

# ---------------------------------------------------------------------------
# Pure-math diagnostic helpers (unit-tested directly, no torch/model needed)
# ---------------------------------------------------------------------------


def clamped_fraction(is_clamped_flags: list[bool]) -> float:
    """Fraction of per-update ``is_clamped`` flags that are True. Returns
    0.0 for an empty list rather than raising/NaN-ing, matching
    ``train_nnpu_baseline``'s own ``if epoch_updates else 0.0`` guard."""
    if not is_clamped_flags:
        return 0.0
    return float(sum(1 for f in is_clamped_flags if f) / len(is_clamped_flags))


def percentile_summary(values: list[float], percentiles: tuple[float, ...] = (5.0, 50.0, 95.0)) -> dict:
    """Min/max/mean plus the requested percentiles of a real list of
    per-update values. Raises ``ValueError`` on an empty list -- a
    percentile of nothing is undefined, and silently returning ``None``
    for every field would be easy to misread as "all zero"."""
    if not values:
        raise ValueError("percentile_summary: values must be non-empty.")
    arr = np.asarray(values, dtype=np.float64)
    result = {
        "n": int(arr.size),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "mean": float(arr.mean()),
    }
    for p in percentiles:
        result[f"p{int(p) if float(p).is_integer() else p}"] = float(np.percentile(arr, p))
    return result


def epoch_level_risk_aggregation(per_update_values: list[float], per_update_batch_sizes: list[int]) -> float:
    """The SAME batch-size-weighted epoch aggregate
    ``train_nnpu_baseline`` itself computes (``sums[...] / n_total``) --
    re-derived here from genuine per-update values so the diagnostic's
    own epoch aggregate can be cross-checked against the accepted loop's
    aggregate for an identical-prior rerun (see the regression test)."""
    if not per_update_values:
        raise ValueError("epoch_level_risk_aggregation: no per-update values given.")
    if len(per_update_values) != len(per_update_batch_sizes):
        raise ValueError("per_update_values and per_update_batch_sizes must be the same length.")
    total_n = sum(per_update_batch_sizes)
    if total_n <= 0:
        raise ValueError("epoch_level_risk_aggregation: total batch size must be positive.")
    weighted_sum = sum(v * n for v, n in zip(per_update_values, per_update_batch_sizes))
    return weighted_sum / total_n


def prediction_saturation_summary(proba: np.ndarray) -> dict:
    """Descriptive stats for one group's ``predict_proba`` output
    (Section 6): count/min/max/mean/median/std/percentiles plus the three
    named saturation fractions. ``proba`` must be a finite, 1-D (or
    squeezable) array in [0, 1] -- raises rather than silently producing
    NaN summary stats for a malformed input."""
    arr = np.asarray(proba, dtype=np.float64).reshape(-1)
    if arr.size == 0:
        raise ValueError("prediction_saturation_summary: proba must be non-empty.")
    if not np.isfinite(arr).all():
        raise ValueError("prediction_saturation_summary: proba contains non-finite value(s).")
    if (arr < 0).any() or (arr > 1).any():
        raise ValueError("prediction_saturation_summary: proba must be bounded in [0, 1].")
    return {
        "n": int(arr.size),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": float(arr.std()),
        "p5": float(np.percentile(arr, 5)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
        "p95": float(np.percentile(arr, 95)),
        "fraction_lt_0_01": float((arr < 0.01).mean()),
        "fraction_gt_0_99": float((arr > 0.99).mean()),
        "fraction_gt_0_5": float((arr > 0.5).mean()),
    }


# ---------------------------------------------------------------------------
# Diagnostic training loop -- mirrors train_nnpu_baseline exactly, adds
# per-update bookkeeping only.
# ---------------------------------------------------------------------------


def train_nnpu_with_diagnostics(
    config: ExperimentConfig,
    dataset: NnPuDataset,
    run_dir: Path,
    early_stopping_patience: int | None = 10,
    min_improvement: float = 1e-4,
) -> dict:
    """Diagnostic-instrumented re-run of the accepted nnPU training loop.

    Every mathematical step (optimizer, batch construction, risk
    computation) is IDENTICAL to ``nnpu_baseline.train_nnpu_baseline`` --
    this function imports and calls the exact same
    ``nnpu_risk.compute_nnpu_risk`` and the exact same
    ``nnpu_baseline._CyclingIndexSampler`` with the exact same RNG seed
    streams, so a same-seed, same-prior rerun through this function
    reproduces the accepted loop's own per-epoch aggregates exactly (see
    the regression test). The only addition is capturing each mini-batch
    update's ``negative_risk_unclamped``/``is_clamped`` into a real list
    per epoch, from which min/max/percentiles/clamped-fraction are
    computed -- genuine per-update statistics, not inferred from the
    epoch aggregate alone.
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
    positive_cycle_rng = np.random.default_rng(config.train_seed + 1_000_003)
    positive_sampler = _CyclingIndexSampler(n_positive_train, positive_cycle_rng)

    best_val_risk = float("inf")
    best_epoch: int | None = None
    epochs_without_improvement = 0
    history: list[dict] = []
    diagnostic_history: list[dict] = []
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
        per_update_negative_unclamped: list[float] = []
        per_update_is_clamped: list[bool] = []
        per_update_batch_sizes: list[int] = []

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

            # --- diagnostic-only bookkeeping, no effect on training ---
            per_update_negative_unclamped.append(risk.negative_risk_unclamped)
            per_update_is_clamped.append(risk.is_clamped)
            per_update_batch_sizes.append(batch_n)

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

        # Real per-update diagnostics for this epoch (Section 5): distinct
        # from (a) the epoch-level aggregate above and (b) the
        # full-validation-set R_n computed once per epoch over the WHOLE
        # validation set -- all three are labeled separately, never
        # conflated (Section 5's "important diagnostic distinction").
        update_summary = percentile_summary(per_update_negative_unclamped)
        reaggregated_train_negative_unclamped = epoch_level_risk_aggregation(
            per_update_negative_unclamped, per_update_batch_sizes
        )
        diagnostic_record = {
            "epoch": epoch,
            "n_updates": epoch_updates,
            "n_clamped_updates": epoch_clamped_updates,
            "clamped_update_fraction": clamped_fraction(per_update_is_clamped),
            "per_update_negative_risk_unclamped": update_summary,
            "epoch_aggregate_negative_risk_unclamped_recomputed": reaggregated_train_negative_unclamped,
            "epoch_aggregate_is_negative": bool(reaggregated_train_negative_unclamped < 0.0),
            "full_validation_negative_risk_unclamped": val_risk.negative_risk_unclamped,
            "full_validation_is_clamped": val_risk.is_clamped,
        }
        diagnostic_history.append(diagnostic_record)

        save_checkpoint(run_dir, model, epoch=epoch, metrics=metrics, is_best=False)
        if is_best:
            save_checkpoint(run_dir, model, epoch=epoch, metrics=metrics, is_best=True)

        if early_stopping_patience is not None and epochs_without_improvement >= early_stopping_patience:
            break

    elapsed_seconds = time.time() - start_time

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

    # Additional diagnostic-only stability summary (Section 5/11): distinct
    # from the accepted loop's own stability_diagnostics block above
    # (kept byte-identical in shape/naming for direct comparability).
    epoch_aggregate_negative_risk_values = [d["epoch_aggregate_negative_risk_unclamped_recomputed"] for d in diagnostic_history]
    full_validation_negative_risk_values = [d["full_validation_negative_risk_unclamped"] for d in diagnostic_history]
    prior_sensitivity_stability = {
        "fraction_epochs_with_negative_epoch_aggregate_train_risk": (
            float(np.mean([v < 0.0 for v in epoch_aggregate_negative_risk_values]))
            if epoch_aggregate_negative_risk_values
            else None
        ),
        "fraction_epochs_with_negative_full_validation_risk": (
            float(np.mean([v < 0.0 for v in full_validation_negative_risk_values]))
            if full_validation_negative_risk_values
            else None
        ),
        "mean_per_update_clamped_fraction_all_epochs": (
            float(np.mean([d["clamped_update_fraction"] for d in diagnostic_history])) if diagnostic_history else None
        ),
        "mean_per_update_clamped_fraction_last_5_epochs": (
            float(np.mean([d["clamped_update_fraction"] for d in diagnostic_history[-min(5, len(diagnostic_history)):]]))
            if diagnostic_history
            else None
        ),
        "r_n_never_negative_for_any_epoch": bool(
            all(v >= 0.0 for v in epoch_aggregate_negative_risk_values) if epoch_aggregate_negative_risk_values else False
        ),
    }

    curve_path = render_loss_curve_svg(
        history,
        Path(run_dir) / "learning_curve.svg",
        train_key="train_nnpu_risk",
        val_key="val_nnpu_risk",
        title=f"nnPU prior-sensitivity diagnostic (pi={prior}): train (blue) vs validation (red) risk",
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
        "prior_sensitivity_stability": prior_sensitivity_stability,
        "history": history,
        "diagnostic_history": diagnostic_history,
        "learning_curve_path": str(curve_path),
    }


# ---------------------------------------------------------------------------
# Best-checkpoint prediction-distribution diagnostics (Section 6)
# ---------------------------------------------------------------------------


def compute_group_score_distributions(model, dataset: NnPuDataset) -> dict:
    """``predict_proba()`` on the best checkpoint's reloaded model, broken
    out into the six groups Section 6 requires: training-side E1/E2/C1 and
    validation-side E1/E2/C1. Uses ``dataset``'s own tier arrays
    (``train_positive_tiers``/``validation_positive_tiers``) to split E1
    from E2 -- never re-derives tiers from a separate source. C1 has no
    tier split (it is the unlabeled group, not labeled-positive evidence).
    """
    import torch

    def _group_proba(features: np.ndarray) -> np.ndarray:
        if features.shape[0] == 0:
            raise ValueError("compute_group_score_distributions: an empty feature group was passed in.")
        x = torch.from_numpy(features)
        return model.predict_proba(x).detach().cpu().numpy().reshape(-1)

    train_tiers = dataset.train_positive_tiers
    val_tiers = dataset.validation_positive_tiers

    groups = {
        "train_e1": dataset.train_positive_features[train_tiers == "E1"],
        "train_e2": dataset.train_positive_features[train_tiers == "E2"],
        "train_c1": dataset.train_unlabeled_features,
        "val_e1": dataset.validation_positive_features[val_tiers == "E1"],
        "val_e2": dataset.validation_positive_features[val_tiers == "E2"],
        "val_c1": dataset.validation_unlabeled_features,
    }

    result = {}
    for name, feats in groups.items():
        if feats.shape[0] == 0:
            result[name] = {"n": 0, "note": "empty group -- NOT MEASURED"}
            continue
        proba = _group_proba(feats.astype(np.float32))
        result[name] = prediction_saturation_summary(proba)
    return result
