"""Live C1 retrieval: cosine-similarity search against the REAL trained 128-D embedding
space, over the full Tier1/Tier2 pool (781 sequences) -- not just the 5 hardcoded
examples in c1_trained_retrieval_demo.json.

Reuses the exact projection-head-loading and projection logic from
generate_c1_trained_model_artifacts.py (same file that produced the static artifacts),
imported directly rather than reimplemented, so the live numbers stay consistent with
what's already shown on the page (same checkpoint, same population, same similarity
method as the displayed "primary_metrics").

Population choice: the query/gallery pool is tier12 (Tier1+Tier2 rows from
AOP-BenchPos.csv, 781 rows) -- the SAME population the static retrieval demo and the
displayed primary_metrics/ablation-comparison numbers are computed over. A row index is
used as the stable id (not a peptide_id lookup against the separate, Tier_Dual-deduped
aop_sequences.parquet) because a handful of dual-mechanism sequences legitimately appear
twice in tier12 (once per tier) -- row index avoids any ambiguity there.
"""
from __future__ import annotations

import sys
import threading

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from . import paths

_lock = threading.Lock()
_state: dict = {}


def _import_generator():
    sys.path.insert(0, str(paths.SCRIPTS_DIR))
    import generate_c1_trained_model_artifacts as c1gen  # noqa: E402
    return c1gen


def load_c1_state() -> None:
    """Load once at backend startup; safe to call again (no-op if already loaded)."""
    with _lock:
        if _state:
            return
        c1gen = _import_generator()

        aop_benchpos = pd.read_csv(paths.DATA_RAW / "AOP-BenchPos.csv")
        esm_embeddings = np.load(paths.DATA_RAW / "esm2_650M.npy")
        esm_sequences = (paths.DATA_RAW / "esm2_650M_sequences.txt").read_text().splitlines()
        assert (aop_benchpos["sequence"].values == np.array(esm_sequences)).all()

        seq_to_emb = {seq: emb for seq, emb in zip(aop_benchpos["sequence"], esm_embeddings)}

        tier12 = aop_benchpos[aop_benchpos["tier"].isin(["Tier1", "Tier2"])].reset_index(drop=True)

        head, _ = c1gen.load_projection_head("phase4_model.pt", 1280)
        project_fn = c1gen.make_project_fn(head, seq_to_emb)

        with torch.no_grad():
            pool_emb = project_fn(tier12["sequence"].tolist())  # (781, 128), already L2-normalized

        _state["tier12"] = tier12
        _state["pool_emb"] = pool_emb  # numpy array
        print(f"[live/c1] loaded projection head + {len(tier12)}-sequence pool embeddings")


def get_live_pool() -> list[dict]:
    """Lightweight list for the frontend's searchable query picker (no embeddings sent)."""
    tier12 = _state["tier12"]
    return [
        {"id": f"Q{i:04d}", "sequence": row.sequence, "mechanism_tier": row.tier}
        for i, row in enumerate(tier12.itertuples(index=False))
    ]


def live_retrieval(query_id: str, top_k: int = 10) -> dict:
    tier12 = _state["tier12"]
    pool_emb = _state["pool_emb"]

    try:
        qi = int(query_id.lstrip("Q"))
    except (ValueError, AttributeError):
        raise ValueError(f"Unknown query id: {query_id!r}")
    if not (0 <= qi < len(tier12)):
        raise ValueError(f"Unknown query id: {query_id!r}")

    sims = pool_emb @ pool_emb[qi]
    order = np.argsort(-sims)
    order = order[order != qi][:top_k]

    qrow = tier12.iloc[qi]
    return {
        "query": {"id": f"Q{qi:04d}", "sequence": qrow["sequence"], "mechanism_tier": qrow["tier"]},
        "top_matches": [
            {
                "rank": r + 1,
                "id": f"Q{idx:04d}",
                "sequence": tier12.iloc[idx]["sequence"],
                "mechanism_tier": tier12.iloc[idx]["tier"],
                "similarity": round(float(sims[idx]), 4),
            }
            for r, idx in enumerate(order)
        ],
        "pool_size": int(len(tier12)),
        "live": True,
    }
