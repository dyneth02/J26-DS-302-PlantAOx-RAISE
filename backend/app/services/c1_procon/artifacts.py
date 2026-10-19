"""Read-only access to Component 01's accepted artifacts.

Every function only reads files under ``data/processed/c1_procon``; nothing is
written, no result is recomputed that the research notebooks already produced,
and no filesystem path is ever accepted from a caller. A missing or unreadable
file raises ``ArtifactUnavailableError`` (served as 503) -- never mock data.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import ArtifactUnavailableError

C1_RECOVERY_HINT = (
    "Run the C1 notebooks (notebooks/c1_procon) or restore data/processed/c1_procon "
    "from the repository; see src/plantaox/c1_procon/docs/PIPELINE_README.md."
)


def c1_processed_dir(settings: Settings | None = None) -> Path:
    return (settings or get_settings()).data_processed / "c1_procon"


def _missing(path: Path) -> ArtifactUnavailableError:
    return ArtifactUnavailableError(
        f"Accepted artifact is missing from this checkout: {path.name}. {C1_RECOVERY_HINT}",
        artifact_path=str(path),
    )


def read_csv(relative: str, settings: Settings | None = None) -> pd.DataFrame:
    path = c1_processed_dir(settings) / relative
    if not path.exists():
        raise _missing(path)
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ArtifactUnavailableError(
            f"Accepted artifact could not be read or parsed: {path.name} ({exc}).",
            artifact_path=str(path),
        ) from exc


def read_json(relative: str, settings: Settings | None = None) -> dict:
    path = c1_processed_dir(settings) / relative
    if not path.exists():
        raise _missing(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactUnavailableError(
            f"Accepted artifact could not be read or parsed: {path.name} ({exc}).",
            artifact_path=str(path),
        ) from exc


def num(value: Any) -> float | None:
    """JSON-safe float: NaN / None -> None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def req(value: Any) -> float:
    f = num(value)
    if f is None:
        raise ArtifactUnavailableError("An accepted C1 table contains a missing value where one is required.")
    return f


# Every file the C1 API reads, grouped for the artifact-status endpoint.
EXPECTED_ARTIFACTS: dict[str, list[str]] = {
    "benchmark": ["AOP-BenchPos_S2.csv", "step1_manifest.json"],
    "retrieval (steps 4-6)": [
        "results/step4_collapse_report.csv",
        "results/step5_mc_retrieval.csv",
        "results/step5_paired_comparisons.csv",
        "results/step5_geometry_heldout.csv",
        "results/step6_seed_spread.csv",
        "results/step6_scale_sweep.csv",
    ],
    "embeddings and pairs": [
        "results/embedding_projection.csv",
        "results/embedding_stats.json",
        "pairs_manifest.json",
        "pairs/strict/positive_pairs.csv",
        "results/oof_probe_scores.csv",
    ],
    "probe (step 5 v4)": ["results/step5_probe.csv", "results/step5_probe_paired.csv"],
    "confound controls (step 8)": [
        "results/step8/step8_headline.csv",
        "results/step8/step8_probe_strict.csv",
        "results/step8/step8_probe_anoxpepred_only.csv",
        "results/step8/step8_delta_esm_over_confounds.csv",
        "results/step8/step8_length_matched.csv",
        "results/step8/step8_learning_curve.csv",
        "results/step8/step8_cv_design.csv",
    ],
}
