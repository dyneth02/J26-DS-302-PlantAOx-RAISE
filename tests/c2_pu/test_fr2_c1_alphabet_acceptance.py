"""FR2 Bucket 2.1 follow-up acceptance checks: the standard-20-amino-acid
alphabet policy fix (2026-10-14), applied to the real, full v2 C1 artifact
(not a sample). Skips cleanly if not present.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from plantaox.c2_pu.common.io import read_fasta
from plantaox.c2_pu.common.sequence import is_standard_alphabet
from plantaox.c2_pu.run import run_fr2_c1_alphabet_fix

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

V1_FASTA_PATH = PROCESSED_DIR / "stage_c1_decoys.fasta"
V2_FASTA_PATH = PROCESSED_DIR / "stage_c1_decoys_v2.fasta"
V2_ACCESSION_MAP_PATH = PROCESSED_DIR / "c1_accession_map_v2.csv"
ALPHABET_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c1_alphabet_exclusion_log.csv"
ALPHABET_REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c1_alphabet_replacement_log.csv"
ALPHABET_FIX_REPORT_PATH = PROCESSED_DIR / "c1_alphabet_fix_report.json"
POSITIVE_POOL_PATH = PROCESSED_DIR / "aop_positives_provisional.parquet"
CONFLICT_LOG_PATH = REPO_ROOT / "data" / "interim" / "c2_pu" / "label_conflicts_anox_vs_multiaop.csv"

pytestmark = pytest.mark.skipif(
    not V2_FASTA_PATH.exists(), reason="FR2 C1 v2 (alphabet-fixed) pool not present in this checkout"
)


def test_v1_artifact_preserved_untouched_as_historical_evidence():
    # The explicit instruction was to preserve the existing accepted v1
    # artifact and version the correction separately, not overwrite it --
    # if this ever fails, v1 was mutated in place.
    v1_records = read_fasta(V1_FASTA_PATH)
    non_standard_in_v1 = [s for _, s in v1_records if not is_standard_alphabet(s)]
    assert len(non_standard_in_v1) == 260  # record-level count (259 unique sequences)


def test_v2_pool_has_zero_non_standard_alphabet_sequences():
    records = read_fasta(V2_FASTA_PATH)
    assert len(records) == 5000
    assert all(is_standard_alphabet(s) for _, s in records)


def test_v2_pool_has_zero_contamination_against_positives_and_conflicts():
    clean_seqs = {s for _, s in read_fasta(V2_FASTA_PATH)}
    screen = set(pd.read_parquet(POSITIVE_POOL_PATH)["sequence"]) | set(
        pd.read_csv(CONFLICT_LOG_PATH)["sequence"]
    )
    assert clean_seqs.isdisjoint(screen)


def test_v2_pool_record_count_and_length_window():
    records = read_fasta(V2_FASTA_PATH)
    assert len(records) == 5000
    lengths = [len(s) for _, s in records]
    assert min(lengths) >= 3
    assert max(lengths) <= 50


def test_alphabet_logs_are_consistent_with_the_report():
    report = json.loads(ALPHABET_FIX_REPORT_PATH.read_text())
    exclusion_df = pd.read_csv(ALPHABET_EXCLUSION_LOG_PATH)
    replacement_df = pd.read_csv(ALPHABET_REPLACEMENT_LOG_PATH)
    assert len(exclusion_df) == report["n_non_standard_removed"] == 260
    assert len(replacement_df) == report["n_replacements_made"] == 260
    assert report["shortfall"] == 0


def test_v2_accession_map_covers_every_record_with_no_duplicates():
    records = read_fasta(V2_FASTA_PATH)
    accession_map = pd.read_csv(V2_ACCESSION_MAP_PATH)
    assert len(accession_map) == len(records)
    assert set(accession_map["sequence"]) == {s for _, s in records}


def test_replacements_are_disjoint_from_removed_non_standard_sequences():
    exclusion_df = pd.read_csv(ALPHABET_EXCLUSION_LOG_PATH)
    replacement_df = pd.read_csv(ALPHABET_REPLACEMENT_LOG_PATH)
    assert set(exclusion_df["sequence"]).isdisjoint(set(replacement_df["sequence"]))


def test_rerunning_alphabet_fix_is_reproducible():
    import hashlib

    def file_hash(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    before = {
        p: file_hash(p)
        for p in [
            V2_FASTA_PATH,
            ALPHABET_EXCLUSION_LOG_PATH,
            ALPHABET_REPLACEMENT_LOG_PATH,
            V2_ACCESSION_MAP_PATH,
        ]
    }
    run_fr2_c1_alphabet_fix()
    after = {p: file_hash(p) for p in before}
    for p in before:
        assert before[p] == after[p], f"{p.name} changed across a reproducibility re-run"
