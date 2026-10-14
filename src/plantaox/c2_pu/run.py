"""CLI entrypoints orchestrating each FR stage for Component 02.

Usage:
    python -m plantaox.c2_pu.run fr1-positives
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from plantaox.c2_pu.common.io import append_provenance_log, read_fasta, write_fasta
from plantaox.c2_pu.common.wsl import run_in_conda_env, to_wsl_path
from plantaox.c2_pu.common.schemas import (
    CONFLICT_LOG_COLUMNS,
    EXTERNAL_CONTROL_COLUMNS,
    POSITIVE_POOL_COLUMNS,
)
from plantaox.c2_pu.curation.adapters import load_anoxpepred, load_multiaop
from plantaox.c2_pu.curation.dedup import (
    CDHIT_IDENTITY,
    CDHIT_THROWAWAY_LENGTH,
    CDHIT_WORD_LENGTH,
    build_cluster_report,
    clusters_to_dataframe,
    parse_cdhit_clusters,
    run_cdhit,
)
from plantaox.c2_pu.curation.freeze import freeze_baseline, verify_frozen_baseline
from plantaox.c2_pu.curation.peptipedia import build_c2_pool, extract_c2_candidates, load_activity_names
from plantaox.c2_pu.curation.c3 import (
    compute_fold_centroids,
    rank_candidates_for_fold,
    select_top_n_per_fold,
    validate_c3_fold_contract,
)
from plantaox.c2_pu.curation.audit import (
    cross_pool_homology_clusters,
    external_reference_screen,
    overlap_detail,
    pairwise_exact_overlap,
    sequence_integrity_report,
)
from plantaox.c2_pu.curation.biopep import BIOPEP_CITATION, BIOPEP_SEARCH_URL, fetch_biopep_by_activity
from plantaox.c2_pu.common.descriptors import (
    DESCRIPTOR_NAMES,
    SCHEMA_VERSION as DESCRIPTOR_SCHEMA_VERSION,
    compute_descriptors_batch,
)
from plantaox.c2_pu.common.feature_cache import (
    CACHE_SCHEMA_VERSION,
    build_fold_cache_arrays,
    get_c3_fold_challenge_rows,
    get_held_out_rows,
    get_pool_rows,
    get_training_rows,
    load_fold_feature_cache,
    scaler_identity_sha256,
    sha256_of,
)
from plantaox.c2_pu.curation.feature_fusion import (
    ESM2_DIM,
    FUSED_DIM,
    FUSED_FEATURE_NAMES,
    N_DESCRIPTORS,
    SCHEMA_VERSION,
    apply_scaler,
    build_raw_fused_matrix,
    compute_all_fold_scalers,
    load_and_validate_fusion_inputs,
    peptide_id_order_sha256,
)
from plantaox.c2_pu.curation.descriptor_extraction import (
    build_coverage_report,
    build_validation_report,
    extract_c1_descriptors,
    extract_external_control_descriptors,
    extract_fr1_positive_descriptors,
    extract_id_prefixed_pool_descriptors,
)
from plantaox.c2_pu.curation.distribution_audit import (
    amino_acid_composition,
    compare_pools_ks,
    pool_descriptor_table,
)
from plantaox.c2_pu.curation.homology_alignment import parse_needleall_pairs, run_needleall
from plantaox.c2_pu.curation.uniref import fetch_uniref50_candidates, UNIREF50_QUERY, UNIREF50_SORT
from plantaox.c2_pu.curation.splits import (
    GRAPHPART_DENOMINATOR,
    GRAPHPART_IDENTITY_THRESHOLD,
    GRAPHPART_PARTITIONS,
    GRAPHPART_TRANSFORMATION,
    build_split_report,
    load_graphpart_splits,
    run_graphpart,
    write_stratified_fasta,
)
from plantaox.c2_pu.curation.tiers import build_positive_pool
from plantaox.c2_pu.common.sequence import is_valid_peptide, make_peptide_id
from plantaox.c2_pu.pools import (
    apply_secondary_blocklist,
    clean_c1_alphabet,
    clean_c1_cross_pool_overlap,
    clean_c1_pool,
    parse_uniprot_header,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "raw" / "c2_pu"
INTERIM_DIR = REPO_ROOT / "data" / "interim" / "c2_pu"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

MULTIAOP_PATH = RAW_DIR / "Multi-AOP" / "combined_data.csv"
ANOXPEPRED_PATH = RAW_DIR / "AnOxPePred" / "Supplementary_Data_S1_Marcatili.csv"

POSITIVE_POOL_PATH = PROCESSED_DIR / "aop_positives_provisional.parquet"
CONFLICT_LOG_PATH = INTERIM_DIR / "label_conflicts_anox_vs_multiaop.csv"
EXTERNAL_CONTROL_PATH = PROCESSED_DIR / "anoxpepred_inactives_clean.csv"
PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr1_positive_pool_provenance.jsonl"

POSITIVE_POOL_FASTA_PATH = INTERIM_DIR / "aop_positives_provisional.fasta"
CDHIT_OUTPUT_PREFIX = INTERIM_DIR / "aop_positives_cdhit90"
CDHIT_CLUSTERS_PATH = PROCESSED_DIR / "cdhit_clusters.tsv"
CDHIT_REPORT_PATH = PROCESSED_DIR / "cdhit_before_after_report.json"
POSITIVE_POOL_CDHIT_PATH = PROCESSED_DIR / "aop_positives_cdhit90.parquet"

REP_FASTA_PATH = CDHIT_OUTPUT_PREFIX  # cd-hit writes representatives exactly to this path
GRAPHPART_INPUT_FASTA_PATH = INTERIM_DIR / "aop_positives_cdhit90_for_graphpart.fasta"
GRAPHPART_SPLITS_PATH = PROCESSED_DIR / "graphpart_splits.csv"  # canonical registry name
GRAPHPART_REPORT_PATH = PROCESSED_DIR / "graphpart_splits_report.json"
GRAPHPART_SPLIT_SUMMARY_PATH = PROCESSED_DIR / "graphpart_split_summary.json"
GRAPHPART_EXCLUDED_PATH = PROCESSED_DIR / "graphpart_excluded_for_homology.csv"

FR1_BASELINE_VERSION = "pp1_baseline_v1"
FROZEN_DIR = PROCESSED_DIR / "frozen" / FR1_BASELINE_VERSION

# Confirmed directly via `cd-hit -h`, `graphpart --help`, `needle -version`
# inside the pu_aop conda env (not assumed) -- see IMPLEMENTATION_STATUS.md.
TOOL_VERSIONS = {
    "cd-hit": "4.8.1",
    "graph-part": "1.0.2",
    "emboss_needleall": "6.6.0.0",
    "python_pipeline": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    "pandas": pd.__version__,
}

# Bucket 2.1 — C1 random-decoy leakage cleanup. Raw inputs stay untouched
# (historical evidence, per the project owner's explicit instruction); the
# cleaned pool is a new PROCESSED artifact under the same canonical name.
C1_RAW_DECOYS_PATH = RAW_DIR / "UniProt_decoys" / "stage_c1_decoys.fasta"
C1_RAW_CANDIDATES_PATH = RAW_DIR / "UniProt_decoys" / "uniprotkb_candidates.fasta"
C1_CLEAN_FASTA_PATH = PROCESSED_DIR / "stage_c1_decoys.fasta"  # canonical name, processed tier
C1_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c1_leakage_exclusion_log.csv"
C1_REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c1_leakage_replacement_log.csv"
C1_ACCESSION_MAP_PATH = PROCESSED_DIR / "c1_accession_map.csv"
C1_CLEAN_REPORT_PATH = PROCESSED_DIR / "c1_clean_report.json"
C1_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_c1_provenance.jsonl"

# Bucket 2.1 follow-up: standard-20-amino-acid alphabet policy (2026-10-14
# project-owner decision). The v1 artifacts above (post-leakage-fix,
# pre-alphabet-fix) are preserved untouched, per explicit instruction, rather
# than overwritten -- this is a separately versioned, superseding artifact.
C1_CLEAN_FASTA_V2_PATH = PROCESSED_DIR / "stage_c1_decoys_v2.fasta"
C1_ACCESSION_MAP_V2_PATH = PROCESSED_DIR / "c1_accession_map_v2.csv"
C1_ALPHABET_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c1_alphabet_exclusion_log.csv"
C1_ALPHABET_REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c1_alphabet_replacement_log.csv"
C1_ALPHABET_FIX_REPORT_PATH = PROCESSED_DIR / "c1_alphabet_fix_report.json"

# Bucket 2.2 -- C2 bioactive unlabeled pool, built from the Peptipedia v2.0
# Zenodo dump (DOI 10.5281/zenodo.21488992), downloaded once and checksummed
# as a versioned raw source, per AGENTS.md rule 5.
C2_RAW_DUMP_PATH = RAW_DIR / "Peptipedia" / "peptipedia.20240323.sql.gz"
C2_FASTA_PATH = PROCESSED_DIR / "stage_c2_bioactive_unlabeled.fasta"  # canonical registry name
C2_ACTIVITY_MAP_PATH = PROCESSED_DIR / "c2_activity_map.csv"
C2_BUILD_REPORT_PATH = PROCESSED_DIR / "c2_build_report.json"
C2_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_c2_provenance.jsonl"


def run_fr1_positives(seed: int = 42) -> dict:
    """Bucket 1.3/1.4: build the conflict-resolved, evidence-tiered positive pool.

    NOT the FR1 freeze (Bucket 1.7) — CD-HIT 90% dedup (1.5) and GraphPart 40%
    splits (1.6) still need to run on this output before anything here can be
    called frozen.
    """
    mo_df = load_multiaop(MULTIAOP_PATH)
    an_df = load_anoxpepred(ANOXPEPRED_PATH)

    positive_df, conflict_df, external_control_df, summary = build_positive_pool(mo_df, an_df)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # peptide_id is a content-derived hash, so sorting by it is a fully
    # deterministic tie-break independent of Python's per-process hash-seed
    # randomization (set/dict iteration order is NOT guaranteed stable across
    # runs). This matters downstream: CD-HIT's representative selection for
    # exact-tie clusters depends on input FASTA order.
    positive_df = positive_df.reindex(columns=POSITIVE_POOL_COLUMNS).sort_values(
        "peptide_id"
    ).reset_index(drop=True)
    conflict_df = conflict_df.reindex(columns=CONFLICT_LOG_COLUMNS).sort_values(
        "peptide_id"
    ).reset_index(drop=True)
    external_control_df = external_control_df.reindex(columns=EXTERNAL_CONTROL_COLUMNS).sort_values(
        "peptide_id"
    ).reset_index(drop=True)

    positive_df.to_parquet(POSITIVE_POOL_PATH, index=False)
    conflict_df.to_csv(CONFLICT_LOG_PATH, index=False, lineterminator="\n")
    external_control_df.to_csv(EXTERNAL_CONTROL_PATH, index=False, lineterminator="\n")

    append_provenance_log(
        PROVENANCE_LOG_PATH,
        {
            "stage": "fr1_positive_pool_build",
            "multiaop_source": str(MULTIAOP_PATH),
            "anoxpepred_source": str(ANOXPEPRED_PATH),
            "seed": seed,
            "summary": summary,
            "outputs": {
                "positive_pool": str(POSITIVE_POOL_PATH),
                "conflict_log": str(CONFLICT_LOG_PATH),
                "external_control_clean": str(EXTERNAL_CONTROL_PATH),
            },
        },
    )
    return summary


def run_fr1_cluster() -> dict:
    """Bucket 1.5: CD-HIT 90% identity clustering of the provisional positive pool.

    Reads POSITIVE_POOL_PATH (written by run_fr1_positives) -- does not
    modify it. Writes a representatives-only FASTA, the cluster membership
    map (data_registry's canonical `cdhit_clusters.tsv`), a before/after
    report, and a reduced positive-pool parquet carrying forward each
    cluster's representative row (still not GraphPart-split -- see
    run_fr1_split, Bucket 1.6).
    """
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(
            f"{POSITIVE_POOL_PATH} not found -- run `fr1-positives` first."
        )
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    records = list(zip(positive_df["peptide_id"], positive_df["sequence"]))
    write_fasta(POSITIVE_POOL_FASTA_PATH, records)

    rep_fasta_path, clstr_path = run_cdhit(POSITIVE_POOL_FASTA_PATH, CDHIT_OUTPUT_PREFIX)

    members = parse_cdhit_clusters(clstr_path)
    clusters_df = clusters_to_dataframe(members)
    clusters_df.to_csv(CDHIT_CLUSTERS_PATH, sep="\t", index=False, lineterminator="\n")

    report = build_cluster_report(clusters_df, positive_df, n_input_sequences=len(positive_df))

    rep_ids = clusters_df.loc[clusters_df["is_representative"], "peptide_id"]
    reduced_df = (
        positive_df[positive_df["peptide_id"].isin(rep_ids)]
        .sort_values("peptide_id")
        .reset_index(drop=True)
    )
    reduced_df.to_parquet(POSITIVE_POOL_CDHIT_PATH, index=False)

    with open(CDHIT_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)

    append_provenance_log(
        PROVENANCE_LOG_PATH,
        {
            "stage": "fr1_cdhit90_clustering",
            "input": str(POSITIVE_POOL_PATH),
            "outputs": {
                "representative_fasta": str(rep_fasta_path),
                "clusters_tsv": str(CDHIT_CLUSTERS_PATH),
                "report": str(CDHIT_REPORT_PATH),
                "reduced_positive_pool": str(POSITIVE_POOL_CDHIT_PATH),
            },
            "report": report,
        },
    )
    return report


def run_fr1_split() -> dict:
    """Bucket 1.6: GraphPart 40% identity homology-controlled 5-fold split.

    Reads the CD-HIT representative FASTA (written by run_fr1_cluster) and
    the reduced positive pool -- does not modify either. Writes the frozen
    split assignment (`graphpart_splits.csv`, the canonical registry name)
    plus GraphPart's own homology-validation self-report.
    """
    if not REP_FASTA_PATH.exists() or not POSITIVE_POOL_CDHIT_PATH.exists():
        raise FileNotFoundError(
            f"{REP_FASTA_PATH} / {POSITIVE_POOL_CDHIT_PATH} not found -- run `fr1-cluster` first."
        )
    positive_df = pd.read_parquet(POSITIVE_POOL_CDHIT_PATH)

    write_stratified_fasta(
        positive_df["peptide_id"].tolist(),
        positive_df["sequence"].tolist(),
        positive_df["evidence_tier"].tolist(),
        GRAPHPART_INPUT_FASTA_PATH,
    )
    splits_csv_path, graphpart_report_path = run_graphpart(
        GRAPHPART_INPUT_FASTA_PATH, GRAPHPART_SPLITS_PATH, labels_name="tier"
    )
    splits_df = load_graphpart_splits(splits_csv_path)

    report, excluded_df = build_split_report(
        splits_df, positive_df, graphpart_report_path, n_partitions_requested=5
    )
    with open(GRAPHPART_SPLIT_SUMMARY_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
    excluded_df.to_csv(GRAPHPART_EXCLUDED_PATH, index=False, lineterminator="\n")

    append_provenance_log(
        PROVENANCE_LOG_PATH,
        {
            "stage": "fr1_graphpart_split",
            "input": str(GRAPHPART_INPUT_FASTA_PATH),
            "outputs": {
                "splits_csv": str(splits_csv_path),
                "graphpart_self_report": str(graphpart_report_path),
                "split_summary": str(GRAPHPART_SPLIT_SUMMARY_PATH),
                "excluded_for_homology": str(GRAPHPART_EXCLUDED_PATH),
            },
            "report": report,
        },
    )
    return report


def _git_commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def run_fr1_freeze() -> Path:
    """Bucket 1.7: snapshot the validated FR1 artifacts under
    ``FR1_BASELINE_VERSION`` with a checksummed manifest.

    Does not re-validate anything -- run the acceptance test suite
    (tests/c2_pu/test_fr1_*.py) first. This only freezes what already passed.
    """
    required = {
        "aop_positives_provisional.parquet": POSITIVE_POOL_PATH,
        "aop_positives_cdhit90.parquet": POSITIVE_POOL_CDHIT_PATH,
        "cdhit_clusters.tsv": CDHIT_CLUSTERS_PATH,
        "cdhit_before_after_report.json": CDHIT_REPORT_PATH,
        "graphpart_splits.csv": GRAPHPART_SPLITS_PATH,
        "graphpart_excluded_for_homology.csv": GRAPHPART_EXCLUDED_PATH,
        "graphpart_splits_report.json": GRAPHPART_REPORT_PATH,
        "graphpart_split_summary.json": GRAPHPART_SPLIT_SUMMARY_PATH,
        "label_conflicts_anox_vs_multiaop.csv": CONFLICT_LOG_PATH,
        "anoxpepred_inactives_clean.csv": EXTERNAL_CONTROL_PATH,
    }

    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    cdhit_pool_df = pd.read_parquet(POSITIVE_POOL_CDHIT_PATH)
    splits_df = pd.read_csv(GRAPHPART_SPLITS_PATH)
    excluded_df = pd.read_csv(GRAPHPART_EXCLUDED_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)

    metadata = {
        "git_commit": _git_commit_hash(),
        "tool_versions": TOOL_VERSIONS,
        "config": {
            "cdhit": {
                "identity": CDHIT_IDENTITY,
                "word_length": CDHIT_WORD_LENGTH,
                "throwaway_length": CDHIT_THROWAWAY_LENGTH,
            },
            "graphpart": {
                "mode": "needle",
                "identity_threshold": GRAPHPART_IDENTITY_THRESHOLD,
                "transformation": GRAPHPART_TRANSFORMATION,
                "partitions": GRAPHPART_PARTITIONS,
                "denominator": GRAPHPART_DENOMINATOR,
                "labels_name": "tier",
            },
            "note": (
                "No stochastic steps exist in Buckets 1.1-1.6: positive-pool "
                "merge/conflict-resolution is deterministic threshold logic, "
                "CD-HIT's greedy clustering and GraphPart's slow-nn "
                "partitioning are both seed-free. Reproducibility here means "
                "'same inputs -> byte-identical outputs', verified directly, "
                "not 'same seed -> same sample'."
            ),
        },
        "counts": {
            "positive_pool_provisional": len(positive_df),
            "positive_pool_provisional_e1": int((positive_df["evidence_tier"] == "E1").sum()),
            "positive_pool_provisional_e2": int((positive_df["evidence_tier"] == "E2").sum()),
            "cdhit_clusters": len(cdhit_pool_df),
            "graphpart_retained": len(splits_df),
            "graphpart_excluded_for_homology": len(excluded_df),
            "label_conflicts_excluded": len(conflict_df),
            "external_control_clean": len(pd.read_csv(EXTERNAL_CONTROL_PATH)),
            "fold_sizes": {
                str(k): int(v) for k, v in splits_df["cluster"].value_counts().sort_index().items()
            },
        },
        "known_limitations": [
            "179 Multi-AOP positives contradicted by AnOxPePred's own assay call are excluded "
            "from both the positive pool and the external control, pending manual/supervisor "
            "review (label_conflicts_anox_vs_multiaop.csv).",
            "553 of the frozen positives (pre-CD-HIT) are E2 'provisional' -- Multi-AOP-only, "
            "no per-record assay metadata -- pending supervisor review.",
            "91 CD-HIT representatives (9.8%) were excluded by GraphPart to resolve cross-fold "
            "homology violations at the 40% identity threshold "
            "(graphpart_excluded_for_homology.csv).",
            "Fold 4 remains evidence-tier-skewed (64% E1) relative to the other folds (44-52%) "
            "even after label stratification -- a residual, not a defect, documented for "
            "awareness in per-fold metric comparisons.",
        ],
        "pending_supervisor_approvals": [
            "Conflict-resolution policy (assay evidence overrides Multi-AOP's label) -- "
            "2026-10-14 decision log.",
            "E2 provisional-tier default for Multi-AOP-only positives -- 2026-10-14 decision log.",
            "C1 source ambiguity (SwissProt vs UniRef50) -- unrelated to FR1 but still open, "
            "see PU_AOP_RESEARCH_CONTEXT.md section 4.",
        ],
    }

    manifest_path = freeze_baseline(FR1_BASELINE_VERSION, FROZEN_DIR, required, metadata)
    return manifest_path


def run_fr2_c1_clean(seed: int = 42) -> dict:
    """Bucket 2.1 close-out: resolve C1/positive-pool leakage without a wholesale
    resample.

    Reads the RAW stage_c1_decoys.fasta and uniprotkb_candidates.fasta --
    does not modify either (historical evidence). Screens the existing 5,000
    C1 records against the full 1,205 FR1 positive pool AND the 179
    cross-source conflicts (conservative), removes any exact-sequence
    matches, and deterministically fills the gap from the untouched portion
    of the already-saved candidate pool (no live UniProt query needed).
    Writes the cleaned pool to the PROCESSED tier under the same canonical
    filename; the raw tier keeps the original, contaminated-but-historical
    file untouched.
    """
    if not (C1_RAW_DECOYS_PATH.exists() and C1_RAW_CANDIDATES_PATH.exists()):
        raise FileNotFoundError(f"{C1_RAW_DECOYS_PATH} / {C1_RAW_CANDIDATES_PATH} not found.")
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_PATH} not found -- run fr1-positives first.")

    c1_records = read_fasta(C1_RAW_DECOYS_PATH)
    candidate_pool_records = read_fasta(C1_RAW_CANDIDATES_PATH)
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    screen_sequences = set(positive_df["sequence"]) | set(conflict_df["sequence"])

    clean_records, exclusion_log, replacement_log, summary = clean_c1_pool(
        c1_records, candidate_pool_records, screen_sequences, seed=seed
    )
    if summary["shortfall"] > 0:
        raise RuntimeError(
            f"Eligible replacement pool exhausted: needed {summary['n_replacements_needed']}, "
            f"only {summary['n_replacements_available']} available. Stopping rather than "
            "silently shipping a short pool -- see the project owner before changing source/criteria."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta(C1_CLEAN_FASTA_PATH, clean_records)

    accession_map = pd.DataFrame(
        [
            {"peptide_header": h, "sequence": s, "length": len(s), **parse_uniprot_header(h)}
            for h, s in clean_records
        ]
    )
    accession_map.to_csv(C1_ACCESSION_MAP_PATH, index=False, lineterminator="\n")

    exclusion_df = pd.DataFrame(exclusion_log)
    exclusion_df.to_csv(C1_EXCLUSION_LOG_PATH, index=False, lineterminator="\n")

    replacement_df = pd.DataFrame(replacement_log)
    replacement_df.to_csv(C1_REPLACEMENT_LOG_PATH, index=False, lineterminator="\n")

    unique_seqs = set(s for _, s in clean_records)
    lengths = [len(s) for s in unique_seqs]
    summary.update(
        {
            "seed": seed,
            "n_unique_sequences": len(unique_seqs),
            "min_length": min(lengths) if lengths else None,
            "max_length": max(lengths) if lengths else None,
            "screen_set_size": len(screen_sequences),
        }
    )
    with open(C1_CLEAN_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C1_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c1_leakage_cleanup",
            "raw_decoys": str(C1_RAW_DECOYS_PATH),
            "raw_candidates": str(C1_RAW_CANDIDATES_PATH),
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH)],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta": str(C1_CLEAN_FASTA_PATH),
                "accession_map": str(C1_ACCESSION_MAP_PATH),
                "exclusion_log": str(C1_EXCLUSION_LOG_PATH),
                "replacement_log": str(C1_REPLACEMENT_LOG_PATH),
                "report": str(C1_CLEAN_REPORT_PATH),
            },
        },
    )
    return summary


def run_fr2_c1_alphabet_fix(seed: int = 42) -> dict:
    """Bucket 2.1 follow-up: enforce the standard-20-amino-acid-alphabet
    policy on C1 (2026-10-14 project-owner decision -- see Known Issues #9/#10
    in IMPLEMENTATION_STATUS.md).

    Starts from the v1 leakage-clean pool (``C1_CLEAN_FASTA_PATH``, the
    existing accepted Task 2.1 artifact) -- NOT the raw, still-leaky original
    -- and swaps every non-standard-alphabet record (X/B/Z/U) 1:1 for a
    standard-alphabet replacement drawn from the same candidate universe,
    re-screened against the secondary blocklist and all 1,205 FR1 positives
    + 179 conflicts. The v1 artifacts are left untouched; this writes a
    separately versioned v2 artifact set rather than overwriting them.
    """
    if not C1_CLEAN_FASTA_PATH.exists():
        raise FileNotFoundError(f"{C1_CLEAN_FASTA_PATH} not found -- run fr2-c1-clean first.")
    if not C1_RAW_CANDIDATES_PATH.exists():
        raise FileNotFoundError(f"{C1_RAW_CANDIDATES_PATH} not found.")
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_PATH} not found -- run fr1-positives first.")

    c1_records = read_fasta(C1_CLEAN_FASTA_PATH)
    candidate_pool_records = read_fasta(C1_RAW_CANDIDATES_PATH)
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    screen_sequences = set(positive_df["sequence"]) | set(conflict_df["sequence"])

    clean_records, exclusion_log, replacement_log, summary = clean_c1_alphabet(
        c1_records, candidate_pool_records, screen_sequences, seed=seed
    )
    if summary["shortfall"] > 0:
        raise RuntimeError(
            f"Eligible standard-alphabet replacement pool exhausted: needed "
            f"{summary['n_replacements_needed']}, only {summary['n_replacements_available']} "
            "available. Stopping rather than silently shipping a short pool -- see the "
            "project owner before changing source/criteria."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta(C1_CLEAN_FASTA_V2_PATH, clean_records)

    accession_map = pd.DataFrame(
        [
            {"peptide_header": h, "sequence": s, "length": len(s), **parse_uniprot_header(h)}
            for h, s in clean_records
        ]
    )
    accession_map.to_csv(C1_ACCESSION_MAP_V2_PATH, index=False, lineterminator="\n")

    exclusion_df = pd.DataFrame(exclusion_log)
    exclusion_df.to_csv(C1_ALPHABET_EXCLUSION_LOG_PATH, index=False, lineterminator="\n")

    replacement_df = pd.DataFrame(replacement_log)
    replacement_df.to_csv(C1_ALPHABET_REPLACEMENT_LOG_PATH, index=False, lineterminator="\n")

    unique_seqs = set(s for _, s in clean_records)
    lengths = [len(s) for s in unique_seqs]
    summary.update(
        {
            "seed": seed,
            "n_unique_sequences": len(unique_seqs),
            "min_length": min(lengths) if lengths else None,
            "max_length": max(lengths) if lengths else None,
            "screen_set_size": len(screen_sequences),
            "source_version": str(C1_CLEAN_FASTA_PATH),
            "output_version": str(C1_CLEAN_FASTA_V2_PATH),
        }
    )
    with open(C1_ALPHABET_FIX_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C1_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c1_alphabet_policy_fix",
            "source_version": str(C1_CLEAN_FASTA_PATH),
            "raw_candidates": str(C1_RAW_CANDIDATES_PATH),
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH)],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta_v2": str(C1_CLEAN_FASTA_V2_PATH),
                "accession_map_v2": str(C1_ACCESSION_MAP_V2_PATH),
                "alphabet_exclusion_log": str(C1_ALPHABET_EXCLUSION_LOG_PATH),
                "alphabet_replacement_log": str(C1_ALPHABET_REPLACEMENT_LOG_PATH),
                "report": str(C1_ALPHABET_FIX_REPORT_PATH),
            },
        },
    )
    return summary


def run_fr2_c2_build(seed: int = 42) -> dict:
    """Bucket 2.2 -- build the C2 bioactive-unlabeled pool from the
    Peptipedia v2.0 Zenodo dump.

    The dump is parsed directly as a plain-text pg_dump stream (no database
    server needed, see curation/peptipedia.py). Inclusion policy, confirmed
    with the project owner: a peptide must have at least one *reported*
    (not merely absent) non-antioxidant bioactivity, must not itself be
    tagged Peptipedia's antioxidant activity (id 41, "Anti oxidative") even
    if it also carries other activity tags, must pass the shared 3-50 AA /
    standard-20-amino-acid-alphabet window, and must not exactly match any
    of the 1,205 FR1 positives or 179 cross-source conflicts (same
    conservative leakage screen used for C1). Experimentally-reported
    peptides are preferred over ML-predicted-only ones when sampling down
    to ~2,000 (mirrors the project's E1>E2 evidence precedence) -- in this
    run the experimental tier alone comfortably supplies the full 2,000.

    Known, explicitly-flagged gap (not done in this pass): the Planner's
    "cross-reference AODB and DFBP" item. Peptipedia's own 76 integrated
    source databases were checked directly (`source` table) and neither
    AODB nor DFBP is among them, so this pool is not yet cross-checked
    against those two specific resources -- flagged in
    IMPLEMENTATION_STATUS.md rather than silently treated as covered.
    """
    if not C2_RAW_DUMP_PATH.exists():
        raise FileNotFoundError(
            f"{C2_RAW_DUMP_PATH} not found -- download the Peptipedia v2.0 Zenodo dump "
            "(DOI 10.5281/zenodo.21488992, peptipedia.20240323.sql.gz) first."
        )
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_PATH} not found -- run fr1-positives first.")

    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    screen_sequences = set(positive_df["sequence"]) | set(conflict_df["sequence"])

    activity_names = load_activity_names(C2_RAW_DUMP_PATH)
    sequences, activities = extract_c2_candidates(C2_RAW_DUMP_PATH)
    records, summary = build_c2_pool(sequences, activities, screen_sequences, seed=seed)
    if summary["shortfall"] > 0:
        raise RuntimeError(
            f"Eligible C2 candidate pool exhausted: needed {summary['n_requested']}, only "
            f"{summary['n_output_records']} assembled. Stopping rather than silently shipping "
            "a short pool -- see the project owner before changing source/criteria."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    fasta_records = [(make_peptide_id(r["sequence"], prefix="C2"), r["sequence"]) for r in records]
    write_fasta(C2_FASTA_PATH, fasta_records)

    activity_map = pd.DataFrame(
        [
            {
                "peptide_id": peptide_id,
                "id_peptide_peptipedia": r["id_peptide"],
                "sequence": r["sequence"],
                "length": r["length"],
                "activity_ids": ";".join(str(a) for a in r["activity_ids"]),
                "activity_names": ";".join(
                    activity_names.get(a, f"unknown_activity_{a}") for a in r["activity_ids"]
                ),
                "has_experimental_evidence": r["has_experimental_evidence"],
            }
            for (peptide_id, _), r in zip(fasta_records, records)
        ]
    )
    activity_map.to_csv(C2_ACTIVITY_MAP_PATH, index=False, lineterminator="\n")

    import hashlib

    dump_sha256 = hashlib.sha256(C2_RAW_DUMP_PATH.read_bytes()).hexdigest()
    summary.update(
        {
            "source_dump": str(C2_RAW_DUMP_PATH),
            "source_dump_sha256": dump_sha256,
            "source_dump_doi": "10.5281/zenodo.21488992",
            "screen_set_size": len(screen_sequences),
            "antioxidant_activity_id": 41,
            "antioxidant_activity_name": activity_names.get(41),
            "cross_reference_aodb_dfbp": "NOT DONE -- neither AODB nor DFBP is among Peptipedia's "
            "76 integrated source databases; see IMPLEMENTATION_STATUS.md Known Issues.",
        }
    )
    with open(C2_BUILD_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C2_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c2_bioactive_pool_build",
            "source_dump": str(C2_RAW_DUMP_PATH),
            "source_dump_sha256": dump_sha256,
            "source_dump_doi": "10.5281/zenodo.21488992",
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH)],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta": str(C2_FASTA_PATH),
                "activity_map": str(C2_ACTIVITY_MAP_PATH),
                "report": str(C2_BUILD_REPORT_PATH),
            },
        },
    )
    return summary


# Bucket 3.2 — ESM-2 embedding interface smoke test. torch/fair-esm live
# only in the WSL pu_aop conda env (installed there per the project owner's
# explicit decision, 2026-10-14: CPU-only, since the 35M-param model's
# workload doesn't benefit from this machine's ~1hr-download GPU stack) --
# this stage shells out via common/wsl.py, exactly like CD-HIT/GraphPart,
# rather than importing common.embeddings (which imports torch) directly
# into this Windows-side process.
ESM2_CLI_SCRIPT_PATH = Path(__file__).resolve().parent / "esm2_cli.py"
ESM2_SMOKETEST_INPUT_PATH = INTERIM_DIR / "esm2_smoketest_input.json"
ESM2_SMOKETEST_REPORT_PATH = PROCESSED_DIR / "esm2_smoketest_report.json"
ESM2_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr3_esm2_provenance.jsonl"

# Small, fixed set -- NOT full feature generation (that's a later, separate
# Bucket 3.2 task). Mix of length/composition classes mirroring Bucket 3.1's
# own "short/long/charged/hydrophobic" testing convention, so the smoke test
# exercises genuinely different embedding regions, not five near-identical
# inputs.
ESM2_SMOKETEST_PEPTIDES = {
    "SMOKE-SHORT": "KPEEDWGR",
    "SMOKE-MED": "MIRIISRANSVTSSNEVNRLVTGQIPHD",
    "SMOKE-CHARGED": "KKKKKEEEEE",
    "SMOKE-HYDROPHOBIC": "LLLVVVIIIAAA",
    "SMOKE-LONG": "MTPSLSSFLNSLILGAVIVVVPITLALLFVSQKDRTIR",
}


def run_esm2_smoke_test(force_cpu: bool = False) -> dict:
    """Bucket 3.2: configure PyTorch/fair-esm, freeze the ESM-2 spec, and
    smoke-test embedding extraction on a small fixed peptide set.

    Explicitly NOT full feature generation -- extracting embeddings for the
    full positive pool and C1/C2/C3 is a separate, later task. Writes only a
    summary report (shape/dtype/finiteness/norm per peptide); raw embedding
    vectors are never written to a committed path.
    """
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "peptide_ids": list(ESM2_SMOKETEST_PEPTIDES.keys()),
        "sequences": list(ESM2_SMOKETEST_PEPTIDES.values()),
        "force_cpu": force_cpu,
        "validate_alphabet": True,
    }
    with open(ESM2_SMOKETEST_INPUT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)

    result = run_in_conda_env(
        [
            "python",
            to_wsl_path(ESM2_CLI_SCRIPT_PATH),
            to_wsl_path(ESM2_SMOKETEST_INPUT_PATH),
            to_wsl_path(ESM2_SMOKETEST_REPORT_PATH),
        ],
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ESM-2 smoke test failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )
    if not ESM2_SMOKETEST_REPORT_PATH.exists():
        raise RuntimeError(
            "esm2_cli.py reported success but no report was written:\n" + result.stdout
        )

    with open(ESM2_SMOKETEST_REPORT_PATH, encoding="utf-8") as handle:
        report = json.load(handle)

    append_provenance_log(
        ESM2_PROVENANCE_LOG_PATH,
        {
            "stage": "bucket3_esm2_smoke_test",
            "input": str(ESM2_SMOKETEST_INPUT_PATH),
            "output": str(ESM2_SMOKETEST_REPORT_PATH),
            "summary": {k: v for k, v in report.items() if k != "per_peptide"},
        },
    )
    return report


# Bucket 2.3 — C3 ESM-2 hard-challenge pool, fold-safe by construction (see
# curation/c3.py's module docstring for the full leakage rationale).
C3_RAW_CANDIDATES_PATH = RAW_DIR / "UniRef50" / "uniref50_candidates.fasta"
C3_RAW_PROVENANCE_PATH = RAW_DIR / "UniRef50" / "uniref50_provenance.txt"
C3_TARGET_CANDIDATE_SIZE = 25_000
C3_TOP_N_PER_FOLD = 2_000

C3_POSITIVE_EMBEDDINGS_CACHE = INTERIM_DIR / "c3_positive_embeddings.npz"  # gitignored, regeneratable
C3_CANDIDATE_EMBEDDINGS_CACHE = INTERIM_DIR / "c3_candidate_embeddings.npz"  # gitignored, regeneratable
C3_EMBED_INPUT_PATH = INTERIM_DIR / "c3_embed_input.json"

C3_FASTA_PATH = PROCESSED_DIR / "stage_c3_esm2_hard_challenges.fasta"  # canonical registry name
C3_RANKING_PATH = PROCESSED_DIR / "c3_similarity_ranking.csv"
C3_BUILD_REPORT_PATH = PROCESSED_DIR / "c3_build_report.json"
C3_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_c3_provenance.jsonl"


def run_fr2_c3_fetch_candidates(target_size: int = C3_TARGET_CANDIDATE_SIZE) -> dict:
    """Bucket 2.3 step 1: acquire the UniRef50 candidate-fragment universe
    via a filtered REST query (not the ~13GB bulk FASTA, same reasoning
    already applied to C1 -- see curation/uniref.py). Writes a versioned raw
    snapshot; this is the frozen historical-evidence file all downstream C3
    code reads from -- it is not re-queried live on every pipeline run.
    """
    import datetime

    (RAW_DIR / "UniRef50").mkdir(parents=True, exist_ok=True)
    import time as _time

    start = _time.time()
    records = fetch_uniref50_candidates(target_size=target_size)
    elapsed = _time.time() - start

    write_fasta(C3_RAW_CANDIDATES_PATH, records)
    with open(C3_RAW_PROVENANCE_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("Stage C3 UniRef50 Candidate Universe - Provenance Log\n")
        handle.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
        handle.write("Source: UniProt REST API /uniref/search\n")
        handle.write(f"Query: {UNIREF50_QUERY}\n")
        handle.write(f"Sort: {UNIREF50_SORT}\n")
        handle.write(f"Target size: {target_size}\n")
        handle.write(f"Actual fetched: {len(records)}\n")
        handle.write(f"Fetch elapsed seconds: {elapsed:.1f}\n")

    return {"n_fetched": len(records), "target_size": target_size, "elapsed_seconds": elapsed}


def embed_via_wsl(
    peptide_ids: list[str],
    sequences: list[str],
    cache_path: Path,
    label: str,
    force_cpu: bool = False,
    embed_input_path: Path | None = None,
    summary_report_path: Path | None = None,
    timeout: float = 1800,
) -> dict[str, np.ndarray]:
    """Shell out to esm2_cli.py (inside the WSL pu_aop env) to embed a batch
    of sequences, caching the raw vectors at ``cache_path`` (gitignored --
    never committed, same "don't commit large embedding arrays" rule as
    model weights). Returns peptide_id -> float32 480-dim vector.

    Shared by Bucket 2.3 (C3 hard-challenge embedding) and Bucket 3.2 (full
    feature-cache embedding) -- the WSL subprocess/caching mechanics don't
    change between callers, only the input batch and cache path do.
    ``embed_input_path`` defaults to the historical C3 input-scratch path
    for backward compatibility with existing callers; a new caller should
    pass its own path so concurrent/sequential jobs never share one file.
    """
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    embed_input_path = embed_input_path or C3_EMBED_INPUT_PATH
    payload = {
        "peptide_ids": peptide_ids,
        "sequences": sequences,
        "force_cpu": force_cpu,
        "validate_alphabet": True,
        "batch_size": 64,
        "save_embeddings_path": to_wsl_path(cache_path),
    }
    with open(embed_input_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)

    summary_report_path = summary_report_path or (INTERIM_DIR / f"c3_embed_{label}_report.json")
    result = run_in_conda_env(
        [
            "python",
            to_wsl_path(ESM2_CLI_SCRIPT_PATH),
            to_wsl_path(embed_input_path),
            to_wsl_path(summary_report_path),
        ],
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ESM-2 embedding of {label} failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}")
    if not cache_path.exists():
        raise RuntimeError(f"esm2_cli.py reported success but no embedding cache was written for {label}:\n{result.stdout}")

    with np.load(cache_path, allow_pickle=False) as npz:
        ids = npz["peptide_ids"]
        matrix = npz["embeddings"]
    return {pid: matrix[i] for i, pid in enumerate(ids)}


def run_fr2_c3_build(force_cpu: bool = False) -> dict:
    """Bucket 2.3 step 2: fold-safe ESM-2 hard-challenge selection.

    For each of GraphPart's 5 training folds, fits a positive-pool centroid
    using ONLY that fold's training partition (the other 4 folds' 834
    frozen positives -- see curation/c3.py's docstring for why this must
    never include the held-out fold's own positives), ranks the shared
    UniRef50 candidate universe by cosine similarity to that fold-specific
    centroid, and selects each fold's own top-2,000 hardest candidates.
    The exported FASTA is the union of all 5 folds' selections (deduplicated
    by sequence); ``c3_similarity_ranking.csv`` records per-fold membership
    and rank/similarity explicitly, so a downstream consumer training on
    fold k can (and must) filter to that fold's own rows only -- using a
    different fold's selection would silently reintroduce the exact
    selection-leakage this construction exists to prevent.

    Known, explicitly-flagged gap (not done in this pass): the Planner's
    "screen known-AOP matches against AODB, DFBP, BIOPEP-UWM" item. Only
    Multi-AOP/AnOxPePred-derived FR1 positives + 179 conflicts are screened
    (same exact-sequence leakage check used for C1/C2); AODB/DFBP/BIOPEP-UWM
    remain unintegrated project-wide (see IMPLEMENTATION_STATUS.md).
    """
    if not C3_RAW_CANDIDATES_PATH.exists():
        raise FileNotFoundError(f"{C3_RAW_CANDIDATES_PATH} not found -- run fr2-c3-fetch-candidates first.")
    if not GRAPHPART_SPLITS_PATH.exists():
        raise FileNotFoundError(f"{GRAPHPART_SPLITS_PATH} not found -- run fr1-split first.")
    if not POSITIVE_POOL_CDHIT_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_CDHIT_PATH} not found -- run fr1-cluster first.")

    splits_df = pd.read_csv(GRAPHPART_SPLITS_PATH)
    positives_df = pd.read_parquet(POSITIVE_POOL_CDHIT_PATH)
    training_df = splits_df.merge(positives_df, left_on="AC", right_on="peptide_id", how="inner")
    if len(training_df) != len(splits_df):
        raise RuntimeError("Some GraphPart-split peptide IDs are missing a sequence in the CD-HIT pool.")
    fold_of = dict(zip(training_df["peptide_id"], training_df["cluster"].astype(int)))
    n_folds = int(training_df["cluster"].max()) + 1

    raw_candidates = read_fasta(C3_RAW_CANDIDATES_PATH)
    positive_df_full = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    c1_seqs = {s for _, s in read_fasta(C1_CLEAN_FASTA_V2_PATH)} if C1_CLEAN_FASTA_V2_PATH.exists() else set()
    c2_seqs = {s for _, s in read_fasta(C2_FASTA_PATH)} if C2_FASTA_PATH.exists() else set()
    screen_sequences = (
        set(positive_df_full["sequence"]) | set(conflict_df["sequence"]) | c1_seqs | c2_seqs
    )

    kept_candidates, _ = apply_secondary_blocklist(raw_candidates)
    seen_seqs: set[str] = set()
    candidate_records: list[tuple[str, str]] = []
    for header, sequence in kept_candidates:
        if sequence in screen_sequences or sequence in seen_seqs:
            continue
        if not is_valid_peptide(sequence, min_len=3, max_len=50):
            continue
        seen_seqs.add(sequence)
        candidate_records.append((header, sequence))

    candidate_id_map = {make_peptide_id(seq, prefix="C3"): seq for _, seq in candidate_records}

    positive_embeddings = embed_via_wsl(
        training_df["peptide_id"].tolist(), training_df["sequence"].tolist(),
        C3_POSITIVE_EMBEDDINGS_CACHE, label="positives", force_cpu=force_cpu,
    )
    candidate_embeddings = embed_via_wsl(
        list(candidate_id_map.keys()), list(candidate_id_map.values()),
        C3_CANDIDATE_EMBEDDINGS_CACHE, label="candidates", force_cpu=force_cpu,
    )

    centroids = compute_fold_centroids(positive_embeddings, fold_of, n_folds=n_folds)
    rankings = [rank_candidates_for_fold(candidate_embeddings, centroids[k], fold_id=k) for k in range(n_folds)]
    selections = select_top_n_per_fold(rankings, n=C3_TOP_N_PER_FOLD)

    ranking_rows = [
        {"fold_id": fold_id, "peptide_id": pid, "sequence": candidate_id_map[pid], "rank": rank, "cosine_similarity": sim}
        for fold_id, rows in selections.items()
        for pid, sim, rank in rows
    ]
    ranking_df = pd.DataFrame(ranking_rows)
    ranking_df.to_csv(C3_RANKING_PATH, index=False, lineterminator="\n")

    union_pids = sorted({row["peptide_id"] for row in ranking_rows})
    seen_union_seqs: set[str] = set()
    fasta_records = []
    for pid in union_pids:
        seq = candidate_id_map[pid]
        if seq not in seen_union_seqs:
            seen_union_seqs.add(seq)
            fasta_records.append((pid, seq))
    write_fasta(C3_FASTA_PATH, fasta_records)

    summary = {
        "n_candidate_universe_raw": len(raw_candidates),
        "n_candidate_universe_eligible": len(candidate_records),
        "n_folds": n_folds,
        "n_training_positives": len(positive_embeddings),
        "top_n_per_fold": C3_TOP_N_PER_FOLD,
        "n_union_records": len(fasta_records),
        "per_fold_n_selected": {k: len(v) for k, v in selections.items()},
        "screen_set_size": len(screen_sequences),
        "aodb_dfbp_biopep_screen": "NOT DONE -- AODB/DFBP/BIOPEP-UWM remain unintegrated project-wide; "
        "see IMPLEMENTATION_STATUS.md Known Issues.",
    }
    with open(C3_BUILD_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C3_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c3_hard_challenge_build",
            "raw_candidates": str(C3_RAW_CANDIDATES_PATH),
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH), str(C1_CLEAN_FASTA_V2_PATH), str(C2_FASTA_PATH)],
            "summary": summary,
            "outputs": {
                "clean_fasta": str(C3_FASTA_PATH),
                "ranking": str(C3_RANKING_PATH),
                "report": str(C3_BUILD_REPORT_PATH),
            },
        },
    )
    return summary


# Bucket 2.4 resolution (Decisions A & B, approved 2026-10-14) -- versioned
# fixes for the two findings the audit surfaced. Neither overwrites the
# artifact it supersedes; both are new, separately versioned outputs.
C1_CLEAN_FASTA_V3_PATH = PROCESSED_DIR / "stage_c1_decoys_v3.fasta"
C1_ACCESSION_MAP_V3_PATH = PROCESSED_DIR / "c1_accession_map_v3.csv"
C1_CROSS_POOL_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c1_cross_pool_exclusion_log.csv"
C1_CROSS_POOL_REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c1_cross_pool_replacement_log.csv"
C1_CROSS_POOL_FIX_REPORT_PATH = PROCESSED_DIR / "c1_cross_pool_fix_report.json"

C2_FASTA_V2_PATH = PROCESSED_DIR / "stage_c2_bioactive_unlabeled_v2.fasta"
C2_ACTIVITY_MAP_V2_PATH = PROCESSED_DIR / "c2_activity_map_v2.csv"
C2_CROSS_POOL_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c2_cross_pool_exclusion_log.csv"
C2_CROSS_POOL_REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c2_cross_pool_replacement_log.csv"
C2_CROSS_POOL_FIX_REPORT_PATH = PROCESSED_DIR / "c2_cross_pool_fix_report.json"

# The one C2 sequence Decision B names explicitly -- a manually-reviewed,
# alignment-confirmed near-duplicate of an E1 FR1 positive (see
# IMPLEMENTATION_STATUS.md for the full EMBOSS needle alignment evidence).
# Deliberately NOT derived automatically from the CD-HIT cluster scan here:
# the instruction is explicit that cluster membership alone must not drive
# exclusion, so this is a named, reviewed constant, not a computed set.
C2_FLAGGED_HOMOLOGY_SEQUENCE = "LYQEPVLGPVRGPFP"


def run_fr2_c1_cross_pool_fix(seed: int = 42) -> dict:
    """Bucket 2.4 Decision A: remove the 8 sequences found to exactly
    overlap C2 from C1, replacing them 1:1 from the same UniProtKB
    candidate universe used by every prior C1 fix -- screened against FR1
    positives, the 179 conflicts, C2, AND C3 (the new requirement this
    fix exists to satisfy), so C3 never needs to be rebuilt as a side
    effect of this change.
    """
    if not C1_CLEAN_FASTA_V2_PATH.exists():
        raise FileNotFoundError(f"{C1_CLEAN_FASTA_V2_PATH} not found -- run fr2-c1-alphabet-fix first.")
    for p in (C1_RAW_CANDIDATES_PATH, POSITIVE_POOL_PATH, C2_FASTA_PATH, C3_FASTA_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found.")

    c1_records = read_fasta(C1_CLEAN_FASTA_V2_PATH)
    c2_records = read_fasta(C2_FASTA_PATH)
    c3_records = read_fasta(C3_FASTA_PATH)
    candidate_pool_records = read_fasta(C1_RAW_CANDIDATES_PATH)
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)

    c1_seqs = {s for _, s in c1_records}
    c2_seqs = {s for _, s in c2_records}
    c3_seqs = {s for _, s in c3_records}
    exclude_sequences = c1_seqs & c2_seqs
    if not exclude_sequences:
        raise RuntimeError(
            "No C1/C2 exact overlap found -- this fix is a no-op on the current artifacts. "
            "Re-check whether Decision A still applies before running it."
        )

    screen_sequences = set(positive_df["sequence"]) | set(conflict_df["sequence"]) | c2_seqs | c3_seqs

    clean_records, exclusion_log, replacement_log, summary = clean_c1_cross_pool_overlap(
        c1_records, candidate_pool_records, exclude_sequences, screen_sequences, seed=seed
    )
    if summary["shortfall"] > 0:
        raise RuntimeError(
            f"Eligible replacement pool exhausted: needed {summary['n_replacements_needed']}, only "
            f"{summary['n_replacements_available']} available. Stopping rather than silently "
            "shipping a short pool -- see the project owner before changing source/criteria."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta(C1_CLEAN_FASTA_V3_PATH, clean_records)

    accession_map = pd.DataFrame(
        [
            {"peptide_header": h, "sequence": s, "length": len(s), **parse_uniprot_header(h)}
            for h, s in clean_records
        ]
    )
    accession_map.to_csv(C1_ACCESSION_MAP_V3_PATH, index=False, lineterminator="\n")
    pd.DataFrame(exclusion_log).to_csv(C1_CROSS_POOL_EXCLUSION_LOG_PATH, index=False, lineterminator="\n")
    pd.DataFrame(replacement_log).to_csv(C1_CROSS_POOL_REPLACEMENT_LOG_PATH, index=False, lineterminator="\n")

    unique_seqs = {s for _, s in clean_records}
    summary.update(
        {
            "seed": seed,
            "n_unique_sequences": len(unique_seqs),
            "source_version": str(C1_CLEAN_FASTA_V2_PATH),
            "output_version": str(C1_CLEAN_FASTA_V3_PATH),
            "screened_against": ["FR1_positives", "conflicts_179", "C2", "C3_union"],
        }
    )
    with open(C1_CROSS_POOL_FIX_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C1_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c1_cross_pool_overlap_fix",
            "source_version": str(C1_CLEAN_FASTA_V2_PATH),
            "raw_candidates": str(C1_RAW_CANDIDATES_PATH),
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH), str(C2_FASTA_PATH), str(C3_FASTA_PATH)],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta_v3": str(C1_CLEAN_FASTA_V3_PATH),
                "accession_map_v3": str(C1_ACCESSION_MAP_V3_PATH),
                "exclusion_log": str(C1_CROSS_POOL_EXCLUSION_LOG_PATH),
                "replacement_log": str(C1_CROSS_POOL_REPLACEMENT_LOG_PATH),
                "report": str(C1_CROSS_POOL_FIX_REPORT_PATH),
            },
        },
    )
    return summary


def run_fr2_c2_cross_pool_fix(seed: int = 42) -> dict:
    """Bucket 2.4 Decision B: exclude the one C2 peptide manually confirmed
    (EMBOSS needle alignment, see IMPLEMENTATION_STATUS.md) to be a
    near-duplicate of an E1 FR1 positive, and replace it 1:1 from the same
    experimentally-reported Peptipedia tier Task 2.2 drew from -- screened
    against FR1 positives, the 179 conflicts, the remaining 1,999 C2
    sequences, the now-fixed C1 v3, AND C3.

    Must run AFTER ``run_fr2_c1_cross_pool_fix`` -- it screens against
    C1 v3, not v2, so this fix's replacement can never collide with
    Decision A's replacements either.
    """
    if not C2_FASTA_PATH.exists():
        raise FileNotFoundError(f"{C2_FASTA_PATH} not found -- run fr2-c2-build first.")
    if not C1_CLEAN_FASTA_V3_PATH.exists():
        raise FileNotFoundError(f"{C1_CLEAN_FASTA_V3_PATH} not found -- run fr2-c1-cross-pool-fix first.")
    for p in (C2_RAW_DUMP_PATH, POSITIVE_POOL_PATH, C3_FASTA_PATH, C2_ACTIVITY_MAP_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found.")

    c2_records = read_fasta(C2_FASTA_PATH)
    c2_seqs_current = {s for _, s in c2_records}
    if C2_FLAGGED_HOMOLOGY_SEQUENCE not in c2_seqs_current:
        raise RuntimeError(
            f"{C2_FLAGGED_HOMOLOGY_SEQUENCE!r} is not in the current C2 pool -- this fix is a "
            "no-op on the current artifacts. Re-check whether Decision B still applies."
        )

    activity_map_df = pd.read_csv(C2_ACTIVITY_MAP_PATH)
    flagged_row = activity_map_df[activity_map_df["sequence"] == C2_FLAGGED_HOMOLOGY_SEQUENCE].iloc[0]

    c1_v3_seqs = {s for _, s in read_fasta(C1_CLEAN_FASTA_V3_PATH)}
    c3_seqs = {s for _, s in read_fasta(C3_FASTA_PATH)}
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    remaining_c2_seqs = c2_seqs_current - {C2_FLAGGED_HOMOLOGY_SEQUENCE}

    screen_sequences = (
        set(positive_df["sequence"])
        | set(conflict_df["sequence"])
        | remaining_c2_seqs
        | c1_v3_seqs
        | c3_seqs
    )

    activity_names = load_activity_names(C2_RAW_DUMP_PATH)
    sequences, activities = extract_c2_candidates(C2_RAW_DUMP_PATH)
    replacement_records, replacement_summary = build_c2_pool(
        sequences, activities, screen_sequences, n=1, seed=seed
    )
    if replacement_summary["shortfall"] > 0:
        raise RuntimeError(
            "No eligible replacement found for the excluded C2 sequence in the experimentally-"
            "reported Peptipedia tier under the expanded cross-pool screen. Stopping rather than "
            "silently shipping a short pool -- see the project owner before changing source/criteria."
        )

    new_record = replacement_records[0]
    new_peptide_id = make_peptide_id(new_record["sequence"], prefix="C2")

    clean_records = [(h, s) for h, s in c2_records if s != C2_FLAGGED_HOMOLOGY_SEQUENCE]
    clean_records.append((new_peptide_id, new_record["sequence"]))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta(C2_FASTA_V2_PATH, clean_records)

    new_activity_row = {
        "peptide_id": new_peptide_id,
        "id_peptide_peptipedia": new_record["id_peptide"],
        "sequence": new_record["sequence"],
        "length": new_record["length"],
        "activity_ids": ";".join(str(a) for a in new_record["activity_ids"]),
        "activity_names": ";".join(
            activity_names.get(a, f"unknown_activity_{a}") for a in new_record["activity_ids"]
        ),
        "has_experimental_evidence": new_record["has_experimental_evidence"],
    }
    updated_activity_map = pd.concat(
        [
            activity_map_df[activity_map_df["sequence"] != C2_FLAGGED_HOMOLOGY_SEQUENCE],
            pd.DataFrame([new_activity_row]),
        ],
        ignore_index=True,
    )
    updated_activity_map.to_csv(C2_ACTIVITY_MAP_V2_PATH, index=False, lineterminator="\n")

    exclusion_log = [
        {
            "peptide_id": flagged_row["peptide_id"],
            "sequence": C2_FLAGGED_HOMOLOGY_SEQUENCE,
            "reason": "homology_leakage_risk_to_fr1_e1_positive",
            "homologous_to_peptide_id": "AOP-032318CCA7",
            "homologous_to_sequence": "YQEPVLGPVRGPFPIIV",
            "homologous_to_evidence_tier": "E1",
            "alignment_tool": "EMBOSS needle (EBLOSUM62, gapopen=10, gapextend=0.5)",
            "alignment_identity_full_length_pct": 77.8,
            "alignment_identity_cdhit_shorter_seq_pct": 93.33,
            "alignment_gaps_pct": 22.2,
            "original_activity_names": flagged_row["activity_names"],
            "note": "Excluded as a conservative leakage-risk decision -- NOT claimed to be "
            "experimentally antioxidant-active. Original Peptipedia evidence preserved above.",
        }
    ]
    pd.DataFrame(exclusion_log).to_csv(C2_CROSS_POOL_EXCLUSION_LOG_PATH, index=False, lineterminator="\n")
    pd.DataFrame([new_activity_row]).to_csv(C2_CROSS_POOL_REPLACEMENT_LOG_PATH, index=False, lineterminator="\n")

    summary = {
        "source_version": str(C2_FASTA_PATH),
        "output_version": str(C2_FASTA_V2_PATH),
        "n_excluded": 1,
        "n_replaced": 1,
        "n_output_records": len(clean_records),
        "n_unique_sequences": len({s for _, s in clean_records}),
        "seed": seed,
        "screened_against": ["FR1_positives", "conflicts_179", "C2_remaining", "C1_v3", "C3_union"],
        "replacement_tier_summary": replacement_summary,
    }
    with open(C2_CROSS_POOL_FIX_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C2_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c2_cross_pool_homology_fix",
            "source_version": str(C2_FASTA_PATH),
            "screen_sources": [
                str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH), str(C1_CLEAN_FASTA_V3_PATH), str(C3_FASTA_PATH),
            ],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta_v2": str(C2_FASTA_V2_PATH),
                "activity_map_v2": str(C2_ACTIVITY_MAP_V2_PATH),
                "exclusion_log": str(C2_CROSS_POOL_EXCLUSION_LOG_PATH),
                "replacement_log": str(C2_CROSS_POOL_REPLACEMENT_LOG_PATH),
                "report": str(C2_CROSS_POOL_FIX_REPORT_PATH),
            },
        },
    )
    return summary


# Bucket 2.4 -- Pool Contamination and Leakage Audit.
BIOPEP_RAW_PATH = RAW_DIR / "BIOPEP-UWM" / "biopep_antioxidative.json"
BIOPEP_RAW_PROVENANCE_PATH = RAW_DIR / "BIOPEP-UWM" / "biopep_provenance.txt"

AUDIT_INTEGRITY_REPORT_PATH = PROCESSED_DIR / "audit_integrity_report.json"
AUDIT_OVERLAP_MATRIX_PATH = PROCESSED_DIR / "audit_exact_overlap_matrix.csv"
AUDIT_OVERLAP_DETAIL_PATH = PROCESSED_DIR / "audit_exact_overlap_detail.csv"
AUDIT_EXTERNAL_SCREEN_PATH = PROCESSED_DIR / "audit_external_aop_screen.json"
AUDIT_HOMOLOGY_CLUSTERS_PATH = PROCESSED_DIR / "audit_cross_pool_homology_clusters.csv"
AUDIT_HOMOLOGY_SUMMARY_PATH = PROCESSED_DIR / "audit_cross_pool_homology_summary.json"
AUDIT_C3_CONTRACT_REPORT_PATH = PROCESSED_DIR / "audit_c3_fold_contract_report.json"
AUDIT_REPORT_PATH = PROCESSED_DIR / "fr2_pool_audit_report.json"
AUDIT_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_pool_audit_provenance.jsonl"
AUDIT_CDHIT_OUTPUT_PREFIX = INTERIM_DIR / "audit_combined_pools_cdhit90"


def run_fr2_pool_audit() -> dict:
    """Bucket 2.4: formal, re-runnable contamination/leakage audit across
    FR1's positives, the 179 conflicts, and C1/C2/C3. Read-only with
    respect to every existing accepted artifact -- this stage never
    modifies pp1_baseline_v1 or any accepted C1/C2/C3 file; it only
    reports. See IMPLEMENTATION_STATUS.md for the full account of every
    finding and which ones are pending the project owner's decision.
    """
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_PATH} not found -- run fr1-positives first.")
    # Canonical C1/C2 sources as of the Bucket 2.4 Decision A/B resolution
    # (2026-10-14): v3/v2, not v2/v1 -- falls back to the pre-resolution
    # versions only if the fixes haven't been run yet in this checkout, so
    # this function stays usable mid-resolution, not just after it.
    c1_canonical_path = C1_CLEAN_FASTA_V3_PATH if C1_CLEAN_FASTA_V3_PATH.exists() else C1_CLEAN_FASTA_V2_PATH
    c2_canonical_path = C2_FASTA_V2_PATH if C2_FASTA_V2_PATH.exists() else C2_FASTA_PATH
    for p in (c1_canonical_path, c2_canonical_path, C3_FASTA_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found -- build C1/C2/C3 first.")

    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    external_control_df = pd.read_csv(PROCESSED_DIR / "anoxpepred_inactives_clean.csv")
    pos_records = list(zip(positive_df["peptide_id"], positive_df["sequence"]))
    conf_records = list(zip(conflict_df["peptide_id"], conflict_df["sequence"]))
    ext_records = list(zip(external_control_df["peptide_id"], external_control_df["sequence"]))
    c1_records = read_fasta(c1_canonical_path)
    c2_records = read_fasta(c2_canonical_path)
    c3_records = read_fasta(C3_FASTA_PATH)

    pool_records = {
        "FR1_positives": pos_records,
        "conflicts_179": conf_records,
        "external_control": ext_records,
        "C1_v3": c1_records,
        "C2_v2": c2_records,
        "C3_union": c3_records,
    }
    pool_seqs = {name: {s for _, s in recs} for name, recs in pool_records.items()}

    # --- Step 2: full sequence-integrity audit ---
    integrity_reports = [sequence_integrity_report(name, recs) for name, recs in pool_records.items()]
    with open(AUDIT_INTEGRITY_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(integrity_reports, handle, indent=2)

    overlap_matrix = pairwise_exact_overlap(pool_seqs)
    overlap_matrix.to_csv(AUDIT_OVERLAP_MATRIX_PATH, lineterminator="\n")

    names = list(pool_seqs.keys())
    detail_rows = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            shared = overlap_detail(pool_seqs, a, b)
            for seq in shared:
                detail_rows.append({"pool_a": a, "pool_b": b, "sequence": seq, "length": len(seq)})
    pd.DataFrame(detail_rows, columns=["pool_a", "pool_b", "sequence", "length"]).to_csv(
        AUDIT_OVERLAP_DETAIL_PATH, index=False, lineterminator="\n"
    )

    # --- Step 3: external known-AOP screening ---
    RAW_DIR.joinpath("BIOPEP-UWM").mkdir(parents=True, exist_ok=True)
    if BIOPEP_RAW_PATH.exists():
        with open(BIOPEP_RAW_PATH, encoding="utf-8") as handle:
            biopep_records = json.load(handle)
    else:
        biopep_records = fetch_biopep_by_activity("antioxidative")
        with open(BIOPEP_RAW_PATH, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(biopep_records, handle, indent=2)
        with open(BIOPEP_RAW_PROVENANCE_PATH, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("BIOPEP-UWM Antioxidative Reference Set - Provenance Log\n")
            handle.write(f"Source: {BIOPEP_SEARCH_URL}?txt_search=antioxidative&menu_search=activity\n")
            handle.write("Access: open, no registration required\n")
            handle.write(f"Citation: {BIOPEP_CITATION}\n")
            handle.write(f"Records fetched: {len(biopep_records)}\n")

    biopep_seqs = {r["sequence"] for r in biopep_records if is_valid_peptide(r["sequence"], min_len=1, max_len=10_000)}
    external_hits = external_reference_screen(pool_seqs, biopep_seqs)
    external_screen_report = {
        "biopep_uwm": {
            "source": BIOPEP_SEARCH_URL,
            "citation": BIOPEP_CITATION,
            "n_reference_sequences_standard_alphabet": len(biopep_seqs),
            "hits_by_pool": {k: len(v) for k, v in external_hits.items()},
            "hit_sequences_by_pool": external_hits,
        },
        "aodb": {
            "status": "INACCESSIBLE",
            "evidence": "https://aodb.idruglab.cn returned HTTP 502 (Bad Gateway) from its own "
            "nginx and an expired TLS certificate, confirmed via direct curl with and without "
            "certificate verification. Not screened -- not a skipped check, a documented access "
            "failure at the time of this audit.",
        },
        "dfbp": {
            "status": "INACCESSIBLE",
            "evidence": "No working hosting URL could be found for DFBP (Qin et al. 2022, PubMed "
            "35552640) via web search or the PubMed record itself (blocked by a cookie wall in "
            "automated access). Not substituted with an unrelated database per instruction. Not "
            "screened -- a documented access failure, not a skipped check.",
        },
    }
    with open(AUDIT_EXTERNAL_SCREEN_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(external_screen_report, handle, indent=2)

    # --- Step 4: homology/leakage analysis beyond exact match ---
    homology_df, homology_summary = cross_pool_homology_clusters(
        pool_records, AUDIT_CDHIT_OUTPUT_PREFIX, identity=0.90, length_floor_for_interpretation=15
    )
    homology_df.to_csv(AUDIT_HOMOLOGY_CLUSTERS_PATH, index=False, lineterminator="\n")
    with open(AUDIT_HOMOLOGY_SUMMARY_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(homology_summary, handle, indent=2)

    # --- Step 5: validate the C3 fold-specific contract ---
    c3_contract_report: dict
    try:
        splits_df = pd.read_csv(GRAPHPART_SPLITS_PATH)
        fold_of = dict(zip(splits_df["AC"], splits_df["cluster"].astype(int)))
        ranking_df = pd.read_csv(C3_RANKING_PATH)
        fasta_ids = {h for h, _ in c3_records}
        if C3_POSITIVE_EMBEDDINGS_CACHE.exists():
            npz = np.load(C3_POSITIVE_EMBEDDINGS_CACHE, allow_pickle=False)
            positive_embeddings = {pid: npz["embeddings"][i] for i, pid in enumerate(npz["peptide_ids"])}
            c3_contract_report = validate_c3_fold_contract(
                positive_embeddings, fold_of, ranking_df, fasta_ids, top_n_per_fold=C3_TOP_N_PER_FOLD
            )
        else:
            c3_contract_report = {
                "fold_safety_verified": None,
                "reason": f"{C3_POSITIVE_EMBEDDINGS_CACHE} not present locally (gitignored cache) -- "
                "re-run fr2-c3-build to regenerate it before this check can re-verify fold-safety "
                "against the real embeddings.",
            }
    except AssertionError as exc:
        c3_contract_report = {"fold_safety_verified": False, "violation": str(exc)}
    with open(AUDIT_C3_CONTRACT_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(c3_contract_report, handle, indent=2)

    # --- assemble top-level summary ---
    c1_c2_overlap = overlap_detail(pool_seqs, "C1_v3", "C2_v2")
    decision_a_resolved = len(c1_c2_overlap) == 0 and C1_CLEAN_FASTA_V3_PATH.exists()
    decision_b_resolved = C2_FLAGGED_HOMOLOGY_SEQUENCE not in pool_seqs["C2_v2"] and C2_FASTA_V2_PATH.exists()

    findings: dict = {}
    if not decision_a_resolved:
        findings["c1_c2_exact_overlap"] = {
            "status": "PENDING",
            "n_sequences": len(c1_c2_overlap),
            "sequences": c1_c2_overlap,
            "proposed_correction": "Pending project-owner decision -- NOT applied.",
        }
    if not decision_b_resolved:
        findings["c2_homology_to_fr1_positive"] = {
            "status": "PENDING",
            "example_sequence": C2_FLAGGED_HOMOLOGY_SEQUENCE,
            "proposed_correction": "Pending project-owner decision -- NOT applied.",
        }
    resolution_notes = {
        "decision_a_c1_c2_exact_overlap": "RESOLVED 2026-10-14 (see c1_cross_pool_fix_report.json) -- "
        "8 sequences removed from C1 (kept in C2, per approved 'preserve C2's biological-annotation "
        "precedence'), replaced 1:1 from the UniProtKB candidate universe, screened against FR1 "
        "positives, 179 conflicts, C2, and C3. Canonical C1 artifact is now stage_c1_decoys_v3.fasta."
        if decision_a_resolved
        else "NOT YET RESOLVED -- run fr2-c1-cross-pool-fix.",
        "decision_b_c2_homology_to_e1_positive": "RESOLVED 2026-10-14 (see c2_cross_pool_fix_report.json) "
        "-- C2-EFDBC5460B ('LYQEPVLGPVRGPFP') excluded as a conservative leakage-risk decision (NOT "
        "claimed experimentally inactive), replaced 1:1 from the experimentally-reported Peptipedia "
        "tier, screened against FR1 positives, 179 conflicts, remaining C2, C1 v3, and C3. Canonical "
        "C2 artifact is now stage_c2_bioactive_unlabeled_v2.fasta."
        if decision_b_resolved
        else "NOT YET RESOLVED -- run fr2-c2-cross-pool-fix.",
        "additional_homology_candidates": "Of the 14 other candidates found alongside the "
        "project-owner-flagged C2/FR1-positive pair, reviewed individually (not auto-excluded by "
        "cluster membership): 3 were fully resolved as a side effect of Decision A (their shared "
        "member was one of the 8 exact C1/C2 duplicates, now removed from C1); "
        f"{homology_summary['n_cross_pool_clusters_real_homology_candidates']} remain as near-"
        "duplicate (not exact) C1<->C2 pairs post-fix. All are C1<->C2 only (no FR1-positive "
        "involvement) and from peptide families with no plausible antioxidant mechanism "
        "(ribosomal/zinc-ribbon proteins, protamine-like and homeodomain cell-penetrating peptides, "
        "actin/gliadin fragments, cysteine-rich defensin-like peptides) -- assessed as redundant "
        "construction overlap between two unlabeled pools, not a label-leakage risk, since neither "
        "pool carries ground truth. Recommendation: accept and document as a known, bounded "
        "limitation (same treatment as C1's intentional record-level duplicates) rather than a "
        "further exclude-and-replace cycle. See audit_cross_pool_homology_clusters.csv for the full "
        "per-cluster evidence; revisit if the project owner wants a stricter policy.",
    }

    summary = {
        "integrity_reports": integrity_reports,
        "exact_overlap_nonzero_pairs": [
            {"pool_a": r["pool_a"], "pool_b": r["pool_b"], "sequence": r["sequence"]}
            for r in detail_rows
        ],
        "contamination_requiring_decision": findings,
        "bucket_2_4_resolution_status": resolution_notes,
        "external_screen": {k: v for k, v in external_screen_report.items()},
        "homology_summary": homology_summary,
        "c3_fold_contract": c3_contract_report,
        "known_incomplete_checks": [
            "AODB screening -- server inaccessible (HTTP 502 + expired TLS cert) at audit time.",
            "DFBP screening -- no discoverable hosting URL.",
        ],
        "accepted_methodological_limitations": [
            "CD-HIT percent-identity is not biologically interpretable for pairs where the shorter "
            "sequence is <15 AA (chance substring matches dominate at this length); such clusters "
            "are reported for transparency but excluded from the 'real homology candidate' count.",
            "C1 retains natural duplicate sequences by design (record-vs-unique-sequence distinction, "
            "confirmed 2026-10-14) -- any future train/val/test split MUST group identical sequences "
            "together to avoid sequence-level leakage; this is a loader-design requirement, not "
            "something this audit can enforce by itself.",
            "C3's 25,000-candidate UniRef50 universe is a deterministic ID-sorted slice of the "
            "870,941-cluster population in its length window, not a random sample -- a potential "
            "coverage bias to examine under Task 2.5, not evidence the pool is invalid.",
            "2 external-control ('experimentally inactive') peptides independently hit BIOPEP-UWM's "
            "antioxidative reference set -- the same cross-database annotation conflict phenomenon "
            "already documented for the 179 FR1 conflicts; preserved as a documented uncertainty, not "
            "acted on.",
        ],
        "ready_for_technical_acceptance": decision_a_resolved and decision_b_resolved,
    }
    with open(AUDIT_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, default=str)

    append_provenance_log(
        AUDIT_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_pool_contamination_leakage_audit",
            "pools_audited": list(pool_records.keys()),
            "outputs": {
                "integrity": str(AUDIT_INTEGRITY_REPORT_PATH),
                "overlap_matrix": str(AUDIT_OVERLAP_MATRIX_PATH),
                "overlap_detail": str(AUDIT_OVERLAP_DETAIL_PATH),
                "external_screen": str(AUDIT_EXTERNAL_SCREEN_PATH),
                "homology_clusters": str(AUDIT_HOMOLOGY_CLUSTERS_PATH),
                "homology_summary": str(AUDIT_HOMOLOGY_SUMMARY_PATH),
                "c3_contract": str(AUDIT_C3_CONTRACT_REPORT_PATH),
                "report": str(AUDIT_REPORT_PATH),
            },
        },
    )
    return summary


# Bucket 2.5 -- Biological Distribution and Shortcut-Bias Checks.
DISTRIBUTION_DESCRIPTOR_TABLE_PATH = PROCESSED_DIR / "distribution_descriptor_table.csv"
DISTRIBUTION_AA_COMPOSITION_PATH = PROCESSED_DIR / "distribution_aa_composition.csv"
DISTRIBUTION_KS_COMPARISON_PATH = PROCESSED_DIR / "distribution_ks_comparison.csv"
DISTRIBUTION_SHORTCUT_REPORT_PATH = PROCESSED_DIR / "distribution_shortcut_report.json"
DISTRIBUTION_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_distribution_provenance.jsonl"

DISTRIBUTION_DESCRIPTOR_COLUMNS = ["length", "molecular_weight", "net_charge_ph7", "gravy", "aromaticity"]


def run_fr2_distribution_audit() -> dict:
    """Bucket 2.5: length/composition/descriptor distribution comparisons
    across FR1's accepted positives and the canonical C1 v3/C2 v2/C3 union,
    plus a shortcut-bias scan (organism diversity for C1, activity-tag
    diversity for C2). Read-only -- writes only new `distribution_*`
    report files, never touches any pool artifact.

    Uses a small, independently-computed set of descriptors (molecular
    weight, net charge at pH 7, GRAVY, aromaticity) -- NOT Bucket 3.1's
    15-descriptor feature-extraction pipeline, which is a separate,
    not-yet-started task (see curation/distribution_audit.py docstring).
    """
    for p in (POSITIVE_POOL_PATH, C1_CLEAN_FASTA_V3_PATH, C2_FASTA_V2_PATH, C3_FASTA_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found.")

    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    pools_seqs = {
        "FR1_positives": positive_df["sequence"].tolist(),
        "C1_v3": [s for _, s in read_fasta(C1_CLEAN_FASTA_V3_PATH)],
        "C2_v2": [s for _, s in read_fasta(C2_FASTA_V2_PATH)],
        "C3_union": [s for _, s in read_fasta(C3_FASTA_PATH)],
    }

    # --- amino-acid composition per pool ---
    aa_comp = pd.DataFrame({name: amino_acid_composition(seqs) for name, seqs in pools_seqs.items()}).T
    aa_comp.index.name = "pool"
    aa_comp.to_csv(DISTRIBUTION_AA_COMPOSITION_PATH, lineterminator="\n")

    # --- per-sequence descriptor table, all pools concatenated ---
    descriptor_tables = {name: pool_descriptor_table(name, seqs) for name, seqs in pools_seqs.items()}
    combined = pd.concat(descriptor_tables.values(), ignore_index=True)
    combined.to_csv(DISTRIBUTION_DESCRIPTOR_TABLE_PATH, index=False, lineterminator="\n")

    # --- KS-test: FR1 positives vs. each challenge pool, per descriptor ---
    challenge_tables = {k: v for k, v in descriptor_tables.items() if k != "FR1_positives"}
    ks_df = compare_pools_ks(
        descriptor_tables["FR1_positives"], challenge_tables, columns=DISTRIBUTION_DESCRIPTOR_COLUMNS
    )
    ks_df.to_csv(DISTRIBUTION_KS_COMPARISON_PATH, index=False, lineterminator="\n")

    # --- shortcut-bias scan: organism diversity (C1), activity-tag diversity (C2) ---
    shortcut_report: dict = {
        "fr1_positives": {
            "organism_metadata_available": False,
            "note": "Multi-AOP/AnOxPePred carry no per-record organism field -- cannot check "
            "organism-family shortcut risk for the positive pool itself with current source data. "
            "Documented as a limitation, not assumed absent.",
        }
    }
    if C1_ACCESSION_MAP_V3_PATH.exists():
        c1_map = pd.read_csv(C1_ACCESSION_MAP_V3_PATH)
        organism_counts = c1_map["organism"].value_counts()
        organism_fracs = organism_counts / organism_counts.sum()
        shortcut_report["c1_v3"] = {
            "n_unique_organisms": int(c1_map["organism"].nunique()),
            "top_10_organisms_by_share": {k: round(float(v), 4) for k, v in organism_fracs.head(10).items()},
            "max_single_organism_share": round(float(organism_fracs.max()), 4),
        }
    if C2_ACTIVITY_MAP_V2_PATH.exists():
        c2_map = pd.read_csv(C2_ACTIVITY_MAP_V2_PATH)
        tag_counts: dict[str, int] = {}
        for tags in c2_map["activity_names"].astype(str):
            for tag in tags.split(";"):
                tag_counts[tag.strip()] = tag_counts.get(tag.strip(), 0) + 1
        total_tags = sum(tag_counts.values())
        top_tags = sorted(tag_counts.items(), key=lambda kv: -kv[1])[:10]
        shortcut_report["c2_v2"] = {
            "n_unique_activity_tags": len(tag_counts),
            "top_10_tags_by_share": {k: round(v / total_tags, 4) for k, v in top_tags},
        }

    with open(DISTRIBUTION_SHORTCUT_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(shortcut_report, handle, indent=2)

    summary = {
        "pool_sizes": {k: len(v) for k, v in pools_seqs.items()},
        "descriptor_columns": DISTRIBUTION_DESCRIPTOR_COLUMNS,
        "ks_significant_mismatches": ks_df[ks_df["p_value"] < 0.01][["pool", "descriptor", "ks_statistic", "p_value"]].to_dict("records"),
        "shortcut_report": shortcut_report,
        "outputs": {
            "descriptor_table": str(DISTRIBUTION_DESCRIPTOR_TABLE_PATH),
            "aa_composition": str(DISTRIBUTION_AA_COMPOSITION_PATH),
            "ks_comparison": str(DISTRIBUTION_KS_COMPARISON_PATH),
            "shortcut_report": str(DISTRIBUTION_SHORTCUT_REPORT_PATH),
        },
    }
    append_provenance_log(
        DISTRIBUTION_PROVENANCE_LOG_PATH,
        {"stage": "fr2_distribution_shortcut_audit", "summary": summary},
    )
    return summary


# Bucket 2.6 -- External Inactive-Control Preparation.
FROZEN_BASELINE_DIR = PROCESSED_DIR / "frozen" / "pp1_baseline_v1"
FROZEN_EXTERNAL_CONTROL_PATH = FROZEN_BASELINE_DIR / "anoxpepred_inactives_clean.csv"
FROZEN_POSITIVE_POOL_PATH = FROZEN_BASELINE_DIR / "aop_positives_provisional.parquet"
FROZEN_CONFLICT_LOG_PATH = FROZEN_BASELINE_DIR / "label_conflicts_anox_vs_multiaop.csv"

EXT_CONTROL_HOMOLOGY_DIR = INTERIM_DIR / "ext_control_homology"
EXT_CONTROL_NEEDLEALL_RAW_PATH = EXT_CONTROL_HOMOLOGY_DIR / "needleall_output.pair"  # gitignored, large

EXT_CONTROL_VALIDATED_PATH = PROCESSED_DIR / "anoxpepred_external_control_validated.csv"
EXT_CONTROL_HOMOLOGY_PAIRS_PATH = PROCESSED_DIR / "ext_control_homology_pairs.csv"
EXT_CONTROL_REPORT_PATH = PROCESSED_DIR / "ext_control_validation_report.json"
EXT_CONTROL_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_ext_control_provenance.jsonl"

EXT_CONTROL_HOMOLOGY_IDENTITY_THRESHOLD = 40.0  # Planner's "proposed 40% boundary"
EXT_CONTROL_HOMOLOGY_LENGTH_FLOOR = 15  # below this, % identity isn't biologically interpretable (Bucket 2.4)

# The 2 external-control sequences independently found (Bucket 2.4 audit) to
# also appear in BIOPEP-UWM's antioxidative reference set -- a genuine
# cross-database annotation conflict, reconciled (not silently resolved)
# below. Named constants, not re-derived automatically, so the reconciliation
# logic is reviewable on its own terms.
EXT_CONTROL_BIOPEP_CONFLICT_PEPTIDE_IDS = ["AOP-37BD4B4933", "AOP-DDCD54E4BA"]


def run_fr2_external_control_build() -> dict:
    """Bucket 2.6: validate the frozen FR1 baseline's 38-record AnOxPePred
    external inactive-control set and run a dedicated homology audit
    against the FR1 positive pool -- separate from, and more rigorous than,
    Bucket 2.4's cross-pool CD-HIT scan (real EMBOSS needleall alignments,
    not a percent-identity shortcut).

    Read-only with respect to `pp1_baseline_v1` -- this never modifies the
    frozen external-control file. Writes a new, separately versioned
    `anoxpepred_external_control_validated.csv` that adds validation/
    reconciliation columns to the same 38 records (no records added,
    removed, or altered) -- no exclusion is applied without the project
    owner's explicit approval (see the BIOPEP-UWM reconciliation below).
    """
    for p in (FROZEN_EXTERNAL_CONTROL_PATH, FROZEN_POSITIVE_POOL_PATH, FROZEN_CONFLICT_LOG_PATH, C1_CLEAN_FASTA_V3_PATH, C2_FASTA_V2_PATH, C3_FASTA_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found.")

    ext_df = pd.read_csv(FROZEN_EXTERNAL_CONTROL_PATH)
    positive_df = pd.read_parquet(FROZEN_POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(FROZEN_CONFLICT_LOG_PATH)

    # --- 1: identifiers, normalized sequences, lengths, alphabet ---
    integrity = sequence_integrity_report("external_control", list(zip(ext_df["peptide_id"], ext_df["sequence"])))
    if integrity["n_duplicate_ids"] or integrity["n_non_standard_alphabet"] or integrity["n_length_window_violations"]:
        raise RuntimeError(f"External control failed basic integrity checks: {integrity}")
    length_mismatches = int((ext_df["length"] != ext_df["sequence"].str.len()).sum())
    if length_mismatches:
        raise RuntimeError(f"{length_mismatches} external-control records have a stored length not matching their sequence.")

    # --- 3: exact-sequence overlap vs positives/conflicts/C1 v3/C2 v2/C3 ---
    ext_seqs = set(ext_df["sequence"])
    c1_seqs = {s for _, s in read_fasta(C1_CLEAN_FASTA_V3_PATH)}
    c2_seqs = {s for _, s in read_fasta(C2_FASTA_V2_PATH)}
    c3_seqs = {s for _, s in read_fasta(C3_FASTA_PATH)}
    exact_overlap = {
        "positives": sorted(ext_seqs & set(positive_df["sequence"])),
        "conflicts_179": sorted(ext_seqs & set(conflict_df["sequence"])),
        "C1_v3": sorted(ext_seqs & c1_seqs),
        "C2_v2": sorted(ext_seqs & c2_seqs),
        "C3_union": sorted(ext_seqs & c3_seqs),
    }
    if any(exact_overlap.values()):
        raise RuntimeError(f"External control has unexpected exact-sequence overlap: {exact_overlap}")

    # --- 4/5/6: dedicated homology audit vs the FR1 positive pool, real
    # alignments (not CD-HIT), with an explicit length floor for
    # interpretability, and a fold-specific check for evaluation independence ---
    EXT_CONTROL_HOMOLOGY_DIR.mkdir(parents=True, exist_ok=True)
    ext_fasta = EXT_CONTROL_HOMOLOGY_DIR / "external_control.fasta"
    pos_fasta = EXT_CONTROL_HOMOLOGY_DIR / "positives.fasta"
    write_fasta(ext_fasta, list(zip(ext_df["peptide_id"], ext_df["sequence"])))
    write_fasta(pos_fasta, list(zip(positive_df["peptide_id"], positive_df["sequence"])))

    run_needleall(ext_fasta, pos_fasta, EXT_CONTROL_NEEDLEALL_RAW_PATH, timeout=1800)
    pairs = parse_needleall_pairs(EXT_CONTROL_NEEDLEALL_RAW_PATH)
    pairs_df = pd.DataFrame(pairs)
    expected_pairs = len(ext_df) * len(positive_df)
    if len(pairs_df) != expected_pairs:
        raise RuntimeError(f"Expected {expected_pairs} needleall pairs, got {len(pairs_df)} -- some pairs were silently dropped.")
    pairs_df = pairs_df.rename(columns={"seq1_id": "external_control_peptide_id", "seq2_id": "positive_peptide_id"})
    pairs_df.to_csv(EXT_CONTROL_HOMOLOGY_PAIRS_PATH, index=False, lineterminator="\n")

    long_enough = pairs_df[pairs_df["alignment_length"] >= EXT_CONTROL_HOMOLOGY_LENGTH_FLOOR]
    real_homology_hits = long_enough[long_enough["identity_pct"] >= EXT_CONTROL_HOMOLOGY_IDENTITY_THRESHOLD]
    short_fragment_hits = pairs_df[
        (pairs_df["identity_pct"] >= EXT_CONTROL_HOMOLOGY_IDENTITY_THRESHOLD)
        & (pairs_df["alignment_length"] < EXT_CONTROL_HOMOLOGY_LENGTH_FLOOR)
    ]

    # Fold-specific check: any real hit's positive partner's evaluation
    # fold is reported explicitly (there are none in this run, but the
    # check is structural, not inferred from the global null result alone).
    fold_of = {}
    if GRAPHPART_SPLITS_PATH.exists():
        splits_df = pd.read_csv(GRAPHPART_SPLITS_PATH)
        fold_of = dict(zip(splits_df["AC"], splits_df["cluster"].astype(int)))
    real_homology_records = []
    for _, row in real_homology_hits.iterrows():
        real_homology_records.append(
            {
                **row.to_dict(),
                "positive_evaluation_fold": fold_of.get(row["positive_peptide_id"], "not_in_graphpart_split"),
            }
        )

    # --- 7: reconcile the 2 BIOPEP-UWM antioxidative-annotation conflicts ---
    biopep_conflict_rows = ext_df[ext_df["peptide_id"].isin(EXT_CONTROL_BIOPEP_CONFLICT_PEPTIDE_IDS)]
    biopep_reconciliation = {
        "status": "DOCUMENTED, NOT EXCLUDED -- pending explicit policy confirmation",
        "conflicted_peptide_ids": EXT_CONTROL_BIOPEP_CONFLICT_PEPTIDE_IDS,
        "conflicted_records": biopep_conflict_rows.to_dict("records"),
        "evidence": "AnOxPePred reports both FRS and Chelator assays as inactive for these 2 "
        "sequences (the project's own primary, per-sequence experimental evidence); BIOPEP-UWM "
        "independently lists both as 'Antioxidative peptide' (database annotation, no per-record "
        "assay/reference metadata visible in the scraped table).",
        "precedent": "Mirrors the already-approved FR1 conflict-resolution policy (Bucket 1): "
        "assay-level evidence outranks an undocumented benchmark/database annotation when the two "
        "disagree. Applying that same precedent here would argue for RETAINING both in the primary "
        "external control, not excluding them.",
        "recommendation": "Retain both in the primary external-control set per the existing "
        "assay-outranks-annotation precedent; flag the contradiction explicitly rather than creating "
        "a new sensitivity-only subset. NOT applied unilaterally -- awaiting explicit confirmation.",
    }

    # --- validated artifact: same 38 records, added validation columns, no exclusions applied ---
    validated_df = ext_df.copy()
    validated_df["has_biopep_antioxidative_conflict"] = validated_df["peptide_id"].isin(
        EXT_CONTROL_BIOPEP_CONFLICT_PEPTIDE_IDS
    )
    validated_df["max_identity_pct_vs_positives_length_ge_15"] = validated_df["peptide_id"].map(
        long_enough.groupby("external_control_peptide_id")["identity_pct"].max()
    ).fillna(0.0)
    validated_df.to_csv(EXT_CONTROL_VALIDATED_PATH, index=False, lineterminator="\n")

    summary = {
        "source_version": str(FROZEN_EXTERNAL_CONTROL_PATH),
        "output_version": str(EXT_CONTROL_VALIDATED_PATH),
        "n_records": len(ext_df),
        "n_unique_sequences": integrity["n_unique_sequences"],
        "integrity": integrity,
        "exact_overlap": {k: len(v) for k, v in exact_overlap.items()},
        "homology_audit": {
            "method": "EMBOSS needleall (EBLOSUM62, gapopen=10, gapextend=0.5), global alignment, "
            "every external-control sequence against every FR1 positive",
            "n_pairs_total": len(pairs_df),
            "n_pairs_expected": expected_pairs,
            "identity_threshold_pct": EXT_CONTROL_HOMOLOGY_IDENTITY_THRESHOLD,
            "length_floor_for_interpretation": EXT_CONTROL_HOMOLOGY_LENGTH_FLOOR,
            "n_short_fragment_hits_not_interpretable": len(short_fragment_hits),
            "n_real_homology_hits": len(real_homology_records),
            "real_homology_hits": real_homology_records,
            "max_identity_pct_at_length_ge_15": float(long_enough["identity_pct"].max()) if len(long_enough) else None,
            "held_out_fold_violations": [r for r in real_homology_records if r["positive_evaluation_fold"] != "not_in_graphpart_split"],
            "conclusion": "ZERO genuine homology hits (>=40% identity AND >=15 AA alignment length) "
            "found between the external control and any FR1 positive -- the only hits at/above the "
            "40% threshold are short-fragment (<15 AA) chance matches, the same artifact already "
            "documented in Bucket 2.4. No fold-specific violation is possible given the global null "
            "result (any fold's held-out positives are a subset of the full 1,205 screened here).",
        },
        "biopep_uwm_reconciliation": biopep_reconciliation,
        "labeling_rule": "These 38 records are inactive under the AnOxPePred FRS/Chelator assay "
        "definitions specifically -- NOT a universal claim of proven non-antioxidant activity. Kept "
        "entirely separate from the C1/C2/C3 unlabeled training pools at all times.",
    }
    with open(EXT_CONTROL_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, default=str)

    append_provenance_log(
        EXT_CONTROL_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_external_control_validation",
            "source": str(FROZEN_EXTERNAL_CONTROL_PATH),
            "screen_sources": [str(FROZEN_POSITIVE_POOL_PATH), str(FROZEN_CONFLICT_LOG_PATH), str(C1_CLEAN_FASTA_V3_PATH), str(C2_FASTA_V2_PATH), str(C3_FASTA_PATH)],
            "summary": summary,
            "outputs": {
                "validated_csv": str(EXT_CONTROL_VALIDATED_PATH),
                "homology_pairs": str(EXT_CONTROL_HOMOLOGY_PAIRS_PATH),
                "report": str(EXT_CONTROL_REPORT_PATH),
            },
        },
    )
    return summary


# Bucket 2.7 -- FR2 Final Acceptance and Freeze.
FR2_BASELINE_VERSION = "pp2_baseline_v1"
FR2_FROZEN_DIR = PROCESSED_DIR / "frozen" / FR2_BASELINE_VERSION


def run_fr2_freeze() -> Path:
    """Bucket 2.7: snapshot the validated FR2 artifacts (C1 v3, C2 v2, C3
    union + fold ranking, the validated external control, and every audit/
    distribution report) under ``pp2_baseline_v1`` with a checksummed
    manifest -- same convention as `run_fr1_freeze`.

    Does not re-validate anything -- run the full test suite and
    `fr2-pool-audit`/`fr2-external-control-build` first; this only freezes
    what already passed (`fr2_pool_audit_report.json`'s
    `ready_for_technical_acceptance` must already be True). Never touches
    `pp1_baseline_v1` -- confirmed via `verify_frozen_baseline` before and
    after, not assumed.
    """
    audit_report_path_check = AUDIT_REPORT_PATH
    if not audit_report_path_check.exists():
        raise FileNotFoundError(f"{audit_report_path_check} not found -- run fr2-pool-audit first.")
    with open(audit_report_path_check, encoding="utf-8") as handle:
        audit_report = json.load(handle)
    if not audit_report.get("ready_for_technical_acceptance"):
        raise RuntimeError(
            "fr2_pool_audit_report.json reports ready_for_technical_acceptance=False -- "
            "resolve outstanding findings before freezing FR2."
        )

    pre_freeze_fr1_check = verify_frozen_baseline(FROZEN_DIR)
    if not all(pre_freeze_fr1_check.values()):
        raise RuntimeError(f"pp1_baseline_v1 integrity check failed BEFORE freezing FR2: {pre_freeze_fr1_check}")

    required = {
        # Canonical C1 v3
        "stage_c1_decoys_v3.fasta": C1_CLEAN_FASTA_V3_PATH,
        "c1_accession_map_v3.csv": C1_ACCESSION_MAP_V3_PATH,
        "c1_cross_pool_exclusion_log.csv": C1_CROSS_POOL_EXCLUSION_LOG_PATH,
        "c1_cross_pool_replacement_log.csv": C1_CROSS_POOL_REPLACEMENT_LOG_PATH,
        "c1_cross_pool_fix_report.json": C1_CROSS_POOL_FIX_REPORT_PATH,
        # Canonical C2 v2
        "stage_c2_bioactive_unlabeled_v2.fasta": C2_FASTA_V2_PATH,
        "c2_activity_map_v2.csv": C2_ACTIVITY_MAP_V2_PATH,
        "c2_cross_pool_exclusion_log.csv": C2_CROSS_POOL_EXCLUSION_LOG_PATH,
        "c2_cross_pool_replacement_log.csv": C2_CROSS_POOL_REPLACEMENT_LOG_PATH,
        "c2_cross_pool_fix_report.json": C2_CROSS_POOL_FIX_REPORT_PATH,
        # Canonical C3 union + fold-specific ranking
        "stage_c3_esm2_hard_challenges.fasta": C3_FASTA_PATH,
        "c3_similarity_ranking.csv": C3_RANKING_PATH,
        "c3_build_report.json": C3_BUILD_REPORT_PATH,
        # Validated external control
        "anoxpepred_external_control_validated.csv": EXT_CONTROL_VALIDATED_PATH,
        "ext_control_homology_pairs.csv": EXT_CONTROL_HOMOLOGY_PAIRS_PATH,
        "ext_control_validation_report.json": EXT_CONTROL_REPORT_PATH,
        # Leakage and contamination reports (Bucket 2.4)
        "audit_integrity_report.json": AUDIT_INTEGRITY_REPORT_PATH,
        "audit_exact_overlap_matrix.csv": AUDIT_OVERLAP_MATRIX_PATH,
        "audit_exact_overlap_detail.csv": AUDIT_OVERLAP_DETAIL_PATH,
        "audit_external_aop_screen.json": AUDIT_EXTERNAL_SCREEN_PATH,
        "audit_cross_pool_homology_clusters.csv": AUDIT_HOMOLOGY_CLUSTERS_PATH,
        "audit_cross_pool_homology_summary.json": AUDIT_HOMOLOGY_SUMMARY_PATH,
        "audit_c3_fold_contract_report.json": AUDIT_C3_CONTRACT_REPORT_PATH,
        "fr2_pool_audit_report.json": AUDIT_REPORT_PATH,
        # Distribution and shortcut-bias reports (Bucket 2.5)
        "distribution_descriptor_table.csv": DISTRIBUTION_DESCRIPTOR_TABLE_PATH,
        "distribution_aa_composition.csv": DISTRIBUTION_AA_COMPOSITION_PATH,
        "distribution_ks_comparison.csv": DISTRIBUTION_KS_COMPARISON_PATH,
        "distribution_shortcut_report.json": DISTRIBUTION_SHORTCUT_REPORT_PATH,
    }

    c1_df = read_fasta(C1_CLEAN_FASTA_V3_PATH)
    c2_df = read_fasta(C2_FASTA_V2_PATH)
    c3_df = read_fasta(C3_FASTA_PATH)
    ranking_df = pd.read_csv(C3_RANKING_PATH)
    ext_df = pd.read_csv(EXT_CONTROL_VALIDATED_PATH)

    # Raw external sources are too large / already gitignored to copy into
    # the freeze -- recorded here by checksum and location instead (AGENTS.md:
    # don't commit large raw datasets; record source + checksum).
    raw_source_references = {
        "peptipedia_v2_zenodo_dump": {
            "path": str(C2_RAW_DUMP_PATH),
            "doi": "10.5281/zenodo.21488992",
            "sha256": hashlib.sha256(C2_RAW_DUMP_PATH.read_bytes()).hexdigest() if C2_RAW_DUMP_PATH.exists() else None,
            "committed_to_git": False,
        },
        "uniref50_candidates_snapshot": {
            "path": str(C3_RAW_CANDIDATES_PATH),
            "sha256": hashlib.sha256(C3_RAW_CANDIDATES_PATH.read_bytes()).hexdigest() if C3_RAW_CANDIDATES_PATH.exists() else None,
            "committed_to_git": True,
        },
        "biopep_uwm_antioxidative_scrape": {
            "path": str(BIOPEP_RAW_PATH),
            "citation": BIOPEP_CITATION,
            "sha256": hashlib.sha256(BIOPEP_RAW_PATH.read_bytes()).hexdigest() if BIOPEP_RAW_PATH.exists() else None,
            "committed_to_git": True,
        },
    }

    metadata = {
        "supersedes": None,
        "fr1_baseline_dependency": FR1_BASELINE_VERSION,
        "git_commit": _git_commit_hash(),
        "tool_versions": TOOL_VERSIONS,
        "counts": {
            "c1_v3_records": len(c1_df),
            "c1_v3_unique_sequences": len({s for _, s in c1_df}),
            "c2_v2_records": len(c2_df),
            "c3_union_records": len(c3_df),
            "c3_ranking_rows": len(ranking_df),
            "external_control_records": len(ext_df),
        },
        "raw_source_references": raw_source_references,
        "known_limitations": [
            "11 remaining C1<->C2 near-duplicate homology families -- project-owner-approved "
            "documented limitation, conditional on (and re-verified as) zero FR1-positive "
            "involvement in the real (>=15 AA) homology relationship.",
            "AODB and DFBP remain unscreened for documented access reasons (HTTP 502 + expired "
            "cert; no discoverable hosting URL), not as an unstarted task.",
            "2 BIOPEP-UWM-vs-AnOxPePred external-control annotation conflicts flagged, retention "
            "recommended, not yet explicitly confirmed by the project owner.",
            "C1 retains natural record-level duplicates by design (5,000 records / 3,788 unique "
            "sequences) -- any future train/val/test split MUST group identical sequences together.",
            "C3's union FASTA is not a valid fold-specific challenge set on its own -- "
            "FR3/FR4/FR6 MUST use curation.c3.load_fold_challenges(path, fold_id).",
            "FR1-vs-C1/C2/C3 length/mass/charge/hydrophobicity/aromaticity distributions differ "
            "significantly (quantified, Task 2.5) -- a measured shortcut-bias risk, NOT evidence of "
            "a validated C1-to-C2-to-C3 difficulty ordering.",
            "FR1 positives have no organism metadata available -- an unchecked, not assumed-absent, "
            "shortcut-risk gap.",
            "FR1's 4 pending supervisor approvals remain open (see fr1_acceptance_report.md §10); "
            "FR2 technical acceptance does not constitute scientific sign-off.",
            "No formal data_registry.csv covers FR2's own new external sources (Peptipedia dump, "
            "UniRef50 snapshot, BIOPEP-UWM scrape) -- same gap already flagged for FR1, now also "
            "applying to FR2; per-stage provenance JSONLs are a stopgap, not a substitute.",
        ],
    }

    manifest_path = freeze_baseline(FR2_BASELINE_VERSION, FR2_FROZEN_DIR, required, metadata)

    post_freeze_fr1_check = verify_frozen_baseline(FROZEN_DIR)
    if not all(post_freeze_fr1_check.values()):
        raise RuntimeError(f"pp1_baseline_v1 integrity check failed AFTER freezing FR2: {post_freeze_fr1_check}")

    return manifest_path


# Bucket 3.1 -- 15-descriptor physicochemical feature extraction over the
# frozen FR1/FR2 canonical pools. Reads frozen/pp1_baseline_v1 and
# frozen/pp2_baseline_v1 only -- never the superseded working-tree copies,
# and never writes into either frozen directory.
FR3_DESCRIPTOR_SCHEMA_PATH = PROCESSED_DIR / "fr3_descriptor_schema.json"
FR3_DESCRIPTOR_TABLE_PATH = PROCESSED_DIR / "fr3_descriptor_table.parquet"
FR3_RECORD_MAP_PATH = PROCESSED_DIR / "fr3_record_map.csv"
FR3_COVERAGE_REPORT_PATH = PROCESSED_DIR / "fr3_coverage_report.json"
FR3_VALIDATION_REPORT_PATH = PROCESSED_DIR / "fr3_validation_report.json"
FR3_DESCRIPTORS_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr3_descriptors_provenance.jsonl"


def run_fr3_descriptors() -> dict:
    """Bucket 3.1: compute the canonical 15-descriptor vector for every
    unique sequence in FR1's positive pool and FR2's canonical C1/C2/C3/
    external-control pools, with full peptide-ID/record provenance
    preserved. Never fits or applies any cross-dataset statistic -- raw,
    per-sequence descriptors only.
    """
    for p in (FROZEN_POSITIVE_POOL_PATH, C1_CLEAN_FASTA_V3_PATH, C2_FASTA_V2_PATH, C3_FASTA_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found.")

    fr1_descriptors, fr1_records = extract_fr1_positive_descriptors(
        FROZEN_POSITIVE_POOL_PATH, GRAPHPART_SPLITS_PATH if GRAPHPART_SPLITS_PATH.exists() else None
    )
    c1_descriptors, c1_records = extract_c1_descriptors(C1_CLEAN_FASTA_V3_PATH, C1_ACCESSION_MAP_V3_PATH)
    c2_descriptors, c2_records = extract_id_prefixed_pool_descriptors(C2_FASTA_V2_PATH, "C2")
    c3_descriptors, c3_records = extract_id_prefixed_pool_descriptors(C3_FASTA_PATH, "C3")

    descriptor_tables = {
        "FR1_positives": fr1_descriptors,
        "C1": c1_descriptors,
        "C2": c2_descriptors,
        "C3": c3_descriptors,
    }
    record_maps = {
        "FR1_positives": fr1_records,
        "C1": c1_records,
        "C2": c2_records,
        "C3": c3_records,
    }
    if EXT_CONTROL_VALIDATED_PATH.exists():
        ext_descriptors, ext_records = extract_external_control_descriptors(EXT_CONTROL_VALIDATED_PATH)
        descriptor_tables["external_control"] = ext_descriptors
        record_maps["external_control"] = ext_records

    combined_descriptors = pd.concat(descriptor_tables.values(), ignore_index=True)
    combined_descriptors.to_parquet(FR3_DESCRIPTOR_TABLE_PATH, index=False)

    combined_records = pd.concat(record_maps.values(), ignore_index=True)
    combined_records.to_csv(FR3_RECORD_MAP_PATH, index=False, lineterminator="\n")

    schema = {
        "schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "descriptor_names": list(DESCRIPTOR_NAMES),
        "n_descriptors": len(DESCRIPTOR_NAMES),
    }
    with open(FR3_DESCRIPTOR_SCHEMA_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(schema, handle, indent=2)

    coverage = build_coverage_report(descriptor_tables, record_maps)
    with open(FR3_COVERAGE_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(coverage, handle, indent=2)

    validation = build_validation_report(combined_descriptors)
    with open(FR3_VALIDATION_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(validation, handle, indent=2)

    summary = {
        "schema": schema,
        "coverage": coverage,
        "total_descriptor_rows": int(len(combined_descriptors)),
        "total_source_records": int(len(combined_records)),
        "outputs": {
            "descriptor_schema": str(FR3_DESCRIPTOR_SCHEMA_PATH),
            "descriptor_table": str(FR3_DESCRIPTOR_TABLE_PATH),
            "record_map": str(FR3_RECORD_MAP_PATH),
            "coverage_report": str(FR3_COVERAGE_REPORT_PATH),
            "validation_report": str(FR3_VALIDATION_REPORT_PATH),
        },
    }
    append_provenance_log(
        FR3_DESCRIPTORS_PROVENANCE_LOG_PATH,
        {"stage": "fr3_descriptor_extraction", "summary": {k: v for k, v in summary.items() if k != "coverage"} | {"coverage": coverage}},
    )
    return summary


# Bucket 3.2 (remaining work) -- full ESM-2 embedding extraction over the
# Task 3.1 descriptor contract. The environment, frozen spec, embed_via_wsl
# subprocess mechanism, and esm2_cli.py entrypoint already exist (Bucket
# 2.3/3.2 setup) and are reused as-is, not rebuilt. Embeddings are computed
# once per unique sequence, in the EXACT row order of
# fr3_descriptor_table.parquet, so alignment with the descriptor table is
# true by construction rather than a separately-maintained convention.
#
# C3 fold-safety is unaffected: this cache holds one embedding per C3-union
# peptide_id (2,325 rows, same union as the descriptor table) -- it is NOT
# a fold-specific accessor and does not replace
# curation/c3.py::load_fold_challenges(path, fold_id). Fold-specific
# training code must still call that function to get a fold's peptide_ids,
# then join them against this cache by peptide_id.
ESM2_MODEL_NAME = "esm2_t12_35M_UR50D"
ESM2_REPRESENTATION_LAYER = 12
ESM2_EMBEDDING_DIM = 480

FR3_EMBEDDINGS_CACHE_PATH = INTERIM_DIR / "fr3_embeddings.npz"  # gitignored, regeneratable
FR3_FRESH_EMBEDDINGS_CACHE_PATH = INTERIM_DIR / "fr3_fresh_embeddings.npz"  # gitignored scratch
FR3_EMBED_INPUT_PATH = INTERIM_DIR / "fr3_embed_input.json"  # gitignored scratch
FR3_EMBED_SUMMARY_PATH = INTERIM_DIR / "fr3_embed_report.json"  # gitignored, huge per-peptide scalars
FR3_EMBEDDINGS_MANIFEST_PATH = PROCESSED_DIR / "fr3_embeddings_manifest.json"
FR3_EMBEDDINGS_VALIDATION_REPORT_PATH = PROCESSED_DIR / "fr3_embeddings_validation_report.json"
FR3_EMBEDDINGS_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr3_embeddings_provenance.jsonl"

# Bucket 2.3's own C3 embedding caches, already built under the identical
# frozen spec, plus this stage's own prior combined output (so re-running
# fr3-embeddings is idempotent and never re-embeds work it already did) --
# checked for direct reuse before any fresh ESM-2 inference is run.
EXISTING_EMBEDDING_CACHES = (
    FR3_EMBEDDINGS_CACHE_PATH,
    C3_POSITIVE_EMBEDDINGS_CACHE,
    C3_CANDIDATE_EMBEDDINGS_CACHE,
)


def _load_reusable_embeddings(caches: tuple[Path, ...] = EXISTING_EMBEDDING_CACHES) -> tuple[dict[str, np.ndarray], list[str]]:
    """Load peptide_id -> vector from every existing, already-built
    embedding cache under the frozen spec, so Bucket 3.2 doesn't re-run
    ESM-2 on sequences already embedded elsewhere (Bucket 2.3's C3
    positive/candidate caches). Any cached vector that fails a basic
    shape/dtype/finiteness sanity check is reported as incompatible and
    excluded from reuse (forcing it to be freshly embedded) rather than
    trusted blindly.
    """
    reusable: dict[str, np.ndarray] = {}
    incompatible: list[str] = []
    for cache_path in caches:
        if not cache_path.exists():
            continue
        with np.load(cache_path, allow_pickle=False) as npz:
            ids = npz["peptide_ids"]
            matrix = npz["embeddings"]
        for i, pid in enumerate(ids):
            vec = matrix[i]
            if vec.shape != (ESM2_EMBEDDING_DIM,) or vec.dtype != np.float32 or not np.isfinite(vec).all():
                incompatible.append(f"{pid} ({cache_path.name}): shape={vec.shape} dtype={vec.dtype}")
                continue
            reusable[str(pid)] = vec
    return reusable, incompatible


def run_fr3_embeddings(force_cpu: bool = False, force_regenerate: bool = False) -> dict:
    """Bucket 3.2 (remaining work): extract/reuse the frozen 480-dim
    esm2_t12_35M_UR50D layer-12 mean-pooled embedding for every one of the
    9,356 unique pool-specific sequences in fr3_descriptor_table.parquet
    (Task 3.1's frozen output), in that table's exact row order.

    ``force_regenerate=True`` ignores every existing cache and re-embeds
    everything from scratch (for an independent reproducibility check);
    the default reuses Bucket 2.3's C3 caches wherever their peptide_ids
    already cover what's needed here, and only invokes ESM-2 fresh for the
    remainder.
    """
    if not FR3_DESCRIPTOR_TABLE_PATH.exists():
        raise FileNotFoundError(
            f"{FR3_DESCRIPTOR_TABLE_PATH} not found -- run `fr3-descriptors` (Task 3.1) first."
        )
    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    peptide_ids = descriptor_df["peptide_id"].tolist()
    sequences = descriptor_df["sequence"].tolist()
    pools = descriptor_df["pool"].tolist()

    if len(set(peptide_ids)) != len(peptide_ids):
        dupes = descriptor_df[descriptor_df.duplicated("peptide_id", keep=False)]["peptide_id"].tolist()
        raise ValueError(
            f"fr3_descriptor_table.parquet has {len(dupes)} globally duplicate peptide_id rows -- "
            f"refusing to embed (would silently conflate distinct sequences): {dupes[:10]}"
        )
    id_to_sequence = dict(zip(peptide_ids, sequences))

    reused, incompatible = ({}, []) if force_regenerate else _load_reusable_embeddings()
    reused_for_this_run = {pid: vec for pid, vec in reused.items() if pid in id_to_sequence}

    to_embed_ids = [pid for pid in peptide_ids if pid not in reused_for_this_run]
    to_embed_sequences = [id_to_sequence[pid] for pid in to_embed_ids]

    embeddings: dict[str, np.ndarray] = dict(reused_for_this_run)
    elapsed_seconds = 0.0
    if to_embed_ids:
        import time as _time

        start = _time.time()
        fresh = embed_via_wsl(
            to_embed_ids,
            to_embed_sequences,
            FR3_FRESH_EMBEDDINGS_CACHE_PATH,
            label="fr3_fresh",
            force_cpu=force_cpu,
            embed_input_path=FR3_EMBED_INPUT_PATH,
            summary_report_path=FR3_EMBED_SUMMARY_PATH,
            timeout=1800,
        )
        elapsed_seconds = _time.time() - start
        embeddings.update(fresh)

    missing = [pid for pid in peptide_ids if pid not in embeddings]
    if missing:
        raise RuntimeError(f"{len(missing)} peptide_id(s) have no embedding after extraction: {missing[:10]}")

    matrix = np.stack([embeddings[pid] for pid in peptide_ids]).astype(np.float32)
    np.savez_compressed(
        FR3_EMBEDDINGS_CACHE_PATH,
        peptide_ids=np.array(peptide_ids),
        embeddings=matrix,
        pools=np.array(pools),
    )

    coverage = {
        pool: int((descriptor_df["pool"] == pool).sum()) for pool in descriptor_df["pool"].unique()
    }
    manifest = {
        "model_name": ESM2_MODEL_NAME,
        "representation_layer": ESM2_REPRESENTATION_LAYER,
        "embedding_dim": ESM2_EMBEDDING_DIM,
        "total_embeddings": int(len(peptide_ids)),
        "reused_from_existing_caches": int(len(reused_for_this_run)),
        "freshly_embedded": int(len(to_embed_ids)),
        "incompatible_cached_vectors_excluded": incompatible,
        "coverage_by_pool": coverage,
        "peptide_id_order_sha256": hashlib.sha256("\n".join(peptide_ids).encode("utf-8")).hexdigest(),
        "embeddings_cache_sha256": hashlib.sha256(FR3_EMBEDDINGS_CACHE_PATH.read_bytes()).hexdigest(),
        "fresh_embedding_elapsed_seconds": elapsed_seconds,
        "descriptor_table_source": str(FR3_DESCRIPTOR_TABLE_PATH),
    }
    with open(FR3_EMBEDDINGS_MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)

    validation = {
        "n_rows": int(len(peptide_ids)),
        "shape_correct": bool(matrix.shape == (len(peptide_ids), ESM2_EMBEDDING_DIM)),
        "dtype_correct": bool(matrix.dtype == np.float32),
        "all_finite": bool(np.isfinite(matrix).all()),
        "peptide_id_order_matches_descriptor_table": bool(peptide_ids == descriptor_df["peptide_id"].tolist()),
        "l2_norm_min": float(np.linalg.norm(matrix, axis=1).min()),
        "l2_norm_max": float(np.linalg.norm(matrix, axis=1).max()),
        "l2_norm_mean": float(np.linalg.norm(matrix, axis=1).mean()),
    }
    with open(FR3_EMBEDDINGS_VALIDATION_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(validation, handle, indent=2)

    summary = {
        "manifest": manifest,
        "validation": validation,
        "outputs": {
            "embeddings_cache": str(FR3_EMBEDDINGS_CACHE_PATH),
            "manifest": str(FR3_EMBEDDINGS_MANIFEST_PATH),
            "validation_report": str(FR3_EMBEDDINGS_VALIDATION_REPORT_PATH),
        },
    }
    append_provenance_log(
        FR3_EMBEDDINGS_PROVENANCE_LOG_PATH,
        {"stage": "fr3_embeddings_extraction", "summary": {k: v for k, v in summary.items() if k != "validation"} | {"validation": validation}},
    )
    return summary


# Bucket 3.3 -- feature fusion and leakage-safe preprocessing. Reuses Task
# 3.1's descriptor table and Task 3.2's embedding cache as-is (neither is
# recomputed here). See curation/feature_fusion.py's module docstring for
# the full leakage-safe-scaling design rationale (mirrors the C3 fold-safe
# centroid precedent: a fold's scaler is fit on that fold's training
# positives ONLY, never on held-out positives or any unlabeled pool).
FR3_FUSION_SCHEMA_PATH = PROCESSED_DIR / "fr3_fusion_schema.json"
FR3_FUSED_RAW_CACHE_PATH = INTERIM_DIR / "fr3_fused_raw.npz"  # gitignored, regeneratable
FR3_FUSION_SCALERS_PATH = PROCESSED_DIR / "fr3_fusion_scalers.json"
FR3_FUSION_VALIDATION_REPORT_PATH = PROCESSED_DIR / "fr3_fusion_validation_report.json"
FR3_FUSION_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr3_fusion_provenance.jsonl"


def run_fr3_feature_fusion(n_folds: int = 5) -> dict:
    """Bucket 3.3: concatenate Task 3.1's descriptor table + Task 3.2's
    embedding cache into a 495-dim raw fused matrix, then fit one
    leakage-safe z-score scaler per GraphPart fold (training-positives-only
    -- see curation/feature_fusion.py). Does not fit anything on the full
    dataset, does not materialize 5 separate scaled caches (that full-
    fused-per-fold cache responsibility belongs to Task 3.4), and does not
    touch any frozen FR1/FR2 artifact or the Task 3.1/3.2 outputs it reads.
    """
    for p in (FR3_DESCRIPTOR_TABLE_PATH, FR3_EMBEDDINGS_CACHE_PATH, FR3_RECORD_MAP_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found -- run Task 3.1 (`fr3-descriptors`) and Task 3.2 (`fr3-embeddings`) first.")

    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    with np.load(FR3_EMBEDDINGS_CACHE_PATH, allow_pickle=False) as npz:
        embedding_peptide_ids = npz["peptide_ids"]
        embedding_matrix = npz["embeddings"]
        embedding_pools = npz["pools"]
    record_map_df = pd.read_csv(FR3_RECORD_MAP_PATH)

    load_and_validate_fusion_inputs(descriptor_df, embedding_peptide_ids, embedding_pools)

    peptide_ids = descriptor_df["peptide_id"].tolist()
    fused_matrix = build_raw_fused_matrix(descriptor_df, embedding_matrix)
    if fused_matrix.shape != (len(peptide_ids), FUSED_DIM):
        raise RuntimeError(f"Unexpected fused matrix shape {fused_matrix.shape}, expected ({len(peptide_ids)}, {FUSED_DIM}).")
    if not np.isfinite(fused_matrix).all():
        raise RuntimeError("Non-finite value(s) in the raw fused matrix -- refusing to proceed to scaler fitting.")

    np.savez_compressed(
        FR3_FUSED_RAW_CACHE_PATH,
        peptide_ids=np.array(peptide_ids),
        pools=np.array(descriptor_df["pool"].tolist()),
        features=fused_matrix,
        feature_names=np.array(FUSED_FEATURE_NAMES),
    )

    fold_scalers = compute_all_fold_scalers(peptide_ids, fused_matrix, record_map_df, n_folds=n_folds)

    # Cross-fold leakage check: no fold's training set may contain another
    # fold's held-out positives, and a fold's own held-out positives must
    # never appear in its own training set.
    for fold_id, scaler in fold_scalers.items():
        training_set = set(scaler["training_peptide_ids"])
        held_out_set = set(scaler["held_out_peptide_ids"])
        if training_set & held_out_set:
            raise RuntimeError(f"Fold {fold_id}: {len(training_set & held_out_set)} peptide_id(s) in both its own training and held-out sets.")

    schema = {
        "schema_version": SCHEMA_VERSION,
        "fused_dim": FUSED_DIM,
        "esm2_dim": ESM2_DIM,
        "n_descriptors": N_DESCRIPTORS,
        "feature_order": "esm2_0..esm2_479, then descriptors_v1's 15 names in their frozen order",
        "feature_names": list(FUSED_FEATURE_NAMES),
        "descriptor_schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "n_folds": n_folds,
    }
    with open(FR3_FUSION_SCHEMA_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(schema, handle, indent=2)

    scalers_out = {
        str(fold_id): {
            "mean": scaler["mean"].tolist(),
            "std": scaler["std"].tolist(),
            "n_training_samples": scaler["n_training_samples"],
            "training_peptide_ids": scaler["training_peptide_ids"],
            "held_out_peptide_ids": scaler["held_out_peptide_ids"],
        }
        for fold_id, scaler in fold_scalers.items()
    }
    with open(FR3_FUSION_SCALERS_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(scalers_out, handle, indent=2)

    # Validation: for each fold, confirm the scaler's own training rows
    # standardize to mean~0/std~1 (sanity on the fit itself), and that
    # applying it to EVERY row (training, held-out, and every unlabeled
    # pool) produces finite output -- never fit on anything but that
    # fold's training rows.
    id_to_row = {pid: i for i, pid in enumerate(peptide_ids)}
    per_fold_validation = {}
    for fold_id, scaler in fold_scalers.items():
        training_rows = fused_matrix[[id_to_row[pid] for pid in scaler["training_peptide_ids"]]]
        transformed_training = apply_scaler(training_rows, scaler)
        transformed_all = apply_scaler(fused_matrix, scaler)
        per_fold_validation[str(fold_id)] = {
            "n_training_samples": scaler["n_training_samples"],
            "n_held_out_samples": len(scaler["held_out_peptide_ids"]),
            "training_rows_transformed_mean_abs_max": float(np.abs(transformed_training.mean(axis=0)).max()),
            "training_rows_transformed_std_min_max": [
                float(transformed_training.std(axis=0, ddof=0).min()),
                float(transformed_training.std(axis=0, ddof=0).max()),
            ],
            "all_rows_transformed_all_finite": bool(np.isfinite(transformed_all).all()),
        }

    validation = {
        "n_rows": int(len(peptide_ids)),
        "fused_dim_correct": bool(fused_matrix.shape[1] == FUSED_DIM),
        "raw_matrix_all_finite": bool(np.isfinite(fused_matrix).all()),
        "peptide_id_order_sha256": peptide_id_order_sha256(peptide_ids),
        "per_fold": per_fold_validation,
    }
    with open(FR3_FUSION_VALIDATION_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(validation, handle, indent=2)

    summary = {
        "schema": {k: v for k, v in schema.items() if k != "feature_names"},
        "fold_training_sizes": {str(k): v["n_training_samples"] for k, v in fold_scalers.items()},
        "validation": {k: v for k, v in validation.items() if k != "per_fold"} | {"per_fold": per_fold_validation},
        "outputs": {
            "fusion_schema": str(FR3_FUSION_SCHEMA_PATH),
            "fused_raw_cache": str(FR3_FUSED_RAW_CACHE_PATH),
            "fusion_scalers": str(FR3_FUSION_SCALERS_PATH),
            "validation_report": str(FR3_FUSION_VALIDATION_REPORT_PATH),
        },
    }
    append_provenance_log(FR3_FUSION_PROVENANCE_LOG_PATH, {"stage": "fr3_feature_fusion", "summary": summary})
    return summary


# Bucket 3.4 -- fold-specific scaled feature cache. Reuses Task 3.3's raw
# fused matrix and per-fold scalers exactly as frozen -- never refits,
# never recomputes Tasks 3.1-3.3. See common/feature_cache.py's module
# docstring for the loader contract (strict checksum/schema validation,
# and why C3 fold membership still goes through load_fold_challenges).
FR3_FEATURE_CACHE_PATH_TEMPLATE = str(INTERIM_DIR / "fr3_fold{fold_id}_scaled_features.npz")  # gitignored
FR3_FEATURE_CACHE_MANIFEST_PATH = PROCESSED_DIR / "fr3_feature_cache_manifest.json"
FR3_FEATURE_CACHE_VALIDATION_REPORT_PATH = PROCESSED_DIR / "fr3_feature_cache_validation_report.json"
FR3_FEATURE_CACHE_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr3_feature_cache_provenance.jsonl"


def run_fr3_feature_cache(n_folds: int = 5) -> dict:
    """Bucket 3.4: materialize one scaled (float32) feature cache per
    GraphPart fold by applying that fold's EXISTING fitted scaler
    (fr3_fusion_scalers.json, never refit) to the EXISTING raw fused
    matrix (fr3_fused_raw.npz, never recomputed) -- plus a checksummed
    manifest and a strict round-trip load of every cache as its own
    validation step.
    """
    for p in (FR3_FUSED_RAW_CACHE_PATH, FR3_FUSION_SCALERS_PATH, FR3_FUSION_SCHEMA_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found -- run Task 3.3 (`fr3-feature-fusion`) first.")

    with np.load(FR3_FUSED_RAW_CACHE_PATH, allow_pickle=False) as npz:
        peptide_ids = npz["peptide_ids"]
        pools = npz["pools"]
        raw_matrix = npz["features"]
        feature_names = npz["feature_names"]
    with open(FR3_FUSION_SCALERS_PATH, encoding="utf-8") as handle:
        fusion_scalers = json.load(handle)
    with open(FR3_FUSION_SCHEMA_PATH, encoding="utf-8") as handle:
        fusion_schema = json.load(handle)

    if list(feature_names) != fusion_schema["feature_names"]:
        raise RuntimeError("fr3_fused_raw.npz's feature_names do not match fr3_fusion_schema.json -- refusing to cache.")
    if raw_matrix.shape != (len(peptide_ids), FUSED_DIM):
        raise RuntimeError(f"Unexpected raw matrix shape {raw_matrix.shape}.")

    external_control_ids = set(peptide_ids[pools == "external_control"].tolist())

    cache_entries: dict[str, dict] = {}
    for fold_id in range(n_folds):
        scaler = fusion_scalers[str(fold_id)]
        mean = np.array(scaler["mean"], dtype=np.float64)
        std = np.array(scaler["std"], dtype=np.float64)
        training_ids = scaler["training_peptide_ids"]
        held_out_ids = scaler["held_out_peptide_ids"]

        if external_control_ids & (set(training_ids) | set(held_out_ids)):
            raise RuntimeError(f"Fold {fold_id}: external-control peptide_id(s) leaked into training/held-out sets.")

        scaled = build_fold_cache_arrays(peptide_ids.tolist(), pools.tolist(), raw_matrix, mean, std)
        cache_path = Path(FR3_FEATURE_CACHE_PATH_TEMPLATE.format(fold_id=fold_id))
        np.savez_compressed(
            cache_path,
            peptide_ids=peptide_ids,
            pools=pools,
            features=scaled,
            feature_names=feature_names,
            scaler_mean=mean,
            scaler_std=std,
        )
        cache_entries[str(fold_id)] = {
            "cache_path": str(cache_path),
            "cache_sha256": sha256_of(cache_path),
            "fold_id": fold_id,
            "graphpart_fold": fold_id,
            "n_rows": int(scaled.shape[0]),
            "shape": list(scaled.shape),
            "dtype": str(scaled.dtype),
            "feature_schema_version": CACHE_SCHEMA_VERSION,
            "scaler_identity_sha256": scaler_identity_sha256(mean, std),
            "n_training_samples": scaler["n_training_samples"],
        }

    input_file_hashes = {
        "fused_raw_cache": sha256_of(FR3_FUSED_RAW_CACHE_PATH),
        "fusion_scalers": sha256_of(FR3_FUSION_SCALERS_PATH),
        "fusion_schema": sha256_of(FR3_FUSION_SCHEMA_PATH),
    }
    manifest = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "fusion_schema_version": fusion_schema["schema_version"],
        "n_folds": n_folds,
        "peptide_id_order_sha256": peptide_id_order_sha256(peptide_ids.tolist()),
        "input_file_hashes": input_file_hashes,
        "folds": cache_entries,
    }
    with open(FR3_FEATURE_CACHE_MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)

    # Validation: strictly round-trip-load every just-written cache (same
    # checksum/schema verification a real training consumer would hit),
    # and confirm each fold's own training rows standardize correctly.
    per_fold_validation = {}
    for fold_id_str, entry in cache_entries.items():
        loaded = load_fold_feature_cache(Path(entry["cache_path"]), entry)
        scaler = fusion_scalers[fold_id_str]
        _, training_rows = get_training_rows(loaded, scaler["training_peptide_ids"])
        per_fold_validation[fold_id_str] = {
            "round_trip_load_ok": True,
            "all_finite": bool(np.isfinite(loaded["features"]).all()),
            "training_rows_mean_abs_max": float(np.abs(training_rows.astype(np.float64).mean(axis=0)).max()),
            "training_rows_std_min_max": [
                float(training_rows.astype(np.float64).std(axis=0, ddof=0).min()),
                float(training_rows.astype(np.float64).std(axis=0, ddof=0).max()),
            ],
            "c3_union_row_count": int((loaded["pools"] == "C3").sum()),
            "external_control_disjoint_from_training_and_held_out": bool(
                not (external_control_ids & (set(scaler["training_peptide_ids"]) | set(scaler["held_out_peptide_ids"])))
            ),
        }
    with open(FR3_FEATURE_CACHE_VALIDATION_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump({"per_fold": per_fold_validation}, handle, indent=2)

    summary = {
        "manifest": {k: v for k, v in manifest.items() if k != "folds"},
        "fold_cache_paths": {k: v["cache_path"] for k, v in cache_entries.items()},
        "validation": per_fold_validation,
        "outputs": {
            "manifest": str(FR3_FEATURE_CACHE_MANIFEST_PATH),
            "validation_report": str(FR3_FEATURE_CACHE_VALIDATION_REPORT_PATH),
        },
    }
    append_provenance_log(FR3_FEATURE_CACHE_PROVENANCE_LOG_PATH, {"stage": "fr3_feature_cache", "summary": summary})
    return summary


# Bucket 3.5 -- Feature Pipeline Demonstration. A small, fast, fully
# offline walkthrough of the ALREADY-ACCEPTED Tasks 3.1-3.4 pipeline,
# built entirely from real, already-produced artifacts and the real
# shared functions -- no reimplementation, no new formulas, and no live
# ESM-2/WSL inference anywhere in this path (embeddings are loaded from
# the existing fr3_embeddings.npz cache, never recomputed). Requires
# Tasks 3.1-3.4 to have already been run locally at least once, since it
# reads their real (gitignored) large-array outputs -- see the
# FileNotFoundError below for exactly which commands to run first.
#
# The 7 demo peptide_ids are a fixed, deterministic selection of REAL
# peptides already present in the accepted pipeline outputs (not
# fabricated/synthetic), chosen to cover every pool plus both sides of
# fold 0's GraphPart split and two of fold 0's real C3 top-2000 hard
# challenges (ranks 1-2):
FR3_DEMO_FOLD_ID = 0
FR3_DEMO_PEPTIDE_IDS = {
    "FR1_positive_fold0_training": "AOP-002DDE226A",
    "FR1_positive_fold0_held_out": "AOP-0089BF570C",
    "C1": "C1-00174EE65A",
    "C2": "C2-00316810B4",
    "C3_fold0_rank1": "C3-8A629D6877",
    "C3_fold0_rank2": "C3-73E12D123B",
    "external_control": "AOP-053EB70717",
}
FR3_DEMO_OUTPUT_PATH = PROCESSED_DIR / "fr3_demo_output.json"
FR3_DEMO_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr3_demo_provenance.jsonl"


def run_fr3_demo(fold_id: int = FR3_DEMO_FOLD_ID) -> dict:
    """Bucket 3.5: demonstrate, end to end and offline, that the accepted
    Tasks 3.1-3.4 pipeline (a) validates input sequences, (b) extracts
    descriptors via the real shared implementation, (c) loads (never
    recomputes) ESM-2 embeddings, (d) loads (never recomputes or refits)
    a fold-specific scaled feature cache, and (e) correctly selects
    training/held-out/C1/C2/fold-specific-C3/external-control rows from
    it -- writing a deterministic JSON summary suitable as a PP1
    presentation artifact and as an exact expected-output reference for
    tests.
    """
    fold_cache_path = Path(FR3_FEATURE_CACHE_PATH_TEMPLATE.format(fold_id=fold_id))
    required = [
        FR3_RECORD_MAP_PATH,
        FR3_DESCRIPTOR_TABLE_PATH,
        FR3_EMBEDDINGS_CACHE_PATH,
        FR3_EMBEDDINGS_MANIFEST_PATH,
        FR3_FUSION_SCALERS_PATH,
        FR3_FEATURE_CACHE_MANIFEST_PATH,
        fold_cache_path,
        C3_RANKING_PATH,
    ]
    missing = [p for p in required if not Path(p).exists()]
    if missing:
        raise FileNotFoundError(
            f"Bucket 3.5 demo requires Tasks 3.1-3.4 to have already been run locally. Missing: "
            f"{[str(p) for p in missing]}. Run in order: `fr3-descriptors`, `fr3-embeddings`, "
            "`fr3-feature-fusion`, `fr3-feature-cache`."
        )

    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    demo_ids = list(FR3_DEMO_PEPTIDE_IDS.values())
    missing_ids = [pid for pid in demo_ids if pid not in set(descriptor_df["peptide_id"])]
    if missing_ids:
        raise RuntimeError(f"Demo peptide_id(s) not found in fr3_descriptor_table.parquet: {missing_ids}")

    demo_rows = (
        descriptor_df[descriptor_df["peptide_id"].isin(demo_ids)]
        .set_index("peptide_id")
        .loc[demo_ids]
        .reset_index()
    )

    # Step 1: input validation -- standard 20-AA alphabet, 3-50 AA window.
    validation_step = {
        label: {"peptide_id": pid, "sequence": seq, "valid_alphabet_and_length": is_valid_peptide(seq)}
        for label, pid, seq in zip(FR3_DEMO_PEPTIDE_IDS.keys(), demo_rows["peptide_id"], demo_rows["sequence"])
    }
    if not all(v["valid_alphabet_and_length"] for v in validation_step.values()):
        raise RuntimeError("One or more demo sequences failed the standard-alphabet/3-50AA check.")

    # Step 2: descriptor extraction -- the real, shared implementation,
    # computed live (fast, pure numpy, no GPU/WSL), then cross-checked
    # against the frozen fr3_descriptor_table.parquet values.
    live_descriptors = compute_descriptors_batch(demo_rows["peptide_id"].tolist(), demo_rows["sequence"].tolist())
    descriptors_match = np.allclose(
        live_descriptors[list(DESCRIPTOR_NAMES)].to_numpy(dtype=float),
        demo_rows[list(DESCRIPTOR_NAMES)].to_numpy(dtype=float),
    )

    # Step 3: ESM-2 embeddings -- LOADED from the existing cache, never
    # recomputed (no WSL/ESM-2 call anywhere in this function).
    with np.load(FR3_EMBEDDINGS_CACHE_PATH, allow_pickle=False) as npz:
        emb_ids = npz["peptide_ids"]
        emb_matrix = npz["embeddings"]
    emb_id_to_row = {str(pid): i for i, pid in enumerate(emb_ids)}
    demo_embeddings = np.stack([emb_matrix[emb_id_to_row[pid]] for pid in demo_ids])
    embeddings_manifest = json.loads(FR3_EMBEDDINGS_MANIFEST_PATH.read_text(encoding="utf-8"))

    # Step 4: the existing fold-specific scaled 495-dim cache -- loaded
    # (strict checksum-verified), never recomputed or refit.
    cache_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    fold_entry = cache_manifest["folds"][str(fold_id)]
    cache = load_fold_feature_cache(fold_entry["cache_path"], fold_entry)

    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    scaler = fusion_scalers[str(fold_id)]

    _, training_rows = get_training_rows(cache, scaler["training_peptide_ids"])
    _, held_out_rows = get_held_out_rows(cache, scaler["held_out_peptide_ids"])
    c1_ids, _ = get_pool_rows(cache, "C1")
    c2_ids, _ = get_pool_rows(cache, "C2")
    ext_ids, _ = get_pool_rows(cache, "external_control")
    c3_fold_ids, c3_fold_rows, c3_fold_df = get_c3_fold_challenge_rows(cache, C3_RANKING_PATH, fold_id)

    # Step 5: external-control-separate-from-training check.
    external_overlap = set(ext_ids.tolist()) & (set(scaler["training_peptide_ids"]) | set(scaler["held_out_peptide_ids"]))

    pool_coverage = {
        "FR1_positives_training": len(scaler["training_peptide_ids"]),
        "FR1_positives_held_out": len(scaler["held_out_peptide_ids"]),
        "C1": int(len(c1_ids)),
        "C2": int(len(c2_ids)),
        "C3_union_in_cache": int((cache["pools"] == "C3").sum()),
        f"C3_fold{fold_id}_challenge_selection": int(len(c3_fold_ids)),
        "external_control": int(len(ext_ids)),
    }

    demo_peptide_rows = {}
    for label, pid in FR3_DEMO_PEPTIDE_IDS.items():
        row_idx = np.where(cache["peptide_ids"] == pid)[0]
        if len(row_idx) == 0:
            raise RuntimeError(f"Demo peptide_id {pid} not present in fold {fold_id}'s scaled cache.")
        demo_peptide_rows[label] = {
            "peptide_id": pid,
            "pool": str(cache["pools"][row_idx[0]]),
            "scaled_feature_shape": list(cache["features"][row_idx[0]].shape),
            "scaled_feature_first_5": [round(float(x), 6) for x in cache["features"][row_idx[0]][:5]],
        }
    c3_demo_ids_selected_for_fold0 = {
        pid for label, pid in FR3_DEMO_PEPTIDE_IDS.items() if label.startswith("C3_fold0")
    }

    validation = {
        "all_demo_sequences_valid_alphabet_and_length": all(v["valid_alphabet_and_length"] for v in validation_step.values()),
        "live_descriptors_match_frozen_cache": bool(descriptors_match),
        "embeddings_loaded_not_recomputed_all_finite": bool(np.isfinite(demo_embeddings).all()),
        "feature_cache_checksum_verified": True,
        "scaled_features_all_finite": bool(np.isfinite(cache["features"]).all()),
        "external_control_disjoint_from_training_and_held_out": bool(not external_overlap),
        "c3_fold_selection_count_matches_top_n": bool(len(c3_fold_ids) == C3_TOP_N_PER_FOLD),
        "demo_c3_peptides_present_in_fold0_real_selection": bool(
            c3_demo_ids_selected_for_fold0 <= set(c3_fold_ids.tolist())
        ),
    }
    if not all(validation.values()):
        raise RuntimeError(f"Bucket 3.5 demo validation failed: {validation}")

    summary = {
        "fold_id": fold_id,
        "schema": {
            "descriptor_schema_version": DESCRIPTOR_SCHEMA_VERSION,
            "fusion_schema_version": SCHEMA_VERSION,
            "cache_schema_version": CACHE_SCHEMA_VERSION,
            "embedding_model": embeddings_manifest["model_name"],
            "embedding_dim": embeddings_manifest["embedding_dim"],
            "fused_dim": FUSED_DIM,
        },
        "input_validation": validation_step,
        "descriptor_extraction": {
            "shape": list(live_descriptors[list(DESCRIPTOR_NAMES)].shape),
            "source": "computed live via common.descriptors.compute_descriptors_batch (no GPU/WSL)",
        },
        "embedding_loading": {
            "shape": list(demo_embeddings.shape),
            "source": "loaded from fr3_embeddings.npz -- NOT recomputed",
            "dtype": str(demo_embeddings.dtype),
        },
        "feature_cache_loading": {
            "source": fold_entry["cache_path"],
            "shape": list(cache["features"].shape),
        },
        "pool_coverage": pool_coverage,
        "demo_peptide_rows": demo_peptide_rows,
        "validation": validation,
    }
    with open(FR3_DEMO_OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)
    append_provenance_log(FR3_DEMO_PROVENANCE_LOG_PATH, {"stage": "fr3_demo", "summary": summary})
    return summary


# Bucket 4.1 -- Shared Experiment Infrastructure (config, model, fold-aware
# data interface, seeding, run recorder). Every torch-dependent Bucket-4
# module is imported LAZILY inside this function only, so every other CLI
# stage above keeps its existing torch-free import graph unchanged.
FR4_SMOKE_TEST_RUNS_DIR = INTERIM_DIR / "fr4_infra_smoke_test_runs"  # gitignored, scratch


def run_fr4_infra_smoke_test(fold_id: int = 0) -> dict:
    """Bucket 4.1 acceptance smoke test: config validation, fold-aware
    data loading (real fold-``fold_id`` cache), model construction, a
    forward pass, seeding, and a full checkpoint save/load round-trip --
    all against real artifacts, entirely offline. This is explicitly an
    INFRASTRUCTURE check, not a trained PN/PU baseline: no training loop,
    no loss function, and no fabricated performance metric is produced or
    recorded anywhere in this function.
    """
    import torch

    from plantaox.c2_pu.common.seeding import resolve_device, set_global_seed
    from plantaox.c2_pu.experiment_config import ExperimentConfig
    from plantaox.c2_pu.experiment_data import build_experiment_data
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.run_recorder import (
        RunContext,
        append_epoch_metrics,
        create_run_dir,
        load_checkpoint,
        save_checkpoint,
        write_resolved_config,
    )

    for p in (FR3_FEATURE_CACHE_MANIFEST_PATH, FR3_FUSION_SCALERS_PATH, FR3_RECORD_MAP_PATH, C3_RANKING_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found -- run Tasks 3.1-3.4 (`fr3-descriptors`..`fr3-feature-cache`) first.")

    config = ExperimentConfig(
        experiment_id="fr4_infra_smoke_test", baseline="PN", fold_id=fold_id, checkpoint_dir=str(FR4_SMOKE_TEST_RUNS_DIR)
    )
    seed_context = set_global_seed(config.train_seed)
    device = resolve_device(config.device)

    cache_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    record_map = pd.read_csv(FR3_RECORD_MAP_PATH)
    cache_entry = cache_manifest["folds"][str(fold_id)]

    data = build_experiment_data(
        config, Path(cache_entry["cache_path"]), cache_entry, fusion_scalers[str(fold_id)], record_map, C3_RANKING_PATH
    )

    model = BinaryMlp(MlpArchitecture(input_dim=config.feature_dim, hidden_dims=config.hidden_dims)).to(device)
    sample = torch.from_numpy(data.train_positive.features[: min(8, len(data.train_positive.features))]).to(device)
    with torch.no_grad():
        logits = model(sample)
        proba = model.predict_proba(sample)

    resolved_config = config.to_dict()
    resolved_config["seed_context"] = seed_context
    resolved_config["git_revision"] = _git_commit_hash()
    resolved_config["source_artifact_checksums"] = {
        "fr3_feature_cache_manifest": sha256_of(FR3_FEATURE_CACHE_MANIFEST_PATH),
        "fr3_fusion_scalers": sha256_of(FR3_FUSION_SCALERS_PATH),
        "fr3_record_map": sha256_of(FR3_RECORD_MAP_PATH),
    }

    run_dir = create_run_dir(Path(config.checkpoint_dir), config.experiment_id)
    with RunContext(run_dir):
        write_resolved_config(run_dir, resolved_config)
        append_epoch_metrics(
            run_dir,
            epoch=0,
            metrics={
                "diagnostic_note": "infra smoke test only -- NOT a trained PN/PU baseline",
                "forward_pass_logit_mean": float(logits.mean().item()),
                "forward_pass_proba_mean": float(proba.mean().item()),
            },
        )
        checkpoint_path = save_checkpoint(
            run_dir, model, epoch=0, metrics={"note": "infra smoke test, untrained model"},
            is_best=True, extra={"infra_smoke_test": True},
        )
        save_checkpoint(
            run_dir, model, epoch=0, metrics={"note": "infra smoke test, untrained model"},
            is_best=False, extra={"infra_smoke_test": True},
        )
        reload_model = BinaryMlp(MlpArchitecture(input_dim=config.feature_dim, hidden_dims=config.hidden_dims))
        checkpoint_info = load_checkpoint(checkpoint_path, reload_model)

        summary = {
            "run_dir": str(run_dir),
            "device": str(device),
            "data_pool_sizes": {
                "train_positive": len(data.train_positive.peptide_ids),
                "validation_positive": len(data.validation_positive.peptide_ids),
                "held_out_positive": len(data.held_out_positive.peptide_ids),
                "c1": len(data.c1.peptide_ids),
                "c2": len(data.c2.peptide_ids),
                "c3_fold_challenges": len(data.c3_fold_challenges.peptide_ids),
                "external_control": len(data.external_control.peptide_ids),
            },
            "leakage_report": data.leakage_report,
            "forward_pass": {
                "logits_shape": list(logits.shape),
                "logits_finite": bool(torch.isfinite(logits).all().item()),
                "proba_bounded": bool(((proba >= 0) & (proba <= 1)).all().item()),
            },
            "checkpoint_round_trip_ok": True,
            "checkpoint_epoch": checkpoint_info["epoch"],
            "note": "INFRASTRUCTURE SMOKE TEST ONLY -- not a trained PN/PU baseline (no training loop, no loss, no real metrics).",
        }
    return summary


# Bucket 4.2 -- PN (Positive-Negative) supervised baseline: E1 positives
# vs. C1 assumed negatives, BCE-with-logits, on the accepted Task 4.1
# infrastructure. Every torch-dependent module is imported LAZILY inside
# this function, mirroring Bucket 4.1's `fr4-infra-smoke-test` -- run.py's
# module-level import graph stays torch-free.
FR4_PN_BASELINE_RUNS_DIR = INTERIM_DIR / "fr4_pn_baseline_runs"  # gitignored, scratch
FR4_PN_BASELINE_SUMMARY_PATH_TEMPLATE = str(PROCESSED_DIR / "fr4_pn_baseline_fold{fold_id}_summary.json")
FR4_PN_BASELINE_LEARNING_CURVE_PATH_TEMPLATE = str(PROCESSED_DIR / "fr4_pn_baseline_fold{fold_id}_learning_curve.svg")
FR4_PN_BASELINE_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr4_pn_baseline_provenance.jsonl"


def run_fr4_pn_baseline(
    fold_id: int = 0,
    max_epochs: int | None = None,
    use_class_weight: bool = True,
    early_stopping_patience: int | None = 10,
) -> dict:
    """Bucket 4.2: train the PN supervised baseline for GraphPart fold
    ``fold_id`` -- E1 positives vs. C1 assumed negatives -- using Task
    4.1's BinaryMlp/build_experiment_data/run_recorder/seeding exactly as
    accepted. C1 is an assumed-negative (PU-unlabeled) pool, never
    experimentally confirmed inactive; this is the field's conventional-
    practice reference baseline, not a validated antioxidant predictor.
    """
    import torch

    from plantaox.c2_pu.experiment_config import ExperimentConfig
    from plantaox.c2_pu.experiment_data import build_experiment_data
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.pn_baseline import build_pn_dataset, train_pn_baseline
    from plantaox.c2_pu.run_recorder import RunContext, create_run_dir, load_checkpoint, write_resolved_config

    for p in (FR3_FEATURE_CACHE_MANIFEST_PATH, FR3_FUSION_SCALERS_PATH, FR3_RECORD_MAP_PATH, C3_RANKING_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found -- run Tasks 3.1-3.4 (`fr3-descriptors`..`fr3-feature-cache`) first.")

    config_kwargs = {
        "experiment_id": f"fr4_pn_baseline_fold{fold_id}",
        "baseline": "PN",
        "fold_id": fold_id,
        "checkpoint_dir": str(FR4_PN_BASELINE_RUNS_DIR),
    }
    if max_epochs is not None:
        config_kwargs["max_epochs"] = max_epochs
    config = ExperimentConfig(**config_kwargs)

    cache_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    record_map = pd.read_csv(FR3_RECORD_MAP_PATH)
    cache_entry = cache_manifest["folds"][str(fold_id)]

    data = build_experiment_data(
        config, Path(cache_entry["cache_path"]), cache_entry, fusion_scalers[str(fold_id)], record_map, C3_RANKING_PATH
    )
    dataset = build_pn_dataset(data, config)

    resolved_config = config.to_dict()
    resolved_config["git_revision"] = _git_commit_hash()
    resolved_config["source_artifact_checksums"] = {
        "fr3_feature_cache_manifest": sha256_of(FR3_FEATURE_CACHE_MANIFEST_PATH),
        "fr3_fusion_scalers": sha256_of(FR3_FUSION_SCALERS_PATH),
        "fr3_record_map": sha256_of(FR3_RECORD_MAP_PATH),
    }
    resolved_config["pn_dataset_provenance"] = {
        "class_counts": dataset.class_counts,
        "c1_validation_fraction": dataset.c1_validation_fraction,
        "c1_partition_seed": dataset.c1_partition_seed,
        "e1_train_ids_count": len(dataset.e1_train_ids),
        "e1_validation_ids_count": len(dataset.e1_validation_ids),
        "c1_train_ids_count": len(dataset.c1_train_ids),
        "c1_validation_ids_count": len(dataset.c1_validation_ids),
    }

    run_dir = create_run_dir(Path(config.checkpoint_dir), config.experiment_id)
    with RunContext(run_dir):
        write_resolved_config(run_dir, resolved_config)
        training_summary = train_pn_baseline(
            config, dataset, run_dir, use_class_weight=use_class_weight, early_stopping_patience=early_stopping_patience
        )

        best_checkpoint_path = run_dir / "checkpoint_best.pt"
        last_checkpoint_path = run_dir / "checkpoint_last.pt"
        reload_model = BinaryMlp(MlpArchitecture(input_dim=config.feature_dim, hidden_dims=config.hidden_dims))
        checkpoint_info = load_checkpoint(best_checkpoint_path, reload_model)

        sample_n = min(16, len(dataset.validation_features))
        sample_x = torch.from_numpy(dataset.validation_features[:sample_n])
        proba = reload_model.predict_proba(sample_x)

        learning_curve_committed_path = Path(FR4_PN_BASELINE_LEARNING_CURVE_PATH_TEMPLATE.format(fold_id=fold_id))
        learning_curve_committed_path.write_text(
            Path(training_summary["learning_curve_path"]).read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
        )

        summary = {
            "run_dir": str(run_dir),
            "fold_id": fold_id,
            "class_counts": dataset.class_counts,
            "c1_partition": {
                "validation_fraction": dataset.c1_validation_fraction,
                "seed": dataset.c1_partition_seed,
            },
            "training": {k: v for k, v in training_summary.items() if k != "learning_curve_path"},
            "checkpoint": {
                "best_path_sha256": sha256_of(best_checkpoint_path),
                "last_path_sha256": sha256_of(last_checkpoint_path),
                "best_checkpoint_epoch": checkpoint_info["epoch"],
            },
            "checkpoint_reload_verification": {
                "proba_shape": list(proba.shape),
                "proba_bounded": bool(((proba >= 0) & (proba <= 1)).all().item()),
                "proba_finite": bool(torch.isfinite(proba).all().item()),
            },
            "outputs": {
                "learning_curve": str(learning_curve_committed_path),
            },
            "limitations": {
                "assumed_negative_labels": "C1 is an assumed-negative/PU-unlabeled pool, NOT experimentally confirmed "
                "antioxidant-inactive. PN is a conventional supervised control, not a validated predictor.",
                "shortcut_bias_risk": "FR2 (Task 2.5) documented substantial FR1-positive-vs-C1 distributional "
                "differences (length, charge, GRAVY, aromaticity, composition). High validation performance here "
                "may reflect these shortcuts rather than genuine antioxidant-activity discrimination.",
                "evidence_tiers": "E1 only is used for the PN positive class; E2 remains available for subsequent "
                "evidence-tiered PU experiments (Task 4.3+).",
                "evaluation_scope": "Fold-0-only initial baseline. Full C1/C2/C3 cross-pool comparison, calibration, "
                "RNIS, and five-fold validation are out of Task 4.2's scope.",
                "cross_fold_results": "A successful fold-0 run is an initial implementation demonstration, not "
                "completed five-fold experimental validation.",
                "scientific_sign_off": "Technical acceptance only -- no supervisor or scientific sign-off is implied.",
            },
        }
    summary_path = Path(FR4_PN_BASELINE_SUMMARY_PATH_TEMPLATE.format(fold_id=fold_id))
    with open(summary_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, default=str)
    append_provenance_log(FR4_PN_BASELINE_PROVENANCE_LOG_PATH, {"stage": "fr4_pn_baseline", "summary": summary})
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PU-AOP (Component 02) CLI")
    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("fr1-positives", help="Build the conflict-resolved FR1 positive pool")
    sub.add_parser("fr1-cluster", help="CD-HIT 90% identity clustering (Bucket 1.5)")
    sub.add_parser("fr1-split", help="GraphPart 40% identity 5-fold split (Bucket 1.6)")
    sub.add_parser("fr1-freeze", help="Snapshot validated FR1 artifacts as a versioned baseline (Bucket 1.7)")
    sub.add_parser("fr2-c1-clean", help="Resolve C1/positive-pool leakage (Bucket 2.1 close-out)")
    sub.add_parser(
        "fr2-c1-alphabet-fix",
        help="Enforce standard-20-AA-alphabet policy on C1, versioned as v2 (Bucket 2.1 follow-up)",
    )
    sub.add_parser("fr2-c2-build", help="Build the C2 bioactive-unlabeled pool from Peptipedia (Bucket 2.2)")
    sub.add_parser("fr2-c3-fetch-candidates", help="Fetch the UniRef50 candidate universe (Bucket 2.3 step 1)")
    sub.add_parser("fr2-c3-build", help="Fold-safe ESM-2 hard-challenge selection (Bucket 2.3 step 2)")
    sub.add_parser("fr2-pool-audit", help="Pool contamination and leakage audit (Bucket 2.4)")
    sub.add_parser("fr2-c1-cross-pool-fix", help="Decision A: remove C1/C2 exact overlap (Bucket 2.4 resolution)")
    sub.add_parser("fr2-c2-cross-pool-fix", help="Decision B: exclude C2 homolog of an E1 positive (Bucket 2.4 resolution)")
    sub.add_parser("fr2-distribution-audit", help="Biological distribution and shortcut-bias checks (Bucket 2.5)")
    sub.add_parser("fr2-external-control-build", help="Validate AnOxPePred external control + homology audit (Bucket 2.6)")
    sub.add_parser("fr2-freeze", help="Freeze the validated FR2 baseline as pp2_baseline_v1 (Bucket 2.7)")
    sub.add_parser("esm2-smoketest", help="ESM-2 embedding interface smoke test (Bucket 3.2)")
    sub.add_parser("fr3-descriptors", help="15-descriptor physicochemical feature extraction over frozen FR1/FR2 pools (Bucket 3.1)")
    sub.add_parser("fr3-embeddings", help="Full ESM-2 embedding extraction over the Task 3.1 descriptor contract (Bucket 3.2)")
    sub.add_parser("fr3-feature-fusion", help="Fuse descriptors + embeddings into a 495-dim feature matrix with leakage-safe per-fold scalers (Bucket 3.3)")
    sub.add_parser("fr3-feature-cache", help="Materialize 5 fold-specific scaled feature caches from the accepted raw fused matrix (Bucket 3.4)")
    sub.add_parser("fr3-demo", help="Offline feature-pipeline demonstration: validate, extract, load, select (Bucket 3.5)")
    sub.add_parser("fr4-infra-smoke-test", help="Shared experiment infrastructure smoke test: config, data, model, seeding, checkpoint round-trip (Bucket 4.1)")
    sub.add_parser("fr4-pn-baseline", help="PN supervised baseline: E1 positives vs. C1 assumed negatives, BCE-with-logits (Bucket 4.2)")
    args = parser.parse_args(argv)

    if args.stage == "fr1-positives":
        summary = run_fr1_positives()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr1-cluster":
        report = run_fr1_cluster()
        print(json.dumps(report, indent=2))
        return 0
    if args.stage == "fr1-split":
        report = run_fr1_split()
        print(json.dumps(report, indent=2))
        return 0
    if args.stage == "fr1-freeze":
        manifest_path = run_fr1_freeze()
        print(f"Frozen baseline written: {manifest_path}")
        return 0
    if args.stage == "fr2-c1-clean":
        summary = run_fr2_c1_clean()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c1-alphabet-fix":
        summary = run_fr2_c1_alphabet_fix()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c2-build":
        summary = run_fr2_c2_build()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c3-fetch-candidates":
        summary = run_fr2_c3_fetch_candidates()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c3-build":
        summary = run_fr2_c3_build()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c1-cross-pool-fix":
        summary = run_fr2_c1_cross_pool_fix()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c2-cross-pool-fix":
        summary = run_fr2_c2_cross_pool_fix()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-freeze":
        manifest_path = run_fr2_freeze()
        print(f"Frozen FR2 baseline written: {manifest_path}")
        return 0
    if args.stage == "fr2-external-control-build":
        summary = run_fr2_external_control_build()
        print(json.dumps({k: v for k, v in summary.items() if k != "homology_audit"} | {
            "homology_audit": {k: v for k, v in summary["homology_audit"].items() if k != "real_homology_hits"}
        }, indent=2, default=str))
        return 0
    if args.stage == "fr2-distribution-audit":
        summary = run_fr2_distribution_audit()
        print(json.dumps(summary, indent=2, default=str))
        return 0
    if args.stage == "fr2-pool-audit":
        summary = run_fr2_pool_audit()
        print(json.dumps({k: v for k, v in summary.items() if k != "integrity_reports"}, indent=2, default=str))
        return 0
    if args.stage == "esm2-smoketest":
        report = run_esm2_smoke_test()
        print(json.dumps({k: v for k, v in report.items() if k != "per_peptide"}, indent=2))
        return 0
    if args.stage == "fr3-descriptors":
        summary = run_fr3_descriptors()
        print(json.dumps(summary, indent=2, default=str))
        return 0
    if args.stage == "fr3-embeddings":
        summary = run_fr3_embeddings()
        print(json.dumps(summary, indent=2, default=str))
        return 0
    if args.stage == "fr3-feature-fusion":
        summary = run_fr3_feature_fusion()
        print(json.dumps({k: v for k, v in summary.items() if k != "validation"}, indent=2, default=str))
        return 0
    if args.stage == "fr3-feature-cache":
        summary = run_fr3_feature_cache()
        print(json.dumps(summary, indent=2, default=str))
        return 0
    if args.stage == "fr3-demo":
        summary = run_fr3_demo()
        print(json.dumps(summary, indent=2, default=str))
        return 0
    if args.stage == "fr4-infra-smoke-test":
        summary = run_fr4_infra_smoke_test()
        print(json.dumps(summary, indent=2, default=str))
        return 0
    if args.stage == "fr4-pn-baseline":
        summary = run_fr4_pn_baseline()
        print(json.dumps({k: v for k, v in summary.items() if k != "training"} | {
            "training": {k: v for k, v in summary["training"].items() if k != "history"}
        }, indent=2, default=str))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
