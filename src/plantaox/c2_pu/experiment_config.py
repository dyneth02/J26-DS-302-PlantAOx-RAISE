"""Bucket 4.1 -- typed, validated experiment configuration (Task 4.1 §A).

A plain, dependency-free ``dataclass`` (no pydantic -- not already a
project dependency, and the validation this config needs is simple
range/membership checks, consistent with this project's existing
hand-rolled-validation style) with ``__post_init__`` validation that
raises a specific, descriptive ``ValueError`` for every invalid field
rather than failing deep inside training code later.

This captures the "effective parameters" half of Task 4.1 §A's
record-keeping requirement. The other half (source-artifact checksums,
code revision, software versions, timestamps, run status) is assembled
at run time by ``run_recorder.py``, which references real files rather
than duplicating anything this module would have to keep in sync with.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

BASELINES = ("PN", "nnPU", "TwoStepPU", "PUBagging")
FEATURE_REPRESENTATIONS = ("fused", "esm", "descriptors")
FEATURE_DIMENSIONS = {"fused": 495, "esm": 480, "descriptors": 15}
OPTIMIZERS = ("adam", "sgd")
DEVICES = ("auto", "cpu", "cuda")
UNLABELED_POOL_CHOICES = ("C1", "C2")
EVALUATION_POOL_CHOICES = ("held_out_positive", "C1", "C2", "C3", "external_control")
GRAPHPART_N_FOLDS = 5


@dataclass(frozen=True)
class ExperimentConfig:
    # Identity
    experiment_id: str
    baseline: str

    # Frozen baseline identifiers (never silently repointed at a different version)
    positive_pool_version: str = "pp1_baseline_v1"
    challenge_pool_version: str = "pp2_baseline_v1"

    # Data selection
    fold_id: int = 0
    feature_representation: str = "fused"
    positive_pools: tuple[str, ...] = ("FR1_positives",)
    unlabeled_pools: tuple[str, ...] = ("C1", "C2")
    evaluation_pools: tuple[str, ...] = ("held_out_positive", "C1", "C3", "external_control")
    validation_fraction: float = 0.15

    # Seeds
    train_seed: int = 42
    eval_seed: int = 42

    # Architecture
    hidden_dims: tuple[int, ...] = (128, 64)
    activation: str = "relu"

    # Optimizer
    optimizer: str = "adam"
    learning_rate: float = 1e-3
    weight_decay: float = 0.0

    # Training loop shape (no training objective is implemented in this task)
    batch_size: int = 32
    max_epochs: int = 100
    device: str = "auto"
    checkpoint_dir: str = "checkpoints"

    def __post_init__(self):
        if not self.experiment_id or not isinstance(self.experiment_id, str):
            raise ValueError(f"experiment_id must be a non-empty string, got {self.experiment_id!r}")
        if self.baseline not in BASELINES:
            raise ValueError(f"baseline must be one of {BASELINES}, got {self.baseline!r}")
        if not isinstance(self.fold_id, int) or isinstance(self.fold_id, bool) or not (0 <= self.fold_id < GRAPHPART_N_FOLDS):
            raise ValueError(f"fold_id must be an int in [0, {GRAPHPART_N_FOLDS}), got {self.fold_id!r}")
        if self.feature_representation not in FEATURE_REPRESENTATIONS:
            raise ValueError(f"feature_representation must be one of {FEATURE_REPRESENTATIONS}, got {self.feature_representation!r}")
        if not self.positive_pools:
            raise ValueError("positive_pools must not be empty")
        unknown_unlabeled = set(self.unlabeled_pools) - set(UNLABELED_POOL_CHOICES)
        if unknown_unlabeled:
            raise ValueError(f"unlabeled_pools contains unsupported pool(s) {unknown_unlabeled}; allowed: {UNLABELED_POOL_CHOICES}")
        unknown_eval = set(self.evaluation_pools) - set(EVALUATION_POOL_CHOICES)
        if unknown_eval:
            raise ValueError(f"evaluation_pools contains unsupported pool(s) {unknown_eval}; allowed: {EVALUATION_POOL_CHOICES}")
        if not (0.0 < self.validation_fraction < 1.0):
            raise ValueError(f"validation_fraction must be in (0, 1), got {self.validation_fraction}")
        if not isinstance(self.train_seed, int) or isinstance(self.train_seed, bool):
            raise ValueError(f"train_seed must be a plain int, got {self.train_seed!r}")
        if not isinstance(self.eval_seed, int) or isinstance(self.eval_seed, bool):
            raise ValueError(f"eval_seed must be a plain int, got {self.eval_seed!r}")
        if not self.hidden_dims or any((not isinstance(h, int)) or h <= 0 for h in self.hidden_dims):
            raise ValueError(f"hidden_dims must be a non-empty tuple of positive ints, got {self.hidden_dims}")
        if self.activation != "relu":
            raise ValueError(f"Only activation='relu' is currently supported, got {self.activation!r}")
        if self.optimizer not in OPTIMIZERS:
            raise ValueError(f"optimizer must be one of {OPTIMIZERS}, got {self.optimizer!r}")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be positive, got {self.learning_rate}")
        if self.weight_decay < 0:
            raise ValueError(f"weight_decay must be >= 0, got {self.weight_decay}")
        if not isinstance(self.batch_size, int) or self.batch_size <= 0:
            raise ValueError(f"batch_size must be a positive int, got {self.batch_size!r}")
        if not isinstance(self.max_epochs, int) or self.max_epochs <= 0:
            raise ValueError(f"max_epochs must be a positive int, got {self.max_epochs!r}")
        if self.device not in DEVICES:
            raise ValueError(f"device must be one of {DEVICES}, got {self.device!r}")
        if not self.checkpoint_dir:
            raise ValueError("checkpoint_dir must not be empty")

    @property
    def feature_dim(self) -> int:
        return FEATURE_DIMENSIONS[self.feature_representation]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["feature_dim"] = self.feature_dim
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentConfig":
        known_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        for tuple_field in ("positive_pools", "unlabeled_pools", "evaluation_pools", "hidden_dims"):
            if tuple_field in filtered:
                filtered[tuple_field] = tuple(filtered[tuple_field])
        return cls(**filtered)
