"""Tests for the Task 3.36 SHAP-faithfulness preparation contract."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.shap_faithfulness import (
    DEFAULT_PLAN_PATH,
    DEFAULT_SCHEMA_PATH,
    KernelShapBackend,
    KernelShapExplanation,
    KernelShapRequest,
    SHAP_FAITHFULNESS_FIELDS,
    ShapFaithfulnessError,
    ShapFaithfulnessRecord,
    pair_kernel_shap_with_p1_deltas,
    render_implementation_plan,
    schema_document,
    write_schema_and_plan,
)


TEST_DIRECTORY = Path(__file__).resolve().parent


def _request() -> KernelShapRequest:
    return KernelShapRequest(
        sequence_id="C3-TEST-000001",
        sequence="WYH",
        predictor_id="predictor-a",
        predictor_version="1.2.3",
        background_dataset_version="background-v1",
        random_seed=42,
    )


def _explanation() -> KernelShapExplanation:
    return KernelShapExplanation(
        values=(-0.2, 0.05, 0.1),
        backend_id="kernel-shap-adapter",
        backend_version="0.1.0",
    )


def _p1_row(position: int, delta: float) -> dict[str, object]:
    sequence = "WYH"
    return {
        "sequence_id": "C3-TEST-000001",
        "original_sequence": sequence,
        "predictor_id": "predictor-a",
        "predictor_version": "1.2.3",
        "variant_id": f"C3-TEST-000001-P1-{position:04d}-A",
        "position": str(position),
        "original_residue": sequence[position - 1],
        "substituted_residue": "A",
        "perturbation_type": "P1",
        "delta_score": str(delta),
        "absolute_delta_score": str(abs(delta)),
    }


class _Backend:
    backend_id = "kernel-shap-adapter"
    version = "0.1.0"

    def explain(self, request, predictor):
        return _explanation()


class ShapFaithfulnessTests(unittest.TestCase):
    def test_schema_contains_all_required_fields_and_primary_comparison(self):
        document = schema_document()
        field_names = tuple(field["name"] for field in document["fields"])
        self.assertEqual(field_names, SHAP_FAITHFULNESS_FIELDS)
        for required in (
            "sequence_id",
            "sequence",
            "predictor_id",
            "residue_position",
            "residue",
            "shap_value",
            "absolute_shap_value",
            "p1_delta_score",
            "absolute_p1_delta_score",
        ):
            with self.subTest(required=required):
                self.assertIn(required, field_names)
        self.assertEqual(
            document["primary_comparison"]["notation"],
            "|SHAP_i| vs |DeltaScore_i|",
        )
        self.assertEqual(
            document["primary_comparison"]["planned_measure"],
            "Pearson correlation r",
        )

    def test_kernel_shap_boundary_is_structural_and_deferred(self):
        backend = _Backend()
        self.assertIsInstance(backend, KernelShapBackend)
        explanation = backend.explain(_request(), predictor=None)
        self.assertEqual(len(explanation.values), len(_request().sequence))
        scope = schema_document()["pp1_scope"]
        self.assertFalse(scope["complete_shap_experiment_required_for_pp1"])
        self.assertFalse(scope["scientific_shap_results_produced"])
        self.assertFalse(
            schema_document()["kernel_shap_boundary"]["concrete_backend_implemented"]
        )

    def test_p1_rows_pair_to_positions_and_preserve_signed_values(self):
        records = pair_kernel_shap_with_p1_deltas(
            _request(),
            _explanation(),
            [_p1_row(3, -0.3), _p1_row(1, 0.4)],
        )
        self.assertEqual([record.residue_position for record in records], [1, 3])
        self.assertEqual(records[0].residue, "W")
        self.assertEqual(records[0].shap_value, -0.2)
        self.assertEqual(records[0].absolute_shap_value, 0.2)
        self.assertEqual(records[0].p1_delta_score, 0.4)
        self.assertEqual(records[0].absolute_p1_delta_score, 0.4)
        self.assertEqual(records[1].p1_delta_score, -0.3)
        self.assertEqual(records[1].absolute_p1_delta_score, 0.3)
        self.assertEqual(
            ShapFaithfulnessRecord.from_mapping(records[0].as_dict()), records[0]
        )

    def test_invalid_explanations_and_p1_joins_are_rejected(self):
        with self.assertRaisesRegex(ShapFaithfulnessError, "one value per"):
            pair_kernel_shap_with_p1_deltas(
                _request(),
                KernelShapExplanation(
                    values=(0.1, 0.2),
                    backend_id="backend",
                    backend_version="1",
                ),
                [_p1_row(1, 0.2)],
            )
        invalid_kind = {**_p1_row(1, 0.2), "perturbation_type": "P2"}
        with self.assertRaisesRegex(ShapFaithfulnessError, "only P1"):
            pair_kernel_shap_with_p1_deltas(
                _request(), _explanation(), [invalid_kind]
            )
        mismatch = {**_p1_row(1, 0.2), "predictor_version": "different"}
        with self.assertRaisesRegex(ShapFaithfulnessError, "predictor_version"):
            pair_kernel_shap_with_p1_deltas(_request(), _explanation(), [mismatch])
        duplicate = _p1_row(1, 0.2)
        with self.assertRaisesRegex(ShapFaithfulnessError, "duplicate"):
            pair_kernel_shap_with_p1_deltas(
                _request(), _explanation(), [duplicate, duplicate]
            )

    def test_schema_and_plan_generation_is_deterministic(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            schema_one, plan_one = write_schema_and_plan(
                temporary / "one.json", temporary / "one.md"
            )
            schema_two, plan_two = write_schema_and_plan(
                temporary / "two.json", temporary / "two.md"
            )
            self.assertEqual(schema_one.read_bytes(), schema_two.read_bytes())
            self.assertEqual(plan_one.read_bytes(), plan_two.read_bytes())
            self.assertEqual(
                json.loads(schema_one.read_text(encoding="utf-8")), schema_document()
            )
            self.assertEqual(
                plan_one.read_text(encoding="utf-8"),
                render_implementation_plan(schema_document()),
            )

    def test_committed_schema_and_plan_are_byte_reproducible(self):
        self.assertEqual(
            json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8")),
            schema_document(),
        )
        self.assertEqual(
            DEFAULT_PLAN_PATH.read_text(encoding="utf-8"),
            render_implementation_plan(schema_document()),
        )


if __name__ == "__main__":
    unittest.main()
