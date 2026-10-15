"""FR1 — case/alphabet/length normalization and stable peptide ID assignment.

Sequence normalization (upper-case, strip) already happens in
``curation.adapters`` at load time. This module applies the project-wide
length window and assigns deterministic peptide IDs to a finalized set of
sequences, once tiering/conflict-resolution has decided which sequences are
actually accepted (see ``curation.tiers``).
"""

from __future__ import annotations

from plantaox.c2_pu.common.sequence import is_standard_alphabet, make_peptide_id


def apply_length_filter(
    sequences: set[str], min_len: int = 3, max_len: int = 50
) -> tuple[set[str], set[str]]:
    """Split a sequence set into (kept, dropped) by the shared 3-50 AA window.

    Also drops anything outside the 20 standard amino acids, since a
    non-standard residue cannot be fed through the shared descriptor/ESM-2
    feature pipeline either way.
    """
    kept: set[str] = set()
    dropped: set[str] = set()
    for seq in sequences:
        if min_len <= len(seq) <= max_len and is_standard_alphabet(seq):
            kept.add(seq)
        else:
            dropped.add(seq)
    return kept, dropped


def assign_peptide_ids(sequences: set[str], prefix: str = "AOP") -> dict[str, str]:
    """Deterministic sequence -> peptide_id mapping (stable across re-runs)."""
    return {seq: make_peptide_id(seq, prefix=prefix) for seq in sequences}
