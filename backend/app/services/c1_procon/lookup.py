"""Peptide look-up: validation, benchmark record, amino-acid composition and nearest benchmark peptides.

Mirrors the input rules of the release helper ``aop_procon.validate_sequence`` (20 canonical amino acids, benchmark
length range 3-49). No model is run: scoring a peptide that is not in the benchmark needs its ESM-2 embedding, which
the downloadable release does offline. The query is only ever used as a string; it is never turned into a path.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from backend.app.schemas.c1_procon import LookupRecord, LookupResponse, NearestPeptide
from backend.app.services.c1_procon.artifacts import num, read_csv

AA = "ACDEFGHIKLMNPQRSTVWY"
BENCHMARK_LENGTH_RANGE = (3, 49)
MAX_QUERY_LENGTH = 200
NEAREST = 5


def composition_vector(sequence: str) -> np.ndarray:
    return np.array([sequence.count(a) / len(sequence) for a in AA], dtype=float)


@lru_cache(maxsize=1)
def _benchmark() -> tuple[pd.DataFrame, np.ndarray]:
    s2 = read_csv("AOP-BenchPos_S2.csv")
    oof = read_csv("results/oof_probe_scores.csv")[["sequence", "oof_mc_score_strict", "oof_mc_score_extended"]]
    table = s2.merge(oof, on="sequence", how="left").reset_index(drop=True)
    matrix = np.stack([composition_vector(seq) for seq in table["sequence"]])
    return table, matrix


def clear_cache() -> None:
    _benchmark.cache_clear()


def _problems(sequence: str) -> list[str]:
    if not sequence:
        return ["empty input"]
    if len(sequence) > MAX_QUERY_LENGTH:
        return [f"too long (more than {MAX_QUERY_LENGTH} letters)"]
    bad = sorted(set(sequence) - set(AA))
    if bad:
        return ["non-canonical residues: " + "".join(bad) + " (only the 20 standard amino acids are accepted)"]
    return []


def _opt_int(value) -> int | None:
    f = num(value)
    return None if f is None else int(f)


def lookup_peptide(raw: str) -> LookupResponse:
    sequence = (raw or "").strip().upper()
    problems = _problems(sequence)
    if problems:
        return LookupResponse(
            query=sequence[:MAX_QUERY_LENGTH], valid=False, problems=problems, in_benchmark=False, composition={}, nearest=[], notes=[]
        )

    notes: list[str] = []
    low, high = BENCHMARK_LENGTH_RANGE
    if not low <= len(sequence) <= high:
        notes.append(f"Length {len(sequence)} is outside the benchmark range {low}-{high} amino acids: any conclusion is an extrapolation.")

    table, matrix = _benchmark()
    hit = table[table["sequence"] == sequence]
    record: LookupRecord | None = None
    if not hit.empty:
        r = hit.iloc[0]
        strict = r["strict_evidence"]
        record = LookupRecord(
            sequence=sequence,
            labels=str(r["labels"]),
            length=int(r["length"]),
            source_group=None if pd.isna(r["source_group"]) else str(r["source_group"]),
            fold=_opt_int(r["lso_fold"]),
            homology_group=_opt_int(r["homology_group"]),
            strict_evidence=None if pd.isna(strict) else str(strict) == "True",
            oof_mc_score_strict=num(r["oof_mc_score_strict"]),
            oof_mc_score_extended=num(r["oof_mc_score_extended"]),
        )
        if record.labels == "GEN":
            notes.append("GEN means antioxidant according to a database, but the mechanism is not established. It does not mean inactive.")
        notes.append(
            "The out-of-fold MC scores come from a weak probe (fold-mean AUROC about 0.61 strict); the single feature data source scores 0.64. "
            "They are not a mechanism, activity or safety prediction."
        )
    else:
        notes.append(
            "This peptide is not in the benchmark. Scoring a new peptide needs its ESM-2 650M embedding, which the release package "
            "(aop_procon.score_peptides) computes offline; any score would carry the same weak signal (AUROC about 0.6)."
        )

    vec = composition_vector(sequence)
    norms = np.linalg.norm(matrix, axis=1) * (np.linalg.norm(vec) or 1.0)
    cosines = (matrix @ vec) / np.where(norms == 0, 1.0, norms)
    order = [i for i in np.argsort(-cosines) if table.at[i, "sequence"] != sequence][:NEAREST]
    nearest = [
        NearestPeptide(
            sequence=str(table.at[i, "sequence"]),
            labels=str(table.at[i, "labels"]),
            length=int(table.at[i, "length"]),
            cosine=float(cosines[i]),
        )
        for i in order
    ]

    return LookupResponse(
        query=sequence,
        valid=True,
        problems=[],
        in_benchmark=record is not None,
        record=record,
        composition={a: float(v) for a, v in zip(AA, vec)},
        nearest=nearest,
        notes=notes,
    )
