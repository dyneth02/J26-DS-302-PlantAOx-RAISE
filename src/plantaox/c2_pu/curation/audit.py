"""Bucket 2.4 -- Pool Contamination and Leakage Audit.

Formal, re-runnable integrity/overlap/homology checks across FR1's
positives, the 179 cross-source conflicts, and the three unlabeled
challenge pools (C1/C2/C3). This module holds the pure logic; `run.py`'s
`run_fr2_pool_audit()` wires it to the real on-disk artifacts and writes
the report files.

**Two distinct overlap concepts, never conflated:**

- *Exact-sequence overlap*: the same literal sequence appears in two pools.
  Cheap, unambiguous, already enforced at construction time for most pairs
  (C1/C2/C3 were each screened against FR1 positives/conflicts when built)
  but -- as this audit exists to check -- never verified pairwise against
  *each other* until now.
- *Homology* (near-duplicate, non-exact): two different sequences are
  similar enough to plausibly share the same biological origin/activity.
  This is NOT the same risk as exact overlap and is NOT caught by it --
  see the long docstring on `cross_pool_homology_clusters` below for why a
  naive single-threshold CD-HIT scan is actively misleading for a
  3-50 AA peptide population, and how this module avoids that trap.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from plantaox.c2_pu.common.sequence import is_standard_alphabet
from plantaox.c2_pu.curation.dedup import (
    clusters_to_dataframe,
    parse_cdhit_clusters,
    run_cdhit,
)


def sequence_integrity_report(
    name: str, records: list[tuple[str, str]], min_len: int = 3, max_len: int = 50
) -> dict:
    """Per-pool integrity counts: record/ID/sequence counts, duplicate IDs,
    alphabet violations, length-window violations. Never removes or alters
    anything -- a pure read-only report."""
    ids = [h for h, _ in records]
    seqs = [s for _, s in records]
    return {
        "pool": name,
        "n_records": len(records),
        "n_unique_ids": len(set(ids)),
        "n_duplicate_ids": len(records) - len(set(ids)),
        "n_unique_sequences": len(set(seqs)),
        "n_duplicate_sequences": len(records) - len(set(seqs)),
        "n_non_standard_alphabet": sum(1 for s in seqs if not is_standard_alphabet(s)),
        "n_length_window_violations": sum(1 for s in seqs if not (min_len <= len(s) <= max_len)),
    }


def pairwise_exact_overlap(pools: dict[str, set[str]]) -> pd.DataFrame:
    """Symmetric matrix of exact-sequence intersection counts between every
    pair of pools (diagonal = each pool's own unique-sequence count)."""
    names = list(pools.keys())
    data = {
        b: [len(pools[a] & pools[b]) if a != b else len(pools[a]) for a in names] for b in names
    }
    return pd.DataFrame(data, index=names)


def overlap_detail(pools: dict[str, set[str]], pool_a: str, pool_b: str) -> list[str]:
    """The actual overlapping sequences between two named pools, sorted."""
    return sorted(pools[pool_a] & pools[pool_b])


def external_reference_screen(pools: dict[str, set[str]], reference_seqs: set[str]) -> dict:
    """Exact-sequence hits between each pool and an external known-AOP
    reference set (e.g. BIOPEP-UWM's antioxidative peptides). A hit in C1/
    C2/C3 is a real contamination signal; a hit in FR1_positives/conflicts
    is expected corroborating evidence, not a problem."""
    return {name: sorted(seqs & reference_seqs) for name, seqs in pools.items()}


def cross_pool_homology_clusters(
    pools: dict[str, list[tuple[str, str]]],
    output_prefix: Path,
    identity: float = 0.90,
    word_length: int = 2,
    throwaway_length: int = 2,
    length_floor_for_interpretation: int = 15,
) -> tuple[pd.DataFrame, dict]:
    """Cluster every pool's sequences together (CD-HIT, inside WSL) and
    report which clusters contain members from more than one pool --
    candidate near-duplicate/homology leakage, distinct from exact overlap.

    **Why this needs a length floor to be scientifically meaningful, not
    just a style choice:** CD-HIT's percent identity for a short/long pair
    is computed over the shorter sequence's length. For a 3-residue
    fragment, ANY 50-mer that happens to contain that exact tripeptide as
    a substring scores 100% identity to it -- with only 20^3=8,000 possible
    tripeptides, this happens constantly by chance across a ~9,500-sequence
    pool spanning 3-50 AA, producing large, biologically meaningless mixed
    clusters (empirically confirmed on this exact dataset: a 90%-identity
    run produced 460 "cross-pool" clusters, the overwhelming majority of
    which were single 3-4 AA fragments trivially matching an unrelated
    50-mer that happens to contain them as a substring). This is the same
    short-peptide percent-identity caveat already discovered and documented
    for GraphPart's `-dn` denominator choice (see IMPLEMENTATION_STATUS.md)
    -- it recurs here because CD-HIT has no equivalent full-length-
    denominator option to work around it.

    This function therefore reports TWO things, never conflating them:
    1. ``clusters_df``: every cross-pool cluster found, unfiltered, with
       each member's length -- for full transparency (nothing hidden).
    2. The returned summary dict's ``real_homology_clusters``: the subset
       where at least 2 members from *different* pools are BOTH
       ``>= length_floor_for_interpretation`` AA -- the only subset this
       function treats as plausibly biologically meaningful. Everything
       else is reported as "not interpretable as homology," not silently
       dropped.
    """
    combined_records = []
    seq_index = 0
    for pool_name, records in pools.items():
        for _, sequence in records:
            combined_records.append((f"SEQ{seq_index:06d}|{pool_name}", sequence))
            seq_index += 1

    combined_fasta = output_prefix.with_suffix(".input.fasta")
    from plantaox.c2_pu.common.io import write_fasta

    write_fasta(combined_fasta, combined_records)

    _, clstr_path = run_cdhit(
        combined_fasta, output_prefix, identity=identity, word_length=word_length,
        throwaway_length=throwaway_length,
    )
    members = parse_cdhit_clusters(clstr_path)
    df = clusters_to_dataframe(members)

    id_to_seq = dict(combined_records)
    df["sequence"] = df["peptide_id"].map(id_to_seq)
    df["length"] = df["sequence"].str.len()
    df["pool"] = df["peptide_id"].apply(lambda pid: pid.split("|", 1)[1])

    cross_pool_cluster_ids = [
        cid for cid, g in df.groupby("cluster_id") if g["pool"].nunique() > 1
    ]
    cross_df = df[df["cluster_id"].isin(cross_pool_cluster_ids)].copy()

    real_clusters = []
    for cid, g in cross_df.groupby("cluster_id"):
        long_enough = g[g["length"] >= length_floor_for_interpretation]
        if long_enough["pool"].nunique() > 1:
            real_clusters.append(cid)

    summary = {
        "identity_threshold": identity,
        "length_floor_for_interpretation": length_floor_for_interpretation,
        "n_total_clusters": int(df["cluster_id"].nunique()),
        "n_cross_pool_clusters_raw": len(cross_pool_cluster_ids),
        "n_cross_pool_clusters_short_fragment_only_not_interpretable": len(cross_pool_cluster_ids)
        - len(real_clusters),
        "n_cross_pool_clusters_real_homology_candidates": len(real_clusters),
        "real_homology_cluster_ids": real_clusters,
    }
    return cross_df, summary
