from __future__ import annotations

from backend.app.core import plantaox_bridge  # noqa: F401
from backend.app.core.errors import ResourceNotFoundError
from backend.app.schemas.c2_pu import Fr3ExampleResponse, Fr3SummaryResponse
from backend.app.services.c2_pu.artifacts import c2_interim_dir, load_processed_json


def _demo_payload() -> dict:
    return load_processed_json("fr3_demo_output.json")


def _descriptor_names() -> list[str]:
    return load_processed_json("fr3_descriptor_schema.json")["descriptor_names"]


def list_fr3_examples() -> Fr3SummaryResponse:
    from plantaox.c2_pu.common.descriptors import compute_descriptors

    demo = _demo_payload()
    fold_cache_path = c2_interim_dir() / "fr3_fold0_scaled_features.npz"

    examples: list[Fr3ExampleResponse] = []
    for role, record in demo["input_validation"].items():
        sequence = record["sequence"]
        descriptors = compute_descriptors(sequence) if record["valid_alphabet_and_length"] else None
        examples.append(
            Fr3ExampleResponse(
                peptide_id=record["peptide_id"],
                role=role,
                sequence=sequence,
                length=len(sequence),
                valid_alphabet_and_length=record["valid_alphabet_and_length"],
                descriptors=descriptors,
                embedding_available=True,
                embedding_dim=demo["schema"]["embedding_dim"],
                fused_dim=demo["schema"]["fused_dim"],
            )
        )

    return Fr3SummaryResponse(
        fold_id=demo["fold_id"],
        descriptor_names=_descriptor_names(),
        embedding_model=demo["schema"]["embedding_model"],
        embedding_dim=demo["schema"]["embedding_dim"],
        fused_dim=demo["schema"]["fused_dim"],
        pool_coverage=demo["pool_coverage"],
        feature_cache_available=fold_cache_path.exists(),
        examples=examples,
    )


def get_fr3_example(peptide_id: str) -> Fr3ExampleResponse:
    summary = list_fr3_examples()
    for example in summary.examples:
        if example.peptide_id == peptide_id:
            return example
    raise ResourceNotFoundError(f"No FR3 demonstration example with peptide_id={peptide_id!r}")
