"""Bucket 2.2 (FR2/C2) -- streaming parser and curation logic for the
Peptipedia v2.0 database dump (Zenodo DOI 10.5281/zenodo.21488992,
``peptipedia.20240323.sql.gz``, ODbL-1.0 licensed).

The dump is a **plain-text** ``pg_dump`` (not a binary/custom-format dump),
so its ``COPY public.<table> (...) FROM stdin; ... \\.`` blocks are parsed
directly as tab-delimited text -- no PostgreSQL server install or import
step is required. This keeps Bucket 2.2 consistent with AGENTS.md rule 6
("don't bulk-download/stand up infrastructure when a lighter-weight
approach will do"): the only heavy step is the one-time 281MB versioned
download itself, not an ongoing database service.

Policy, confirmed with the project owner (see IMPLEMENTATION_STATUS.md):
peptides tagged Peptipedia activity id 41 ("Anti oxidative") are excluded
from C2 entirely, regardless of whether that tag itself is predicted or
experimentally reported -- the same conservative "exclude anything that
might be a real positive" rule already applied to C1's leakage screening.
"""

from __future__ import annotations

import gzip
import random
from pathlib import Path
from typing import Iterator

from plantaox.c2_pu.common.sequence import is_standard_alphabet

# Confirmed by inspecting the dump's `activity` table directly (213 rows) --
# id 41 is Peptipedia's sole antioxidant-type category ("Anti oxidative").
# Never regenerate this from a name-string match: Peptipedia's own `activity`
# table is the source of truth, and names could be re-worded in a future dump
# version without the numeric id changing.
ANTIOXIDANT_ACTIVITY_ID = 41

C2_SAMPLE_SIZE = 2000
C2_SEED = 42


def _unescape_copy_field(field: str) -> str | None:
    """Undo PostgreSQL COPY TEXT format escaping for one field. ``\\N`` is
    SQL NULL; the rest are the handful of C-style escapes pg_dump emits."""
    if field == "\\N":
        return None
    return (
        field.replace("\\t", "\t")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\\\", "\\")
    )


def iter_copy_rows(dump_path: str | Path, table_name: str) -> Iterator[list[str | None]]:
    """Stream rows from one ``COPY public.<table_name> (...) FROM stdin;``
    block in a gzip-compressed plain-text pg_dump, without ever holding the
    full decompressed dump in memory. Yields one list of unescaped fields
    per row, in file order, stopping at the block's terminating ``\\.`` line.
    """
    prefix = f"COPY public.{table_name} ("
    in_block = False
    with gzip.open(dump_path, mode="rt", encoding="utf-8", newline="\n") as handle:
        for line in handle:
            if not in_block:
                if line.startswith(prefix):
                    in_block = True
                continue
            if line in ("\\.\n", "\\."):
                break
            yield [_unescape_copy_field(f) for f in line.rstrip("\n").split("\t")]


def load_activity_names(dump_path: str | Path) -> dict[int, str]:
    """id_activity -> name, from the small (213-row) ``activity`` table."""
    return {int(row[0]): row[1] for row in iter_copy_rows(dump_path, "activity")}


def extract_c2_candidates(
    dump_path: str | Path, min_len: int = 3, max_len: int = 50
) -> tuple[dict[int, str], dict[int, list[tuple[int, bool]]]]:
    """Two-pass streaming extraction, bounded to the standard-alphabet /
    length-windowed subset so the second pass's in-memory activity map never
    has to cover the dump's full ~4M peptide rows.

    Pass 1 (``peptide``): keep sequences in the shared 3-50 AA window with a
    standard 20-amino-acid alphabet (same policy as C1/positives).
    Pass 2 (``peptide_has_activity``): for eligible ids only, collect every
    (id_activity, predicted) assignment -- including antioxidant tags, which
    callers must still explicitly exclude (this function does not filter by
    activity itself, so the antioxidant-exclusion policy stays visible and
    testable at the caller level rather than buried here).

    Returns (sequences, activities_by_id). A peptide with no activity row at
    all (id not a key in ``activities_by_id``) has no reported bioactivity
    and is not a C2 candidate (C2 requires a *documented* non-antioxidant
    bioactivity, not merely the absence of an antioxidant one).
    """
    sequences: dict[int, str] = {}
    for row in iter_copy_rows(dump_path, "peptide"):
        id_peptide, sequence = int(row[0]), row[1]
        if sequence is not None and min_len <= len(sequence) <= max_len and is_standard_alphabet(sequence):
            sequences[id_peptide] = sequence

    activities: dict[int, list[tuple[int, bool]]] = {}
    for row in iter_copy_rows(dump_path, "peptide_has_activity"):
        id_peptide = int(row[0])
        if id_peptide not in sequences:
            continue
        id_activity, predicted = int(row[1]), row[2] == "t"
        activities.setdefault(id_peptide, []).append((id_activity, predicted))

    return sequences, activities


