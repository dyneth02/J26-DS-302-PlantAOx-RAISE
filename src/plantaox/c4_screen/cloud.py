"""Reference-cloud metadata handling; never creates or embeds cloud sequences."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


CLOUD_COLUMNS = ["id", "sequence", "evidence_tier", "source", "is_plant"]


def build_reference_meta(sequence_csv: str | Path, output_csv: str | Path | None = None) -> pd.DataFrame:
    """Validate and normalize the supplied cloud sequence metadata."""
    source = Path(sequence_csv)
    if not source.is_file():
        raise FileNotFoundError(f"Reference-cloud sequence metadata is missing: {source}")
    frame = pd.read_csv(source)
    missing = set(CLOUD_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"ref_cloud_sequences.csv missing columns: {sorted(missing)}")
    result = frame[CLOUD_COLUMNS].copy()
    if len(result) != 500:
        raise ValueError(f"Expected 500 reference sequences, found {len(result)}")
    if result["id"].isna().any() or result["id"].duplicated().any():
        raise ValueError("Reference cloud IDs must be present and unique")
    if result["sequence"].isna().any() or result["sequence"].duplicated().any():
        raise ValueError("Reference cloud sequences must be present and unique")
    if not result["source"].eq("mock_cloud").all():
        raise ValueError("Reference cloud source must be mock_cloud for this provisional cloud")
    result["is_plant"] = result["is_plant"].astype(str).str.lower().map({"true": True, "false": False})
    if result["is_plant"].isna().any():
        raise ValueError("is_plant must contain only true/false values")
    if output_csv is not None:
        destination = Path(output_csv)
        destination.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(destination, index=False, lineterminator="\n")
    return result
