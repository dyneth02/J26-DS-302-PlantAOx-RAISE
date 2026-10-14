"""Bucket 3.1 -- canonical 15-dimensional physicochemical descriptor schema.

This is the single, frozen feature contract for every downstream consumer
(FR3 training, the 495-dim ESM-2+descriptor fusion in Bucket 3.3, and
``curation/distribution_audit.py``'s Task 2.5 pool comparison, which now
imports its 4 shared formulas from here instead of defining its own copies).

Schema version: ``descriptors_v1``. Feature names and column order are part
of the frozen contract -- do not reorder, rename, or silently redefine a
feature; a genuine change gets a new schema version.

Decision log (see IMPLEMENTATION_STATUS.md for the full entry):
    * Net charge / pI reuse the exact Expasy/EMBOSS-style pKa table already
      validated in ``distribution_audit.py`` (Task 2.5), for cross-task
      consistency rather than introducing a second, slightly different
      charge model.
    * The instability-index dipeptide weight table (``DIWV``, Guruprasad
      K., Reddy B.V.B., Pandit M.W., Protein Engineering 4:155-161 (1990))
      is reproduced verbatim from Biopython's ``Bio.SeqUtils.ProtParamData``
      (BSD/Biopython-licensed, itself citing the same paper) rather than
      hand-transcribed from memory, since a silently-wrong entry in a
      400-cell lookup table would not be caught by a handful of unit tests.
    * A Boman (2003) solubility/interaction index was originally proposed
      as feature #9, but no independently verifiable source for its
      per-residue scale could be located (search turned up only unverified,
      possibly-confused tables). Rather than freeze an unverifiable
      constant, it was replaced with ``frac_proline`` -- trivially
      verifiable (a residue count) and directly motivated by this
      project's own Task 2.5 finding that FR1 positives are
      proline-enriched (10.6%) relative to every challenge pool
      (4.1-5.6%), i.e. a project-evidenced, not just textbook, descriptor.
    * Composition-group membership (charged / polar / hydrophobic) is a
      non-overlapping assignment per residue (e.g. Cys is grouped under
      "polar" only, not also "hydrophobic") so the three *_frac features
      don't silently double-count the same residue.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from plantaox.c2_pu.common.sequence import is_standard_alphabet, is_valid_peptide

SCHEMA_VERSION = "descriptors_v1"

# ---------------------------------------------------------------------------
# Reference constants (single source of truth -- reused by
# curation/distribution_audit.py, not redefined there).
# ---------------------------------------------------------------------------

# Average residue masses (Da) within a peptide chain (free amino acid mass
# minus one water, added back once per peptide below).
RESIDUE_MASS = {
    "A": 71.0788, "R": 156.1875, "N": 114.1038, "D": 115.0886, "C": 103.1388,
    "E": 129.1155, "Q": 128.1307, "G": 57.0519, "H": 137.1411, "I": 113.1594,
    "L": 113.1594, "K": 128.1741, "M": 131.1926, "F": 147.1766, "P": 97.1167,
    "S": 87.0782, "T": 101.1051, "W": 186.2132, "Y": 163.1760, "V": 99.1326,
}
WATER_MASS = 18.0153

# Kyte & Doolittle (1982) hydropathy index, J. Mol. Biol. 157:105-132. Used
# for GRAVY. Matches Biopython's Bio.SeqUtils.ProtParamData.kd exactly.
KYTE_DOOLITTLE = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

# Common Expasy/EMBOSS-style pKa table (side chains + termini) for an
# approximate net-charge-at-pH calculation (Henderson-Hasselbalch).
PKA_POSITIVE = {"Nterm": 9.69, "K": 10.53, "R": 12.48, "H": 6.0}
PKA_NEGATIVE = {"Cterm": 2.34, "D": 3.65, "E": 4.25, "C": 8.3, "Y": 10.07}

AROMATIC_RESIDUES = {"F", "W", "Y"}
STANDARD_AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"

# Eisenberg et al. (1984) normalized consensus hydrophobicity scale,
# J. Mol. Biol. 179:125-142 -- used for the hydrophobic moment (distinct
# from Kyte-Doolittle, which is not the scale the original moment paper
# uses).
EISENBERG = {
    "A": 0.62, "R": -2.53, "N": -0.78, "D": -0.90, "C": 0.29, "Q": -0.85,
    "E": -0.74, "G": 0.48, "H": -0.40, "I": 1.38, "L": 1.06, "K": -1.50,
    "M": 0.64, "F": 1.19, "P": 0.12, "S": -0.18, "T": -0.05, "W": 0.81,
    "Y": 0.26, "V": 1.08,
}
_HELIX_DELTA_DEGREES = 100.0  # alpha-helix residue rotation per Eisenberg 1984

# Instability-index dipeptide weight table, Guruprasad K., Reddy B.V.B.,
# Pandit M.W., Protein Engineering 4:155-161 (1990). Reproduced verbatim
# from Biopython's Bio.SeqUtils.ProtParamData.DIWV (BSD/Biopython License).
DIWV = {
    "A": {"A": 1.0, "C": 44.94, "E": 1.0, "D": -7.49, "G": 1.0, "F": 1.0, "I": 1.0,
          "H": -7.49, "K": 1.0, "M": 1.0, "L": 1.0, "N": 1.0, "Q": 1.0, "P": 20.26,
          "S": 1.0, "R": 1.0, "T": 1.0, "W": 1.0, "V": 1.0, "Y": 1.0},
    "C": {"A": 1.0, "C": 1.0, "E": 1.0, "D": 20.26, "G": 1.0, "F": 1.0, "I": 1.0,
          "H": 33.60, "K": 1.0, "M": 33.60, "L": 20.26, "N": 1.0, "Q": -6.54, "P": 20.26,
          "S": 1.0, "R": 1.0, "T": 33.60, "W": 24.68, "V": -6.54, "Y": 1.0},
    "E": {"A": 1.0, "C": 44.94, "E": 33.60, "D": 20.26, "G": 1.0, "F": 1.0, "I": 20.26,
          "H": -6.54, "K": 1.0, "M": 1.0, "L": 1.0, "N": 1.0, "Q": 20.26, "P": 20.26,
          "S": 20.26, "R": 1.0, "T": 1.0, "W": -14.03, "V": 1.0, "Y": 1.0},
    "D": {"A": 1.0, "C": 1.0, "E": 1.0, "D": 1.0, "G": 1.0, "F": -6.54, "I": 1.0,
          "H": 1.0, "K": -7.49, "M": 1.0, "L": 1.0, "N": 1.0, "Q": 1.0, "P": 1.0,
          "S": 20.26, "R": -6.54, "T": -14.03, "W": 1.0, "V": 1.0, "Y": 1.0},
    "G": {"A": -7.49, "C": 1.0, "E": -6.54, "D": 1.0, "G": 13.34, "F": 1.0, "I": -7.49,
          "H": 1.0, "K": -7.49, "M": 1.0, "L": 1.0, "N": -7.49, "Q": 1.0, "P": 1.0,
          "S": 1.0, "R": 1.0, "T": -7.49, "W": 13.34, "V": 1.0, "Y": -7.49},
    "F": {"A": 1.0, "C": 1.0, "E": 1.0, "D": 13.34, "G": 1.0, "F": 1.0, "I": 1.0,
          "H": 1.0, "K": -14.03, "M": 1.0, "L": 1.0, "N": 1.0, "Q": 1.0, "P": 20.26,
          "S": 1.0, "R": 1.0, "T": 1.0, "W": 1.0, "V": 1.0, "Y": 33.601},
    "I": {"A": 1.0, "C": 1.0, "E": 44.94, "D": 1.0, "G": 1.0, "F": 1.0, "I": 1.0,
          "H": 13.34, "K": -7.49, "M": 1.0, "L": 20.26, "N": 1.0, "Q": 1.0, "P": -1.88,
          "S": 1.0, "R": 1.0, "T": 1.0, "W": 1.0, "V": -7.49, "Y": 1.0},
    "H": {"A": 1.0, "C": 1.0, "E": 1.0, "D": 1.0, "G": -9.37, "F": -9.37, "I": 44.94,
          "H": 1.0, "K": 24.68, "M": 1.0, "L": 1.0, "N": 24.68, "Q": 1.0, "P": -1.88,
          "S": 1.0, "R": 1.0, "T": -6.54, "W": -1.88, "V": 1.0, "Y": 44.94},
    "K": {"A": 1.0, "C": 1.0, "E": 1.0, "D": 1.0, "G": -7.49, "F": 1.0, "I": -7.49,
          "H": 1.0, "K": 1.0, "M": 33.60, "L": -7.49, "N": 1.0, "Q": 24.64, "P": -6.54,
          "S": 1.0, "R": 33.60, "T": 1.0, "W": 1.0, "V": -7.49, "Y": 1.0},
    "M": {"A": 13.34, "C": 1.0, "E": 1.0, "D": 1.0, "G": 1.0, "F": 1.0, "I": 1.0,
          "H": 58.28, "K": 1.0, "M": -1.88, "L": 1.0, "N": 1.0, "Q": -6.54, "P": 44.94,
          "S": 44.94, "R": -6.54, "T": -1.88, "W": 1.0, "V": 1.0, "Y": 24.68},
    "L": {"A": 1.0, "C": 1.0, "E": 1.0, "D": 1.0, "G": 1.0, "F": 1.0, "I": 1.0,
          "H": 1.0, "K": -7.49, "M": 1.0, "L": 1.0, "N": 1.0, "Q": 33.60, "P": 20.26,
          "S": 1.0, "R": 20.26, "T": 1.0, "W": 24.68, "V": 1.0, "Y": 1.0},
    "N": {"A": 1.0, "C": -1.88, "E": 1.0, "D": 1.0, "G": -14.03, "F": -14.03, "I": 44.94,
          "H": 1.0, "K": 24.68, "M": 1.0, "L": 1.0, "N": 1.0, "Q": -6.54, "P": -1.88,
          "S": 1.0, "R": 1.0, "T": -7.49, "W": -9.37, "V": 1.0, "Y": 1.0},
    "Q": {"A": 1.0, "C": -6.54, "E": 20.26, "D": 20.26, "G": 1.0, "F": -6.54, "I": 1.0,
          "H": 1.0, "K": 1.0, "M": 1.0, "L": 1.0, "N": 1.0, "Q": 20.26, "P": 20.26,
          "S": 44.94, "R": 1.0, "T": 1.0, "W": 1.0, "V": -6.54, "Y": -6.54},
    "P": {"A": 20.26, "C": -6.54, "E": 18.38, "D": -6.54, "G": 1.0, "F": 20.26, "I": 1.0,
          "H": 1.0, "K": 1.0, "M": -6.54, "L": 1.0, "N": 1.0, "Q": 20.26, "P": 20.26,
          "S": 20.26, "R": -6.54, "T": 1.0, "W": -1.88, "V": 20.26, "Y": 1.0},
    "S": {"A": 1.0, "C": 33.60, "E": 20.26, "D": 1.0, "G": 1.0, "F": 1.0, "I": 1.0,
          "H": 1.0, "K": 1.0, "M": 1.0, "L": 1.0, "N": 1.0, "Q": 20.26, "P": 44.94,
          "S": 20.26, "R": 20.26, "T": 1.0, "W": 1.0, "V": 1.0, "Y": 1.0},
    "R": {"A": 1.0, "C": 1.0, "E": 1.0, "D": 1.0, "G": -7.49, "F": 1.0, "I": 1.0,
          "H": 20.26, "K": 1.0, "M": 1.0, "L": 1.0, "N": 13.34, "Q": 20.26, "P": 20.26,
          "S": 44.94, "R": 58.28, "T": 1.0, "W": 58.28, "V": 1.0, "Y": -6.54},
    "T": {"A": 1.0, "C": 1.0, "E": 20.26, "D": 1.0, "G": -7.49, "F": 13.34, "I": 1.0,
          "H": 1.0, "K": 1.0, "M": 1.0, "L": 1.0, "N": -14.03, "Q": -6.54, "P": 1.0,
          "S": 1.0, "R": 1.0, "T": 1.0, "W": -14.03, "V": 1.0, "Y": 1.0},
    "W": {"A": -14.03, "C": 1.0, "E": 1.0, "D": 1.0, "G": -9.37, "F": 1.0, "I": 1.0,
          "H": 24.68, "K": 1.0, "M": 24.68, "L": 13.34, "N": 13.34, "Q": 1.0, "P": 1.0,
          "S": 1.0, "R": 1.0, "T": -14.03, "W": 1.0, "V": -7.49, "Y": 1.0},
    "V": {"A": 1.0, "C": 1.0, "E": 1.0, "D": -14.03, "G": -7.49, "F": 1.0, "I": 1.0,
          "H": 1.0, "K": -1.88, "M": 1.0, "L": 1.0, "N": 1.0, "Q": 1.0, "P": 20.26,
          "S": 1.0, "R": 1.0, "T": -7.49, "W": 1.0, "V": 1.0, "Y": -6.54},
    "Y": {"A": 24.68, "C": 1.0, "E": -6.54, "D": 24.68, "G": -7.49, "F": 1.0, "I": 1.0,
          "H": 13.34, "K": 1.0, "M": 44.94, "L": 1.0, "N": 1.0, "Q": 1.0, "P": 13.34,
          "S": 1.0, "R": -15.91, "T": -7.49, "W": -9.37, "V": 1.0, "Y": 13.34},
}

# Non-overlapping composition groups (each residue assigned to exactly one
# of charged/polar/hydrophobic; G and P are left uncategorized for this
# 3-way split since neither fits cleanly, consistent with common CTD-style
# groupings). positive/negative are a separate, independent split.
_CHARGED = set("DEKR")
_POLAR = set("STNQCY")
_HYDROPHOBIC = set("AVLIMFW")
_POSITIVE = set("KRH")
_NEGATIVE = set("DE")

DESCRIPTOR_NAMES = (
    "length",
    "molecular_weight",
    "net_charge_ph7",
    "isoelectric_point",
    "gravy",
    "aromaticity",
    "instability_index",
    "aliphatic_index",
    "hydrophobic_moment",
    "frac_charged",
    "frac_polar",
    "frac_hydrophobic",
    "frac_positive",
    "frac_negative",
    "frac_proline",
)
assert len(DESCRIPTOR_NAMES) == 15


class InvalidPeptideError(ValueError):
    """Raised when descriptor extraction is given a sequence outside the
    project's standard-20-AA-alphabet, 3-50 AA contract."""


