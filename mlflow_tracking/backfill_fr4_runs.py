"""Import the accepted, frozen C2 (PU-AOP) FR4 runs into a local MLflow store.

READ-ONLY with respect to the research project: this script only *reads*
files under data/processed/c2_pu and data/interim/c2_pu, and only *writes*
inside mlflow_tracking/ (the SQLite store and artifact directory). It never
imports plantaox, never retrains, and never touches a frozen artifact.

Only the runs the frozen release actually accepted are imported -- each is
located via the `run_dir` recorded in its accepted summary JSON. The many
other timestamped run directories under data/interim/c2_pu are test-suite
reruns, not experiments, and are deliberately ignored.

Every imported run is tagged `provenance=backfilled_from_frozen_pp1` and keeps
its original start time, so the MLflow UI never presents these as runs that
were tracked live.

Usage (from the repository root):
    mlflow_tracking/.venv/Scripts/python.exe mlflow_tracking/backfill_fr4_runs.py
    mlflow_tracking/.venv/Scripts/python.exe mlflow_tracking/backfill_fr4_runs.py --rebuild
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import shutil
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from mlflow.entities import Metric, Param, RunTag  # noqa: E402
from mlflow.tracking import MlflowClient  # noqa: E402

TRACKING_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRACKING_DIR.parent
PROCESSED = REPO_ROOT / "data" / "processed" / "c2_pu"
INTERIM = REPO_ROOT / "data" / "interim" / "c2_pu"
DB_PATH = TRACKING_DIR / "mlflow.db"
ARTIFACT_ROOT = TRACKING_DIR / "mlartifacts"
TRACKING_URI = f"sqlite:///{DB_PATH.as_posix()}"

EXP_BASELINES = "C2 PU-AOP | SO4 Baseline Comparison"
EXP_PRIOR = "C2 PU-AOP | SO4 nnPU Prior Sensitivity"
EXP_CURRICULUM = "C2 PU-AOP | SO4 Evidence-Weighted Curriculum"

CAVEAT = (
    "Backfilled read-only from the frozen c2_pp1_freeze_v1 release (tag c2-pp1-v1); "
    "not tracked live. Fold 0 only. Scores are uncalibrated model outputs, not "
    "biological probabilities. All five baselines have negative MCC and AUROC < 0.5 "
    "on the assay-supported external-control evaluation. C1/C2/C3 are unlabeled "
    "pools, not confirmed negatives."
)

BASELINE_SUMMARIES = {
    "M1": ("PN", "fr4_pn_baseline_fold0_summary.json"),
    "M2": ("Direct-clamped nnPU", "fr4_nnpu_baseline_fold0_summary.json"),
    "M3": ("Corrective nnPU", "fr4_nnpu_corrective_fold0_summary.json"),
    "M4": ("Two-Step PU", "fr4_two_step_pu_baseline_fold0_summary.json"),
    "M5": ("PU-Bagging", "fr4_pu_bagging_baseline_fold0_summary.json"),
}

# Per-epoch fields worth charting; anything else in the JSONL is bookkeeping.
EPOCH_METRIC_KEYS = (
    "train_bce_loss",
    "val_bce_loss",
    "train_nnpu_risk",
    "val_nnpu_risk",
    "train_optimizer_loss",
    "train_negative_risk_unclamped",
    "val_negative_risk_unclamped",
    "train_corrective_branch_fraction",
    "train_clamped_update_fraction",
)


# --------------------------------------------------------------------------- #
# Read-only helpers
# --------------------------------------------------------------------------- #
def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def local_run_dir(recorded: str) -> Path:
    """Summaries record absolute paths from the producing machine; re-anchor
    on this checkout's data/interim/c2_pu using the trailing components."""
    parts = Path(recorded.replace("\\", "/")).parts
    idx = parts.index("c2_pu")
    return INTERIM.joinpath(*parts[idx + 1 :])


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def run_start_ms(run_dir: Path) -> int:
    """Original start time, parsed from the run directory's UTC stamp
    (e.g. ..._fold0__20261014T223957Z)."""
    stamp = run_dir.name.split("__")[-1].split("_")[0]
    parsed = dt.datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp() * 1000)


