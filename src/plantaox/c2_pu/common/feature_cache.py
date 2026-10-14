"""Bucket 3.4 -- fold-specific scaled feature cache: build + strict loaders.

Deliberately minimal imports (numpy, pandas, json, hashlib only -- no
``common.embeddings``, no ``esm``/``torch``, no WSL subprocess machinery)
so that loading a cache for training never requires ESM-2 inference, a
WSL environment, or recomputing Task 3.1's descriptors -- the whole point
of a "feature cache." This module is the only place Task 3.4 writes code;
``run.py`` orchestrates I/O around it (raw-matrix/scaler loading, file
writes) the same way it does for every other FR3 stage.

Five caches exist, one per GraphPart fold (0-4). Each covers ALL 9,356
rows (every pool), scaled under THAT fold's own scaler (training-
positives-only fit, frozen in ``fr3_fusion_scalers.json`` by Task 3.3 --
never refit here). A row's presence in fold k's cache is not a claim that
it belongs to fold k's curriculum: C1/C2 membership is a straightforward
pool filter, but **C3's fold-specific hard-challenge selection must still
be resolved through ``curation/c3.py::load_fold_challenges(path,
fold_id)``, joined against this cache by peptide_id** -- this module
provides a helper that does exactly that and nothing that would let a
caller silently treat the whole C3 union as one fold's challenge set.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

CACHE_SCHEMA_VERSION = "feature_cache_v1"


class CorruptedCacheError(ValueError):
    """Raised when a cache file's SHA-256 doesn't match its manifest entry,
    or its internal shape/dtype/schema doesn't match what the manifest
    claims -- never silently loaded and trusted anyway."""


class FeatureCacheMembershipError(ValueError):
    """Raised by the C3 fold-challenge helper if asked for peptide_ids the
    cache doesn't contain -- surfaces a real contract violation rather
    than silently returning a partial/empty result."""


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_fold_cache_arrays(
    peptide_ids: list[str],
    pools: list[str],
    raw_matrix: np.ndarray,
    scaler_mean: np.ndarray,
    scaler_std: np.ndarray,
) -> np.ndarray:
    """Apply an already-fitted (never refit here) fold scaler to every row
    of the raw fused matrix, downcast to float32 for storage (the
    scaler's own fit/apply arithmetic stays float64; float32 rounding
    here is ~1e-7 relative, far below any meaningful downstream signal,
    consistent with this project's established embedding-cache dtype)."""
    from plantaox.c2_pu.curation.feature_fusion import apply_scaler

    scaled = apply_scaler(raw_matrix, {"mean": scaler_mean, "std": scaler_std})
    return scaled.astype(np.float32)


def scaler_identity_sha256(mean: np.ndarray, std: np.ndarray) -> str:
    """A compact fingerprint of a fold's exact scaler parameters, so a
    cache's embedded scaler can be checked against the authoritative
    fr3_fusion_scalers.json without comparing 495-element arrays by hand."""
    payload = np.concatenate([np.asarray(mean, dtype=np.float64), np.asarray(std, dtype=np.float64)])
    return hashlib.sha256(payload.tobytes()).hexdigest()


def load_fold_feature_cache(cache_path: Path, manifest_entry: dict) -> dict:
    """Strict loader: verifies the cache file's SHA-256 against
    ``manifest_entry['cache_sha256']`` BEFORE reading its arrays, and
    verifies shape/dtype/schema-version after loading. Raises
    CorruptedCacheError on any mismatch -- never returns a partially-
    trusted cache.
    """
    cache_path = Path(cache_path)
    if not cache_path.exists():
        raise CorruptedCacheError(f"Cache file not found: {cache_path}")

    actual_sha256 = sha256_of(cache_path)
    expected_sha256 = manifest_entry["cache_sha256"]
    if actual_sha256 != expected_sha256:
        raise CorruptedCacheError(
            f"{cache_path}: SHA-256 mismatch -- expected {expected_sha256}, got {actual_sha256}. "
            "Refusing to load a cache file that doesn't match its manifest entry."
        )

    with np.load(cache_path, allow_pickle=False) as npz:
        peptide_ids = npz["peptide_ids"]
        pools = npz["pools"]
        features = npz["features"]
        feature_names = npz["feature_names"]
        scaler_mean = npz["scaler_mean"]
        scaler_std = npz["scaler_std"]

    expected_shape = tuple(manifest_entry["shape"])
    if features.shape != expected_shape:
        raise CorruptedCacheError(f"{cache_path}: shape {features.shape} != manifest-declared {expected_shape}")
    if str(features.dtype) != manifest_entry["dtype"]:
        raise CorruptedCacheError(f"{cache_path}: dtype {features.dtype} != manifest-declared {manifest_entry['dtype']}")
    if manifest_entry["feature_schema_version"] != CACHE_SCHEMA_VERSION:
        raise CorruptedCacheError(
            f"{cache_path}: manifest schema_version {manifest_entry['feature_schema_version']} "
            f"!= this loader's {CACHE_SCHEMA_VERSION}"
        )
    actual_scaler_identity = scaler_identity_sha256(scaler_mean, scaler_std)
    if actual_scaler_identity != manifest_entry["scaler_identity_sha256"]:
        raise CorruptedCacheError(
            f"{cache_path}: embedded scaler does not match manifest's scaler_identity_sha256 "
            f"(expected {manifest_entry['scaler_identity_sha256']}, got {actual_scaler_identity})"
        )

    return {
        "fold_id": manifest_entry["fold_id"],
        "peptide_ids": peptide_ids,
        "pools": pools,
        "features": features,
        "feature_names": feature_names,
        "scaler_mean": scaler_mean,
        "scaler_std": scaler_std,
    }


def get_pool_rows(cache: dict, pool: str) -> tuple[np.ndarray, np.ndarray]:
    """Returns (peptide_ids, features) for every row in ``pool`` (e.g.
    "C1", "C2", "external_control"). For "FR1_positives" training/held-out
    splits, use get_training_rows/get_held_out_rows instead (pool alone
    doesn't distinguish them). For C3's fold-specific hard-challenge
    selection, use get_c3_fold_challenge_rows -- NOT this function, which
    would return the entire C3 union."""
    mask = cache["pools"] == pool
    return cache["peptide_ids"][mask], cache["features"][mask]


def _rows_for_ids(cache: dict, peptide_ids: list[str]) -> tuple[np.ndarray, np.ndarray]:
    id_to_row = {pid: i for i, pid in enumerate(cache["peptide_ids"])}
    missing = [pid for pid in peptide_ids if pid not in id_to_row]
    if missing:
        raise FeatureCacheMembershipError(f"{len(missing)} peptide_id(s) not present in this cache: {missing[:10]}")
    idx = [id_to_row[pid] for pid in peptide_ids]
    return cache["peptide_ids"][idx], cache["features"][idx]


def get_training_rows(cache: dict, training_peptide_ids: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """``training_peptide_ids`` comes from fr3_fusion_scalers.json's
    ``[fold_id]["training_peptide_ids"]`` -- the exact set that fold's
    scaler was fit on."""
    return _rows_for_ids(cache, training_peptide_ids)


def get_held_out_rows(cache: dict, held_out_peptide_ids: list[str]) -> tuple[np.ndarray, np.ndarray]:
    return _rows_for_ids(cache, held_out_peptide_ids)


def get_c3_fold_challenge_rows(
    cache: dict, ranking_path: Path, fold_id: int
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """The ONLY sanctioned way to get a fold's scaled C3 hard-challenge
    rows out of a feature cache: resolves fold-specific membership via
    ``curation/c3.py::load_fold_challenges`` (never by filtering
    ``pool == "C3"``, which is the whole union, not one fold's
    selection), then joins those peptide_ids into this cache's scaled
    features. ``fold_id`` must match the cache's own fold_id -- using a
    different fold's challenge selection against this cache's scaling
    would silently mix two folds' leakage-safety guarantees.
    """
    from plantaox.c2_pu.curation.c3 import load_fold_challenges

    if fold_id != cache["fold_id"]:
        raise ValueError(
            f"Requested C3 fold_id={fold_id} does not match this cache's own fold_id={cache['fold_id']} -- "
            "a fold's C3 challenge selection must be scored under that SAME fold's scaler."
        )
    fold_df = load_fold_challenges(ranking_path, fold_id)
    peptide_ids, features = _rows_for_ids(cache, fold_df["peptide_id"].tolist())
    return peptide_ids, features, fold_df
