from __future__ import annotations

from backend.app.schemas.c1_procon import ArtifactStatusItem, ArtifactStatusResponse
from backend.app.services.c1_procon.artifacts import EXPECTED_ARTIFACTS, c1_processed_dir


def get_artifact_status() -> ArtifactStatusResponse:
    base = c1_processed_dir()
    items: list[ArtifactStatusItem] = []
    for category, files in EXPECTED_ARTIFACTS.items():
        for rel in files:
            path = base / rel
            items.append(
                ArtifactStatusItem(
                    name=path.name,
                    path=f"data/processed/c1_procon/{rel}",
                    exists=path.exists(),
                    category=category,
                )
            )
    missing = [i.path for i in items if not i.exists]
    return ArtifactStatusResponse(all_present=not missing, missing=missing, artifacts=items)
