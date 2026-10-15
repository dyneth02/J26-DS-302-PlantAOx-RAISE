"""Bucket 4.1 acceptance tests: the one-command shared-infrastructure
smoke test against the real local Tasks 3.1-3.4 artifacts.

Gated to skip cleanly when those artifacts aren't present locally.
Explicitly verifies this is an INFRASTRUCTURE check, never presented or
usable as a trained PN/PU baseline result.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from plantaox.c2_pu.run import (
    FR3_DEMO_OUTPUT_PATH,
    FR3_DESCRIPTOR_TABLE_PATH,
    FR3_EMBEDDINGS_MANIFEST_PATH,
    FR3_FEATURE_CACHE_MANIFEST_PATH,
    FR3_FUSION_SCALERS_PATH,
    FR3_RECORD_MAP_PATH,
    FR2_FROZEN_DIR,
    FROZEN_DIR,
    run_fr4_infra_smoke_test,
)

REQUIRED_INPUTS = [FR3_FEATURE_CACHE_MANIFEST_PATH, FR3_FUSION_SCALERS_PATH, FR3_RECORD_MAP_PATH]
pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in REQUIRED_INPUTS),
    reason="Tasks 3.1-3.4 outputs not present locally.",
)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def pre_run_hashes():
    hashes = {
        "feature_cache_manifest": _sha256(FR3_FEATURE_CACHE_MANIFEST_PATH),
        "fusion_scalers": _sha256(FR3_FUSION_SCALERS_PATH),
        "record_map": _sha256(FR3_RECORD_MAP_PATH),
    }
    if FR3_DESCRIPTOR_TABLE_PATH.exists():
        hashes["descriptor_table"] = _sha256(FR3_DESCRIPTOR_TABLE_PATH)
    if FR3_EMBEDDINGS_MANIFEST_PATH.exists():
        hashes["embeddings_manifest"] = _sha256(FR3_EMBEDDINGS_MANIFEST_PATH)
    if FR3_DEMO_OUTPUT_PATH.exists():
        hashes["demo_output"] = _sha256(FR3_DEMO_OUTPUT_PATH)
    return hashes


@pytest.fixture(scope="module")
def summary(pre_run_hashes):
    return run_fr4_infra_smoke_test()


def test_all_tasks_3_1_through_3_5_outputs_are_untouched(summary, pre_run_hashes):
    for name, path in [
        ("feature_cache_manifest", FR3_FEATURE_CACHE_MANIFEST_PATH),
        ("fusion_scalers", FR3_FUSION_SCALERS_PATH),
        ("record_map", FR3_RECORD_MAP_PATH),
        ("descriptor_table", FR3_DESCRIPTOR_TABLE_PATH),
        ("embeddings_manifest", FR3_EMBEDDINGS_MANIFEST_PATH),
        ("demo_output", FR3_DEMO_OUTPUT_PATH),
    ]:
        if name in pre_run_hashes:
            assert _sha256(path) == pre_run_hashes[name], f"{name} changed after running the Bucket 4.1 smoke test"


def test_frozen_baselines_are_untouched(summary):
    assert FROZEN_DIR.exists() and FR2_FROZEN_DIR.exists()
    assert not (FROZEN_DIR / "run_manifest.json").exists()
    assert not (FR2_FROZEN_DIR / "run_manifest.json").exists()


def test_smoke_test_raises_a_clear_error_when_prerequisites_are_missing(tmp_path, monkeypatch):
    import plantaox.c2_pu.run as run_module

    bogus_path = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(run_module, "FR3_FEATURE_CACHE_MANIFEST_PATH", bogus_path)
    with pytest.raises(FileNotFoundError, match="Tasks 3.1-3.4"):
        run_fr4_infra_smoke_test()


def test_data_pool_sizes_match_the_documented_fold_0_split(summary):
    assert summary["data_pool_sizes"]["held_out_positive"] == 124
    assert summary["data_pool_sizes"]["c1"] == 3788
    assert summary["data_pool_sizes"]["c2"] == 2000
    assert summary["data_pool_sizes"]["c3_fold_challenges"] == 2000
    assert summary["data_pool_sizes"]["external_control"] == 38
    train_plus_val = summary["data_pool_sizes"]["train_positive"] + summary["data_pool_sizes"]["validation_positive"]
    assert train_plus_val == 710  # fold 0's total training-side positives


def test_leakage_report_found_nothing(summary):
    assert summary["leakage_report"]["overlap_found"] is False


def test_forward_pass_is_well_formed(summary):
    assert summary["forward_pass"]["logits_finite"] is True
    assert summary["forward_pass"]["proba_bounded"] is True


def test_checkpoint_round_trip_succeeded(summary):
    assert summary["checkpoint_round_trip_ok"] is True
    assert summary["checkpoint_epoch"] == 0


def test_run_dir_contains_the_full_expected_artifact_set(summary):
    run_dir = Path(summary["run_dir"])
    assert (run_dir / "run_manifest.json").exists()
    assert (run_dir / "resolved_config.json").exists()
    assert (run_dir / "epoch_metrics.jsonl").exists()
    assert (run_dir / "checkpoint_best.pt").exists()
    assert (run_dir / "checkpoint_last.pt").exists()

    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"

    resolved_config = json.loads((run_dir / "resolved_config.json").read_text(encoding="utf-8"))
    assert "source_artifact_checksums" in resolved_config
    assert "seed_context" in resolved_config
    assert resolved_config["experiment_id"] == "fr4_infra_smoke_test"


def test_summary_is_explicitly_not_presented_as_a_trained_baseline(summary):
    assert "INFRASTRUCTURE SMOKE TEST ONLY" in summary["note"]
    assert "not a trained PN/PU baseline" in summary["note"]
    # No fabricated performance metric keys anywhere in the summary.
    forbidden_keys = {"accuracy", "mcc", "auprc", "auroc", "f1", "precision", "recall", "loss", "rnis"}
    flat_keys = set(summary.keys()) | set(summary.get("forward_pass", {}).keys()) | set(summary.get("data_pool_sizes", {}).keys())
    assert flat_keys.isdisjoint(forbidden_keys)


def test_rerunning_the_smoke_test_is_reproducible_in_its_substantive_content(summary):
    second = run_fr4_infra_smoke_test()
    assert second["data_pool_sizes"] == summary["data_pool_sizes"]
    assert second["leakage_report"] == summary["leakage_report"]
    assert second["forward_pass"]["logits_finite"] is True


def test_run_recorder_does_not_pollute_prior_run_directories(summary):
    # Every call to run_fr4_infra_smoke_test() must produce its OWN
    # collision-safe run_dir -- never silently overwrite a previous run.
    second_summary = run_fr4_infra_smoke_test()
    assert second_summary["run_dir"] != summary["run_dir"]
