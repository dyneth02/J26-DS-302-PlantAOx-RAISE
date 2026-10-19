"""Loads config/c1.yaml (the parameters of the accepted C1 pipeline)."""

from __future__ import annotations

from pathlib import Path

import yaml

from plantaox.c1_procon.benchmark import repo_root


def default_config_path() -> Path:
    return repo_root() / "config" / "c1.yaml"


def load_config(path: str | Path | None = None) -> dict:
    with open(path or default_config_path(), encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("config/c1.yaml is empty or not a mapping")
    return config