def flatten(prefix: str, value, out: dict) -> None:
    if isinstance(value, dict):
        for key, inner in value.items():
            flatten(f"{prefix}.{key}" if prefix else str(key), inner, out)
    elif isinstance(value, list):
        out[prefix] = json.dumps(value)
    elif value is not None:
        out[prefix] = value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# MLflow writing helpers (only ever touch mlflow_tracking/)
# --------------------------------------------------------------------------- #
def get_experiment(client: MlflowClient, name: str, description: str) -> str:
    existing = client.get_experiment_by_name(name)
    if existing:
        return existing.experiment_id
    exp_id = client.create_experiment(name, artifact_location=(ARTIFACT_ROOT / name.replace(" | ", "__").replace(" ", "_")).as_uri())
    client.set_experiment_tag(exp_id, "mlflow.note.content", description)
    client.set_experiment_tag(exp_id, "component", "C2 PU-AOP")
    return exp_id


def already_imported(client: MlflowClient, exp_id: str, key: str) -> bool:
    hits = client.search_runs([exp_id], filter_string=f"tags.backfill_key = '{key}'", max_results=1)
    return bool(hits)


def new_run(
    client: MlflowClient,
    exp_id: str,
    *,
    key: str,
    name: str,
    start_ms: int,
    tags: dict,
    parent_run_id: str | None = None,
):
    base_tags = {
        "backfill_key": key,
        "provenance": "backfilled_from_frozen_pp1",
        "freeze_id": "c2_pp1_freeze_v1",
        "release_tag": "c2-pp1-v1",
        "fold_id": "0",
        "mlflow.note.content": CAVEAT,
    }
    if parent_run_id:
        base_tags["mlflow.parentRunId"] = parent_run_id
    base_tags.update({k: str(v) for k, v in tags.items()})
    return client.create_run(exp_id, start_time=start_ms, tags=base_tags, run_name=name)


def log_params(client: MlflowClient, run_id: str, params: dict) -> None:
    items = [Param(str(k)[:250], str(v)[:6000]) for k, v in params.items() if v is not None]
    for i in range(0, len(items), 100):
        client.log_batch(run_id, params=items[i : i + 100])


def log_metrics(client: MlflowClient, run_id: str, values: dict, timestamp_ms: int, step: int = 0) -> None:
    metrics = []
    for key, value in values.items():
        if isinstance(value, bool) or value is None:
            continue
        try:
            metrics.append(Metric(key, float(value), timestamp_ms, step))
        except (TypeError, ValueError):
            continue
    for i in range(0, len(metrics), 1000):
        client.log_batch(run_id, metrics=metrics[i : i + 1000])


def log_epoch_history(client: MlflowClient, run_id: str, history: list[dict], start_ms: int, step_key: str = "epoch") -> int:
    metrics = []
    for index, row in enumerate(history):
        step = int(row.get(step_key, row.get("global_epoch", index)))
        ts = start_ms + step * 1000
        for key in EPOCH_METRIC_KEYS:
            if key in row and row[key] is not None:
                metrics.append(Metric(key, float(row[key]), ts, step))
        if "is_best" in row:
            metrics.append(Metric("is_best_epoch", 1.0 if row["is_best"] else 0.0, ts, step))
    for i in range(0, len(metrics), 1000):
        client.log_batch(run_id, metrics=metrics[i : i + 1000])
    return len(history)


def log_artifact_if_exists(client: MlflowClient, run_id: str, path: Path, subdir: str | None = None) -> None:
    if path.exists():
        client.log_artifact(run_id, str(path), subdir)


def finish(client: MlflowClient, run_id: str, end_ms: int) -> None:
    client.set_terminated(run_id, status="FINISHED", end_time=end_ms)


