from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "plantaox-raise-api"}


async def test_components_lists_all_four_with_c1_and_c2_implemented(client):
    resp = await client.get("/api/v1/components")
    assert resp.status_code == 200
    components = resp.json()
    assert {c["code"] for c in components} == {"C1", "C2", "C3", "C4"}
    statuses = {c["code"]: c["status"] for c in components}
    assert statuses["C2"] == "implemented"
    assert statuses["C1"] == "implemented"
    assert statuses["C3"] == "not_integrated"
    assert statuses["C4"] == "not_integrated"
