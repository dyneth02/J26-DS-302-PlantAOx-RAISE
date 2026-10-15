"""Tests for curation.dedup's CD-HIT .clstr parser and report builder.

These test the parsing/reporting LOGIC against synthetic .clstr fixtures and
do not require cd-hit itself to be installed. The actual subprocess call
(run_cdhit) is exercised separately once WSL + cd-hit are available -- see
IMPLEMENTATION_STATUS.md for that setup step.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from plantaox.c2_pu.curation.dedup import (
    build_cluster_report,
    clusters_to_dataframe,
    parse_cdhit_clusters,
    to_wsl_path,
)

SAMPLE_CLSTR = """>Cluster 0
0\t10aa, >AOP-AAAAAAAAAA... *
1\t8aa, >AOP-BBBBBBBBBB... at 87.50%
>Cluster 1
0\t3aa, >AOP-CCCCCCCCCC... *
>Cluster 2
0\t12aa, >AOP-DDDDDDDDDD... *
1\t11aa, >AOP-EEEEEEEEEE... at 91.67%
2\t11aa, >AOP-FFFFFFFFFF... at 90.00%
"""


@pytest.fixture
def sample_clstr_path(tmp_path: Path) -> Path:
    path = tmp_path / "sample.fasta.clstr"
    path.write_text(SAMPLE_CLSTR, encoding="utf-8")
    return path


def test_parse_cdhit_clusters_basic(sample_clstr_path):
    members = parse_cdhit_clusters(sample_clstr_path)
    assert len(members) == 6
    assert {m.cluster_id for m in members} == {0, 1, 2}

    reps = [m for m in members if m.is_representative]
    assert len(reps) == 3  # one representative per cluster
    assert {m.peptide_id for m in reps} == {
        "AOP-AAAAAAAAAA",
        "AOP-CCCCCCCCCC",
        "AOP-DDDDDDDDDD",
    }
    for rep in reps:
        assert rep.pct_identity_to_representative is None

    non_reps = [m for m in members if not m.is_representative]
    b = next(m for m in non_reps if m.peptide_id == "AOP-BBBBBBBBBB")
    assert b.pct_identity_to_representative == 87.50
    assert b.length_aa == 8
    assert b.cluster_id == 0


def test_singleton_cluster_has_only_a_representative(sample_clstr_path):
    members = parse_cdhit_clusters(sample_clstr_path)
    cluster_1_members = [m for m in members if m.cluster_id == 1]
    assert len(cluster_1_members) == 1
    assert cluster_1_members[0].is_representative
    assert cluster_1_members[0].length_aa == 3  # exercises the short-peptide path


def test_unparseable_line_raises(tmp_path):
    bad = tmp_path / "bad.clstr"
    bad.write_text(">Cluster 0\nthis is not a valid member line\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unparseable"):
        parse_cdhit_clusters(bad)


def test_member_before_any_cluster_header_raises(tmp_path):
    bad = tmp_path / "bad.clstr"
    bad.write_text("0\t5aa, >AOP-XXXXXXXXXX... *\n", encoding="utf-8")
    with pytest.raises(ValueError, match="before any"):
        parse_cdhit_clusters(bad)


def test_build_cluster_report(sample_clstr_path):
    members = parse_cdhit_clusters(sample_clstr_path)
    clusters_df = clusters_to_dataframe(members)

    positive_df = pd.DataFrame(
        {
            "peptide_id": [
                "AOP-AAAAAAAAAA",
                "AOP-BBBBBBBBBB",
                "AOP-CCCCCCCCCC",
                "AOP-DDDDDDDDDD",
                "AOP-EEEEEEEEEE",
                "AOP-FFFFFFFFFF",
            ],
            "evidence_tier": ["E1", "E2", "E1", "E2", "E1", "E2"],
        }
    )

    report = build_cluster_report(clusters_df, positive_df, n_input_sequences=6)
    assert report["n_input_sequences"] == 6
    assert report["n_parsed_cluster_members"] == 6
    assert report["n_sequences_dropped_by_cdhit"] == 0
    assert report["n_clusters_after_cdhit90"] == 3
    # Representatives are AAAAAAAAAA (E1), CCCCCCCCCC (E1), DDDDDDDDDD (E2)
    assert report["representative_tier_counts"] == {"E1": 2, "E2": 1}
    assert report["cluster_size_distribution"] == {"1": 1, "2": 1, "3": 1}
    assert report["largest_cluster_size"] == 3


def test_build_cluster_report_flags_dropped_sequences(sample_clstr_path):
    members = parse_cdhit_clusters(sample_clstr_path)
    clusters_df = clusters_to_dataframe(members)
    positive_df = pd.DataFrame({"peptide_id": [], "evidence_tier": []})
    # Pretend the input FASTA had 7 sequences but only 6 came out the other
    # side -- this is exactly the "document threshold violations" requirement.
    report = build_cluster_report(clusters_df, positive_df, n_input_sequences=7)
    assert report["n_sequences_dropped_by_cdhit"] == 1


def test_to_wsl_path_translates_drive_letter():
    result = to_wsl_path(Path(r"C:\Users\metal\Documents\repo\file.fasta"))
    assert result == "/mnt/c/Users/metal/Documents/repo/file.fasta"
