from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.api.v1.c2_pu import fr1 as fr1_route
from backend.app.core.config import Settings
from backend.app.core.errors import ArtifactUnavailableError
from backend.app.services.c2_pu.artifacts import load_frozen_json

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_missing_frozen_manifest_raises_artifact_unavailable():
    empty_root = Path(__file__).resolve().parent
    broken_settings = Settings(repo_root=empty_root)
    with pytest.raises(ArtifactUnavailableError):
        load_frozen_json("pp1_baseline_v1", settings=broken_settings)


async def test_missing_artifact_surfaces_as_503(client, monkeypatch):
    def _boom():
        raise ArtifactUnavailableError("fold-0 feature cache missing", artifact_path="data/interim/c2_pu/fr3_fold0_scaled_features.npz")

    monkeypatch.setattr(fr1_route, "get_fr1_summary", _boom)
    resp = await client.get("/api/v1/c2/fr1/summary")
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"] == "artifact_unavailable"
    assert "fold-0 feature cache missing" in body["detail"]
