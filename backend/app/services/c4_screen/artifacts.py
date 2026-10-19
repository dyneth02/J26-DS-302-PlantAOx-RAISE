"""Cached, read-only loading and query helpers for Component 4 outputs."""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from io import StringIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.app.core.config import get_settings
from backend.app.core.errors import ArtifactUnavailableError, ResourceNotFoundError

PLANT_SPECIES = {
    "soybean": "Glycine max",
    "rice": "Oryza sativa japonica",
    "rapeseed": "Brassica napus",
    "olive": "Olea europaea",
}
PLANTS = tuple(PLANT_SPECIES)
_CANDIDATE_COLUMNS = [
    "sequence", "peptide_id", "length", "n_parents", "provenance",
    "molecular_weight", "isoelectric_point", "gravy", "net_charge_ph7",
]
_MEMBERSHIP_COLUMNS = ["peptide_id", "sequence", "plant"]
_TIER_COLUMNS = ["peptide_id", "sequence", "d_AD", "d_norm", "tier", "embedded", "cloud_source"]
_RANKED_COLUMNS = [
    "peptide_id", "sequence", "d_AD", "d_norm", "tier", "embedded", "cloud_source",
    "SIM_C1", "SIM_C1_source", "PROB_C2", "evidence_tier", "PROB_C2_source", "plant",
    "molecular_weight", "isoelectric_point", "gravy", "net_charge_ph7", "length",
    "provenance", "CS", "rank",
]