# --------------------------------------------------------------------------- #
# Importers
# --------------------------------------------------------------------------- #
def import_baselines(client: MlflowClient) -> int:
    exp_id = get_experiment(
        client,
        EXP_BASELINES,
        "Five accepted FR4/SO4 baselines (PN, direct-clamped nnPU, corrective nnPU, "
        "Two-Step PU, PU-Bagging) evaluated on 124 held-out positives vs 38 "
        "AnOxPePred assay-inactive external controls. " + CAVEAT,
    )
    manifest = read_json(PROCESSED / "C2_PP1_FREEZE_MANIFEST.json")
    accepted = {m["model_id"]: m for m in manifest["accepted_models"]}
    comparison = {row["model_id"]: row for row in read_csv_rows(PROCESSED / "fr4_baseline_comparison_fold0.csv")}
    evaluation = read_json(PROCESSED / "fr4_baseline_evaluation_fold0.json")["models"]

    created = 0
    for model_id, (label, summary_name) in BASELINE_SUMMARIES.items():
        key = f"baseline::{model_id}"
        if already_imported(client, exp_id, key):
            print(f"  skip {key} (already imported)")
            continue

        summary_path = PROCESSED / summary_name
        summary = read_json(summary_path)
        run_dir = local_run_dir(summary["run_dir"])
        start_ms = run_start_ms(run_dir)
        model_meta = accepted[model_id]

        checkpoint_path = REPO_ROOT / model_meta["checkpoint_path"]
        checkpoint_ok = checkpoint_path.exists() and sha256_file(checkpoint_path) == model_meta["checkpoint_sha256"]

        run = new_run(
            client,
            exp_id,
            key=key,
            name=f"{model_id} {label}",
            start_ms=start_ms,
            tags={
                "model_id": model_id,
                "model": label,
                "architecture": model_meta["architecture"],
                "positive_evidence_tiers": model_meta["positive_evidence_tiers"],
                "unlabeled_training_pool": model_meta["unlabeled_training_pool"],
                "original_run_dir": repo_relative(run_dir),
                "checkpoint_sha256": model_meta["checkpoint_sha256"],
                "checkpoint_integrity": "verified" if checkpoint_ok else "MISMATCH_OR_MISSING",
            },
        )
        run_id = run.info.run_id

        params: dict = {}
        config_path = run_dir / "resolved_config.json"
        if config_path.exists():
            config = read_json(config_path)
            for k in ("baseline", "positive_pool_version", "challenge_pool_version", "feature_representation",
                      "validation_fraction", "train_seed", "eval_seed", "hidden_dims", "activation", "optimizer",
                      "learning_rate", "weight_decay", "batch_size", "max_epochs", "feature_dim", "git_revision"):
                if k in config:
                    params[k] = config[k]
        params["positive_prior"] = model_meta.get("positive_prior")
        params["score_transformation"] = model_meta.get("score_transformation")
        for k in ("prior", "beta", "gamma", "nnpu_variant", "hold_out_ratio", "n_estimators"):
            if k in summary:
                params[k] = summary[k]
        log_params(client, run_id, params)

        # Training-side scalars from the accepted summary.
        training = summary.get("training", {})
        train_scalars = {
            f"train.{k}": v
            for k, v in training.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }
        if "estimated_c" in summary:
            train_scalars["train.estimated_c"] = summary["estimated_c"]
        if isinstance(summary.get("oob_metrics"), dict) and summary["oob_metrics"].get("oob_score") is not None:
            train_scalars["train.oob_score"] = summary["oob_metrics"]["oob_score"]

        # Headline external-control evaluation (the accepted Task 4.5 table).
        row = comparison[model_id]
        eval_scalars = {
            f"eval.{k}": row[k]
            for k in ("mcc", "average_precision", "auroc", "precision", "recall", "f1",
                      "balanced_accuracy", "tp", "tn", "fp", "fn", "n_positive", "n_control")
        }

        # Descriptive scoring behaviour on unlabeled pools -- NOT false-positive rates.
        behaviour = {}
        for pool, pool_data in evaluation.get(model_id, {}).get("challenge_behavior", {}).items():
            summary_block = pool_data.get("bounded_score_summary", {})
            for stat in ("fraction_gt_0_5", "mean", "median"):
                if summary_block.get(stat) is not None:
                    behaviour[f"unlabeled_pool_behaviour.{pool}.{stat}"] = summary_block[stat]
        recovery = evaluation.get(model_id, {}).get("positive_recovery", {})
        for tier, block in recovery.get("by_evidence_tier", {}).items():
            if block.get("fraction_gt_0_5") is not None:
                behaviour[f"positive_recovery.{tier}.fraction_gt_0_5"] = block["fraction_gt_0_5"]

        end_ms = start_ms + int(float(training.get("elapsed_seconds", 1)) * 1000)
        log_metrics(client, run_id, {**train_scalars, **eval_scalars, **behaviour}, end_ms)

        epochs = log_epoch_history(client, run_id, read_jsonl(run_dir / "epoch_metrics.jsonl"), start_ms)

        log_artifact_if_exists(client, run_id, summary_path, "accepted_summary")
        log_artifact_if_exists(client, run_id, config_path, "run_config")
        log_artifact_if_exists(client, run_id, run_dir / "learning_curve.svg", "plots")

        finish(client, run_id, end_ms)
        created += 1
        print(f"  imported {key} ({label}): {epochs} epochs, checkpoint {'verified' if checkpoint_ok else 'NOT verified'}")
    return created


