"""Tests for the frozen Task 3.10 perturbation-record schema."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.perturbation_schema import (
    DEFAULT_SCHEMA_PATH,
    PERTURBATION_FIELDS,
    PERTURBATION_SCHEMA_VERSION,
    PerturbationRecord,
    schema_definition,
    write_schema_document,
)


TEST_DIRECTORY = Path(__file__).parent


def _values(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "schema_version": PERTURBATION_SCHEMA_VERSION,
        "variant_id": "C3-TEST-000001-P1-0002-A",
        "sequence_id": "C3-TEST-000001",
        "original_sequence": "AWC",
        "position": 2,
        "original_residue": "W",
        "substituted_residue": "A",
        "perturbed_sequence": "AAC",
        "perturbation_type": "P1",
        "blosum62_score": None,
        "random_seed": None,
        "random_metadata": None,
    }
    values.update(overrides)
    return values


class PerturbationSchemaTests(unittest.TestCase):
    def test_all_perturbation_types_round_trip_through_csv_mapping(self):
        records = [
            PerturbationRecord(**_values()),
            PerturbationRecord(
                **_values(
                    variant_id="C3-TEST-000001-P2-0001-V",
                    position=1,
                    original_residue="A",
                    substituted_residue="V",
                    perturbed_sequence="VWC",
                    perturbation_type="P2",
                    blosum62_score=1,
                )
            ),
            PerturbationRecord(
                **_values(
                    variant_id="C3-TEST-000001-P3-0003-M",
                    position=3,
                    original_residue="C",
                    substituted_residue="M",
                    perturbed_sequence="AWM",
                    perturbation_type="P3",
                    random_seed=42,
                    random_metadata='{"choice_index": 4, "strategy": "uniform"}',
                )
            ),
        ]

        for record in records:
            serialized = record.as_dict()
            self.assertEqual(tuple(serialized), PERTURBATION_FIELDS)
            self.assertEqual(PerturbationRecord.from_mapping(serialized), record)
        self.assertEqual(
            records[2].random_metadata,
            '{"choice_index":4,"strategy":"uniform"}',
        )

    def test_record_requires_exactly_one_declared_same_length_edit(self):
        invalid_cases = (
            {"perturbed_sequence": "AVC"},
            {"perturbed_sequence": "AACV"},
            {"perturbed_sequence": "AAM", "substituted_residue": "A"},
            {"position": 1},
            {"original_residue": "Y"},
            {"substituted_residue": "W", "perturbed_sequence": "AWC"},
        )
        for changes in invalid_cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                PerturbationRecord(**_values(**changes))

    def test_type_specific_metadata_is_strict(self):
        with self.assertRaisesRegex(ValueError, "P1 records"):
            PerturbationRecord(**_values(blosum62_score=1))
        with self.assertRaisesRegex(ValueError, "require blosum62_score"):
            PerturbationRecord(**_values(perturbation_type="P2"))
        with self.assertRaisesRegex(ValueError, "require random_seed"):
            PerturbationRecord(**_values(perturbation_type="P3"))
        with self.assertRaisesRegex(ValueError, "JSON object"):
            PerturbationRecord(
                **_values(
                    perturbation_type="P3",
                    random_seed=42,
                    random_metadata="[]",
                )
            )

    def test_mapping_rejects_missing_unknown_and_malformed_fields(self):
        missing = _values()
        del missing["position"]
        with self.assertRaisesRegex(ValueError, "Missing perturbation"):
            PerturbationRecord.from_mapping(missing)

        with self.assertRaisesRegex(ValueError, "Unknown perturbation"):
            PerturbationRecord.from_mapping({**_values(), "unexpected": "value"})

        with self.assertRaisesRegex(ValueError, "position must be an integer"):
            PerturbationRecord.from_mapping({**_values(), "position": "2.0"})

    def test_committed_schema_matches_code_and_is_byte_reproducible(self):
        committed = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(committed, schema_definition())
        self.assertEqual(
            [field["name"] for field in committed["fields"]],
            list(PERTURBATION_FIELDS),
        )
        self.assertEqual(
            committed["record_semantics"],
            "one record represents exactly one one-position substitution",
        )

        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            first = write_schema_document(Path(directory) / "first.json")
            second = write_schema_document(Path(directory) / "second.json")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), DEFAULT_SCHEMA_PATH.read_bytes())


if __name__ == "__main__":
    unittest.main()
