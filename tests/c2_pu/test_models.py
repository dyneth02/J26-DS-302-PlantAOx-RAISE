"""Unit tests for models.py (Bucket 4.1 §B) -- architecture only, no
training objective is exercised here (there isn't one to exercise yet)."""

from __future__ import annotations

import torch
import pytest

from plantaox.c2_pu.models import ArchitectureMismatchError, BinaryMlp, MlpArchitecture


def test_default_architecture_matches_the_proposed_initial_design():
    arch = MlpArchitecture()
    assert arch.input_dim == 495
    assert arch.hidden_dims == (128, 64)
    assert arch.activation == "relu"


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"input_dim": 0}, "input_dim"),
        ({"input_dim": -5}, "input_dim"),
        ({"hidden_dims": ()}, "hidden_dims"),
        ({"hidden_dims": (128, 0)}, "hidden_dims"),
        ({"activation": "tanh"}, "activation"),
    ],
)
def test_architecture_rejects_invalid_parameters(kwargs, match):
    with pytest.raises(ValueError, match=match):
        MlpArchitecture(**kwargs)


@pytest.mark.parametrize("input_dim", [495, 480, 15])
def test_forward_output_shape_and_finiteness(input_dim):
    model = BinaryMlp(MlpArchitecture(input_dim=input_dim))
    x = torch.randn(16, input_dim)
    logits = model(x)
    assert logits.shape == (16, 1)
    assert torch.isfinite(logits).all()


def test_forward_rejects_wrong_input_dim():
    model = BinaryMlp(MlpArchitecture(input_dim=495))
    with pytest.raises(ValueError, match="Expected input shape"):
        model(torch.randn(4, 480))


def test_predict_proba_is_bounded_and_matches_sigmoid_of_logits():
    model = BinaryMlp(MlpArchitecture(input_dim=495))
    x = torch.randn(10, 495)
    proba = model.predict_proba(x)
    assert proba.shape == (10, 1)
    assert bool(((proba >= 0) & (proba <= 1)).all())
    with torch.no_grad():
        expected = torch.sigmoid(model(x))
    torch.testing.assert_close(proba, expected)


def test_predict_proba_does_not_permanently_change_training_mode():
    model = BinaryMlp(MlpArchitecture(input_dim=495))
    model.train()
    model.predict_proba(torch.randn(2, 495))
    assert model.training is True
    model.eval()
    model.predict_proba(torch.randn(2, 495))
    assert model.training is False


def test_configurable_hidden_dims_change_parameter_count():
    small = BinaryMlp(MlpArchitecture(input_dim=495, hidden_dims=(8,)))
    big = BinaryMlp(MlpArchitecture(input_dim=495, hidden_dims=(128, 64)))
    n_small = sum(p.numel() for p in small.parameters())
    n_big = sum(p.numel() for p in big.parameters())
    assert n_big > n_small


def test_architecture_signature_round_trips_through_dict():
    model = BinaryMlp(MlpArchitecture(input_dim=15, hidden_dims=(32,)))
    signature = model.architecture_signature()
    restored = MlpArchitecture.from_dict(signature)
    assert restored == model.architecture


def test_load_compatible_state_dict_accepts_matching_architecture():
    source = BinaryMlp(MlpArchitecture(input_dim=495))
    target = BinaryMlp(MlpArchitecture(input_dim=495))
    target.load_compatible_state_dict(source.state_dict(), source.architecture_signature())
    for p1, p2 in zip(source.parameters(), target.parameters()):
        assert torch.equal(p1, p2)


def test_load_compatible_state_dict_rejects_mismatched_architecture():
    source = BinaryMlp(MlpArchitecture(input_dim=495, hidden_dims=(128, 64)))
    target = BinaryMlp(MlpArchitecture(input_dim=480, hidden_dims=(128, 64)))
    with pytest.raises(ArchitectureMismatchError):
        target.load_compatible_state_dict(source.state_dict(), source.architecture_signature())
