"""Bucket 4, Task 4.5: focused fold-0 evaluation of accepted baselines."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from plantaox.c2_pu.common.feature_cache import sha256_of
from plantaox.c2_pu.experiment_data import ExperimentData, PoolData

THRESHOLD = 0.5


@dataclass(frozen=True)
class ScoreOutput:
    raw: np.ndarray
    bounded: np.ndarray
    transformation: str


@dataclass(frozen=True)
class LoadedBaseline:
    model_id: str
    name: str
    predict: Callable[[np.ndarray], ScoreOutput]
    provenance: dict


def score_summary(scores: np.ndarray) -> dict:
    values = np.asarray(scores, dtype=np.float64).reshape(-1)
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError("score_summary requires a non-empty finite score array")
    return {
        "n": int(values.size),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "min": float(values.min()),
        "max": float(values.max()),
        "fraction_gt_0_5": float(np.mean(values > THRESHOLD)),
        "fraction_lt_0_01": float(np.mean(values < 0.01)),
        "fraction_gt_0_99": float(np.mean(values > 0.99)),
    }


def classification_metrics(y_true: np.ndarray, raw_scores: np.ndarray, bounded_scores: np.ndarray) -> dict:
    """Metrics at fixed threshold 0.5; ranking metrics use raw finite scores."""
    from sklearn.metrics import (
        average_precision_score,
        balanced_accuracy_score,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        matthews_corrcoef,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    y = np.asarray(y_true, dtype=np.int64).reshape(-1)
    raw = np.asarray(raw_scores, dtype=np.float64).reshape(-1)
    bounded = np.asarray(bounded_scores, dtype=np.float64).reshape(-1)
    if not (len(y) == len(raw) == len(bounded)) or len(y) == 0:
        raise ValueError("labels and score arrays must be non-empty and equal length")
    if not np.isfinite(raw).all() or not np.isfinite(bounded).all():
        raise ValueError("metric scores must be finite")
    if np.any((bounded < 0) | (bounded > 1)):
        raise ValueError("bounded metric scores must lie in [0,1]")
    if len(np.unique(y)) < 2:
        return {"status": "NOT DEFINED", "n": int(len(y)), "class_counts": {str(int(y[0])): int(len(y))}}
    predicted = (bounded >= THRESHOLD).astype(np.int64)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    return {
        "status": "defined", "n": int(len(y)),
        "class_counts": {"positive": int((y == 1).sum()), "negative": int((y == 0).sum())},
        "threshold": THRESHOLD,
        "mcc": float(matthews_corrcoef(y, predicted)),
        "average_precision": float(average_precision_score(y, raw)),
        "auroc": float(roc_auc_score(y, raw)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predicted)),
        "brier_score_bounded": float(brier_score_loss(y, bounded)),
        "confusion_matrix": {"tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn)},
    }


def _validate_scores(raw: np.ndarray, bounded: np.ndarray, expected_n: int) -> None:
    if raw.shape != (expected_n,) or bounded.shape != (expected_n,):
        raise ValueError(f"prediction shape mismatch: expected {(expected_n,)}, got {raw.shape}/{bounded.shape}")
    if not np.isfinite(raw).all() or not np.isfinite(bounded).all():
        raise ValueError("non-finite model score")
    if np.any((bounded < 0) | (bounded > 1)):
        raise ValueError("bounded model score outside [0,1]")


def load_accepted_baselines(summary_paths: dict[str, Path]) -> list[LoadedBaseline]:
    """Load five accepted best checkpoints and verify each recorded SHA-256."""
    import torch

    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.pu_sklearn_common import load_sklearn_checkpoint
    from plantaox.c2_pu.run_recorder import load_checkpoint

    definitions = (
        ("M1", "PN", "torch", "E1", None),
        ("M2", "Direct-clamped nnPU", "torch", "E1+E2", 0.10),
        ("M3", "Corrective nnPU", "torch", "E1+E2", 0.10),
        ("M4", "Two-Step PU", "two_step", "E1+E2", None),
        ("M5", "PU-Bagging", "bagging", "E1+E2", None),
    )
    loaded: list[LoadedBaseline] = []
    for model_id, name, kind, tiers, prior in definitions:
        summary_path = Path(summary_paths[model_id])
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        run_dir = Path(summary["run_dir"])
        suffix = "pt" if kind == "torch" else "joblib"
        checkpoint = run_dir / f"checkpoint_best.{suffix}"
        actual_hash = sha256_of(checkpoint)
        expected_hash = summary["checkpoint"]["best_path_sha256"]
        if actual_hash != expected_hash:
            raise ValueError(f"{name} checkpoint SHA-256 mismatch: {actual_hash} != {expected_hash}")

        if kind == "torch":
            resolved = json.loads((run_dir / "resolved_config.json").read_text(encoding="utf-8"))
            model = BinaryMlp(MlpArchitecture(input_dim=resolved["feature_dim"], hidden_dims=tuple(resolved["hidden_dims"])))
            load_checkpoint(checkpoint, model)

            def predict(features: np.ndarray, model=model) -> ScoreOutput:
                values = model.predict_proba(torch.from_numpy(features.astype(np.float32))).detach().cpu().numpy().reshape(-1)
                return ScoreOutput(values, values.copy(), "sigmoid(BinaryMlp logits); already bounded")
        else:
            estimator = load_sklearn_checkpoint(checkpoint)["estimator"]
            if kind == "two_step":
                def predict(features: np.ndarray, estimator=estimator) -> ScoreOutput:
                    raw = np.asarray(estimator.predict_proba(features)[:, 1], dtype=np.float64)
                    return ScoreOutput(raw, np.clip(raw, 0.0, 1.0),
                                       "Elkan-Noto corrected raw score retained; clipped to [0,1] only for threshold/Brier metrics")
            else:
                def predict(features: np.ndarray, estimator=estimator) -> ScoreOutput:
                    values = np.asarray(estimator.predict_proba(features)[:, 1], dtype=np.float64)
                    return ScoreOutput(values, values.copy(), "PU-Bagging predict_proba; already bounded")

        provenance = {
            "model_id": model_id, "model": name, "checkpoint_path": str(checkpoint),
            "checkpoint_sha256": actual_hash, "summary_path": str(summary_path),
            "architecture": "BinaryMlp 495->128->64->1" if kind == "torch" else "pulearn + LogisticRegression",
            "positive_evidence_tiers": tiers, "unlabeled_training_pool": "C1" if model_id != "M1" else "C1 treated as assumed negative",
            "fold_id": 0, "feature_representation": "fused (495)", "positive_prior": prior,
            "score_transformation": "raw and bounded recorded separately" if kind == "two_step" else "none beyond model inference",
        }
        loaded.append(LoadedBaseline(model_id, name, predict, provenance))
    return loaded


def _tier_summaries(pool: PoolData, scores: np.ndarray) -> dict:
    result = {}
    if pool.evidence_tier is not None:
        for tier in sorted(set(pool.evidence_tier.tolist())):
            result[tier] = score_summary(scores[pool.evidence_tier == tier])
    return result


def evaluate_models(
    data: ExperimentData,
    models: list[LoadedBaseline],
    conflict_control_ids: set[str],
) -> dict:
    pools = {
        "held_out_positive": data.held_out_positive,
        "C1": data.c1, "C2": data.c2, "C3_fold0": data.c3_fold_challenges,
        "external_control": data.external_control,
    }
    expected = {"held_out_positive": 124, "C1": 3788, "C2": 2000, "C3_fold0": 2000, "external_control": 38}
    for key, count in expected.items():
        if len(pools[key].peptide_ids) != count:
            raise ValueError(f"{key}: expected {count} rows, found {len(pools[key].peptide_ids)}")

    all_results = {}
    comparison_rows = []
    proxy_rows = []
    for loaded in models:
        predictions = {}
        for pool_name, pool in pools.items():
            output = loaded.predict(pool.features)
            _validate_scores(output.raw, output.bounded, len(pool.peptide_ids))
            predictions[pool_name] = output

        held = predictions["held_out_positive"]
        ext = predictions["external_control"]
        y_primary = np.concatenate([np.ones(len(held.raw), dtype=np.int64), np.zeros(len(ext.raw), dtype=np.int64)])
        primary = classification_metrics(y_primary, np.concatenate([held.raw, ext.raw]),
                                         np.concatenate([held.bounded, ext.bounded]))
        ext_ids = data.external_control.peptide_ids
        keep = np.asarray([pid not in conflict_control_ids for pid in ext_ids])
        y_sensitivity = np.concatenate([np.ones(len(held.raw), dtype=np.int64), np.zeros(int(keep.sum()), dtype=np.int64)])
        sensitivity = classification_metrics(y_sensitivity, np.concatenate([held.raw, ext.raw[keep]]),
                                             np.concatenate([held.bounded, ext.bounded[keep]]))

        challenge = {}
        for pool_name in ("C1", "C2", "C3_fold0"):
            output = predictions[pool_name]
            summary = score_summary(output.bounded)
            proxy_y = np.concatenate([np.ones(len(held.raw), dtype=np.int64), np.zeros(len(output.raw), dtype=np.int64)])
            proxy = classification_metrics(proxy_y, np.concatenate([held.raw, output.raw]),
                                           np.concatenate([held.bounded, output.bounded]))
            challenge[pool_name] = {"score_summary": summary, "assumed_negative_proxy_metrics": proxy}
            proxy_rows.append({"model_id": loaded.model_id, "model": loaded.name, "challenge_pool": pool_name,
                               **summary, "proxy_mcc": proxy["mcc"], "proxy_average_precision": proxy["average_precision"],
                               "proxy_auroc": proxy["auroc"],
                               "label_assumption": "challenge pool provisionally assigned 0; NOT confirmed biological negatives"})

        all_results[loaded.model_id] = {
            "model": loaded.name,
            "positive_recovery": {"overall": score_summary(held.bounded),
                                  "by_evidence_tier": _tier_summaries(data.held_out_positive, held.bounded)},
            "challenge_behavior": challenge,
            "external_assay_supported": primary,
            "external_assay_supported_excluding_two_disputed_controls": sensitivity,
            "score_metadata": {"transformation": held.transformation,
                               "raw_out_of_bounds_fraction_all_pools": float(np.mean(np.concatenate(
                                   [v.raw for v in predictions.values()]) > 1.0))},
        }
        comparison_rows.append({"model_id": loaded.model_id, "model": loaded.name,
                                **{k: primary[k] for k in ("mcc", "average_precision", "auroc", "precision", "recall", "f1", "balanced_accuracy")},
                                **primary["confusion_matrix"], "n_positive": 124, "n_control": 38,
                                "evaluation": "held-out positives vs external assay-inactive controls"})
    return {"models": all_results, "comparison_rows": comparison_rows, "proxy_rows": proxy_rows,
            "dataset_counts": expected, "threshold": THRESHOLD,
            "leakage_report": data.leakage_report,
            "disputed_external_control_ids": sorted(conflict_control_ids)}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("cannot write an empty comparison CSV")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render_bar_svg(path: Path, title: str, rows: list[dict], value_key: str, y_min: float = 0.0) -> None:
    width, height, margin = 820, 420, 70
    values = [float(r[value_key]) for r in rows]
    high = max(max(values), 0.01)
    low = min(y_min, min(values))
    span = high - low or 1.0
    plot_h = height - 2 * margin
    bar_w = (width - 2 * margin) / len(rows) * 0.6
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{width/2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">{title}</text>',
             f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#333"/>']
    slot = (width - 2 * margin) / len(rows)
    zero_y = margin + (high - 0.0) / span * plot_h
    parts.append(f'<line x1="{margin}" y1="{zero_y:.1f}" x2="{width-margin}" y2="{zero_y:.1f}" stroke="#999"/>')
    for i, (row, value) in enumerate(zip(rows, values)):
        x = margin + i * slot + (slot - bar_w) / 2
        y_value = margin + (high - value) / span * plot_h
        y = min(y_value, zero_y)
        h = max(abs(zero_y - y_value), 1)
        parts += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#3b82f6"/>',
                  f'<text x="{x+bar_w/2:.1f}" y="{height-margin+18}" text-anchor="middle" font-family="sans-serif" font-size="11">{row["model_id"]}</text>',
                  f'<text x="{x+bar_w/2:.1f}" y="{y-6:.1f}" text-anchor="middle" font-family="sans-serif" font-size="11">{value:.3f}</text>']
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8", newline="\n")


def render_challenge_svg(path: Path, proxy_rows: list[dict]) -> None:
    # Compact grouped textual/bar summary; bounded mean scores only.
    width, height, margin = 920, 470, 70
    models = list(dict.fromkeys(r["model_id"] for r in proxy_rows))
    pools = ("C1", "C2", "C3_fold0")
    colors = {"C1": "#2563eb", "C2": "#f59e0b", "C3_fold0": "#10b981"}
    lookup = {(r["model_id"], r["challenge_pool"]): r["mean"] for r in proxy_rows}
    slot = (width - 2 * margin) / len(models)
    bar_w = slot / 4
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">', '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{width/2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">Mean bounded score on unlabeled challenge pools</text>']
    for tick in range(6):
        value = tick / 5
        y = height - margin - value * (height - 2 * margin)
        parts.append(f'<line x1="{margin}" y1="{y:.1f}" x2="{width-margin}" y2="{y:.1f}" stroke="#ddd"/>')
        parts.append(f'<text x="{margin-8}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="10">{value:.1f}</text>')
    for i, model_id in enumerate(models):
        for j, pool in enumerate(pools):
            value = lookup[(model_id, pool)]
            x = margin + i * slot + (j + 0.5) * bar_w
            h = value * (height - 2 * margin)
            parts.append(f'<rect x="{x:.1f}" y="{height-margin-h:.1f}" width="{bar_w-3:.1f}" height="{h:.1f}" fill="{colors[pool]}"/>')
        parts.append(f'<text x="{margin+(i+0.5)*slot:.1f}" y="{height-margin+18}" text-anchor="middle" font-family="sans-serif" font-size="11">{model_id}</text>')
    for j, pool in enumerate(pools):
        parts.append(f'<rect x="{margin+j*150}" y="{height-25}" width="12" height="12" fill="{colors[pool]}"/>')
        parts.append(f'<text x="{margin+18+j*150}" y="{height-15}" font-family="sans-serif" font-size="11">{pool}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8", newline="\n")
