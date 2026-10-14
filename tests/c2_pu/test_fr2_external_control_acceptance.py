"""FR2 Bucket 2.6 acceptance checks against the real, full external-control
validation artifacts. Skips cleanly if not present.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from plantaox.c2_pu.common.io import read_fasta
from plantaox.c2_pu.common.sequence import is_standard_alphabet
from plantaox.c2_pu.run import (
    EXT_CONTROL_BIOPEP_CONFLICT_PEPTIDE_IDS,
    EXT_CONTROL_HOMOLOGY_IDENTITY_THRESHOLD,
    EXT_CONTROL_HOMOLOGY_LENGTH_FLOOR,
    EXT_CONTROL_HOMOLOGY_PAIRS_PATH,
    EXT_CONTROL_REPORT_PATH,
    EXT_CONTROL_VALIDATED_PATH,
    FROZEN_EXTERNAL_CONTROL_PATH,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"
POSITIVE_POOL_PATH = PROCESSED_DIR / "frozen" / "pp1_baseline_v1" / "aop_positives_provisional.parquet"
C1_V3_PATH = PROCESSED_DIR / "stage_c1_decoys_v3.fasta"
C2_V2_PATH = PROCESSED_DIR / "stage_c2_bioactive_unlabeled_v2.fasta"
C3_FASTA_PATH = PROCESSED_DIR / "stage_c3_esm2_hard_challenges.fasta"

pytestmark = pytest.mark.skipif(
    not EXT_CONTROL_VALIDATED_PATH.exists(), reason="FR2 external control validation not present in this checkout"
)


def test_frozen_external_control_is_untouched():
    frozen_df = pd.read_csv(FROZEN_EXTERNAL_CONTROL_PATH)
    assert len(frozen_df) == 38
    assert frozen_df["sequence"].nunique() == 38


def test_validated_artifact_has_same_38_records_with_added_columns_only():
    frozen_df = pd.read_csv(FROZEN_EXTERNAL_CONTROL_PATH)
    validated_df = pd.read_csv(EXT_CONTROL_VALIDATED_PATH)
    assert len(validated_df) == len(frozen_df) == 38
    assert set(frozen_df["sequence"]) == set(validated_df["sequence"])
    assert set(frozen_df.columns).issubset(set(validated_df.columns))
    assert "has_biopep_antioxidative_conflict" in validated_df.columns
    assert "max_identity_pct_vs_positives_length_ge_15" in validated_df.columns


def test_validated_artifact_is_standard_alphabet_and_in_length_window():
    validated_df = pd.read_csv(EXT_CONTROL_VALIDATED_PATH)
    assert all(is_standard_alphabet(s) for s in validated_df["sequence"])
    assert validated_df["length"].between(3, 50).all()


def test_biopep_conflicts_are_flagged_but_not_excluded():
    validated_df = pd.read_csv(EXT_CONTROL_VALIDATED_PATH)
    flagged = validated_df[validated_df["has_biopep_antioxidative_conflict"]]
    assert set(flagged["peptide_id"]) == set(EXT_CONTROL_BIOPEP_CONFLICT_PEPTIDE_IDS)
    assert len(flagged) == 2


def test_external_control_has_zero_exact_overlap_with_every_other_pool():
    ext_seqs = set(pd.read_csv(EXT_CONTROL_VALIDATED_PATH)["sequence"])
    positives = set(pd.read_parquet(POSITIVE_POOL_PATH)["sequence"])
    c1 = {s for _, s in read_fasta(C1_V3_PATH)}
    c2 = {s for _, s in read_fasta(C2_V2_PATH)}
    c3 = {s for _, s in read_fasta(C3_FASTA_PATH)}
    assert ext_seqs.isdisjoint(positives)
    assert ext_seqs.isdisjoint(c1)
    assert ext_seqs.isdisjoint(c2)
    assert ext_seqs.isdisjoint(c3)


def test_homology_pairs_file_covers_every_external_control_x_positive_pair():
    pairs_df = pd.read_csv(EXT_CONTROL_HOMOLOGY_PAIRS_PATH)
    n_positives = len(pd.read_parquet(POSITIVE_POOL_PATH))
    assert len(pairs_df) == 38 * n_positives
    assert pairs_df["identity_pct"].between(0, 100).all()


def test_report_confirms_zero_real_homology_hits_at_the_documented_threshold():
    report = json.loads(EXT_CONTROL_REPORT_PATH.read_text())
    audit = report["homology_audit"]
    assert audit["identity_threshold_pct"] == EXT_CONTROL_HOMOLOGY_IDENTITY_THRESHOLD
    assert audit["length_floor_for_interpretation"] == EXT_CONTROL_HOMOLOGY_LENGTH_FLOOR
    assert audit["n_real_homology_hits"] == 0
    assert audit["held_out_fold_violations"] == []
    # Every pair accounted for -- no silent needleall minscore drop.
    assert audit["n_pairs_total"] == audit["n_pairs_expected"]


def test_labeling_rule_is_explicit_about_assay_scope_not_universal_claim():
    report = json.loads(EXT_CONTROL_REPORT_PATH.read_text())
    assert "NOT a universal claim" in report["labeling_rule"]


@pytest.mark.skipif(
    not Path("data/raw/c2_pu/UniProt_decoys/uniprotkb_candidates.fasta").exists(),
    reason="Dependencies for a full re-run not present locally",
)
def test_rerunning_external_control_build_is_reproducible():
    import hashlib

    from plantaox.c2_pu.run import run_fr2_external_control_build

    def file_hash(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    before = {p: file_hash(p) for p in [EXT_CONTROL_VALIDATED_PATH, EXT_CONTROL_HOMOLOGY_PAIRS_PATH]}
    run_fr2_external_control_build()
    after = {p: file_hash(p) for p in before}
    for p in before:
        assert before[p] == after[p], f"{p.name} changed across a reproducibility re-run"
