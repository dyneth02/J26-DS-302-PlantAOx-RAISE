"""Shared path constants and one-time sys.path setup for the live-computation layer.

The generator scripts under prototype/scripts/ import each other with bare module names
(e.g. `from common_descriptors import compute_descriptors`), which only resolves if
prototype/scripts itself is on sys.path -- so that's what this module adds, once, on
first import. This lets the live endpoints import real functions directly from
generate_c1_trained_model_artifacts.py / generate_c2_artifacts.py (same algorithms that
produced the static artifacts, not reimplemented) rather than duplicating logic.

generate_c3_artifacts.py is deliberately NOT imported this way -- its module-level
`from multiaop_model import MultiAOPPredictor` pulls in torch_geometric/rdkit/xlstm,
which the live C3 endpoint (c2_logreg only, by design -- see the implementation plan)
does not need. c3_perturbation.py reimplements the small, pure-Python perturbation
pieces directly instead.
"""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE_ROOT = BACKEND_ROOT.parent
SCRIPTS_DIR = PROTOTYPE_ROOT / "scripts"
DATA_RAW = PROTOTYPE_ROOT / "data" / "raw"
DATA_PROCESSED = PROTOTYPE_ROOT / "data" / "processed"
TRAINED_MODEL_DIR = DATA_RAW / "trained_model"
ARTIFACTS_ROOT = PROTOTYPE_ROOT / "artifacts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
