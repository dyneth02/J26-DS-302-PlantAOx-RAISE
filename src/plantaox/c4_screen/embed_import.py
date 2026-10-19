"""Validate and load Colab-produced ESM-2 arrays; this module never runs ESM."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


class EmbeddingImportError(ValueError):
    """An embedding handoff is missing or violates its declared contract."""


def row_sequence_sha256(sequences) -> str:
    return hashlib.sha256("\n".join(map(str, sequences)).encode("utf-8")).hexdigest()


def import_embeddings(
    candidates_path: str | Path,
    embedding_dir: str | Path,
    expected_n: int = 152_259,
    dim: int = 1280,
    manifest_copy: str | Path | None = None,
):
    """Validate exact row alignment, hash, shape and finite data, then return float32 arrays."""
    root = Path(embedding_dir)
    paths = {
        "candidate embeddings": root / "c4_esm2_t33_650M.npy",
        "embedding index": root / "c4_embedding_index.parquet",
        "embedding manifest": root / "c4_embedding_manifest.json",
        "reference cloud embeddings": root / "ref_cloud.npy",
        "reference cloud sequences": root / "ref_cloud_sequences.csv",
    }
    missing = [f"{label}: {path}" for label, path in paths.items() if not path.is_file()]
    if missing:
        raise EmbeddingImportError("Embedding import blocked; missing required file(s): " + "; ".join(missing))

    candidates = pd.read_parquet(candidates_path)
    required = {"peptide_id", "sequence"}
    if not required.issubset(candidates.columns):
        raise EmbeddingImportError(f"candidates.parquet missing columns: {sorted(required - set(candidates.columns))}")
    index = pd.read_parquet(paths["embedding index"])
    if not required.issubset(index.columns):
        raise EmbeddingImportError(f"embedding index missing columns: {sorted(required - set(index.columns))}")
    if len(candidates) != expected_n:
        raise EmbeddingImportError(f"candidate count mismatch: expected {expected_n}, found {len(candidates)}")
    if len(index) != expected_n:
        raise EmbeddingImportError(f"embedding index row count mismatch: expected {expected_n}, found {len(index)}")
    if candidates[["peptide_id", "sequence"]].reset_index(drop=True).to_dict("list") != index[["peptide_id", "sequence"]].reset_index(drop=True).to_dict("list"):
        raise EmbeddingImportError("embedding index order does not exactly match candidates.parquet (peptide_id and sequence)")

    manifest = json.loads(paths["embedding manifest"].read_text(encoding="utf-8"))
    if manifest.get("model") != "esm2_t33_650M_UR50D":
        raise EmbeddingImportError(f"embedding manifest model mismatch: {manifest.get('model')!r}")
    if manifest.get("dim") != dim or manifest.get("n") != expected_n:
        raise EmbeddingImportError(f"embedding manifest dimensions/count mismatch: dim={manifest.get('dim')}, n={manifest.get('n')}")
    actual_hash = row_sequence_sha256(candidates["sequence"].tolist())
    if manifest.get("row_id_sha256") != actual_hash:
        raise EmbeddingImportError("embedding manifest row_id_sha256 does not match candidate sequence order")

    matrix = np.load(paths["candidate embeddings"], mmap_mode="r")
    if matrix.shape != (expected_n, dim):
        raise EmbeddingImportError(f"candidate embedding shape mismatch: expected {(expected_n, dim)}, found {matrix.shape}")
    cloud = np.load(paths["reference cloud embeddings"], mmap_mode="r")
    if cloud.shape != (500, dim):
        raise EmbeddingImportError(f"reference cloud shape mismatch: expected {(500, dim)}, found {cloud.shape}")
    for label, array in (("candidate embeddings", matrix), ("reference cloud", cloud)):
        for start in range(0, array.shape[0], 4096):
            if not np.isfinite(array[start:start + 4096]).all():
                raise EmbeddingImportError(f"{label} contains NaN or Inf at rows starting {start}")
    cloud_meta = pd.read_csv(paths["reference cloud sequences"])
    if len(cloud_meta) != 500:
        raise EmbeddingImportError(f"reference cloud sequence row count mismatch: expected 500, found {len(cloud_meta)}")
    if manifest_copy is not None:
        Path(manifest_copy).parent.mkdir(parents=True, exist_ok=True)
        Path(manifest_copy).write_bytes(paths["embedding manifest"].read_bytes())
    return candidates, index, np.asarray(matrix, dtype=np.float32), cloud_meta, np.asarray(cloud, dtype=np.float32), manifest
