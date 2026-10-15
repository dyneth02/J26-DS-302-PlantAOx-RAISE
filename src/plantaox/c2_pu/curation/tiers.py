"""FR1 — E1/E2/E3 evidence-tier assignment and cross-source conflict resolution.

Conflict-resolution policy (confirmed with the project owner, logged in
IMPLEMENTATION_STATUS.md's decision log on 2026-10-14):

1. A sequence labeled positive (label == 1) in Multi-AOP that AnOxPePred's own
   per-sequence assay reports as inactive on BOTH mechanisms (FRS == 0 AND
   Chelator == 0) is a genuine cross-source conflict, not a data error (the
   proposal's own literature review, p.14, cites this exact phenomenon as a
   known field-wide problem). These sequences are EXCLUDED from the positive
   pool entirely.
2. They are NOT silently dropped and NOT reclassified as E3 (E3 is reserved
   for bioactivity-adjacent-but-unrelated evidence, which is a different
   thing from "actively contradicted"). They are logged in full, with
   provenance, in a dedicated conflict report, flagged as external-control
   *candidates* pending manual/homology review — never auto-added to the
   control set.
3. AnOxPePred's "inactive" call for these rows has NOT been checked against
   the original AnOxPePred paper/supplementary methods (we only have this
   CSV) — evidence_status reflects that explicitly rather than asserting
   confirmed experimental inactivity.
4. Positives corroborated by a direct AnOxPePred assay row (FRS == 1 or
   Chelator == 1) are E1. Positives that exist ONLY in Multi-AOP (no
   AnOxPePred row of any kind) cannot be assigned E1 — Multi-AOP carries no
   per-record assay metadata (see curation.adapters.load_multiaop) — so they
   default to E2, explicitly marked provisional and flagged for supervisor
   review, with assay_type/assay_verified recorded as "unknown" rather than
   inferring confirmation from the bare label.
"""

from __future__ import annotations

import pandas as pd

from plantaox.c2_pu.common.schemas import EvidenceTier
from plantaox.c2_pu.common.sequence import make_peptide_id
from plantaox.c2_pu.curation.standardize import apply_length_filter

CONFLICT_RESOLUTION_REASON = (
    "AnOxPePred per-sequence assay (FRS=0 AND Chelator=0) contradicts Multi-AOP's "
    "positive label. Assay-level evidence takes precedence over Multi-AOP's "
    "undocumented benchmark annotation, but the AnOxPePred 'inactive' call has not "
    "been cross-checked against the original paper, so this sequence is withheld "
    "from both the positive pool and the external control pending manual review."
)


def _aggregate_multiaop(mo_df: pd.DataFrame) -> pd.DataFrame:
    """One row per unique sequence: was it EVER labeled positive in Multi-AOP."""
    grouped = mo_df.groupby("sequence")["label"]
    return pd.DataFrame(
        {
            "multiaop_positive": grouped.max().eq(1),
            "multiaop_internally_inconsistent": grouped.nunique().gt(1),
        }
    )


def _aggregate_anoxpepred(an_df: pd.DataFrame) -> pd.DataFrame:
    """One row per unique sequence: aggregated FRS/Chelator + joined sources."""
    grouped = an_df.groupby("sequence")
    return pd.DataFrame(
        {
            "frs": grouped["frs"].max(),
            "chelator": grouped["chelator"].max(),
            "source": grouped["source"].agg(lambda s: ";".join(sorted(set(s)))),
        }
    )


