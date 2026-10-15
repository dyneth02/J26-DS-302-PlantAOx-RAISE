from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from plantaox.c2_pu.pp1_freeze import (
    ESSENTIAL_IGNORED_COUNT,
    RELEASE_ID,
    _preservation_records,
    create_preservation_package,
    sha256_file,
    verify_release,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json"


def test_release_manifest_and_inventory_are_portable_and_consistent():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["release"]["id"] == RELEASE_ID
    assert manifest["release"]["decision"] == "FROZEN — READY WITH LIMITATIONS"
    assert manifest["source_control"]["tag_status"] == "annotated_tag_targets_containing_release_commit"
    assert manifest["preservation"]["status"] == "PASS"
    assert manifest["preservation"]["artifact_count_verified"] == ESSENTIAL_IGNORED_COUNT
    inventory = ROOT / manifest["artifact_inventory"]["path"]
    assert sha256_file(inventory) == manifest["artifact_inventory"]["sha256"]
    with inventory.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == manifest["artifact_inventory"]["record_count"]
    assert all(not Path(row["path"]).is_absolute() for row in rows)
    assert all(row["available_locally"] == "true" for row in rows)


def test_read_only_release_verifier_loads_cache_and_accepted_checkpoints():
    result = verify_release(ROOT, MANIFEST)
    assert result["status"] == "PASS"
    assert result["inventory_missing"] == 0
    assert sorted(result["fr3_feature_caches"]) == ["0", "1", "2", "3", "4"]
    assert result["fold0_cache"]["shape"] == [9356, 495]
    assert result["fr3_embedding_cache"]["total_embeddings"] == 9356
    assert result["c3_contract"] == {"fold0_selected": 2000, "union_in_cache": 2325}
    assert result["external_control_overlap_with_positive_partitions"] == 0
    assert all(item["finite_and_bounded"] for item in result["checkpoint_inference"].values())


def test_preservation_scope_is_exactly_the_manifest_bound_essential_ignored_set():
    _, records = _preservation_records(ROOT, MANIFEST)
    assert len(records) == ESSENTIAL_IGNORED_COUNT
    assert len({row["path"] for row in records}) == ESSENTIAL_IGNORED_COUNT
    assert sum(int(row["size_bytes"]) for row in records) == 39_103_768
    assert all(row["git_disposition"] == "ignored" for row in records)
    assert all(row["retention"] == "essential_to_retain_as_bytes" for row in records)


def test_preservation_package_rejects_a_destination_inside_the_repository():
    with pytest.raises(ValueError, match="outside the repository"):
        create_preservation_package(ROOT, MANIFEST, ROOT / "data")
