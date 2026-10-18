"""Tests for Task 3.12 BLOSUM62 selection support."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import Bio
from Bio.Align import substitution_matrices

from plantaox.c3_aop_bcs.blosum62 import (
    BLOSUM62_LOADER,
    BLOSUM62_MATRIX_NAME,
    BLOSUM62_SUPPORT_VERSION,
    DEFAULT_MANIFEST_PATH,
    MATRIX_ALPHABET,
    MINIMUM_CONSERVATIVE_SCORE,
    TIE_BREAK_RULE,
    evaluate_substitution_candidates,
    load_blosum62,
    select_conservative_substitution,
    support_manifest,
    write_support_manifest,
)
from plantaox.c3_aop_bcs.config import STANDARD_AMINO_ACIDS, load_research_config


TEST_DIRECTORY = Path(__file__).parent


class Blosum62Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = load_blosum62()
        cls.config = load_research_config()

    def test_matrix_contains_complete_symmetric_standard_amino_acid_scores(self):
        self.assertEqual(set(MATRIX_ALPHABET), STANDARD_AMINO_ACIDS)
        self.assertEqual(len(self.matrix), 400)
        self.assertEqual(self.matrix[("A", "A")], 4)
        self.assertEqual(self.matrix[("W", "W")], 11)
        self.assertEqual(self.matrix[("D", "E")], 2)
        self.assertEqual(self.matrix[("E", "D")], 2)
        for left in MATRIX_ALPHABET:
            for right in MATRIX_ALPHABET:
                self.assertEqual(self.matrix[(left, right)], self.matrix[(right, left)])

    def test_matrix_is_loaded_through_biopython(self):
        with patch(
            "plantaox.c3_aop_bcs.blosum62.substitution_matrices.load",
            wraps=substitution_matrices.load,
        ) as mocked_loader:
            matrix = load_blosum62()

        mocked_loader.assert_called_once_with(BLOSUM62_MATRIX_NAME)
        self.assertEqual(matrix[("D", "E")], 2)

    def test_candidates_apply_all_exclusions_and_minimum_score(self):
        for original in STANDARD_AMINO_ACIDS:
            with self.subTest(original=original):
                candidates = evaluate_substitution_candidates(
                    original,
                    self.matrix,
                    self.config.redox_residues,
                )
                excluded = {original, "A", *self.config.redox_residues}
                self.assertTrue(
                    all(candidate.residue not in excluded for candidate in candidates)
                )
                self.assertTrue(
                    all(
                        candidate.score >= MINIMUM_CONSERVATIVE_SCORE
                        for candidate in candidates
                    )
                )
                self.assertEqual(
                    candidates,
                    tuple(
                        sorted(candidates, key=lambda item: (-item.score, item.residue))
                    ),
                )

    def test_highest_score_and_alphabetical_tie_break_are_deterministic(self):
        n_choice = select_conservative_substitution(
            "N",
            self.matrix,
            self.config.redox_residues,
        )
        self.assertIsNotNone(n_choice)
        self.assertEqual((n_choice.residue, n_choice.score), ("D", 1))

        e_choice = select_conservative_substitution(
            "E",
            self.matrix,
            self.config.redox_residues,
        )
        self.assertIsNotNone(e_choice)
        self.assertEqual((e_choice.residue, e_choice.score), ("D", 2))
        self.assertEqual(
            select_conservative_substitution(
                "E",
                self.matrix,
                self.config.redox_residues,
            ),
            e_choice,
        )

    def test_selector_returns_none_when_no_candidate_meets_the_rule(self):
        self.assertIsNone(
            select_conservative_substitution(
                "G",
                self.matrix,
                self.config.redox_residues,
            )
        )

    def test_committed_manifest_is_traceable_and_byte_reproducible(self):
        committed = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(committed, support_manifest())
        self.assertEqual(committed["support_version"], BLOSUM62_SUPPORT_VERSION)
        self.assertEqual(committed["dimensions"], [20, 20])
        self.assertEqual(committed["matrix_provider"]["library"], "Biopython")
        self.assertEqual(committed["matrix_provider"]["version"], Bio.__version__)
        self.assertEqual(committed["matrix_provider"]["loader"], BLOSUM62_LOADER)
        self.assertEqual(
            committed["matrix_provider"]["matrix_identifier"],
            BLOSUM62_MATRIX_NAME,
        )
        self.assertEqual(
            committed["matrix_provider"]["library_alphabet"],
            list(substitution_matrices.load(BLOSUM62_MATRIX_NAME).alphabet),
        )
        self.assertEqual(committed["selection_rule"]["minimum_score"], 1)
        self.assertEqual(committed["selection_rule"]["tie_break"], TIE_BREAK_RULE)

        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            first = write_support_manifest(Path(directory) / "first.json")
            second = write_support_manifest(Path(directory) / "second.json")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), DEFAULT_MANIFEST_PATH.read_bytes())


if __name__ == "__main__":
    unittest.main()
