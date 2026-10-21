from __future__ import annotations

import hashlib
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.schemas.c2_pu import ArtifactStatusResponse, TrackedSourceReport
from backend.app.services.c2_pu.artifacts import load_artifact_inventory, load_freeze_manifest

# Curated, human-meaningful subset of the 170-file inventory -- the "evidence
# trail" a reviewer actually wants to see, not a full repo-relative file dump.
# Each (label, category, repo-relative path, expected_sha256) is checked
# against this checkout's actual bytes on every request; expected_sha256 is
# None where the frozen manifest does not record a top-level hash for that
# file, in which case we can only report presence, not drift.
_CURATED_REPORTS: list[tuple[str, str, str, str | None]] = [
    (
        "PP1 Freeze Manifest",
        "Release Manifest",
        "data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json",
        None,
    ),
    (
        "Freeze Report",
        "Release Documentation",
        "src/plantaox/c2_pu/docs/C2_PP1_FREEZE_REPORT.md",
        "4bde29224d6b8731bdd1c04030327fe3dcf69021eec780a2bbb7f3a456d25484",
    ),
    (
        "Handover Document",
        "Release Documentation",
        "src/plantaox/c2_pu/docs/C2_PP1_HANDOVER.md",
        "a31fe1892ea76b4d70259e7f8538a0f97a13b83b1b7a6c8f1c39321f2c92892a",
    ),
    (
        "Artifact Inventory",
        "Release Manifest",
        "data/processed/c2_pu/C2_PP1_ARTIFACT_INVENTORY.csv",
        "8df86f5865452d5453a7e4adee322a058918ea7999dbff932e4d88b322288ed2",
    ),
    (
        "SO1 Frozen Positive-Pool Manifest",
        "SO1 - Data Curation",
        "data/processed/c2_pu/frozen/pp1_baseline_v1/MANIFEST.json",
        "88f14bb9ba99209a5482a08c2f82baa86434a4af1808f2e373e109efd74c27f2",
    ),
    (
        "SO2 Frozen Challenge-Pool Manifest",
        "SO2 - Challenge Pools",
        "data/processed/c2_pu/frozen/pp2_baseline_v1/MANIFEST.json",
        "dbd8755a69b6f29655c03f5dfa6af5d22b72de32c0708b98c944e6541744e2b4",
    ),
    (
        "SO3 Feature Cache Manifest",
        "SO3 - Feature Engineering",
        "data/processed/c2_pu/fr3_feature_cache_manifest.json",
        "81c87075eec8643a3643a3b726268e35569a1a1f00b15f457d87e1ef3268d97a",
    ),
    (
        "SO4 Baseline Evaluation Report",
        "SO4 - Model Evaluation",
        "data/processed/c2_pu/fr4_baseline_evaluation_fold0.json",
        None,
    ),
    (
        "SO4 Curriculum Summary",
        "SO4 - Model Evaluation",
        "data/processed/c2_pu/fr4_curriculum_fold0_summary.json",
        "cc1e0833df9a85f67aa0a2f46aa5d789d0e40470b67f5cf9a56cb804958c4ddf",
    ),
    (
        "External Control Diagnostic",
        "SO4 - Model Evaluation",
        "data/processed/c2_pu/fr4_external_control_diagnostic.json",
        None,
    ),
]


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tracked_source_reports() -> list[TrackedSourceReport]:
    repo_root = get_settings().repo_root
    reports: list[TrackedSourceReport] = []
    for label, category, rel_path, expected_sha256 in _CURATED_REPORTS:
        full_path = repo_root / rel_path
        if not full_path.exists():
            reports.append(
                TrackedSourceReport(
                    label=label, category=category, path=rel_path, sha256=None, status="missing"
                )
            )
            continue

        actual_sha256 = _sha256_of(full_path)
        if expected_sha256 is None:
            status = "present"
        elif actual_sha256 == expected_sha256:
            status = "verified"
        else:
            status = "modified"

        reports.append(
            TrackedSourceReport(
                label=label, category=category, path=rel_path, sha256=actual_sha256, status=status
            )
        )
    return reports


def get_artifact_status() -> ArtifactStatusResponse:
    """Lightweight existence-only check across the 170-file artifact
    inventory (no SHA-256 recomputation -- several hundred MB of frozen
    checkpoints/caches would make that expensive on every request; the
    authoritative byte-for-byte verification is
    ``python -m plantaox.c2_pu.pp1_freeze verify``, run manually/offline).

    ``tracked_source_reports`` is a separate, curated list of the handful of
    small (KB-scale) documentation/manifest files worth re-hashing on every
    request, each checked live against the frozen manifest's recorded
    SHA-256 so drift from the accepted release is visible immediately.
    """
    manifest = load_freeze_manifest()
    inventory = load_artifact_inventory()
    repo_root = get_settings().repo_root

    missing: list[str] = []
    for _, row in inventory.iterrows():
        if not (repo_root / row["path"]).exists():
            missing.append(row["path"])

    return ArtifactStatusResponse(
        freeze_id=manifest["release"]["id"],
        release_tag=manifest["source_control"]["release_tag"],
        freeze_decision=manifest["release"]["decision"],
        total_tracked=len(inventory),
        present_count=len(inventory) - len(missing),
        missing_count=len(missing),
        missing_paths=missing,
        pending_decisions=manifest["pending_decisions"],
        tracked_source_reports=_tracked_source_reports(),
    )
