"""Standalone entrypoint executed *inside* the WSL `pu_aop` conda env, where
torch/fair-esm are installed -- never imported directly by run.py (which
runs on the Windows-side Python that does NOT have torch). Invoked via
common/wsl.py's run_in_conda_env, the same subprocess pattern used for
CD-HIT and GraphPart.

Usage (from inside the pu_aop env):
    python esm2_cli.py <input.json> <output.json>

input.json: {"peptide_ids": [...], "sequences": [...], "force_cpu": bool,
             "validate_alphabet": bool, "batch_size": int,
             "save_embeddings_path": <optional str>}
output.json: a SUMMARY report only (shape/dtype/finiteness/norm per
peptide) -- raw embedding vectors are never written there, so nothing from
this script risks committing large embedding arrays to git via output.json.

If ``save_embeddings_path`` is given, the raw embedding matrix is ALSO
written there as a compressed ``.npz`` (``peptide_ids``, ``embeddings``) for
callers that genuinely need the vectors (e.g. Bucket 2.3's C3 fold-safe
centroid construction) -- that path must itself be gitignored by the
caller (see IMPLEMENTATION_STATUS.md: embedding caches are a reproducible,
regeneratable local artifact, same as model weights, never committed).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo's src/

import numpy as np

from plantaox.c2_pu.common.embeddings import embed_sequences, load_embedder


def main(argv: list[str]) -> int:
    input_path, output_path = argv[1], argv[2]
    with open(input_path, encoding="utf-8") as handle:
        payload = json.load(handle)

    embedder = load_embedder(force_cpu=payload.get("force_cpu", False))

    start = time.perf_counter()
    embeddings = embed_sequences(
        embedder,
        payload["peptide_ids"],
        payload["sequences"],
        batch_size=payload.get("batch_size", 32),
        validate_alphabet=payload.get("validate_alphabet", True),
    )
    elapsed = time.perf_counter() - start

    save_embeddings_path = payload.get("save_embeddings_path")
    if save_embeddings_path:
        ordered_ids = list(embeddings.keys())
        matrix = np.stack([embeddings[pid] for pid in ordered_ids])
        np.savez_compressed(save_embeddings_path, peptide_ids=np.array(ordered_ids), embeddings=matrix)

    report = {
        "model_name": "esm2_t12_35M_UR50D",
        "representation_layer": 12,
        "device": str(embedder.device),
        "embedding_dim": embedder.embedding_dim,
        "n_sequences": len(payload["sequences"]),
        "elapsed_seconds": elapsed,
        "per_peptide": {
            pid: {
                "shape": list(vec.shape),
                "dtype": str(vec.dtype),
                "all_finite": bool(np.isfinite(vec).all()),
                "mean": float(vec.mean()),
                "std": float(vec.std()),
                "l2_norm": float(np.linalg.norm(vec)),
            }
            for pid, vec in embeddings.items()
        },
    }
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