def c4_data_dir() -> Path:
    configured = os.environ.get("C4_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return get_settings().data_interim / "c4_screen"


def _required(path: Path) -> Path:
    if not path.is_file():
        raise ArtifactUnavailableError(
            f"Required C4 artifact is missing: {path.name}", artifact_path=str(path)
        )
    return path


def _read_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.is_file():
        if required:
            _required(path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactUnavailableError(
            f"C4 artifact could not be read: {path.name} ({exc})", artifact_path=str(path)
        ) from exc


def _read_parquet(path: Path, columns: list[str]) -> pd.DataFrame:
    _required(path)
    try:
        frame = pd.read_parquet(path, columns=columns)
    except (OSError, ValueError, ImportError) as exc:
        raise ArtifactUnavailableError(
            f"C4 parquet artifact could not be read: {path.name} ({exc})", artifact_path=str(path)
        ) from exc
    return frame


@lru_cache(maxsize=4)
def _load_dataset(root_name: str) -> dict[str, Any]:
    """Load each requested parquet projection once per configured data directory."""
    root = Path(root_name)
    candidates = _read_parquet(root / "candidates.parquet", _CANDIDATE_COLUMNS)
    membership = _read_parquet(root / "plant_membership.parquet", _MEMBERSHIP_COLUMNS)
    tiers = _read_parquet(root / "c4_ad_tiers.parquet", _TIER_COLUMNS)
    ranked = _read_parquet(root / "c4_ranked_candidates.parquet", _RANKED_COLUMNS)
    try:
        funnel = pd.read_csv(_required(root / "funnel_summary.csv"))
        tier_plant = pd.read_csv(_required(root / "diagnostics" / "tier_fractions_by_plant.csv"))
        tier_bins = pd.read_csv(_required(root / "diagnostics" / "tier_fractions_by_length_bin.csv"))
        sensitivity_path = root / "diagnostics" / "mean_centering_tier_fraction_sensitivity.csv"
        sensitivity = pd.read_csv(sensitivity_path) if sensitivity_path.is_file() else None
        cloud_meta = pd.read_csv(_required(root / "ref_cloud_meta.csv"))
        output_manifest_path = _required(root / "c4_output_manifest.json")
        output_manifest = _read_json(output_manifest_path)
        params = _read_json(root / "ad_params.json")
        summary = _read_json(root / "summary.json")
        embedding_manifest = _read_json(root / "c4_embedding_manifest.json", required=False)
        signal_manifest = _read_json(root / "signals" / "MOCK_MANIFEST.json", required=False)
        bcs = _read_json(root / "signals" / "c3_bcs.json", required=False)
    except (OSError, pd.errors.ParserError) as exc:
        raise ArtifactUnavailableError(f"A required C4 metadata artifact could not be read ({exc})") from exc

    # The current release manifest is a frozen source label; hash the manifest itself for API provenance.
    output_hash = hashlib.sha256(output_manifest_path.read_bytes()).hexdigest()
    cloud_path = root / "embeddings" / "ref_cloud.npy"
    cloud = None
    if cloud_path.is_file():
        try:
            cloud = np.load(cloud_path, mmap_mode="r")
        except (OSError, ValueError) as exc:
            raise ArtifactUnavailableError(
                f"C4 cloud embeddings could not be read ({exc})", artifact_path=str(cloud_path)
            ) from exc

    return {
        "root": root,
        "candidates": candidates,
        "membership": membership,
        "tiers": tiers,
        "ranked": ranked,
        "funnel": funnel,
        "tier_plant": tier_plant,
        "tier_bins": tier_bins,
        "sensitivity": sensitivity,
        "cloud_meta": cloud_meta,
        "cloud_embeddings": cloud,
        "output_manifest": output_manifest,
        "output_hash": output_hash,
        "params": params,
        "summary": summary,
        "embedding_manifest": embedding_manifest,
        "signal_manifest": signal_manifest,
        "bcs": bcs,
    }


def dataset() -> dict[str, Any]:
    return _load_dataset(str(c4_data_dir()))


def get_plant(plant: str) -> str:
    if plant not in PLANT_SPECIES:
        raise ResourceNotFoundError(f"Unknown C4 plant: {plant!r}")
    return plant


def _to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")


def get_meta() -> dict[str, Any]:
    data = dataset()
    params = data["params"]
    summary = data["summary"]
    cloud = summary.get("cloud", {})
    signal_sources = summary.get("signal_sources", {})
    if not signal_sources:
        signal_sources = {"SIM_C1": "mock", "PROB_C2": "mock", "BCS": "mock"}
    return {
        "ad_params": params,
        "cloud": {
            "source": cloud.get("source", params.get("cloud_source", "unknown")),
            "n": int(cloud.get("n_sequences", params.get("n_cloud", 0))),
            "status": "mock" if cloud.get("mock", params.get("cloud_is_mock", True)) else "provisional real",
        },
        "signal_sources": signal_sources,
        "spec_version": data["bcs"].get("schema_version") or "c4-interface-0.1-provisional",
        "embedding_manifest_summary": {
            key: data["embedding_manifest"].get(key)
            for key in ("model", "layer", "pooling", "dtype_saved", "dim", "n", "device")
            if key in data["embedding_manifest"]
        },
        "output_manifest_hash": data["output_hash"],
        "tag": os.environ.get("C4_RELEASE_TAG", "c4-pp1-v1"),
        "warnings": [
            "The reference cloud is MOCK (mock_cloud).",
            "C1/C2/C3 signals are MOCK (source=mock).",
            "No retrieval metrics were computed on mock inputs.",
        ],
    }


def get_funnel() -> list[dict[str, Any]]:
    return _to_records(dataset()["funnel"].sort_values("plant"))


def get_tier_summary(plant: str | None = None) -> dict[str, Any]:
    data = dataset()
    overall = data["tier_plant"]
    bins = data["tier_bins"]
    sensitivity = data["sensitivity"]
    if plant:
        get_plant(plant)
        overall = overall.loc[overall.plant == plant]
        bins = bins.loc[bins.plant == plant]
        if sensitivity is not None and "group" in sensitivity:
            if sensitivity.group.eq(plant).any():
                sensitivity = sensitivity.loc[sensitivity.group == plant]
            else:
                sensitivity = sensitivity.loc[sensitivity.group == "all_candidates"]
    sensitivity_records = None
    if sensitivity is not None:
        sensitivity_records = _to_records(sensitivity)
        for item in sensitivity_records:
            item["label"] = "sensitivity, not production"
    return {
        "plant": plant,
        "overall": _to_records(overall.sort_values(["plant", "tier"])),
        "by_length_bin": _to_records(bins.sort_values(["plant", "length_bin", "tier"])),
        "mean_centering_sensitivity": sensitivity_records,
        "sensitivity_label": "sensitivity, not production",
    }


def get_ad_histogram(plant: str | None = None, bins: int = 30) -> dict[str, Any]:
    data = dataset()
    cloud = data["cloud_embeddings"]
    if cloud is None:
        raise ArtifactUnavailableError("Reference cloud embeddings are missing", artifact_path=str(data["root"] / "embeddings" / "ref_cloud.npy"))
    cloud = np.asarray(cloud, dtype=np.float32)
    if cloud.ndim != 2 or len(cloud) < 2 or not np.isfinite(cloud).all():
        raise ArtifactUnavailableError("Reference cloud array must be finite with shape (n>=2, dim)")
    total = cloud.sum(axis=0, dtype=np.float64).astype(np.float32)
    centroids = (total[None, :] - cloud) / np.float32(len(cloud) - 1)
    norms = np.linalg.norm(cloud, axis=1) * np.linalg.norm(centroids, axis=1)
    if np.any(norms == 0):
        raise ArtifactUnavailableError("Reference cloud has zero-norm rows; histogram cannot be computed")
    cloud_distances = 1.0 - np.clip(np.einsum("ij,ij->i", cloud, centroids) / norms, -1.0, 1.0)

    tiers = data["tiers"].loc[data["tiers"].embedded.astype(bool), ["peptide_id", "d_AD"]]
    if plant:
        get_plant(plant)
        plant_ids = data["membership"].loc[data["membership"].plant == plant, "peptide_id"]
        tiers = tiers.loc[tiers.peptide_id.isin(plant_ids)]
    candidate_distances = tiers.d_AD.astype(float).to_numpy()
    low = min(float(np.min(cloud_distances)), float(np.min(candidate_distances)))
    high = max(float(np.max(cloud_distances)), float(np.max(candidate_distances)))
    if high <= low:
        high = low + 1.0
    cloud_counts, edges = np.histogram(cloud_distances, bins=bins, range=(low, high))
    candidate_counts, _ = np.histogram(candidate_distances, bins=edges)
    return {
        "plant": plant,
        "bins": bins,
        "edges": edges.tolist(),
        "cloud": {"source": "cloud", "counts": cloud_counts.astype(int).tolist()},
        "candidates": {"source": "candidates", "counts": candidate_counts.astype(int).tolist()},
        "t1": float(data["params"]["t1"]),
        "t2": float(data["params"]["t2"]),
        "cloud_source": str(data["params"].get("cloud_source", "unknown")),
    }


def get_lengths() -> dict[str, Any]:
    data = dataset()
    candidate_counts = data["candidates"].sequence.str.len().value_counts().to_dict()
    cloud_counts = data["cloud_meta"].sequence.str.len().value_counts().to_dict()
    lengths = sorted(set(map(int, candidate_counts)) | set(map(int, cloud_counts)))
    return {
        "candidate_source": "candidates.parquet",
        "cloud_source": str(data["params"].get("cloud_source", "unknown")),
        "distributions": [
            {"length": length, "candidate_count": int(candidate_counts.get(length, 0)),
             "cloud_count": int(cloud_counts.get(length, 0))}
            for length in lengths
        ],
    }


def query_candidates(*, plant: str | None, tier: int | None, len_min: int | None,
                     len_max: int | None, q: str | None, sort: str, order: str,
                     page: int, page_size: int) -> dict[str, Any]:
    data = dataset()
    frame = data["ranked"]
    if plant:
        get_plant(plant)
        frame = frame.loc[frame.plant == plant]
    if tier is not None:
        frame = frame.loc[frame.tier == tier]
    if len_min is not None:
        frame = frame.loc[frame.length >= len_min]
    if len_max is not None:
        frame = frame.loc[frame.length <= len_max]
    if q:
        frame = frame.loc[frame.sequence.str.contains(q, case=False, regex=False)]
    ascending = order == "asc"
    tie_columns = [column for column in ("sequence", "plant", "peptide_id") if column != sort]
    frame = frame.sort_values([sort, *tie_columns], ascending=[ascending] + [True] * len(tie_columns), kind="mergesort")
    total = len(frame)
    start = (page - 1) * page_size
    return {"items": _to_records(frame.iloc[start:start + page_size]), "total": total,
            "page": page, "page_size": page_size}


def _parse_provenance(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value) if isinstance(value, str) else []
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _bcs_value(bcs: dict[str, Any], length: int) -> tuple[float | None, str | None]:
    length_bin = "3-10" if 3 <= length <= 10 else "11-20" if 11 <= length <= 20 else "21-50"
    for item in bcs.get("strata", []):
        if item.get("mechanism") == "ALL" and item.get("length_bin") == length_bin:
            value = float(item["BCS"])
            flag = "LOW" if value < 0.5 else "MEDIUM" if value < 0.7 else "HIGH"
            return value, flag
    return None, None


def _detail(row: pd.Series, data: dict[str, Any]) -> dict[str, Any]:
    provenance = _parse_provenance(row.get("provenance"))
    length = int(row.get("length", len(str(row["sequence"]))))
    bcs_value, bcs_flag = _bcs_value(data["bcs"], length)
    source = str(row.get("cloud_source") or data["params"].get("cloud_source", "unknown"))
    signal_sources = {
        "SIM_C1": str(row.get("SIM_C1_source", "mock")),
        "PROB_C2": str(row.get("PROB_C2_source", "mock")),
        "BCS": str(data["bcs"].get("source", "mock")),
    }
    return {
        "sequence": str(row["sequence"]),
        "peptide_id": str(row["peptide_id"]),
        "species": PLANT_SPECIES[str(row["plant"])],
        "plant": str(row["plant"]),
        "provenance": provenance,
        "parent_accessions": sorted({str(p["parent_accession"]) for p in provenance if p.get("parent_accession")}),
        "enzymes": sorted({str(p["enzyme_path"]) for p in provenance if p.get("enzyme_path")}),
        "physicochemical": {
            "molecular_weight": float(row["molecular_weight"]),
            "pI": float(row["isoelectric_point"]),
            "GRAVY": float(row["gravy"]),
            "net_charge_ph7": float(row["net_charge_ph7"]),
        },
        "SIM_C1": float(row["SIM_C1"]) if pd.notna(row.get("SIM_C1")) else None,
        "PROB_C2": float(row["PROB_C2"]) if pd.notna(row.get("PROB_C2")) else None,
        "evidence_tier": str(row["evidence_tier"]) if pd.notna(row.get("evidence_tier")) else None,
        "tier": int(row["tier"]),
        "flag": {1: "GREEN", 2: "AMBER", 3: "RED"}[int(row["tier"])],
        "d_AD": float(row["d_AD"]),
        "CS": 0.0 if int(row["tier"]) == 3 else float(row["CS"]),
        "rank": int(row["rank"]) if pd.notna(row.get("rank")) else None,
        "BCS": bcs_value,
        "BCS_flag": bcs_flag,
        "BCS_threshold_status": "C4-provisional",
        "signal_sources": signal_sources,
        "cloud_source": source,
        "injected_demo_case": str(row["sequence"]) in set(data["signal_manifest"].get("injected_demo_cases", [])),
        "notice": "DUMMY SIGNALS / MOCK CLOUD" if source == "mock_cloud" or "mock" in signal_sources.values() else "PROVISIONAL REAL CLOUD / MOCK SIGNALS",
    }


def get_candidate(peptide_id: str) -> dict[str, Any]:
    data = dataset()
    frame = data["ranked"].loc[data["ranked"].peptide_id == peptide_id]
    if frame.empty:
        raise ResourceNotFoundError(f"Unknown or unranked C4 peptide_id: {peptide_id!r}")
    row = frame.sort_values(["plant", "rank", "sequence"], kind="mergesort").iloc[0]
    return _detail(row, data)


def get_cards(plant: str, limit: int) -> list[dict[str, Any]]:
    get_plant(plant)
    data = dataset()
    frame = data["ranked"].loc[(data["ranked"].plant == plant) & data["ranked"].tier.isin([1, 2])]
    frame = frame.sort_values(["rank", "CS", "sequence"], ascending=[True, False, True], kind="mergesort").head(limit)
    return [_detail(row, data) for _, row in frame.iterrows()]


def get_abstained(plant: str, page: int, page_size: int) -> dict[str, Any]:
    get_plant(plant)
    data = dataset()
    frame = data["ranked"].loc[(data["ranked"].plant == plant) & (data["ranked"].tier == 3)]
    frame = frame.sort_values(["sequence", "peptide_id"], kind="mergesort")
    total = len(frame)
    start = (page - 1) * page_size
    items = []
    for _, row in frame.iloc[start:start + page_size].iterrows():
        detail = _detail(row, data)
        detail.update({"tier": 3, "flag": "RED", "CS": 0.0})
        items.append(detail)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def cards_csv(plant: str | None) -> str:
    if plant:
        get_plant(plant)
        plants = [plant]
    else:
        plants = list(PLANTS)
    records = [card for current in plants for card in get_cards(current, 50)]
    frame = pd.DataFrame(records)
    if frame.empty:
        return ""
    for column in ("provenance", "physicochemical", "signal_sources"):
        frame[column] = frame[column].map(json.dumps)
    output = StringIO()
    frame.to_csv(output, index=False, lineterminator="\n")
    return output.getvalue()
