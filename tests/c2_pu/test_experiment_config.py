"""Unit tests for experiment_config.py (Bucket 4.1 §A)."""

from __future__ import annotations

import pytest

from plantaox.c2_pu.experiment_config import ExperimentConfig


def _valid_kwargs(**overrides):
    base = {"experiment_id": "exp1", "baseline": "PN"}
    base.update(overrides)
    return base


def test_valid_config_constructs_with_defaults():
    config = ExperimentConfig(**_valid_kwargs())
    assert config.fold_id == 0
    assert config.feature_representation == "fused"
    assert config.feature_dim == 495
    assert config.hidden_dims == (128, 64)


@pytest.mark.parametrize("representation,expected_dim", [("fused", 495), ("esm", 480), ("descriptors", 15)])
def test_feature_dim_matches_representation(representation, expected_dim):
    config = ExperimentConfig(**_valid_kwargs(feature_representation=representation))
    assert config.feature_dim == expected_dim


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"experiment_id": ""}, "experiment_id"),
        ({"baseline": "NotARealBaseline"}, "baseline"),
        ({"fold_id": 5}, "fold_id"),
        ({"fold_id": -1}, "fold_id"),
        ({"feature_representation": "raw"}, "feature_representation"),
        ({"positive_pools": ()}, "positive_pools"),
        ({"unlabeled_pools": ("C1", "C4")}, "unlabeled_pools"),
        ({"evaluation_pools": ("not_a_pool",)}, "evaluation_pools"),
        ({"validation_fraction": 0.0}, "validation_fraction"),
        ({"validation_fraction": 1.0}, "validation_fraction"),
        ({"validation_fraction": 1.5}, "validation_fraction"),
        ({"train_seed": 1.5}, "train_seed"),
        ({"hidden_dims": ()}, "hidden_dims"),
        ({"hidden_dims": (128, -1)}, "hidden_dims"),
        ({"activation": "tanh"}, "activation"),
        ({"optimizer": "rmsprop"}, "optimizer"),
        ({"learning_rate": 0.0}, "learning_rate"),
        ({"learning_rate": -1e-3}, "learning_rate"),
        ({"weight_decay": -0.1}, "weight_decay"),
        ({"batch_size": 0}, "batch_size"),
        ({"max_epochs": 0}, "max_epochs"),
        ({"device": "tpu"}, "device"),
        ({"checkpoint_dir": ""}, "checkpoint_dir"),
    ],
)
def test_invalid_parameters_are_rejected(overrides, match):
    with pytest.raises(ValueError, match=match):
        ExperimentConfig(**_valid_kwargs(**overrides))


def test_fold_id_boundary_values_are_accepted():
    ExperimentConfig(**_valid_kwargs(fold_id=0))
    ExperimentConfig(**_valid_kwargs(fold_id=4))


def test_to_dict_and_from_dict_round_trip():
    config = ExperimentConfig(**_valid_kwargs(hidden_dims=(64, 32), unlabeled_pools=("C1",)))
    data = config.to_dict()
    restored = ExperimentConfig.from_dict(data)
    assert restored == config
    assert data["feature_dim"] == 495


def test_from_dict_ignores_unknown_keys():
    config = ExperimentConfig.from_dict({"experiment_id": "e", "baseline": "nnPU", "unexpected_extra_key": 123})
    assert config.experiment_id == "e"
    assert config.baseline == "nnPU"


def test_config_is_frozen_and_hashable_by_value_equality():
    a = ExperimentConfig(**_valid_kwargs())
    b = ExperimentConfig(**_valid_kwargs())
    assert a == b
    with pytest.raises(Exception):
        a.experiment_id = "changed"  # dataclass(frozen=True) -> FrozenInstanceError
