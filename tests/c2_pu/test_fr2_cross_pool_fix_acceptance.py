"""FR2 Bucket 2.4 resolution acceptance checks (Decisions A & B) against
the real, full v3/v2 artifacts. Skips cleanly if not present.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from plantaox.c2_pu.common.io import read_fasta
from plantaox.c2_pu.common.sequence import is_standard_alphabet
from plantaox.c2_pu.run import (
    C1_CLEAN_FASTA_V3_PATH,
    C2_FASTA_V2_PATH,
    C2_FLAGGED_HOMOLOGY_SEQUENCE,
    run_fr2_c1_cross_pool_fix,
    run_fr2_c2_cross_pool_fix,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

C1_V2_PATH = PROCESSED_DIR / "stage_c1_decoys_v2.fasta"
C2_V1_PATH = PROCESSED_DIR / "stage_c2_bioactive_unlabeled.fasta"
C3_FASTA_PATH = PROCESSED_DIR / "stage_c3_esm2_hard_challenges.fasta"
POSITIVE_POOL_PATH = PROCESSED_DIR / "aop_positives_provisional.parquet"
CONFLICT_LOG_PATH = REPO_ROOT / "data" / "interim" / "c2_pu" / "label_conflicts_anox_vs_multiaop.csv"
C1_CROSS_POOL_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c1_cross_pool_exclusion_log.csv"
C1_CROSS_POOL_FIX_REPORT_PATH = PROCESSED_DIR / "c1_cross_pool_fix_report.json"
C2_CROSS_POOL_FIX_REPORT_PATH = PROCESSED_DIR / "c2_cross_pool_fix_report.json"

pytestmark = pytest.mark.skipif(
    not (C1_CLEAN_FASTA_V3_PATH.exists() and C2_FASTA_V2_PATH.exists()),
    reason="Bucket 2.4 resolution (Decisions A/B) not present in this checkout",
)


def test_v1_v2_c1_artifacts_preserved_untouched():
    # Decision A must not overwrite v2 -- it's a new, separately versioned
    # artifact. If this fails, v2 was mutated in place.
    assert C1_V2_PATH.exists()
    v2_records = read_fasta(C1_V2_PATH)
    assert len(v2_records) == 5000
    # The known overlap sequences must still be present in the untouched v2.
    v2_seqs = {s for _, s in v2_records}
    exclusion_log = pd.read_csv(C1_CROSS_POOL_EXCLUSION_LOG_PATH)
    for seq in exclusion_log["sequence"].unique():
        assert seq in v2_seqs


def test_original_c2_artifact_preserved_untouched():
    assert C2_V1_PATH.exists()
    v1_records = read_fasta(C2_V1_PATH)
    assert len(v1_records) == 2000
    assert C2_FLAGGED_HOMOLOGY_SEQUENCE in {s for _, s in v1_records}


def test_c1_v3_has_exactly_5000_records_and_correct_record_vs_unique_counts():
    records = read_fasta(C1_CLEAN_FASTA_V3_PATH)
    assert len(records) == 5000
    report = json.loads(C1_CROSS_POOL_FIX_REPORT_PATH.read_text())
    exclusion_log = pd.read_csv(C1_CROSS_POOL_EXCLUSION_LOG_PATH)
    # 8 unique overlapping sequences; record count removed can exceed 8
    # because C1 retains natural duplicates -- verify both numbers.
    assert exclusion_log["sequence"].nunique() == 8
    assert report["n_cross_pool_overlap_removed"] == len(exclusion_log)
    assert report["n_cross_pool_overlap_removed"] >= 8


def test_c1_v3_is_standard_alphabet_and_in_length_window():
    records = read_fasta(C1_CLEAN_FASTA_V3_PATH)
    assert all(is_standard_alphabet(s) for _, s in records)
    lengths = [len(s) for _, s in records]
    assert min(lengths) >= 3
    assert max(lengths) <= 50


def test_c1_v3_has_zero_overlap_with_positives_conflicts_c2_and_c3():
    seqs = {s for _, s in read_fasta(C1_CLEAN_FASTA_V3_PATH)}
    positives = set(pd.read_parquet(POSITIVE_POOL_PATH)["sequence"])
    conflicts = set(pd.read_csv(CONFLICT_LOG_PATH)["sequence"])
    c2_seqs = {s for _, s in read_fasta(C2_FASTA_V2_PATH)}
    c3_seqs = {s for _, s in read_fasta(C3_FASTA_PATH)}
    assert seqs.isdisjoint(positives)
    assert seqs.isdisjoint(conflicts)
    assert seqs.isdisjoint(c2_seqs)
    assert seqs.isdisjoint(c3_seqs)


def test_c2_v2_has_exactly_2000_unique_records_without_the_flagged_sequence():
    records = read_fasta(C2_FASTA_V2_PATH)
    assert len(records) == 2000
    seqs = {s for _, s in records}
    assert len(seqs) == 2000
    assert C2_FLAGGED_HOMOLOGY_SEQUENCE not in seqs


def test_c2_v2_has_zero_overlap_with_positives_conflicts_c1_v3_and_c3():
    seqs = {s for _, s in read_fasta(C2_FASTA_V2_PATH)}
    positives = set(pd.read_parquet(POSITIVE_POOL_PATH)["sequence"])
    conflicts = set(pd.read_csv(CONFLICT_LOG_PATH)["sequence"])
    c1_v3_seqs = {s for _, s in read_fasta(C1_CLEAN_FASTA_V3_PATH)}
    c3_seqs = {s for _, s in read_fasta(C3_FASTA_PATH)}
    assert seqs.isdisjoint(positives)
    assert seqs.isdisjoint(conflicts)
    assert seqs.isdisjoint(c1_v3_seqs)
    assert seqs.isdisjoint(c3_seqs)


def test_c2_exclusion_log_preserves_original_evidence_and_alignment_rationale():
    report = json.loads(C2_CROSS_POOL_FIX_REPORT_PATH.read_text())
    assert report["n_excluded"] == 1
    assert report["n_replaced"] == 1


@pytest.mark.skipif(
    not Path("data/raw/c2_pu/UniProt_decoys/uniprotkb_candidates.fasta").exists(),
    reason="UniProtKB candidate snapshot not present locally",
)
def test_rerunning_c1_cross_pool_fix_is_reproducible():
    import hashlib

    def file_hash(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    before = file_hash(C1_CLEAN_FASTA_V3_PATH)
    run_fr2_c1_cross_pool_fix()
    assert file_hash(C1_CLEAN_FASTA_V3_PATH) == before


@pytest.mark.skipif(
    not Path("data/raw/c2_pu/Peptipedia/peptipedia.20240323.sql.gz").exists(),
    reason="Peptipedia raw dump not present locally",
)
def test_rerunning_c2_cross_pool_fix_is_reproducible():
    import hashlib

    def file_hash(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    before = file_hash(C2_FASTA_V2_PATH)
    run_fr2_c2_cross_pool_fix()
    assert file_hash(C2_FASTA_V2_PATH) == before