def build_c2_pool(
    sequences: dict[int, str],
    activities: dict[int, list[tuple[int, bool]]],
    screen_sequences: set[str],
    n: int = C2_SAMPLE_SIZE,
    seed: int = C2_SEED,
) -> tuple[list[dict], dict]:
    """Apply the C2 inclusion policy and deterministically sample ~2,000
    eligible peptides.

    Inclusion: id_peptide has >=1 reported activity, none of which is the
    antioxidant activity (id 41) -- conservative, matching C1's "exclude
    anything that might itself be a real positive" leakage rule. Excludes
    exact-sequence matches against ``screen_sequences`` (FR1's 1,205
    positives + 179 cross-source conflicts), the same screening used for C1.
    Deduplicates by sequence (one record per unique sequence, keeping the
    lowest ``id_peptide`` for determinism when the same sequence was
    submitted under multiple Peptipedia ids).

    Experimentally-reported activities (``predicted=False`` on at least one
    tag) are preferred over predicted-only peptides when down-sampling to
    ``n`` -- mirrors the project's existing E1>E2 evidence-tier precedence.
    Falls back to predicted-only peptides only if the experimental tier
    can't supply ``n`` on its own (reported in the summary, not hidden).

    Returns (records, summary). Each record: id_peptide, sequence, length,
    activity_ids (sorted), has_experimental_evidence.
    """
    by_sequence: dict[str, int] = {}
    for id_peptide, seq in sequences.items():
        if id_peptide not in activities:
            continue
        activity_ids = {a for a, _ in activities[id_peptide]}
        if ANTIOXIDANT_ACTIVITY_ID in activity_ids:
            continue
        if seq in screen_sequences:
            continue
        existing = by_sequence.get(seq)
        if existing is None or id_peptide < existing:
            by_sequence[seq] = id_peptide

    eligible_ids = set(by_sequence.values())
    experimental_ids = sorted(
        pid
        for pid in eligible_ids
        if any(not predicted for _, predicted in activities[pid])
    )
    predicted_only_ids = sorted(eligible_ids - set(experimental_ids))

    random.seed(seed)
    n_from_experimental = min(n, len(experimental_ids))
    chosen = set(random.sample(experimental_ids, n_from_experimental))
    shortfall = n - len(chosen)
    if shortfall > 0 and predicted_only_ids:
        random.seed(seed)
        n_from_predicted = min(shortfall, len(predicted_only_ids))
        chosen |= set(random.sample(predicted_only_ids, n_from_predicted))

    records = [
        {
            "id_peptide": pid,
            "sequence": sequences[pid],
            "length": len(sequences[pid]),
            "activity_ids": sorted({a for a, _ in activities[pid]}),
            "has_experimental_evidence": pid in set(experimental_ids),
        }
        for pid in sorted(chosen)
    ]

    summary = {
        "n_total_eligible_unique_sequences": len(eligible_ids),
        "n_experimental_tier": len(experimental_ids),
        "n_predicted_only_tier": len(predicted_only_ids),
        "n_sampled_from_experimental": len(chosen & set(experimental_ids)),
        "n_sampled_from_predicted_only": len(chosen) - len(chosen & set(experimental_ids)),
        "n_output_records": len(records),
        "n_requested": n,
        "shortfall": n - len(records),
        "seed": seed,
    }
    return records, summary