def build_positive_pool(
    multiaop_df: pd.DataFrame,
    anoxpepred_df: pd.DataFrame,
    min_len: int = 3,
    max_len: int = 50,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Merge Multi-AOP + AnOxPePred into a tiered, conflict-resolved positive pool.

    Returns (positive_df, conflict_df, external_control_clean_df, summary).
    ``positive_df`` is PRE-CD-HIT / PRE-GraphPart — it is the Bucket 1.3/1.4
    output, not yet the frozen FR1 artifact (that freeze happens after
    1.5/1.6, see IMPLEMENTATION_STATUS.md).
    """
    mo_agg = _aggregate_multiaop(multiaop_df)
    an_agg = _aggregate_anoxpepred(anoxpepred_df)

    mo_pos_seqs = set(mo_agg.index[mo_agg["multiaop_positive"]])
    an_active_seqs = set(an_agg.index[(an_agg["frs"] == 1) | (an_agg["chelator"] == 1)])
    an_inactive_seqs = set(an_agg.index[(an_agg["frs"] == 0) & (an_agg["chelator"] == 0)])

    conflict_seqs = mo_pos_seqs & an_inactive_seqs
    e1_seqs = an_active_seqs  # assay-confirmed; disjoint from an_inactive_seqs by construction
    e2_seqs = mo_pos_seqs - an_active_seqs - conflict_seqs
    external_control_clean_seqs = an_inactive_seqs - conflict_seqs

    accepted_seqs = e1_seqs | e2_seqs
    kept_seqs, length_excluded_seqs = apply_length_filter(accepted_seqs, min_len, max_len)

    positive_rows = []
    for seq in kept_seqs:
        in_mo = seq in mo_agg.index
        in_an = seq in an_agg.index
        if seq in e1_seqs:
            frs = int(an_agg.loc[seq, "frs"])
            chelator = int(an_agg.loc[seq, "chelator"])
            assay_type = "+".join(
                name for name, flag in (("FRS", frs), ("Chelator", chelator)) if flag
            )
            positive_rows.append(
                {
                    "peptide_id": make_peptide_id(seq),
                    "sequence": seq,
                    "length": len(seq),
                    "evidence_tier": EvidenceTier.E1.value,
                    "evidence_basis": "anoxpepred_assay",
                    "assay_type": assay_type,
                    "assay_verified": "verified",
                    "provenance_status": "corroborated_by_multiaop" if in_mo else "verified",
                    "in_multiaop": in_mo,
                    "in_anoxpepred": True,
                    "multiaop_label": 1 if in_mo else None,
                    "anoxpepred_frs": frs,
                    "anoxpepred_chelator": chelator,
                    "anoxpepred_source": an_agg.loc[seq, "source"],
                }
            )
        else:  # e2_seqs: Multi-AOP only, no AnOxPePred row
            positive_rows.append(
                {
                    "peptide_id": make_peptide_id(seq),
                    "sequence": seq,
                    "length": len(seq),
                    "evidence_tier": EvidenceTier.E2.value,
                    "evidence_basis": "benchmark_positive_annotation",
                    "assay_type": "unknown",
                    "assay_verified": "unknown",
                    "provenance_status": "source_unresolved",
                    "in_multiaop": True,
                    "in_anoxpepred": False,
                    "multiaop_label": 1,
                    "anoxpepred_frs": None,
                    "anoxpepred_chelator": None,
                    "anoxpepred_source": None,
                }
            )
    positive_df = pd.DataFrame(positive_rows)

    conflict_rows = []
    for seq in conflict_seqs:
        conflict_rows.append(
            {
                "peptide_id": make_peptide_id(seq),
                "sequence": seq,
                "length": len(seq),
                "multiaop_label": 1,
                "anoxpepred_frs": int(an_agg.loc[seq, "frs"]),
                "anoxpepred_chelator": int(an_agg.loc[seq, "chelator"]),
                "anoxpepred_source": an_agg.loc[seq, "source"],
                "conflict_type": "multiaop_positive_vs_anoxpepred_assay_inactive",
                "evidence_status": "csv_reported_inactive_unverified_against_primary_source",
                "resolution": "excluded_pending_manual_review",
                "resolution_reason": CONFLICT_RESOLUTION_REASON,
                "external_control_candidate": True,
                "manual_review_required": True,
            }
        )
    conflict_df = pd.DataFrame(conflict_rows)

    control_rows = []
    for seq in external_control_clean_seqs:
        control_rows.append(
            {
                "peptide_id": make_peptide_id(seq),
                "sequence": seq,
                "length": len(seq),
                "anoxpepred_source": an_agg.loc[seq, "source"],
                "evidence_status": "csv_reported_inactive_no_crosssource_conflict",
            }
        )
    external_control_clean_df = pd.DataFrame(control_rows)

    summary = {
        "n_e1_assay_confirmed": len(e1_seqs),
        "n_e2_provisional": len(e2_seqs),
        "n_conflict_excluded": len(conflict_seqs),
        "n_length_excluded": len(length_excluded_seqs),
        "n_accepted_positives": len(kept_seqs),
        "n_external_control_clean": len(external_control_clean_seqs),
        "n_external_control_conflict_candidates": len(conflict_seqs),
        "n_multiaop_internally_inconsistent": int(
            mo_agg["multiaop_internally_inconsistent"].sum()
        ),
    }
    return positive_df, conflict_df, external_control_clean_df, summary
