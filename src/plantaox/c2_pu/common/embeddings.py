"""ESM-2 (esm2_t12_35M_UR50D) embedding extraction (Bucket 3.2).

Frozen specification (do not change without a new decision-log entry, per
AGENTS.md rule #4 -- this spec is what every downstream cached embedding,
C3 centroid, and fused feature vector will assume):

- **Model**: ``esm2_t12_35M_UR50D`` (fair-esm pretrained checkpoint; 12
  transformer layers, 480-dim hidden representation). Loaded via
  ``esm.pretrained.esm2_t12_35M_UR50D()``, which downloads and caches
  weights under ``~/.cache/torch/hub/checkpoints`` on first use (not
  committed to git -- see AGENTS.md "don't commit model weights").
- **Representation layer**: 12 (the model's final/top transformer layer --
  ``t12`` means 12 layers total, so layer 12 is the last one, not an
  arbitrary middle layer).
- **Tokenization**: the model's own ``alphabet.get_batch_converter()``
  (BOS + residues + EOS, right-padded per batch). Verified empirically
  against a live model load, not assumed from documentation, that
  ``prepend_bos``/``append_eos`` are both True for this checkpoint -- see
  ``test_embeddings.py``.
- **Pooling**: mean over real residue positions only. BOS, EOS, and PAD
  tokens are excluded from the mean using each sequence's own known length
  (``tokens[i, 1:len(seq)+1]``), not a padding-mask heuristic.
- **Output**: float32 numpy array, shape ``(480,)`` per sequence.
- **Device**: CUDA only if ``torch.cuda.is_available()`` AND a real tensor
  op on it succeeds -- never claimed from driver/``nvidia-smi`` presence
  alone (this environment currently runs CPU-only by project-owner
  decision, 2026-10-14 -- see IMPLEMENTATION_STATUS.md decision log).
- **Inference**: ``model.eval()`` + ``torch.no_grad()``. Deterministic --
  ESM-2 has no dropout/batchnorm active at eval time, so repeated calls on
  the same input produce bit-identical output.

**Ambiguous residues (X, B, Z, U) are never silently translated.** ESM's
own alphabet has first-class tokens for these (it is not a hack to pass
them through), but whether to EMBED a sequence containing them is a policy
decision this module refuses to make unilaterally: ``embed_sequences``
validates every sequence against the 20-letter standard alphabet by
default and raises ``AmbiguousResidueError`` (naming every offending
peptide_id, sequence, and residue) rather than silently embedding or
silently skipping them. Callers that have made an explicit, documented
decision about how to handle them pass ``validate_alphabet=False``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from plantaox.c2_pu.common.sequence import STANDARD_AMINO_ACIDS, is_standard_alphabet

MODEL_NAME = "esm2_t12_35M_UR50D"
REPRESENTATION_LAYER = 12
EXPECTED_EMBEDDING_DIM = 480


class AmbiguousResidueError(ValueError):
    """Raised when embed_sequences() is given a non-standard-alphabet
    sequence without an explicit validate_alphabet=False opt-out."""


@dataclass(frozen=True)
class EsmEmbedder:
    model: torch.nn.Module
    alphabet: object
    device: torch.device
    embedding_dim: int


def resolve_device(force_cpu: bool = False) -> torch.device:
    """CUDA only if available AND a real tensor op on it succeeds."""
    if force_cpu or not torch.cuda.is_available():
        return torch.device("cpu")
    try:
        (torch.zeros(1, device="cuda") + 1).cpu()
        return torch.device("cuda")
    except Exception:
        return torch.device("cpu")


def load_embedder(force_cpu: bool = False) -> EsmEmbedder:
    """Load esm2_t12_35M_UR50D in eval mode on the resolved device.

    Downloads and caches weights on first call (fair-esm's own cache
    mechanism) -- not something this repo commits to git.
    """
    import esm  # fair-esm; deferred import so modules that don't need it
    # (e.g. common/__init__) don't pay torch's import cost.

    model, alphabet = esm.pretrained.esm2_t12_35M_UR50D()
    model.eval()
    device = resolve_device(force_cpu)
    model = model.to(device)

    embedding_dim = model.embed_dim
    if embedding_dim != EXPECTED_EMBEDDING_DIM:
        raise RuntimeError(
            f"Expected {EXPECTED_EMBEDDING_DIM}-dim embeddings from {MODEL_NAME}, got "
            f"{embedding_dim} -- the loaded checkpoint doesn't match the frozen spec."
        )
    return EsmEmbedder(model=model, alphabet=alphabet, device=device, embedding_dim=embedding_dim)


def embed_sequences(
    embedder: EsmEmbedder,
    peptide_ids: list[str],
    sequences: list[str],
    batch_size: int = 32,
    validate_alphabet: bool = True,
) -> dict[str, np.ndarray]:
    """Mean-pooled (excluding BOS/EOS/PAD) layer-12 embeddings, float32, keyed by peptide_id.

    Raises AmbiguousResidueError if validate_alphabet (default) and any
    sequence contains a non-standard residue (X/B/Z/U/etc.) -- this never
    silently translates or drops them.
    """
    if len(peptide_ids) != len(sequences):
        raise ValueError("peptide_ids and sequences must be the same length")
    if len(set(peptide_ids)) != len(peptide_ids):
        raise ValueError("peptide_ids must be unique")

    if validate_alphabet:
        offending = [
            (pid, seq, sorted(set(seq) - set(STANDARD_AMINO_ACIDS)))
            for pid, seq in zip(peptide_ids, sequences)
            if not is_standard_alphabet(seq)
        ]
        if offending:
            detail = "; ".join(f"{pid} ({seq}): {residues}" for pid, seq, residues in offending)
            raise AmbiguousResidueError(
                f"{len(offending)} sequence(s) contain non-standard residues and "
                f"validate_alphabet=True (default): {detail}. Pass validate_alphabet=False "
                "only after making an explicit, documented decision about how ESM-2 should "
                "treat these (see IMPLEMENTATION_STATUS.md)."
            )

    results: dict[str, np.ndarray] = {}
    batch_converter = embedder.alphabet.get_batch_converter()
    for start in range(0, len(sequences), batch_size):
        batch_ids = peptide_ids[start : start + batch_size]
        batch_seqs = sequences[start : start + batch_size]
        _, _, tokens = batch_converter(list(zip(batch_ids, batch_seqs)))
        tokens = tokens.to(embedder.device)

        with torch.no_grad():
            out = embedder.model(tokens, repr_layers=[REPRESENTATION_LAYER], return_contacts=False)
        representations = out["representations"][REPRESENTATION_LAYER]  # (B, L, 480)

        for i, (pid, seq) in enumerate(zip(batch_ids, batch_seqs)):
            # Position 0 is BOS; positions 1..len(seq) are the residues;
            # position len(seq)+1 is EOS; anything after is PAD.
            residue_repr = representations[i, 1 : len(seq) + 1]
            mean_repr = residue_repr.mean(dim=0).to(torch.float32).cpu().numpy()
            results[pid] = mean_repr
    return results
