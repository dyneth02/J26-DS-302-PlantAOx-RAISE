"""FR2 Bucket 2.2 acceptance checks against the real, full C2 artifact (not
a sample). Skips cleanly if the Peptipedia raw dump isn't present locally
(it's gitignored -- too large to commit, see .gitignore) or the built
pool hasn't been generated yet.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from plantaox.c2_pu.common.io import read_fasta
from plantaox.c2_pu.common.sequence import is_standard_alphabet
from plantaox.c2_pu.run import C2_RAW_DUMP_PATH, run_fr2_c2_build

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

C2_FASTA_PATH = PROCESSED_DIR / "stage_c2_bioactive_unlabeled.fasta"
C2_ACTIVITY_MAP_PATH = PROCESSED_DIR / "c2_activity_map.csv"
C2_BUILD_REPORT_PATH = PROCESSED_DIR / "c2_build_report.json"
POSITIVE_POOL_PATH = PROCESSED_DIR / "aop_positives_provisional.parquet"
CONFLICT_LOG_PATH = REPO_ROOT / "data" / "interim" / "c2_pu" / "label_conflicts_anox_vs_multiaop.csv"

pytestmark = pytest.mark.skipif(
    not C2_FASTA_PATH.exists(), reason="FR2 C2 bioactive pool not present in this checkout"
)


def test_c2_pool_has_approximately_2000_unique_records():
    records = read_fasta(C2_FASTA_PATH)
    assert len(records) == 2000
    assert len({h for h, _ in records}) == 2000  # peptide IDs unique
    assert len({s for _, s in records}) == 2000  # sequences unique (no resampling needed)


def test_c2_pool_is_standard_alphabet_and_in_length_window():
    records = read_fasta(C2_FASTA_PATH)
    assert all(is_standard_alphabet(s) for _, s in records)
    lengths = [len(s) for _, s in records]
    assert min(lengths) >= 3
    assert max(lengths) <= 50


def test_c2_pool_has_zero_overlap_with_fr1_positives_and_conflicts():
    seqs = {s for _, s in read_fasta(C2_FASTA_PATH)}
    screen = set(pd.read_parquet(POSITIVE_POOL_PATH)["sequence"]) | set(
        pd.read_csv(CONFLICT_LOG_PATH)["sequence"]
    )
    assert seqs.isdisjoint(screen)


def test_c2_pool_has_no_antioxidant_tagged_records():
    activity_map = pd.read_csv(C2_ACTIVITY_MAP_PATH)
    assert not activity_map["activity_names"].str.contains("anti oxidative", case=False).any()
    activity_id_sets = activity_map["activity_ids"].astype(str).str.split(";")
    assert not activity_id_sets.apply(lambda ids: "41" in ids).any()


def test_activity_map_covers_every_record_with_no_duplicates():
    records = read_fasta(C2_FASTA_PATH)
    activity_map = pd.read_csv(C2_ACTIVITY_MAP_PATH)
    assert len(activity_map) == len(records)
    assert set(activity_map["sequence"]) == {s for _, s in records}
    assert set(activity_map["peptide_id"]) == {h for h, _ in records}


def test_build_report_is_consistent_with_the_pool():
    report = json.loads(C2_BUILD_REPORT_PATH.read_text())
    assert report["n_output_records"] == 2000
    assert report["shortfall"] == 0
    assert report["antioxidant_activity_id"] == 41


@pytest.mark.skipif(not C2_RAW_DUMP_PATH.exists(), reason="Peptipedia raw dump not present locally")
def test_rerunning_c2_build_is_reproducible():
    import hashlib

    def file_hash(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    before = {p: file_hash(p) for p in [C2_FASTA_PATH, C2_ACTIVITY_MAP_PATH]}
    run_fr2_c2_build()
    after = {p: file_hash(p) for p in before}
    for p in before:
        assert before[p] == after[p], f"{p.name} changed across a reproducibility re-run"
