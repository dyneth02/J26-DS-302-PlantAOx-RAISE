"""aop_procon -- helper for the AOP-ProCon release v1 (Component 1).

Scope: validate peptide sequences, embed them with ESM-2 650M (same pooling rule as the pipeline), score them with two WEAK
MC-active-vs-FRS-only probes, and return the table described in the release CONTRACT. The probes are NOT activity predictors.

Layout (repository paths, relative to ``data/processed/c1_procon``):
    AOP-BenchPos_S2.csv            the benchmark
    results/oof_probe_scores.csv   out-of-fold probe scores for the benchmark peptides
    release/probes/probe_*.npz     fitted probe weights (strict / extended)
The ESM-2 embedding cache (``esm2_650M.npy`` + ``esm2_650M_sequences.txt``) is NOT committed (large binary files); point
``C1_EMBEDDINGS_DIR`` at a folder that holds it, or pass ``embeddings`` to :func:`score_peptides`.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

AA = "ACDEFGHIKLMNPQRSTVWY"
MODEL_NAME = "esm2_t33_650M_UR50D"
POOLING_RULE = "last layer; max-pool over residues for < 10 aa, mean-pool for >= 10 aa"
TRAIN_LENGTH_RANGE = (3, 49)  # lengths present in the benchmark
EMBEDDING_DIM = 1280


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate the repository root (no pyproject.toml found).")


DATA_DIR = _repo_root() / "data" / "processed" / "c1_procon"


def embeddings_dir() -> Path:
    return Path(os.environ.get("C1_EMBEDDINGS_DIR", DATA_DIR / "embeddings"))


def validate_sequence(seq):
    """Return a list of problems (empty list = valid)."""
    problems = []
    if not isinstance(seq, str) or not seq:
        return ["empty or non-string"]
    bad = sorted(set(seq) - set(AA))
    if bad:
        problems.append("non-canonical residues: " + "".join(bad))
    if len(seq) < TRAIN_LENGTH_RANGE[0] or len(seq) > TRAIN_LENGTH_RANGE[1]:
        problems.append(f"length {len(seq)} outside the benchmark range {TRAIN_LENGTH_RANGE}")
    return problems


def composition(seqs):
    """20-D amino-acid composition (rows sum to 1)."""
    return np.array([[s.count(a) / len(s) for a in AA] for s in seqs])


def load_benchmark():
    return pd.read_csv(DATA_DIR / "AOP-BenchPos_S2.csv")


def load_cache(scale="650M"):
    """Dictionary sequence -> embedding for the 1,389 benchmark sequences (row order file is checked)."""
    folder = embeddings_dir()
    npy, txt = folder / f"esm2_{scale}.npy", folder / f"esm2_{scale}_sequences.txt"
    if not npy.exists() or not txt.exists():
        raise FileNotFoundError(
            f"ESM-2 {scale} cache not found in {folder}. The embedding arrays are not committed to the repository: regenerate them "
            "with notebooks/c1_procon/STEP02, or set C1_EMBEDDINGS_DIR, or pass `embeddings` to score_peptides()."
        )
    arr = np.load(npy)
    seqs = txt.read_text(encoding="utf-8").splitlines()
    assert len(seqs) == arr.shape[0], "embedding rows and sequence list differ"
    return dict(zip(seqs, arr))


_PROBES: dict = {}


def load_probe(mode="strict"):
    if mode not in _PROBES:
        with np.load(DATA_DIR / "release" / "probes" / f"probe_{mode}.npz") as p:
            _PROBES[mode] = {k: p[k] for k in p.files}
    return _PROBES[mode]


def probe_score(E, mode="strict"):
    """Probability-like score for MC-active (1) vs FRS-only (0). Weak: see the CONTRACT for the cross-validated AUROC."""
    p = load_probe(mode)
    z = (np.asarray(E, float) - p["mean"]) / p["scale"]
    return 1.0 / (1.0 + np.exp(-(z @ p["coef"] + float(p["intercept"][0]))))


def esm_embed(seqs, model=None, alphabet=None, device="cpu", batch_size=32):
    """ESM-2 650M embeddings with the pipeline's pooling rule. Loads the model through fair-esm unless one is passed in."""
    import torch

    if model is None:
        import esm

        model, alphabet = getattr(esm.pretrained, MODEL_NAME)()
        model = model.to(device)
    model.eval()
    bc = alphabet.get_batch_converter()
    nl = model.num_layers
    out = []
    for start in range(0, len(seqs), batch_size):
        chunk = list(seqs[start : start + batch_size])
        _, _, tokens = bc([(str(i), s) for i, s in enumerate(chunk)])
        with torch.no_grad():
            reps = model(tokens.to(device), repr_layers=[nl])["representations"][nl]
        for i, s in enumerate(chunk):
            per_res = reps[i, 1 : len(s) + 1].cpu()  # drops the start and end tokens
            out.append((per_res.max(0).values if len(s) < 10 else per_res.mean(0)).numpy())
    return np.stack(out)


