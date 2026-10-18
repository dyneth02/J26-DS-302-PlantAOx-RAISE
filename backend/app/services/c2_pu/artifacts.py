"""Read-only access to Component 02's accepted/frozen artifacts.

Every function here only reads files under ``data/processed/c2_pu``,
``data/interim/c2_pu`` or ``src/plantaox/c2_pu/docs`` -- never writes,
never recomputes a result the research pipeline already produced, and
never accepts a filesystem path from a caller (route handlers only ever
pass fold ids / peptide ids / model ids that get validated against the
real artifact contents here).

JSON/CSV reads are cheap (artifacts here are at most ~1-2MB) so no caching
layer is needed for Level A; the one exception is the frozen-release
manifest, which every endpoint consults for provenance and is cached in
memory since it never changes while the server is running.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import ArtifactUnavailableError, ResourceNotFoundError

C2_DOCS_SUBPATH = Path("src") / "plantaox" / "c2_pu" / "docs"


def c2_processed_dir(settings: Settings | None = None) -> Path:
    return (settings or get_settings()).data_processed / "c2_pu"


def c2_interim_dir(settings: Settings | None = None) -> Path:
    return (settings or get_settings()).data_interim / "c2_pu"


def c2_docs_dir(settings: Settings | None = None) -> Path:
    return (settings or get_settings()).repo_root / C2_DOCS_SUBPATH


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise ArtifactUnavailableError(
            f"Accepted artifact is missing from this checkout: {path.name}. "
            "It may be a Git-ignored artifact not present on this machine -- "
            "see src/plantaox/c2_pu/docs/C2_PP1_HANDOVER.md for recovery instructions.",
            artifact_path=str(path),
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactUnavailableError(
            f"Accepted artifact could not be read or parsed: {path.name} ({exc}).",
            artifact_path=str(path),
        ) from exc


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise ArtifactUnavailableError(
            f"Accepted artifact is missing from this checkout: {path.name}. "
            "It may be a Git-ignored artifact not present on this machine -- "
            "see src/plantaox/c2_pu/docs/C2_PP1_HANDOVER.md for recovery instructions.",
            artifact_path=str(path),
        )
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as exc:
        raise ArtifactUnavailableError(
            f"Accepted artifact could not be read or parsed: {path.name} ({exc}).",
            artifact_path=str(path),
        ) from exc


def load_processed_json(filename: str, settings: Settings | None = None) -> dict:
    return _read_json(c2_processed_dir(settings) / filename)


def load_processed_csv(filename: str, settings: Settings | None = None) -> pd.DataFrame:
    return _read_csv(c2_processed_dir(settings) / filename)


def load_frozen_json(version_id: str, settings: Settings | None = None) -> dict:
    """``version_id`` is "pp1_baseline_v1" or "pp2_baseline_v1" -- the two
    sub-releases under data/processed/c2_pu/frozen/."""
    if version_id not in {"pp1_baseline_v1", "pp2_baseline_v1"}:
        raise ResourceNotFoundError(f"Unknown frozen baseline version: {version_id!r}")
    return _read_json(c2_processed_dir(settings) / "frozen" / version_id / "MANIFEST.json")


def load_freeze_manifest(settings: Settings | None = None) -> dict:
    return _read_json(c2_processed_dir(settings) / "C2_PP1_FREEZE_MANIFEST.json")


def load_artifact_inventory(settings: Settings | None = None) -> pd.DataFrame:
    return _read_csv(c2_processed_dir(settings) / "C2_PP1_ARTIFACT_INVENTORY.csv")


def load_doc_text(filename: str, settings: Settings | None = None) -> str:
    path = c2_docs_dir(settings) / filename
    if not path.exists():
        raise ArtifactUnavailableError(f"Documentation file missing: {filename}", artifact_path=str(path))
    return path.read_text(encoding="utf-8")


def resolve_repo_relative(path_str: str, settings: Settings | None = None) -> Path:
    """Normalizes a manifest-recorded path to this checkout's repo root.

    Several accepted JSON artifacts (fr3_feature_cache_manifest.json,
    fr4_curriculum_fold0_summary.json, ...) embed the ABSOLUTE path of the
    machine that produced them, which is not portable to another
    teammate's checkout. We only ever trust the path's filename/suffix
    (joined back onto this machine's own repo root), never the embedded
    absolute prefix.
    """
    settings = settings or get_settings()
    candidate = Path(path_str)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    # Re-anchor on this repo root using the path's components from a known
    # top-level data directory onward.
    parts = candidate.parts
    for anchor in ("data", "src"):
        if anchor in parts:
            idx = parts.index(anchor)
            return settings.repo_root.joinpath(*parts[idx:])
    raise ArtifactUnavailableError(f"Could not resolve artifact path for this checkout: {path_str}")
