"""FR1 (Bucket 1.7) — dataset freeze: snapshot validated artifacts under a
versioned, immutable baseline identifier (AGENTS.md rule #4: frozen
artifacts stay frozen; a genuine change gets a NEW version ID, never an
in-place mutation).

This does not regenerate or validate anything itself -- it snapshots
already-produced, already-tested files (see run.py's fr1-positives/
fr1-cluster/fr1-split stages, and the FR1 acceptance test suite) alongside a
manifest recording exactly what produced them: tool versions, CLI
configuration, input/output counts, and a SHA-256 checksum per file so any
future drift is immediately detectable.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_baseline(
    version_id: str,
    freeze_dir: Path,
    file_map: dict[str, Path],
    metadata: dict,
) -> Path:
    """Copy each ``file_map`` entry into ``freeze_dir`` and write MANIFEST.json.

    ``file_map`` is {published_filename: source_path}. Returns the path to
    the written manifest.
    """
    freeze_dir.mkdir(parents=True, exist_ok=True)

    checksums: dict[str, str] = {}
    for published_name, source_path in file_map.items():
        if not source_path.exists():
            raise FileNotFoundError(f"Cannot freeze missing file: {source_path}")
        dest_path = freeze_dir / published_name
        shutil.copy2(source_path, dest_path)
        checksums[published_name] = sha256_of(dest_path)

    manifest = {
        "version_id": version_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **metadata,
        "file_checksums": checksums,
    }
    manifest_path = freeze_dir / "MANIFEST.json"
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest_path


def verify_frozen_baseline(freeze_dir: Path) -> dict[str, bool]:
    """Re-check every checksum in an existing freeze's MANIFEST.json.

    Returns {filename: matches_bool}. Use this to detect accidental
    in-place mutation of a frozen directory (AGENTS.md rule #4).
    """
    manifest_path = freeze_dir / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = {}
    for filename, expected_checksum in manifest["file_checksums"].items():
        file_path = freeze_dir / filename
        results[filename] = file_path.exists() and sha256_of(file_path) == expected_checksum
    return results
