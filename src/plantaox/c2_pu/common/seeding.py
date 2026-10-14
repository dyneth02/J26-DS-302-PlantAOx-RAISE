"""Bucket 4.1 -- reusable seed initializer and execution-context recorder.

Seeds Python's ``random``, NumPy, and PyTorch (CPU and CUDA, if present)
from a single integer, and returns a plain dict describing exactly what
was set -- the "effective seed, deterministic-algorithm settings, and
relevant library versions" every experiment's resolved config/run
manifest must record (Task 4.1 §D).

**Determinism claim, precisely scoped:** ``torch.use_deterministic_algorithms(True)``
plus a fixed seed gives byte-identical repeated CPU forward/backward
passes for the operations this project's MLP uses (linear, ReLU,
sigmoid, BCE-with-logits) -- verified directly in
``tests/c2_pu/test_seeding.py``. This is **not** a claim that GPU
execution is bit-identical to CPU execution, nor that every possible
PyTorch op is deterministic on every CUDA device/driver combination --
cuDNN convolution/reduction kernels in particular are well documented as
non-bit-reproducible across GPU architectures even with this flag set.
This module records ``cuda_available`` and (if applicable) the CUDA
device name precisely so a later audit can tell *which* execution context
produced a given result, rather than asserting a universal guarantee this
project cannot verify (no CUDA device is present in this environment --
``torch.cuda.is_available()`` is ``False`` here).
"""

from __future__ import annotations

import os
import platform
import random
import sys

import numpy as np
import torch


def set_global_seed(seed: int, deterministic: bool = True) -> dict:
    """Seed Python/NumPy/PyTorch from one integer and return the exact
    execution context that was configured.

    ``deterministic=True`` (the default) additionally calls
    ``torch.use_deterministic_algorithms(True, warn_only=True)`` --
    ``warn_only`` because a handful of PyTorch ops (not used by this
    project's MLP) have no deterministic CPU implementation and would
    otherwise raise; a warning is preferable to crashing in a module whose
    whole job is being safe to call from any training entrypoint.
    """
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError(f"seed must be a plain int, got {seed!r} ({type(seed).__name__})")

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        torch.cuda.manual_seed_all(seed)

    if deterministic:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.use_deterministic_algorithms(True, warn_only=True)

    return {
        "effective_seed": seed,
        "deterministic_algorithms_requested": deterministic,
        "cuda_available": cuda_available,
        "cuda_device_name": torch.cuda.get_device_name(0) if cuda_available else None,
        "device_count": torch.cuda.device_count() if cuda_available else 0,
        "cpu_count": os.cpu_count(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "python_version": sys.version,
        "platform": platform.platform(),
    }


def resolve_device(requested: str = "auto") -> torch.device:
    """"auto" -> CUDA if available (and a real tensor op on it succeeds),
    else CPU. "cpu"/"cuda" are honored literally (raising if "cuda" is
    requested but unavailable -- never silently falling back without
    saying so, matching common/embeddings.py's resolve_device precedent)."""
    if requested == "cpu":
        return torch.device("cpu")
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("device='cuda' requested but torch.cuda.is_available() is False.")
        return torch.device("cuda")
    if requested != "auto":
        raise ValueError(f"device must be one of 'auto', 'cpu', 'cuda', got {requested!r}")
    if not torch.cuda.is_available():
        return torch.device("cpu")
    try:
        (torch.zeros(1, device="cuda") + 1).cpu()
        return torch.device("cuda")
    except Exception:
        return torch.device("cpu")
