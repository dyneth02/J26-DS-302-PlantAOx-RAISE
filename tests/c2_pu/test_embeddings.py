"""Tests for common/embeddings.py (Bucket 3.2 — ESM-2 embedding interface).

The model-loading/inference tests actually invoke fair-esm + torch and
download/cache ~140MB of weights on first run, so they're marked slow and
skipped cleanly if torch/esm aren't importable in this Python environment
(these tests run from the WSL `pu_aop` conda env where torch/fair-esm are
installed, not the Windows .venv used for the rest of the test suite).
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")
esm = pytest.importorskip("esm")

from plantaox.c2_pu.common.embeddings import (
    EXPECTED_EMBEDDING_DIM,
    REPRESENTATION_LAYER,
    AmbiguousResidueError,
    embed_sequences,
    load_embedder,
    resolve_device,
)


def test_resolve_device_force_cpu_always_returns_cpu():
    assert resolve_device(force_cpu=True) == torch.device("cpu")


def test_resolve_device_returns_cpu_when_cuda_unavailable(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device(force_cpu=False) == torch.device("cpu")


@pytest.fixture(scope="module")
def embedder():
    return load_embedder(force_cpu=True)


@pytest.fixture(scope="module")
def sample_peptides():
    # Small, standard-alphabet, mixed-length peptides -- not drawn from the
    # frozen FR1 positive pool on purpose, so this test never depends on
    # that data being present.
    return {
        "PEP-SHORT": "KPEEDWGR",
        "PEP-MED": "MIRIISRANSVTSSNEVNRLVTGQIPHD",
        "PEP-CHARGED": "KKKKKEEEEE",
        "PEP-HYDROPHOBIC": "LLLVVVIIIAAA",
    }


def test_load_embedder_matches_frozen_spec(embedder):
    assert embedder.embedding_dim == EXPECTED_EMBEDDING_DIM == 480
    assert embedder.device == torch.device("cpu")
    assert not embedder.model.training  # eval mode


def test_embed_sequences_shapes_and_finiteness(embedder, sample_peptides):
    ids = list(sample_peptides.keys())
    seqs = list(sample_peptides.values())
    result = embed_sequences(embedder, ids, seqs)

    assert set(result.keys()) == set(ids)  # peptide-ID alignment
    for pid in ids:
        vec = result[pid]
        assert vec.shape == (EXPECTED_EMBEDDING_DIM,)
        assert vec.dtype == __import__("numpy").float32
        assert __import__("numpy").isfinite(vec).all()


def test_embed_sequences_is_deterministic_in_eval_mode(embedder, sample_peptides):
    ids = list(sample_peptides.keys())
    seqs = list(sample_peptides.values())
    first = embed_sequences(embedder, ids, seqs)
    second = embed_sequences(embedder, ids, seqs)
    for pid in ids:
        assert (first[pid] == second[pid]).all()


def test_embed_sequences_different_sequences_give_different_vectors(embedder, sample_peptides):
    ids = list(sample_peptides.keys())
    seqs = list(sample_peptides.values())
    result = embed_sequences(embedder, ids, seqs)
    # Sanity: a charged-residue peptide and a hydrophobic one should not
    # collapse to (near-)identical embeddings.
    diff = abs(result["PEP-CHARGED"] - result["PEP-HYDROPHOBIC"]).sum()
    assert diff > 1.0


def test_embed_sequences_batching_matches_single_batch(embedder, sample_peptides):
    ids = list(sample_peptides.keys())
    seqs = list(sample_peptides.values())
    one_batch = embed_sequences(embedder, ids, seqs, batch_size=32)
    tiny_batches = embed_sequences(embedder, ids, seqs, batch_size=1)
    for pid in ids:
        assert __import__("numpy").allclose(one_batch[pid], tiny_batches[pid], atol=1e-5)


def test_embed_sequences_rejects_ambiguous_residues_by_default(embedder):
    with pytest.raises(AmbiguousResidueError, match="PEP-X"):
        embed_sequences(embedder, ["PEP-X"], ["MKRXX"])


def test_embed_sequences_allows_ambiguous_when_explicitly_opted_in(embedder):
    # Opting out of validation should not crash -- ESM's alphabet has
    # first-class tokens for X/B/Z/U.
    result = embed_sequences(embedder, ["PEP-X"], ["MKRXX"], validate_alphabet=False)
    assert result["PEP-X"].shape == (EXPECTED_EMBEDDING_DIM,)
    assert __import__("numpy").isfinite(result["PEP-X"]).all()


def test_embed_sequences_rejects_mismatched_lengths(embedder):
    with pytest.raises(ValueError, match="same length"):
        embed_sequences(embedder, ["A", "B"], ["AAAA"])


def test_embed_sequences_rejects_duplicate_peptide_ids(embedder):
    with pytest.raises(ValueError, match="unique"):
        embed_sequences(embedder, ["A", "A"], ["AAAA", "KKKK"])


def test_representation_layer_is_the_models_final_layer(embedder):
    assert REPRESENTATION_LAYER == embedder.model.num_layers
