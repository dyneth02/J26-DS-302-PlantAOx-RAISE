"""Tests for the Component 3 research configuration and loader."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.config import ResearchConfig, load_research_config


TEST_DIRECTORY = Path(__file__).parent


def _valid_values(**overrides):
    values = {
        "random_seed": 42,
        "sequence_min_length": 3,
        "sequence_max_length": 50,
        "redox_residues": ("W", "Y", "H", "M", "C"),
        "cd_hit_identity_threshold": 0.90,
        "primary_delta": 0.05,
        "sensitivity_deltas": (0.02, 0.05, 0.10),
        "pilot_dataset_size": 20,
    }
    values.update(overrides)
    return values


class ResearchConfigTests(unittest.TestCase):
    def test_default_configuration_loads_frozen_protocol_values(self):
        config = load_research_config()

        self.assertEqual(config, ResearchConfig(**_valid_values()))
        self.assertEqual(config.redox_residues, ("W", "Y", "H", "M", "C"))
        self.assertIn(config.primary_delta, config.sensitivity_deltas)

    def test_loader_accepts_an_explicit_configuration_path(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            config_path = Path(directory) / "research_config.toml"
            config_path.write_text(
                """[research]
random_seed = 7
sequence_min_length = 3
sequence_max_length = 50
redox_residues = ["W", "Y", "H", "M", "C"]
cd_hit_identity_threshold = 0.9
primary_delta = 0.05
sensitivity_deltas = [0.02, 0.05, 0.10]
pilot_dataset_size = 12
""",
                encoding="utf-8",
            )

            config = load_research_config(config_path)

        self.assertEqual(config.random_seed, 7)
        self.assertEqual(config.pilot_dataset_size, 12)

    def test_invalid_configuration_values_are_rejected(self):
        invalid_cases = [
            ({"random_seed": -1}, "random_seed"),
            ({"sequence_min_length": 51}, "must not exceed"),
            ({"redox_residues": ("W", "W")}, "duplicates"),
            ({"redox_residues": ("W", "B")}, "standard amino-acid"),
            ({"cd_hit_identity_threshold": 1.1}, "cd_hit_identity_threshold"),
            ({"primary_delta": 0.0}, "primary_delta"),
            ({"sensitivity_deltas": (0.05, 0.02)}, "ascending"),
            ({"sensitivity_deltas": (0.02, 0.10)}, "included"),
            ({"pilot_dataset_size": 0}, "pilot_dataset_size"),
        ]
        for overrides, message in invalid_cases:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, message):
                    ResearchConfig(**_valid_values(**overrides))

    def test_loader_rejects_missing_research_table(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            config_path = Path(directory) / "research_config.toml"
            config_path.write_text("random_seed = 42\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, r"\[research\] table"):
                load_research_config(config_path)

    def test_mapping_rejects_missing_unknown_and_malformed_fields(self):
        missing = _valid_values()
        missing.pop("random_seed")
        with self.assertRaisesRegex(ValueError, "Missing.*random_seed"):
            ResearchConfig.from_mapping(missing)

        unknown = _valid_values(unexpected=True)
        with self.assertRaisesRegex(ValueError, "Unknown.*unexpected"):
            ResearchConfig.from_mapping(unknown)

        malformed = _valid_values(redox_residues="WYHMC")
        with self.assertRaisesRegex(ValueError, "redox_residues must be an array"):
            ResearchConfig.from_mapping(malformed)


if __name__ == "__main__":
    unittest.main()