def import_prior_sensitivity(client: MlflowClient) -> int:
    exp_id = get_experiment(
        client,
        EXP_PRIOR,
        "Direct-clamped nnPU retrained at assumed class priors pi = 0.05, 0.10 (accepted), 0.20. "
        "Diagnostic only: compares training stability across priors and must not be used to "
        "rank or select a prior by raw risk. " + CAVEAT,
    )
    comparison = read_json(PROCESSED / "fr4_nnpu_prior_sensitivity_comparison.json")
    sources = {
        "0.05": PROCESSED / "fr4_nnpu_prior_sensitivity_pi0p05_fold0_summary.json",
        "0.10": PROCESSED / "fr4_nnpu_baseline_fold0_summary.json",
        "0.20": PROCESSED / "fr4_nnpu_prior_sensitivity_pi0p20_fold0_summary.json",
    }

    created = 0
    for prior, summary_path in sources.items():
        key = f"prior::{prior}"
        if already_imported(client, exp_id, key):
            print(f"  skip {key} (already imported)")
            continue

        summary = read_json(summary_path)
        run_dir = local_run_dir(summary["run_dir"])
        start_ms = run_start_ms(run_dir)
        run = new_run(
            client,
            exp_id,
            key=key,
            name=f"nnPU pi={prior}" + (" (accepted baseline)" if prior == "0.10" else ""),
            start_ms=start_ms,
            tags={
                "prior": prior,
                "is_accepted_prior": prior == "0.10",
                "classification": comparison.get("classification"),
                "original_run_dir": repo_relative(run_dir),
            },
        )
        run_id = run.info.run_id

        log_params(client, run_id, {"prior": prior, "nnpu_variant": summary.get("nnpu_variant")})

        table_row = comparison["comparison_table"].get(prior, {})
        scalars = {f"diagnostic.{k}": v for k, v in table_row.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        clamped = comparison.get("mean_clamped_update_fraction_by_prior", {}).get(prior)
        if isinstance(clamped, (int, float)):
            scalars["diagnostic.mean_clamped_update_fraction"] = clamped
        training = summary.get("training", {})
        end_ms = start_ms + int(float(training.get("elapsed_seconds", 1)) * 1000)
        log_metrics(client, run_id, scalars, end_ms)

        epochs = log_epoch_history(client, run_id, read_jsonl(run_dir / "epoch_metrics.jsonl"), start_ms)
        log_artifact_if_exists(client, run_id, summary_path, "accepted_summary")
        finish(client, run_id, end_ms)
        created += 1
        print(f"  imported {key}: {epochs} epochs")

    # Comparison plots are shared across the three priors: attach once to the
    # accepted-prior run so they are browsable without duplication.
    accepted_runs = client.search_runs([exp_id], filter_string="tags.backfill_key = 'prior::0.10'", max_results=1)
    if accepted_runs and created:
        for plot_path in comparison.get("plots", {}).values():
            log_artifact_if_exists(client, accepted_runs[0].info.run_id, PROCESSED / Path(plot_path.replace("\\", "/")).name, "prior_comparison_plots")
        log_artifact_if_exists(client, accepted_runs[0].info.run_id, PROCESSED / "fr4_nnpu_prior_sensitivity_comparison.json", "prior_comparison_plots")
    return created


def import_curriculum(client: MlflowClient) -> int:
    exp_id = get_experiment(
        client,
        EXP_CURRICULUM,
        "Evidence-weighted corrective-nnPU curriculum C1 -> C2 -> C3 (E1 weight 1.0, E2 weight 0.5, "
        "pi = 0.10). Checkpoint selection at every stage uses a C1-based surrogate validation risk; "
        "this is a single weighted run, not a controlled ablation. " + CAVEAT,
    )
    key = "curriculum::parent"
    if already_imported(client, exp_id, key):
        print(f"  skip {key} (already imported)")
        return 0

    summary_path = PROCESSED / "fr4_curriculum_fold0_summary.json"
    summary = read_json(summary_path)
    run_dir = local_run_dir(summary["run_dir"])
    start_ms = run_start_ms(run_dir)
    config = summary["resolved_config"]
    curriculum_cfg = config["curriculum"]
    matched = {row["training_pool"]: row for row in read_csv_rows(PROCESSED / "fr4_pp1_matched_curriculum_fold0.csv")}

    parent = new_run(
        client,
        exp_id,
        key=key,
        name="Curriculum C1 -> C2 -> C3",
        start_ms=start_ms,
        tags={"original_run_dir": repo_relative(run_dir), "learner": curriculum_cfg["learner"]},
    )
    parent_id = parent.info.run_id
    log_params(
        client,
        parent_id,
        {
            "stage_order": " -> ".join(curriculum_cfg["stage_order"]),
            "evidence_weight_E1": curriculum_cfg["positive_evidence_weights"]["E1"],
            "evidence_weight_E2": curriculum_cfg["positive_evidence_weights"]["E2"],
            "prior": curriculum_cfg["prior"],
            "beta": curriculum_cfg["beta"],
            "gamma": curriculum_cfg["gamma"],
            "plateau_patience": curriculum_cfg["plateau_patience"],
            "optimizer_state_policy": curriculum_cfg["optimizer_state_policy"],
            "validation_policy": curriculum_cfg["validation_policy"],
            "learning_rate": config["learning_rate"],
            "batch_size": config["batch_size"],
            "hidden_dims": config["hidden_dims"],
            "train_seed": config["train_seed"],
            "git_revision": config["git_revision"],
        },
    )

    stage_dirs = {"C1": "stage_1_c1", "C2": "stage_2_c2", "C3": "stage_3_c3"}
    stage_offset_ms = start_ms
    last_end = start_ms
    for stage in curriculum_cfg["stage_order"]:
        stage_dir = run_dir / stage_dirs[stage]
        stage_summary = read_json(stage_dir / "stage_summary.json")
        child = new_run(
            client,
            exp_id,
            key=f"curriculum::{stage}",
            name=f"Stage {stage_summary['stage_index']}: {stage}",
            start_ms=stage_offset_ms,
            parent_run_id=parent_id,
            tags={
                "stage": stage,
                "unlabeled_pool": stage_summary["unlabeled_pool"],
                "best_checkpoint_sha256": stage_summary["best_checkpoint_sha256"],
                "parent_checkpoint_sha256": stage_summary.get("parent_checkpoint_sha256") or "none (first stage)",
                "validation_protocol": stage_summary["validation_protocol"],
            },
        )
        child_id = child.info.run_id
        log_params(
            client,
            child_id,
            {
                "stage": stage,
                "n_train_positive": stage_summary["n_train_positive"],
                "n_train_E1": stage_summary["n_train_E1"],
                "n_train_E2": stage_summary["n_train_E2"],
                "n_train_unlabeled": stage_summary["n_train_unlabeled"],
                "n_validation_positive": stage_summary["n_validation_positive"],
                "n_validation_c1": stage_summary["n_validation_c1"],
            },
        )
        history = read_jsonl(stage_dir / "epoch_metrics.jsonl") or stage_summary.get("history", [])
        log_epoch_history(client, child_id, history, stage_offset_ms, step_key="stage_epoch")

        row = matched.get(stage, {})
        stage_metrics = {
            "train.executed_epochs": stage_summary["executed_epochs"],
            "train.best_epoch": stage_summary["best_epoch"],
            "train.best_val_nnpu_risk": stage_summary["best_val_nnpu_risk"],
            "train.final_val_nnpu_risk": stage_summary["final_val_nnpu_risk"],
            "train.mean_corrective_branch_fraction": stage_summary["mean_corrective_branch_fraction"],
            "train.total_optimizer_updates": stage_summary["total_optimizer_updates"],
        }
        for col in ("positive_recovery", "c1_fraction_gt_0_5", "c2_fraction_gt_0_5", "c3_fraction_gt_0_5",
                    "external_mcc", "external_average_precision", "external_auroc", "external_recall",
                    "external_tp", "external_tn", "external_fp", "external_fn"):
            if col in row:
                stage_metrics[f"eval.{col}"] = row[col]
        stage_end = stage_offset_ms + max(len(history), 1) * 1000
        log_metrics(client, child_id, stage_metrics, stage_end)
        # Mirror stage-level outcomes onto the parent as a step series so the
        # parent run shows the C1 -> C2 -> C3 trajectory on one chart.
        log_metrics(
            client,
            parent_id,
            {f"stage_trajectory.{k.split('.', 1)[1]}": v for k, v in stage_metrics.items() if k.startswith("eval.")},
            stage_end,
            step=int(stage_summary["stage_index"]),
        )
        log_artifact_if_exists(client, child_id, stage_dir / "stage_summary.json", "stage_summary")
        finish(client, child_id, stage_end)
        print(f"  imported curriculum::{stage}: {len(history)} epochs")
        stage_offset_ms = stage_end
        last_end = stage_end

    log_artifact_if_exists(client, parent_id, summary_path, "accepted_summary")
    log_artifact_if_exists(client, parent_id, PROCESSED / "fr4_pp1_matched_curriculum_fold0.csv", "accepted_summary")
    log_artifact_if_exists(client, parent_id, PROCESSED / "fr4_curriculum_score_trajectories.svg", "plots")
    finish(client, parent_id, last_end)
    return 4


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete this script's own MLflow store (mlflow.db + mlartifacts/) and re-import from scratch.",
    )
    args = parser.parse_args()

    if args.rebuild:
        if DB_PATH.exists():
            DB_PATH.unlink()
        if ARTIFACT_ROOT.exists():
            shutil.rmtree(ARTIFACT_ROOT)
        print("Removed existing MLflow store.")

    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    client = MlflowClient(tracking_uri=TRACKING_URI)

    print(f"Tracking store: {TRACKING_URI}")
    print("Baselines:")
    n_base = import_baselines(client)
    print("Prior sensitivity:")
    n_prior = import_prior_sensitivity(client)
    print("Curriculum:")
    n_curr = import_curriculum(client)
    print(f"Done. New runs created: baselines={n_base}, priors={n_prior}, curriculum={n_curr}")
    print("Open the UI with:")
    print(f'  mlflow_tracking/.venv/Scripts/mlflow.exe ui --backend-store-uri "{TRACKING_URI}" --port 5000')


if __name__ == "__main__":
    main()
