from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ComponentInfo(BaseModel):
    id: str
    code: str
    title: str
    owner_note: str
    status: Literal["implemented", "not_integrated"]
    base_path: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class ArtifactAvailability(BaseModel):
    name: str
    path: str
    exists: bool
    category: str | None = None
    git_disposition: str | None = None
