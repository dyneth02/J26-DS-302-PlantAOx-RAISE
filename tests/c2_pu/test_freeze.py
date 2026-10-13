"""Tests for curation.freeze (Bucket 1.7 dataset freeze + integrity check)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plantaox.c2_pu.curation.freeze import freeze_baseline, sha256_of, verify_frozen_baseline


@pytest.fixture
def source_files(tmp_path: Path) -> dict[str, Path]:
    a = tmp_path / "a.csv"
    a.write_text("peptide_id,sequence\nAOP-1,AAAK\n", encoding="utf-8")
    b = tmp_path / "b.json"
    b.write_text('{"n": 1}', encoding="utf-8")
    return {"frozen_a.csv": a, "frozen_b.json": b}


def test_freeze_baseline_copies_files_and_writes_manifest(tmp_path, source_files):
    freeze_dir = tmp_path / "frozen" / "pp1_baseline_v1"
    manifest_path = freeze_baseline(
        "pp1_baseline_v1",
        freeze_dir,
        source_files,
        {"tool_versions": {"cd-hit": "4.8.1"}, "counts": {"n_final": 834}},
    )

    assert manifest_path == freeze_dir / "MANIFEST.json"
    assert (freeze_dir / "frozen_a.csv").read_text(encoding="utf-8") == source_files["frozen_a.csv"].read_text(
        encoding="utf-8"
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["version_id"] == "pp1_baseline_v1"
    assert manifest["tool_versions"] == {"cd-hit": "4.8.1"}
    assert manifest["counts"] == {"n_final": 834}
    assert manifest["file_checksums"]["frozen_a.csv"] == sha256_of(freeze_dir / "frozen_a.csv")
    assert "created_at" in manifest


def test_freeze_baseline_raises_on_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        freeze_baseline(
            "v1", tmp_path / "frozen", {"x.csv": tmp_path / "does_not_exist.csv"}, {}
        )


def test_verify_frozen_baseline_detects_no_tampering(tmp_path, source_files):
    freeze_dir = tmp_path / "frozen" / "pp1_baseline_v1"
    freeze_baseline("pp1_baseline_v1", freeze_dir, source_files, {})
    results = verify_frozen_baseline(freeze_dir)
    assert results == {"frozen_a.csv": True, "frozen_b.json": True}


def test_verify_frozen_baseline_detects_tampering(tmp_path, source_files):
    freeze_dir = tmp_path / "frozen" / "pp1_baseline_v1"
    freeze_baseline("pp1_baseline_v1", freeze_dir, source_files, {})

    (freeze_dir / "frozen_a.csv").write_text("TAMPERED", encoding="utf-8")

    results = verify_frozen_baseline(freeze_dir)
    assert results["frozen_a.csv"] is False
    assert results["frozen_b.json"] is True


def test_verify_frozen_baseline_detects_missing_file(tmp_path, source_files):
    freeze_dir = tmp_path / "frozen" / "pp1_baseline_v1"
    freeze_baseline("pp1_baseline_v1", freeze_dir, source_files, {})

    (freeze_dir / "frozen_b.json").unlink()

    results = verify_frozen_baseline(freeze_dir)
    assert results["frozen_b.json"] is False
