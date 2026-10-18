"""Integrity checks for the immutable Task 3.4 raw acquisition."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "data" / "raw" / "c3_aop_bcs" / "PROVENANCE.json"


class RawDataAcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_identity_and_acquisition_date(self):
        self.assertEqual(self.manifest["dataset_version"], "c3_aop_bcs_raw_v1")
        self.assertTrue(self.manifest["raw_files_immutable"])
        self.assertEqual(date.fromisoformat(self.manifest["acquisition_date"]), date(2026, 10, 18))

    def test_every_manifest_file_exists_and_matches_its_version_pin(self):
        self.assertEqual(len(self.manifest["sources"]), 4)

        for source in self.manifest["sources"]:
            with self.subTest(path=source["local_path"]):
                path = REPOSITORY_ROOT / source["local_path"]
                payload = path.read_bytes()
                self.assertEqual(len(payload), source["byte_count"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), source["sha256"])

    def test_csv_structure_counts_and_labels_match_manifest(self):
        for source in self.manifest["sources"]:
            with self.subTest(path=source["local_path"]):
                path = REPOSITORY_ROOT / source["local_path"]
                with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                    reader = csv.DictReader(csv_file)
                    rows = list(reader)

                self.assertEqual(reader.fieldnames, source["columns"])
                self.assertEqual(len(rows), source["data_row_count"])
                if "label_counts" in source:
                    labels = Counter(row["label"] for row in rows)
                    self.assertEqual(labels, Counter(source["label_counts"]))
                if "assay_activity_counts" in source:
                    assay_counts = Counter(
                        "positive" if row["FRS"] == "1" or row["Chelator"] == "1" else "inactive"
                        for row in rows
                    )
                    self.assertEqual(assay_counts, Counter(source["assay_activity_counts"]))

    def test_sources_are_traceable_to_authoritative_repositories(self):
        expected_repositories = {
            "https://github.com/TobiasHeOl/AnOxPePred",
            "https://github.com/CaiJianxiu/Multi-AOP",
        }
        self.assertEqual(
            {source["repository_url"] for source in self.manifest["sources"]},
            expected_repositories,
        )
        self.assertTrue(all(source["upstream_path"] for source in self.manifest["sources"]))


if __name__ == "__main__":
    unittest.main()
