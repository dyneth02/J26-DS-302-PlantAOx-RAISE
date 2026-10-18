"""Shared application settings.

Single source of truth for filesystem roots the services layer reads from.
Nothing here is specific to Component 02 -- component services resolve
their own sub-paths from ``DATA_PROCESSED`` / ``DATA_INTERIM`` / ``SRC_ROOT``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def _find_repo_root() -> Path:
    """Walk up from this file until a directory containing `pyproject.toml`
    is found. Avoids hard-coding an absolute path that breaks on a
    teammate's checkout."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate repository root (no pyproject.toml found above backend/).")


def _default_cors_origins() -> list[str]:
    raw = os.environ.get("PLANTAOX_CORS_ORIGINS")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


@dataclass(frozen=True)
class Settings:
    repo_root: Path = field(default_factory=_find_repo_root)
    cors_origins: list[str] = field(default_factory=_default_cors_origins)

    @property
    def data_processed(self) -> Path:
        return self.repo_root / "data" / "processed"

    @property
    def data_interim(self) -> Path:
        return self.repo_root / "data" / "interim"

    @property
    def data_raw(self) -> Path:
        return self.repo_root / "data" / "raw"

    @property
    def src_root(self) -> Path:
        return self.repo_root / "src"


@lru_cache
def get_settings() -> Settings:
    return Settings()
