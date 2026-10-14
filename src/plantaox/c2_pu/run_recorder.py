"""Bucket 4.1 -- reusable run recorder: run dirs, checkpoints, logs,
manifests (Task 4.1 §E).

Deliberately does not generate or log any training score on its own --
callers supply real metrics (or none at all, for an infra-only smoke
test); this module only knows how to record them safely.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
import traceback
from pathlib import Path

import torch

from plantaox.c2_pu.common.io import append_provenance_log
from plantaox.c2_pu.models import BinaryMlp

RUN_MANIFEST_FILENAME = "run_manifest.json"
RESOLVED_CONFIG_FILENAME = "resolved_config.json"
EPOCH_METRICS_FILENAME = "epoch_metrics.jsonl"
CHECKPOINT_LAST_FILENAME = "checkpoint_last.pt"
CHECKPOINT_BEST_FILENAME = "checkpoint_best.pt"

RUN_STATUSES = ("initialized", "running", "completed", "failed")


def create_run_dir(base_dir: Path, experiment_id: str) -> Path:
    """Collision-safe run directory: ``<base_dir>/<experiment_id>__<UTC
    timestamp>[_<n>]``. Never overwrites an existing run."""
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = base_dir / f"{experiment_id}__{timestamp}"
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = base_dir / f"{experiment_id}__{timestamp}_{suffix}"
    candidate.mkdir(parents=True)
    return candidate


def write_resolved_config(run_dir: Path, resolved_config: dict) -> Path:
    """Writes the resolved experiment configuration exactly once per run.
    The config is meant to be IMMUTABLE for the run's lifetime: a second
    call with different content raises rather than silently overwriting
    what earlier epochs/checkpoints were produced under."""
    path = Path(run_dir) / RESOLVED_CONFIG_FILENAME
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != json.loads(json.dumps(resolved_config, default=str)):
            raise ValueError(f"{path} already exists with DIFFERENT content -- resolved config must be immutable per run.")
        return path
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(resolved_config, handle, indent=2, default=str)
    return path


def append_epoch_metrics(run_dir: Path, epoch: int, metrics: dict) -> None:
    """One JSON-lines record per call -- reuses common/io.py's
    append_provenance_log rather than a second JSONL-append implementation."""
    append_provenance_log(Path(run_dir) / EPOCH_METRICS_FILENAME, {"epoch": epoch, **metrics})


def save_checkpoint(
    run_dir: Path, model: BinaryMlp, epoch: int, metrics: dict, is_best: bool, extra: dict | None = None
) -> Path:
    """Atomic save: write to a temp file in the same directory, then
    ``os.replace()`` into place -- never leaves a half-written checkpoint
    on crash/interrupt. ``is_best`` selects which of the two filenames
    (explicit best-vs-last distinction) gets written; both can exist
    simultaneously."""
    run_dir = Path(run_dir)
    payload = {
        "architecture": model.architecture_signature(),
        "state_dict": model.state_dict(),
        "epoch": epoch,
        "metrics": metrics,
        "torch_version": torch.__version__,
        "saved_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "extra": extra or {},
    }
    filename = CHECKPOINT_BEST_FILENAME if is_best else CHECKPOINT_LAST_FILENAME
    final_path = run_dir / filename
    fd, tmp_path = tempfile.mkstemp(dir=run_dir, suffix=".tmp")
    os.close(fd)
    try:
        torch.save(payload, tmp_path)
        os.replace(tmp_path, final_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    return final_path


def load_checkpoint(path: Path, model: BinaryMlp) -> dict:
    """Loads a checkpoint into ``model``, verifying architecture
    compatibility FIRST via ``model.load_compatible_state_dict`` (Task
    4.1 §B) -- raises ``ArchitectureMismatchError`` naming the mismatch
    rather than a cryptic PyTorch shape error, and ``FileNotFoundError``
    if the path doesn't exist. Returns every other field in the
    checkpoint (epoch, metrics, timestamps, ...).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {path}")
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model.load_compatible_state_dict(payload["state_dict"], payload["architecture"])
    return {k: v for k, v in payload.items() if k != "state_dict"}


def read_run_manifest(run_dir: Path) -> dict:
    path = Path(run_dir) / RUN_MANIFEST_FILENAME
    return json.loads(path.read_text(encoding="utf-8"))


class RunContext:
    """Wraps one experiment run's lifecycle: writes ``run_manifest.json``
    with status ``initialized`` (on construction) -> ``running`` (on
    ``with`` entry) -> ``completed`` or ``failed`` (on exit), capturing
    the full exception type/message/traceback on failure. Never swallows
    an exception -- always re-raised after recording.
    """

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.manifest_path = self.run_dir / RUN_MANIFEST_FILENAME
        self._write_manifest("initialized")

    def _write_manifest(self, status: str, **extra) -> None:
        if status not in RUN_STATUSES:
            raise ValueError(f"status must be one of {RUN_STATUSES}, got {status!r}")
        manifest = {"status": status, "updated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(), **extra}
        with open(self.manifest_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, indent=2, default=str)

    def __enter__(self) -> "RunContext":
        self._write_manifest("running")
        return self

    def __exit__(self, exc_type, exc_value, tb) -> bool:
        if exc_type is None:
            self._write_manifest("completed")
        else:
            self._write_manifest(
                "failed",
                exception_type=exc_type.__name__,
                exception_message=str(exc_value),
                traceback="".join(traceback.format_exception(exc_type, exc_value, tb)),
            )
        return False
