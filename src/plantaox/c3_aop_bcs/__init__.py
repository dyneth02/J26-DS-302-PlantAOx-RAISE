"""Component 3: physicochemical faithfulness audit for AOP predictors."""

from .config import ResearchConfig, load_research_config
from .cleaning import build_cleaned_dataset, clean_records, validate_sequence
from .standardization import build_standardized_dataset, normalize_sequence
from .identity_deduplication import build_cd_hit_dataset
from .redox_eligibility import build_redox_eligible_dataset

__all__ = [
    "ResearchConfig",
    "build_cleaned_dataset",
    "build_cd_hit_dataset",
    "build_redox_eligible_dataset",
    "build_standardized_dataset",
    "clean_records",
    "load_research_config",
    "normalize_sequence",
    "validate_sequence",
]
