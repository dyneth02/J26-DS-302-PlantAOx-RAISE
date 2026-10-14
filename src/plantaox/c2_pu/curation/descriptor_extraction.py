"""Bucket 3.1 -- physicochemical descriptor extraction over the frozen
FR1/FR2 canonical pools.

Reads only from the frozen ``pp1_baseline_v1`` / ``pp2_baseline_v1``
directories (never the superseded working-tree copies), computes the
canonical 15-descriptor vector (``common/descriptors.py``) for every
*unique sequence* per pool, and preserves record-level provenance
separately so no pool's record count or fold/evidence-tier contract is
disturbed.

Per-pool handling, and why:

* **FR1 positives** -- all 1,205 provisional positives get descriptors
  (record-level == sequence-level here; the provisional pool is read
  directly, not the CD-HIT/GraphPart-reduced split). GraphPart fold
  membership and evidence tier are attached as extra columns for the 834
  retained sequences, via ``curation/splits.py::load_graphpart_splits`` --
  never re-derived by hand.
* **C1** -- the frozen FASTA (``stage_c1_decoys_v3.fasta``) has 5,000
  *records* but 3,788 *unique sequences*, and its headers are raw UniProt
  deflines, not peptide IDs. Descriptors are computed once per unique
  sequence (content-addressed ``C1-`` peptide ID via
  ``common.sequence.make_peptide_id``); a separate record map preserves
  every one of the 5,000 source accessions, so no record is dropped and no
  sequence's feature vector is duplicated 5,000/3,788 times over.
* **C2 / C3** -- FASTA headers already ARE the project's peptide IDs
  (``C2-``/``C3-`` prefixes), one record per unique sequence by
  construction. C3's FASTA is the fold-union (2,325 unique sequences from
  5x2,000=10,000 per-fold selection rows) -- descriptors are computed once
  per union sequence (sequence-local and deterministic, so this is safe),
  but fold membership is NOT re-derived here. Downstream fold-specific
  training must still call ``curation/c3.py::load_fold_challenges`` and
  join its ``peptide_id`` column against this module's descriptor table --
  this module never returns a "give me all folds" C3 view itself.
* **External control** (AnOxPePred experimentally-inactive) -- 38 records,
  kept in its own pool column, never merged into the unlabeled pools
  (AGENTS.md rule 2).

No cross-dataset statistic (mean, std, min-max, PCA, etc.) is fit or
applied anywhere in this module -- every value is a raw, per-sequence
physicochemical property. Any learned normalization belongs to a later,
fold-aware stage (Bucket 3.3), not here.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from plantaox.c2_pu.common.descriptors import (
    DESCRIPTOR_NAMES,
    SCHEMA_VERSION,
    compute_descriptors_batch,
)
from plantaox.c2_pu.common.io import read_fasta
from plantaox.c2_pu.common.sequence import make_peptide_id
from plantaox.c2_pu.curation.splits import load_graphpart_splits


def _dedup_by_sequence(peptide_ids: list[str], sequences: list[str]) -> tuple[list[str], list[str]]:
    """First-occurrence dedup, preserving order (for a pool with record-level
    duplicates, e.g. C1)."""
    seen: dict[str, str] = {}
    for pid, seq in zip(peptide_ids, sequences):
        seen.setdefault(seq, pid)
    unique_sequences = list(seen.keys())
    unique_ids = [seen[seq] for seq in unique_sequences]
    return unique_ids, unique_sequences


def extract_fr1_positive_descriptors(
    positive_pool_path: Path, graphpart_splits_path: Path | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (descriptor_df, record_map_df) for the FR1 provisional
    positive pool. ``record_map_df`` carries peptide_id/sequence/
    evidence_tier plus graphpart_fold/graphpart_retained (NaN/False for the
    91 sequences GraphPart excluded for cross-fold homology, per
    IMPLEMENTATION_STATUS.md)."""
    positives_df = pd.read_parquet(positive_pool_path)
    descriptor_df = compute_descriptors_batch(
        positives_df["peptide_id"].tolist(), positives_df["sequence"].tolist()
    )
    descriptor_df.insert(2, "pool", "FR1_positives")

    record_map = positives_df[["peptide_id", "sequence", "evidence_tier"]].copy()
    record_map["pool"] = "FR1_positives"
    record_map["graphpart_fold"] = pd.NA
    record_map["graphpart_retained"] = False
    if graphpart_splits_path is not None and Path(graphpart_splits_path).exists():
        splits_df = load_graphpart_splits(graphpart_splits_path)
        fold_map = dict(zip(splits_df["peptide_id"], splits_df["fold"].astype(int)))
        record_map["graphpart_fold"] = record_map["peptide_id"].map(fold_map)
        record_map["graphpart_retained"] = record_map["peptide_id"].isin(fold_map)
    return descriptor_df, record_map


