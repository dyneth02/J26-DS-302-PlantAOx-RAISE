# FR3 — PN, nnPU, Two-Step PU, and PU-Bagging baselines on fused ESM-2 +
# 15-descriptor features.
"""Bucket 4.1 -- shared, architecture-matched binary MLP.

This module defines the model ARCHITECTURE only (forward logits,
probability inference, checkpoint-compatible state loading). Risk
estimators (PN cross-entropy, nnPU's non-negative risk estimator,
Two-Step PU, PU-Bagging) and their training loops are deliberately NOT
implemented here -- they belong to Task 4.2+, operating on top of this
same shared architecture so every baseline is compared on equal
architectural footing, per the proposal's "architecture-matched
comparison" design (§3.3).

Default input dimension (495) matches the accepted `fusion_v1` schema
(``curation/feature_fusion.py``: 480 ESM-2 dims + 15 `descriptors_v1`
dims) but is not hardcoded -- ``feature_representation="esm"`` (480) or
``"descriptors"`` (15) both work by constructing the model with a
different ``input_dim`` (see ``experiment_config.py``'s
``FEATURE_DIMENSIONS``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import torch
from torch import nn

DEFAULT_INPUT_DIM = 495
DEFAULT_HIDDEN_DIMS = (128, 64)


@dataclass(frozen=True)
class MlpArchitecture:
    """Everything needed to reconstruct an identical, untrained
    ``BinaryMlp`` -- embedded in every checkpoint (Task 4.1 §E) so a
    loader can verify compatibility BEFORE calling ``load_state_dict``,
    rather than hitting a cryptic shape-mismatch error deep inside
    PyTorch."""

    input_dim: int = DEFAULT_INPUT_DIM
    hidden_dims: tuple[int, ...] = DEFAULT_HIDDEN_DIMS
    activation: str = "relu"

    def __post_init__(self):
        if self.input_dim <= 0:
            raise ValueError(f"input_dim must be positive, got {self.input_dim}")
        if not self.hidden_dims or any(h <= 0 for h in self.hidden_dims):
            raise ValueError(f"hidden_dims must be a non-empty tuple of positive ints, got {self.hidden_dims}")
        if self.activation != "relu":
            raise ValueError(f"Only activation='relu' is currently supported, got {self.activation!r}")

    def as_dict(self) -> dict:
        return {"input_dim": self.input_dim, "hidden_dims": list(self.hidden_dims), "activation": self.activation}

    @classmethod
    def from_dict(cls, data: dict) -> "MlpArchitecture":
        return cls(input_dim=data["input_dim"], hidden_dims=tuple(data["hidden_dims"]), activation=data["activation"])


class ArchitectureMismatchError(ValueError):
    """Raised when a checkpoint's recorded architecture doesn't match the
    model instance being loaded into -- never silently loaded anyway."""


class BinaryMlp(nn.Module):
    """Proposed initial architecture (Task 4.1 §B): input -> [128, ReLU]
    -> [64, ReLU] -> 1 logit. Configurable via ``MlpArchitecture``.
    Outputs a single logit per row; ``predict_proba`` applies sigmoid.
    No loss function, optimizer, or training step is defined here.
    """

    def __init__(self, architecture: MlpArchitecture | None = None):
        super().__init__()
        self.architecture = architecture or MlpArchitecture()

        layers: list[nn.Module] = []
        prev_dim = self.architecture.input_dim
        for hidden_dim in self.architecture.hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            prev_dim = hidden_dim
        layers.append(nn.Linear(prev_dim, 1))
        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Returns raw logits, shape (batch, 1) -- never a probability."""
        if x.ndim != 2 or x.shape[1] != self.architecture.input_dim:
            raise ValueError(
                f"Expected input shape (batch, {self.architecture.input_dim}), got {tuple(x.shape)}"
            )
        return self.network(x)

    @torch.no_grad()
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """sigmoid(logits), shape (batch, 1), values in [0, 1]. Runs in
        eval mode (restored to the caller's prior mode afterward) under
        no_grad -- this is inference, not a training-time call."""
        was_training = self.training
        self.eval()
        try:
            return torch.sigmoid(self.forward(x))
        finally:
            self.train(was_training)

    def architecture_signature(self) -> dict:
        """The exact architecture metadata a checkpoint loader needs to
        verify compatibility before calling ``load_state_dict``."""
        return self.architecture.as_dict()

    def load_compatible_state_dict(self, state_dict: dict, checkpoint_architecture: dict) -> None:
        """Loads ``state_dict`` only if ``checkpoint_architecture`` matches
        this model's own architecture exactly -- raises
        ``ArchitectureMismatchError`` naming the specific mismatch
        otherwise, rather than letting PyTorch's own shape-mismatch error
        (or worse, a silent partial load) be the first signal something's
        wrong.
        """
        own = self.architecture_signature()
        if checkpoint_architecture != own:
            raise ArchitectureMismatchError(
                f"Checkpoint architecture {checkpoint_architecture} does not match this model's "
                f"architecture {own} -- refusing to load a possibly-incompatible state_dict."
            )
        self.load_state_dict(state_dict)
