"""Live C3 perturbation scoring for a user-supplied sequence, c2_logreg predictor only.

Deliberately does NOT import generate_c3_artifacts.py -- that module's
`from multiaop_model import MultiAOPPredictor` pulls in torch_geometric/rdkit/xlstm,
none of which this endpoint needs (multiaop_pretrained stays "browse pre-computed
results only" per the implementation plan). The perturbation logic (alanine scan /
BLOSUM62-conservative substitution / random substitution) and the LogRegPredictorAdapter
scoring call are reimplemented here, verified line-for-line against
generate_c3_artifacts.py, rather than importing that heavier module.
"""
from __future__ import annotations

import random
import sys
import threading

import joblib
import numpy as np
from Bio.Align import substitution_matrices

from . import paths

_lock = threading.Lock()
_state: dict = {}

REDOX_RESIDUES = set("WYHMC")
AA = list("ACDEFGHIKLMNPQRSTVWY")
DELTA_THRESHOLD = 0.05
RANDOM_SEED = 42


def _import_descriptors():
    sys.path.insert(0, str(paths.SCRIPTS_DIR))
    from common_descriptors import compute_descriptors, is_valid_sequence  # noqa: E402
    return compute_descriptors, is_valid_sequence


def load_c3_state() -> None:
    with _lock:
        if _state:
            return
        compute_descriptors, is_valid_sequence = _import_descriptors()
        bundle = joblib.load(paths.ARTIFACTS_ROOT / "c2" / "pu_model.joblib")
        _state["model"] = bundle["model"]
        _state["scaler"] = bundle["scaler"]
        _state["feature_cols"] = bundle["features"]
        _state["compute_descriptors"] = compute_descriptors
        _state["is_valid_sequence"] = is_valid_sequence
        _state["blosum62"] = substitution_matrices.load("BLOSUM62")
        print("[live/c3] loaded pu_model.joblib + BLOSUM62")


def _blosum_conservative_sub(residue: str, blosum62) -> str:
    scores = {aa: blosum62[residue, aa] for aa in AA if aa != residue}
    return max(scores, key=scores.get)


def _random_sub(residue: str, rng: random.Random) -> str:
    return rng.choice([aa for aa in AA if aa != residue])


def _mutate_at(seq: str, pos: int, new_residue: str) -> str:
    return seq[:pos] + new_residue + seq[pos + 1:]


def _score_batch(sequences: list[str]) -> list[float]:
    compute_descriptors = _state["compute_descriptors"]
    feature_cols = _state["feature_cols"]
    rows = [compute_descriptors(s) for s in sequences]
    x = np.array([[r[c] for c in feature_cols] for r in rows])
    scaled = _state["scaler"].transform(x)
    return _state["model"].predict_proba(scaled)[:, 1].tolist()


def live_perturbation(sequence: str) -> dict:
    is_valid_sequence = _state["is_valid_sequence"]
    seq = sequence.strip().upper()

    if not (3 <= len(seq) <= 50):
        raise ValueError("Sequence must be 3-50 amino acids long.")
    if not is_valid_sequence(seq):
        raise ValueError("Sequence contains characters outside the 20 standard amino acids.")

    redox_positions = [i for i, c in enumerate(seq) if c in REDOX_RESIDUES]
    non_redox_positions = [i for i, c in enumerate(seq) if c not in REDOX_RESIDUES]
    if not redox_positions:
        raise ValueError(
            "Sequence has no redox-active residue (W/Y/H/M/C) to alanine-scan -- "
            "try a different sequence."
        )
    if not non_redox_positions:
        raise ValueError(
            "Sequence has no non-redox residue to substitute for the conservative/random "
            "perturbations -- try a different sequence."
        )

    # A request-scoped RNG (not the global `random` module) so concurrent requests for
    # different sequences never share/perturb each other's mutation state.
    rng = random.Random(hash(seq) & 0xFFFFFFFF)

    p1_pos = rng.choice(redox_positions)
    p1_seq = _mutate_at(seq, p1_pos, "A")

    p2_pos = rng.choice(non_redox_positions)
    p2_new = _blosum_conservative_sub(seq[p2_pos], _state["blosum62"])
    p2_seq = _mutate_at(seq, p2_pos, p2_new)

    p3_pos = rng.choice(non_redox_positions)
    p3_new = _random_sub(seq[p3_pos], rng)
    p3_seq = _mutate_at(seq, p3_pos, p3_new)

    scores = _score_batch([seq, p1_seq, p2_seq, p3_seq])
    original_score, p1_score, p2_score, p3_score = (round(s, 4) for s in scores)

    return {
        "sequence": seq,
        "original_score": original_score,
        "perturbations": [
            {
                "type": "P1_alanine_scan",
                "position": p1_pos,
                "original_residue": seq[p1_pos],
                "sequence": p1_seq,
                "score": p1_score,
                "delta": round(p1_score - original_score, 4),
            },
            {
                "type": "P2_blosum62_conservative",
                "position": p2_pos,
                "original_residue": seq[p2_pos],
                "new_residue": p2_new,
                "sequence": p2_seq,
                "score": p2_score,
                "delta": round(p2_score - original_score, 4),
            },
            {
                "type": "P3_random_control",
                "position": p3_pos,
                "original_residue": seq[p3_pos],
                "new_residue": p3_new,
                "sequence": p3_seq,
                "score": p3_score,
                "delta": round(p3_score - original_score, 4),
            },
        ],
        "predictor": "c2_logreg",
        "live": True,
    }