def extract_c1_descriptors(
    c1_fasta_path: Path, c1_accession_map_path: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """C1 has 5,000 FASTA records (raw UniProt deflines as headers) but
    only ~3,788 unique sequences. Descriptors are computed once per unique
    sequence; the record map preserves all 5,000 source accessions."""
    records = read_fasta(c1_fasta_path)
    headers = [h for h, _ in records]
    sequences = [s for _, s in records]
    accession_map = pd.read_csv(c1_accession_map_path)
    header_to_accession = dict(zip(accession_map["peptide_header"], accession_map["accession"]))

    content_ids = [make_peptide_id(seq, prefix="C1") for seq in sequences]
    unique_ids, unique_sequences = _dedup_by_sequence(content_ids, sequences)

    descriptor_df = compute_descriptors_batch(unique_ids, unique_sequences)
    descriptor_df.insert(2, "pool", "C1")

    record_map = pd.DataFrame(
        {
            "peptide_id": content_ids,
            "sequence": sequences,
            "accession": [header_to_accession.get(h) for h in headers],
            "source_header": headers,
            "pool": "C1",
        }
    )
    return descriptor_df, record_map


def extract_id_prefixed_pool_descriptors(
    fasta_path: Path, pool_name: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """For C2/C3/any pool whose FASTA headers already are the project's
    content-addressed peptide IDs (one record per unique sequence)."""
    records = read_fasta(fasta_path)
    peptide_ids = [h for h, _ in records]
    sequences = [s for _, s in records]
    descriptor_df = compute_descriptors_batch(peptide_ids, sequences)
    descriptor_df.insert(2, "pool", pool_name)
    record_map = pd.DataFrame({"peptide_id": peptide_ids, "sequence": sequences, "pool": pool_name})
    return descriptor_df, record_map


def extract_external_control_descriptors(
    external_control_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """AnOxPePred external control -- kept in its own 'external_control'
    pool, never merged with C1/C2/C3 (AGENTS.md rule 2)."""
    ext_df = pd.read_csv(external_control_path)
    descriptor_df = compute_descriptors_batch(ext_df["peptide_id"].tolist(), ext_df["sequence"].tolist())
    descriptor_df.insert(2, "pool", "external_control")
    record_map = ext_df[["peptide_id", "sequence"]].copy()
    record_map["pool"] = "external_control"
    return descriptor_df, record_map


def build_coverage_report(descriptor_tables: dict[str, pd.DataFrame], record_maps: dict[str, pd.DataFrame]) -> dict:
    return {
        pool: {
            "unique_sequences_with_descriptors": int(len(descriptor_tables[pool])),
            "source_records": int(len(record_maps[pool])),
        }
        for pool in descriptor_tables
    }


def build_validation_report(combined_descriptors: pd.DataFrame) -> dict:
    """Diagnostics only (missing/nonfinite counts, ranges, near-constant
    flags, pairwise correlation) -- never used for feature selection,
    scaling, or any other data-dependent preprocessing here."""
    values = combined_descriptors[list(DESCRIPTOR_NAMES)]
    report: dict = {"n_rows": int(len(values)), "per_descriptor": {}}
    for name in DESCRIPTOR_NAMES:
        col = values[name]
        report["per_descriptor"][name] = {
            "missing": int(col.isna().sum()),
            "nonfinite": int((~np.isfinite(col.to_numpy(dtype=float))).sum()),
            "min": float(col.min()),
            "max": float(col.max()),
            "mean": float(col.mean()),
            "std": float(col.std()),
            "near_constant": bool(col.std() < 1e-8),
        }
    corr = values.corr()
    high_corr_pairs = []
    for i, a in enumerate(DESCRIPTOR_NAMES):
        for b in DESCRIPTOR_NAMES[i + 1 :]:
            r = corr.loc[a, b]
            if abs(r) >= 0.9:
                high_corr_pairs.append({"a": a, "b": b, "pearson_r": round(float(r), 4)})
    report["high_correlation_pairs_abs_ge_0.9"] = high_corr_pairs
    report["schema_version"] = SCHEMA_VERSION
    return report