# ---------------------------------------------------------------------------
# Individual descriptor formulas.
# ---------------------------------------------------------------------------


def molecular_weight(sequence: str) -> float:
    return sum(RESIDUE_MASS[r] for r in sequence) + WATER_MASS


def gravy(sequence: str) -> float:
    return sum(KYTE_DOOLITTLE[r] for r in sequence) / len(sequence)


def aromaticity(sequence: str) -> float:
    return sum(1 for r in sequence if r in AROMATIC_RESIDUES) / len(sequence)


def net_charge_at_ph(sequence: str, ph: float = 7.0) -> float:
    """Henderson-Hasselbalch net charge at a single pH (not a full pI solve)."""
    positive = 1.0 / (1.0 + 10 ** (ph - PKA_POSITIVE["Nterm"]))
    positive += sum(
        1.0 / (1.0 + 10 ** (ph - PKA_POSITIVE[r])) for r in sequence if r in PKA_POSITIVE
    )
    negative = 1.0 / (1.0 + 10 ** (PKA_NEGATIVE["Cterm"] - ph))
    negative += sum(
        1.0 / (1.0 + 10 ** (PKA_NEGATIVE[r] - ph)) for r in sequence if r in PKA_NEGATIVE
    )
    return positive - negative


def isoelectric_point(sequence: str, tolerance: float = 1e-4) -> float:
    """pH at which ``net_charge_at_ph`` crosses zero, via bisection.

    Net charge is monotonically non-increasing in pH (every term's
    derivative is <= 0), and every peptide has both a basic (N-terminus)
    and an acidic (C-terminus) ionizable group, so a sign change always
    exists within [0, 14] -- well-defined for every valid 3-50 AA peptide.
    """
    lo, hi = 0.0, 14.0
    charge_lo = net_charge_at_ph(sequence, lo)
    charge_hi = net_charge_at_ph(sequence, hi)
    if charge_lo < 0 or charge_hi > 0:
        # Should not happen given the pKa table above, but fail loudly
        # rather than silently returning a meaningless boundary value.
        raise ValueError(f"No sign change in net charge over pH [0, 14] for {sequence!r}")
    while hi - lo > tolerance:
        mid = (lo + hi) / 2
        if net_charge_at_ph(sequence, mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def instability_index(sequence: str) -> float:
    """Guruprasad et al. (1990) dipeptide instability index."""
    total = sum(DIWV[sequence[i]][sequence[i + 1]] for i in range(len(sequence) - 1))
    return (10.0 / len(sequence)) * total


def aliphatic_index(sequence: str) -> float:
    """Ikai (1980), J. Biochem. 88:1895-1898. Mole-percentage convention."""
    n = len(sequence)
    frac_a = sequence.count("A") / n
    frac_v = sequence.count("V") / n
    frac_il = (sequence.count("I") + sequence.count("L")) / n
    return 100.0 * (frac_a + 2.9 * frac_v + 3.9 * frac_il)


def hydrophobic_moment(sequence: str, delta_degrees: float = _HELIX_DELTA_DEGREES) -> float:
    """Eisenberg et al. (1984) mean hydrophobic moment, assuming an
    alpha-helical periodicity (100 degrees/residue)."""
    delta = math.radians(delta_degrees)
    sum_cos = sum(EISENBERG[r] * math.cos(n * delta) for n, r in enumerate(sequence))
    sum_sin = sum(EISENBERG[r] * math.sin(n * delta) for n, r in enumerate(sequence))
    return math.sqrt(sum_cos**2 + sum_sin**2) / len(sequence)


def frac_charged(sequence: str) -> float:
    return sum(1 for r in sequence if r in _CHARGED) / len(sequence)


def frac_polar(sequence: str) -> float:
    return sum(1 for r in sequence if r in _POLAR) / len(sequence)


def frac_hydrophobic(sequence: str) -> float:
    return sum(1 for r in sequence if r in _HYDROPHOBIC) / len(sequence)


def frac_positive(sequence: str) -> float:
    return sum(1 for r in sequence if r in _POSITIVE) / len(sequence)


def frac_negative(sequence: str) -> float:
    return sum(1 for r in sequence if r in _NEGATIVE) / len(sequence)


def frac_proline(sequence: str) -> float:
    return sequence.count("P") / len(sequence)


# ---------------------------------------------------------------------------
# Public extraction API.
# ---------------------------------------------------------------------------


def _validate_or_raise(peptide_ids: list[str], sequences: list[str]) -> None:
    offending = [
        (pid, seq, [r for r in seq if r not in STANDARD_AMINO_ACIDS])
        for pid, seq in zip(peptide_ids, sequences)
        if not is_valid_peptide(seq)
    ]
    if offending:
        detail = "; ".join(
            f"{pid} ({seq}): "
            + ("non-standard residues " + "".join(residues) if residues else "length outside 3-50 AA")
            for pid, seq, residues in offending
        )
        raise InvalidPeptideError(
            f"{len(offending)} sequence(s) fail the standard-20-AA-alphabet, 3-50 AA "
            f"contract required by the Bucket 3.1 descriptor schema: {detail}"
        )


def compute_descriptors(sequence: str) -> dict[str, float]:
    """Compute the frozen 15-descriptor vector for a single sequence.

    Raises ``InvalidPeptideError`` for any sequence outside the standard
    20-AA alphabet or the 3-50 AA length window -- never silently
    substitutes, truncates, or drops residues.
    """
    _validate_or_raise(["<single>"], [sequence])
    return {
        "length": float(len(sequence)),
        "molecular_weight": molecular_weight(sequence),
        "net_charge_ph7": net_charge_at_ph(sequence, 7.0),
        "isoelectric_point": isoelectric_point(sequence),
        "gravy": gravy(sequence),
        "aromaticity": aromaticity(sequence),
        "instability_index": instability_index(sequence),
        "aliphatic_index": aliphatic_index(sequence),
        "hydrophobic_moment": hydrophobic_moment(sequence),
        "frac_charged": frac_charged(sequence),
        "frac_polar": frac_polar(sequence),
        "frac_hydrophobic": frac_hydrophobic(sequence),
        "frac_positive": frac_positive(sequence),
        "frac_negative": frac_negative(sequence),
        "frac_proline": frac_proline(sequence),
    }


def compute_descriptors_batch(peptide_ids: list[str], sequences: list[str]) -> pd.DataFrame:
    """Compute the 15-descriptor matrix for a batch, with peptide-ID mapping.

    Numerically identical to calling ``compute_descriptors`` once per
    sequence (no batch-level statistics are computed or applied -- raw,
    per-sequence descriptors only, per Task 3.1 scope).
    """
    if len(peptide_ids) != len(sequences):
        raise ValueError(
            f"peptide_ids ({len(peptide_ids)}) and sequences ({len(sequences)}) length mismatch"
        )
    _validate_or_raise(peptide_ids, sequences)
    rows = [compute_descriptors(seq) for seq in sequences]
    df = pd.DataFrame(rows, columns=list(DESCRIPTOR_NAMES))
    df.insert(0, "sequence", sequences)
    df.insert(0, "peptide_id", peptide_ids)
    return df
