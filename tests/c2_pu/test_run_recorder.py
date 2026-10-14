"""Unit tests for run_recorder.py (Bucket 4.1 §E)."""

from __future__ import annotations

import json

import torch
import pytest

from plantaox.c2_pu.models import ArchitectureMismatchError, BinaryMlp, MlpArchitecture
from plantaox.c2_pu.run_recorder import (
    RUN_STATUSES,
    RunContext,
    append_epoch_metrics,
    create_run_dir,
    load_checkpoint,
    read_run_manifest,
    save_checkpoint,
    write_resolved_config,
)


def test_create_run_dir_is_collision_safe(tmp_path):
    dir_a = create_run_dir(tmp_path, "exp1")
    dir_b = create_run_dir(tmp_path, "exp1")
    assert dir_a != dir_b
    assert dir_a.exists() and dir_b.exists()


def test_write_resolved_config_is_immutable_for_a_given_run(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    write_resolved_config(run_dir, {"a": 1})
    write_resolved_config(run_dir, {"a": 1})  # identical content -> no error
    with pytest.raises(ValueError, match="immutable"):
        write_resolved_config(run_dir, {"a": 2})


def test_append_epoch_metrics_writes_one_jsonl_record_per_call(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    append_epoch_metrics(run_dir, epoch=0, metrics={"diagnostic": 1.0})
    append_epoch_metrics(run_dir, epoch=1, metrics={"diagnostic": 2.0})
    lines = (run_dir / "epoch_metrics.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["epoch"] == 0
    assert json.loads(lines[1])["epoch"] == 1


def test_checkpoint_round_trip_restores_identical_parameters(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    model = BinaryMlp(MlpArchitecture(input_dim=495))
    path = save_checkpoint(run_dir, model, epoch=3, metrics={"note": "unit test"}, is_best=True)
    assert path.name == "checkpoint_best.pt"

    reloaded = BinaryMlp(MlpArchitecture(input_dim=495))
    info = load_checkpoint(path, reloaded)
    assert info["epoch"] == 3
    for p1, p2 in zip(model.parameters(), reloaded.parameters()):
        assert torch.equal(p1, p2)


def test_best_and_last_checkpoints_are_explicitly_distinct_files(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    model = BinaryMlp(MlpArchitecture(input_dim=495))
    best_path = save_checkpoint(run_dir, model, epoch=5, metrics={}, is_best=True)
    last_path = save_checkpoint(run_dir, model, epoch=6, metrics={}, is_best=False)
    assert best_path != last_path
    assert best_path.exists() and last_path.exists()


def test_load_checkpoint_rejects_architecture_mismatch(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    model = BinaryMlp(MlpArchitecture(input_dim=495))
    path = save_checkpoint(run_dir, model, epoch=0, metrics={}, is_best=True)
    wrong_shape_model = BinaryMlp(MlpArchitecture(input_dim=15))
    with pytest.raises(ArchitectureMismatchError):
        load_checkpoint(path, wrong_shape_model)


def test_load_checkpoint_missing_file_raises_file_not_found(tmp_path):
    model = BinaryMlp(MlpArchitecture(input_dim=495))
    with pytest.raises(FileNotFoundError):
        load_checkpoint(tmp_path / "does_not_exist.pt", model)


def test_checkpoint_save_is_atomic_no_leftover_tmp_file(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    model = BinaryMlp(MlpArchitecture(input_dim=495))
    save_checkpoint(run_dir, model, epoch=0, metrics={}, is_best=True)
    leftover_tmp_files = list(run_dir.glob("*.tmp"))
    assert leftover_tmp_files == []


def test_run_context_records_completed_status_on_success(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    with RunContext(run_dir):
        pass
    manifest = read_run_manifest(run_dir)
    assert manifest["status"] == "completed"


def test_run_context_records_initialized_then_running_then_completed(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    ctx = RunContext(run_dir)
    assert read_run_manifest(run_dir)["status"] == "initialized"
    with ctx:
        assert read_run_manifest(run_dir)["status"] == "running"
    assert read_run_manifest(run_dir)["status"] == "completed"


def test_run_context_captures_exception_details_on_failure(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    with pytest.raises(RuntimeError):
        with RunContext(run_dir):
            raise RuntimeError("deliberate failure for testing")
    manifest = read_run_manifest(run_dir)
    assert manifest["status"] == "failed"
    assert manifest["exception_type"] == "RuntimeError"
    assert "deliberate failure for testing" in manifest["exception_message"]
    assert "RuntimeError" in manifest["traceback"]


def test_run_context_never_swallows_the_exception(tmp_path):
    run_dir = create_run_dir(tmp_path, "exp1")
    with pytest.raises(ValueError):
        with RunContext(run_dir):
            raise ValueError("should propagate")


def test_all_run_statuses_constant_covers_the_lifecycle():
    assert set(RUN_STATUSES) == {"initialized", "running", "completed", "failed"}
