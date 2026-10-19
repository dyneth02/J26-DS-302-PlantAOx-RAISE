from __future__ import annotations

from plantaox.c1_procon.benchmark import EXPECTED_FINGERPRINT
from plantaox.c1_procon.config import load_config
from plantaox.c1_procon.features import AA


def test_config_fingerprint_matches_the_code():
    cfg = load_config()
    assert cfg["benchmark"]["fingerprint"] == EXPECTED_FINGERPRINT
    assert cfg["benchmark"]["primary_mode"] == "strict"


def test_documented_training_and_probe_settings():
    cfg = load_config()
    assert cfg["training"]["temperature"] == 0.2 and cfg["training"]["prototype_push_away_lambda"] == 5.0
    assert cfg["training"]["head"] == {"type": "linear", "input": 1280, "output": 128}
    assert cfg["evaluation"]["probe"]["folds"] == 5 and cfg["evaluation"]["probe"]["repeats"] == 10
    assert cfg["evaluation"]["probe"]["null_noise_seeds"] == 20 and cfg["evaluation"]["seeds_per_recipe"] == 5


def test_pairs_and_embedding_settings():
    cfg = load_config()
    assert cfg["pairs"]["percentile"] == 10 and cfg["pairs"]["k"] == 8
    assert cfg["embeddings"]["dimension"] == 1280 and len(AA) == 20
