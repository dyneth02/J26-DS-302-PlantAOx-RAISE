from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.schemas.c2_pu import ArtifactStatusResponse
from backend.app.services.c2_pu.artifacts import load_artifact_inventory, load_freeze_manifest


def get_artifact_status() -> ArtifactStatusResponse:
    """Lightweight existence-only check across the 170-file artifact
    inventory (no SHA-256 recomputation -- several hundred MB of frozen
    checkpoints/caches would make that expensive on every request; the
    authoritative byte-for-byte verification is
    ``python -m plantaox.c2_pu.pp1_freeze verify``, run manually/offline).
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
    )
