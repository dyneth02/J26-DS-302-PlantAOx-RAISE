"""Tests for Task 3.18 complete perturbation-workflow reproducibility."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.config import load_research_config
from plantaox.c3_aop_bcs.perturbation_pipeline import (
    DEFAULT_OUTPUT_PATH as COMBINED_OUTPUT_PATH,
)
from plantaox.c3_aop_bcs.p3_random_controls import (
    DEFAULT_OUTPUT_PATH as P3_OUTPUT_PATH,
)
from plantaox.c3_aop_bcs.reproducibility import (
    REPRODUCIBILITY_EVIDENCE_VERSION,
    create_reproducibility_evidence,
)
from plantaox.c3_aop_bcs.residue_annotation import (
    NON_REDOX_CLASS,
    OUTPUT_FIELDS as ANNOTATION_FIELDS,
    REDOX_CLASS,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEST_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs"
EVIDENCE_PATH = DATA_DIRECTORY / "perturbation_reproducibility_report_v1.json"


def _annotations(sequence_id: str, sequence: str, redox: set[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    redox_count = sum(residue in redox for residue in sequence)
    for position, residue in enumerate(sequence, start=1):
        row = {field: "" for field in ANNOTATION_FIELDS}
        row.update(
            sequence_id=sequence_id,
            peptide_sequence=sequence,
            sequence_length=str(len(sequence)),
            redox_residue_count=str(redox_count),
            residue_position=str(position),
            residue=residue,
            residue_class=REDOX_CLASS if residue in redox else NON_REDOX_CLASS,
            peptide_redox_position_count=str(redox_count),
        )
        rows.append(row)
    return rows


class PerturbationReproducibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_research_config()

    def test_evidence_is_deterministic_and_confirms_complete_workflow(self):
        rows = _annotations("test", "AWDG", set(self.config.redox_residues))
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            input_path = temporary / "annotations.csv"
            with input_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=ANNOTATION_FIELDS,
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(rows)

            first_path = temporary / "first-evidence.json"
            second_path = temporary / "second-evidence.json"
            first = create_reproducibility_evidence(
                input_path=input_path,
                evidence_path=first_path,
                config=self.config,
                created_on=date(2026, 10, 18),
            )
            second = create_reproducibility_evidence(
                input_path=input_path,
                evidence_path=second_path,
                config=self.config,
                created_on=date(2026, 10, 18),
            )

            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())

        self.assertEqual(first, second)
        self.assertEqual(first["result"], "PASS")
        self.assertEqual(first["run_count"], 2)
        self.assertTrue(all(first["comparisons"].values()))
        self.assertEqual(
            first["runs"][0]["counts"]["generated_by_perturbation_type"],
            {"P1": 1, "P2": 2, "P3": 4},
        )
        self.assertEqual(
            first["runs"][0]["artifacts"]["p3_random_controls"]["record_count"],
            4,
        )

    def test_committed_production_evidence_matches_current_outputs(self):
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            evidence["evidence_version"],
            REPRODUCIBILITY_EVIDENCE_VERSION,
        )
        self.assertEqual(evidence["result"], "PASS")
        self.assertEqual(evidence["run_count"], 2)
        self.assertTrue(all(evidence["comparisons"].values()))
        self.assertEqual(evidence["configuration"]["values"]["random_seed"], 42)

        run_1, run_2 = evidence["runs"]
        self.assertEqual(run_1["counts"], run_2["counts"])
        self.assertEqual(run_1["counts"]["accepted_variant_count"], 10036)
        self.assertEqual(
            run_1["artifacts"]["accepted_perturbations"]["sha256"],
            hashlib.sha256(COMBINED_OUTPUT_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            run_1["artifacts"]["p3_random_controls"]["sha256"],
            hashlib.sha256(P3_OUTPUT_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            run_1["artifacts"]["p3_random_controls"],
            run_2["artifacts"]["p3_random_controls"],
        )


if __name__ == "__main__":
    unittest.main()
