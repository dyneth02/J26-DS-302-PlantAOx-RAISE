"""Component 3: physicochemical faithfulness audit for AOP predictors."""

from .config import ResearchConfig, load_research_config
from .cleaning import build_cleaned_dataset, clean_records, validate_sequence
from .standardization import build_standardized_dataset, normalize_sequence
from .identity_deduplication import build_cd_hit_dataset
from .redox_eligibility import build_redox_eligible_dataset
from .residue_annotation import build_residue_annotation_dataset
from .perturbation_schema import PerturbationRecord
from .p1_alanine_scanning import build_p1_dataset
from .blosum62 import load_blosum62, select_conservative_substitution
from .p2_conservative_substitutions import build_p2_dataset
from .p3_random_controls import build_p3_dataset
from .perturbation_pipeline import build_combined_perturbation_dataset

__all__ = [
    "ResearchConfig",
    "PerturbationRecord",
    "build_p1_dataset",
    "build_p2_dataset",
    "build_p3_dataset",
    "build_combined_perturbation_dataset",
    "load_blosum62",
    "build_cleaned_dataset",
    "build_cd_hit_dataset",
    "build_redox_eligible_dataset",
    "build_residue_annotation_dataset",
    "build_standardized_dataset",
    "clean_records",
    "load_research_config",
    "normalize_sequence",
    "select_conservative_substitution",
    "validate_sequence",
]
