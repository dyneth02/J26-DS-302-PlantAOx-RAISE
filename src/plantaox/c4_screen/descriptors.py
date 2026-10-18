"""Finite Biopython physicochemical descriptors for peptide sequences."""

from __future__ import annotations

import math

from Bio.SeqUtils.ProtParam import ProteinAnalysis


def describe(sequence: str) -> dict[str, float]:
    analysis = ProteinAnalysis(sequence)
    values = {"molecular_weight": float(analysis.molecular_weight()),
              "isoelectric_point": float(analysis.isoelectric_point()),
              "gravy": float(analysis.gravy()), "net_charge_ph7": float(analysis.charge_at_pH(7.0))}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError(f"Non-finite descriptor for sequence {sequence!r}")
    return values


def add_descriptors(rows: list[dict]) -> list[dict]:
    return [{**row, **describe(row["sequence"])} for row in rows]
