"""Unit tests for common/seeding.py (Bucket 4.1 §D)."""

from __future__ import annotations

import random

import numpy as np
import torch
import pytest

from plantaox.c2_pu.common.seeding import resolve_device, set_global_seed
from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture


def test_set_global_seed_returns_the_expected_execution_context_keys():
    ctx = set_global_seed(123)
    expected_keys = {
        "effective_seed",
        "deterministic_algorithms_requested",
        "cuda_available",
        "cuda_device_name",
        "device_count",
        "cpu_count",
        "torch_version",
        "numpy_version",
        "python_version",
        "platform",
    }
    assert expected_keys <= set(ctx.keys())
    assert ctx["effective_seed"] == 123
    assert ctx["deterministic_algorithms_requested"] is True


def test_set_global_seed_rejects_non_int_seed():
    with pytest.raises(ValueError, match="seed"):
        set_global_seed(1.5)
    with pytest.raises(ValueError, match="seed"):
        set_global_seed(True)  # bool is technically an int subclass -- must be rejected explicitly


def test_python_random_is_reproducible_on_cpu():
    set_global_seed(7)
    a = [random.random() for _ in range(5)]
    set_global_seed(7)
    b = [random.random() for _ in range(5)]
    assert a == b


def test_numpy_random_is_reproducible_on_cpu():
    set_global_seed(7)
    a = np.random.rand(5)
    set_global_seed(7)
    b = np.random.rand(5)
    np.testing.assert_array_equal(a, b)


def test_torch_random_tensor_is_reproducible_on_cpu():
    set_global_seed(7)
    a = torch.randn(5, 5)
    set_global_seed(7)
    b = torch.randn(5, 5)
    assert torch.equal(a, b)


def test_model_initialization_and_forward_pass_is_reproducible_on_cpu():
    # The acceptance-grade check: same seed -> byte-identical model weights
    # AND byte-identical forward-pass output, on CPU (the only device
    # verified/available in this environment -- see module docstring for
    # why GPU bit-identity is explicitly NOT claimed).
    set_global_seed(99)
    model_a = BinaryMlp(MlpArchitecture(input_dim=495))
    x_a = torch.randn(4, 495)
    out_a = model_a(x_a)

    set_global_seed(99)
    model_b = BinaryMlp(MlpArchitecture(input_dim=495))
    x_b = torch.randn(4, 495)
    out_b = model_b(x_b)

    assert torch.equal(x_a, x_b)
    for p1, p2 in zip(model_a.parameters(), model_b.parameters()):
        assert torch.equal(p1, p2)
    assert torch.equal(out_a, out_b)


def test_different_seeds_produce_different_initializations():
    set_global_seed(1)
    model_a = BinaryMlp(MlpArchitecture(input_dim=495))
    set_global_seed(2)
    model_b = BinaryMlp(MlpArchitecture(input_dim=495))
    first_param_a = next(model_a.parameters())
    first_param_b = next(model_b.parameters())
    assert not torch.equal(first_param_a, first_param_b)


def test_resolve_device_cpu_is_always_honored():
    assert resolve_device("cpu") == torch.device("cpu")


def test_resolve_device_auto_falls_back_to_cpu_when_cuda_unavailable():
    if torch.cuda.is_available():
        pytest.skip("CUDA is available in this environment; 'auto' would legitimately resolve to cuda.")
    assert resolve_device("auto") == torch.device("cpu")


def test_resolve_device_cuda_raises_clearly_when_unavailable():
    if torch.cuda.is_available():
        pytest.skip("CUDA is available in this environment.")
    with pytest.raises(RuntimeError, match="cuda"):
        resolve_device("cuda")


def test_resolve_device_rejects_unknown_string():
    with pytest.raises(ValueError, match="device"):
        resolve_device("tpu")
