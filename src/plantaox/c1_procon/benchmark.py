"""The AOP-ProCon benchmark (S2 build v3): loading and integrity check.

The benchmark is frozen: every notebook asserts its content fingerprint, so a changed file can never be used by accident.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

EXPECTED_FINGERPRINT = "47d9c2a2fff63eb1"
REQUIRED_COLUMNS = {"sequence", "labels", "sample_weight", "cluster_40", "lso_fold", "homology_group", "strict_evidence"}


class BenchmarkMismatchError(ValueError):
    """The benchmark file is not the frozen S2 build v3."""


def repo_root() -> Path:
    """Directory that contains ``pyproject.toml`` (found by walking up from this file)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate the repository root (no pyproject.toml found).")


def default_benchmark_path() -> Path:
    return repo_root() / "data" / "processed" / "c1_procon" / "AOP-BenchPos_S2.csv"


def s2_fingerprint(s2: pd.DataFrame) -> str:
    """Canonical content hash of the benchmark.

    Same definition as in the Step 1 and Step 2 notebooks: one line per peptide (sorted by sequence) with its sequence,
    labels, homology group, fold and sample weight, hashed with MD5 and shortened to 16 hex characters.
    """
    lines = []
    for r in s2.sort_values("sequence").itertuples():
        lines.append(
            "\t".join(
                [
                    r.sequence,
                    r.labels,
                    "" if pd.isna(r.homology_group) else str(int(r.homology_group)),
                    "" if pd.isna(r.lso_fold) else str(int(r.lso_fold)),
                    f"{float(r.sample_weight):.1f}",
                ]
            )
        )
    return hashlib.md5("\n".join(lines).encode()).hexdigest()[:16]


def load_benchmark(path: str | Path | None = None, verify: bool = True) -> pd.DataFrame:
    """Read the benchmark table; with ``verify`` the structure and the fingerprint are checked."""
    s2 = pd.read_csv(path or default_benchmark_path())
    if verify:
        missing = REQUIRED_COLUMNS - set(s2.columns)
        if missing:
            raise BenchmarkMismatchError(f"benchmark is missing columns: {sorted(missing)}")
        if not s2["sequence"].is_unique:
            raise BenchmarkMismatchError("the benchmark must have one row per unique sequence")
        found = s2_fingerprint(s2)
        if found != EXPECTED_FINGERPRINT:
            raise BenchmarkMismatchError(f"fingerprint {found} is not the frozen S2 build v3 ({EXPECTED_FINGERPRINT})")
    return s2