def score_peptides(seqs, embeddings=None, device="cpu"):
    """Return the contract table (one row per input sequence, same order).

    embeddings: optional array (n, 1280) aligned with seqs; otherwise the embedding cache is used for benchmark sequences
    and ESM-2 is run for the others.
    """
    seqs = [s.strip().upper() if isinstance(s, str) else s for s in seqs]
    bench = load_benchmark().set_index("sequence")
    oof = pd.read_csv(DATA_DIR / "results" / "oof_probe_scores.csv").set_index("sequence")
    probs = [validate_sequence(s) for s in seqs]
    if embeddings is None:
        cache = load_cache("650M")
        E = np.full((len(seqs), EMBEDDING_DIM), np.nan)
        need = [i for i, s in enumerate(seqs) if s not in cache and not probs[i]]
        for i, s in enumerate(seqs):
            if s in cache:
                E[i] = cache[s]
        if need:
            E[need] = esm_embed([seqs[i] for i in need], device=device)
    else:
        E = np.asarray(embeddings, float)
        assert E.shape == (len(seqs), EMBEDDING_DIM), "embeddings must have shape (n, 1280)"
    ok = np.isfinite(E).all(1)
    rows = []
    for i, s in enumerate(seqs):
        mech_active = False
        r = {
            "sequence": s,
            "length": len(s) if isinstance(s, str) else None,
            "valid": not probs[i],
            "problems": "; ".join(probs[i]),
            "in_benchmark": s in bench.index,
        }
        if r["in_benchmark"]:
            b = bench.loc[s]
            se = b["strict_evidence"]
            se = bool(se) if pd.notna(se) else None  # GEN peptides have no strict_evidence value
            r.update({"benchmark_labels": b["labels"], "fold": b["lso_fold"], "homology_group": b["homology_group"], "strict_evidence": se})
            mech_active = b["labels"] != "GEN"
            r["oof_mc_score_strict"] = oof.loc[s].get("oof_mc_score_strict", np.nan)
            r["oof_mc_score_extended"] = oof.loc[s].get("oof_mc_score_extended", np.nan)
        for mode in ("strict", "extended"):
            r[f"mc_score_{mode}"] = float(probe_score(E[i : i + 1], mode)[0]) if ok[i] else np.nan
        # a probe score is in-sample if the peptide belonged to the pool that probe was fitted on
        r["score_is_in_sample_strict"] = bool(r["in_benchmark"] and mech_active and r.get("strict_evidence") is True)
        r["score_is_in_sample_extended"] = bool(r["in_benchmark"] and mech_active)
        r["warning"] = (
            "weak signal: repeated-grouped-CV AUROC about 0.6-0.7, not distinguishable from amino-acid composition; the single feature "
            "source_group is as good, and ESM-2 adds nothing measurable on top of composition + length + source; "
            "for benchmark peptides use the oof_* columns"
        )
        rows.append(r)
    return pd.DataFrame(rows)
