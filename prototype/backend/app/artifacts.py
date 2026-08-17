import json
from pathlib import Path

from fastapi import HTTPException

PROTOTYPE_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_ROOT = PROTOTYPE_ROOT / "artifacts"


def load_json(component: str, filename: str):
    path = ARTIFACTS_ROOT / component / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {component}/{filename}")
    with open(path, "r") as f:
        return json.load(f)
