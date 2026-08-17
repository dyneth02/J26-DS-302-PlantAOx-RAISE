"""Loads the real, previously-trained Multi-AOP CombinedModel checkpoint
(Research/my/data/raw/Multi-AOP/final_model/best_combined_model.pth: sequence xLSTM +
molecular-graph MPNN hybrid, reported val accuracy 0.906 at epoch 17) and exposes it
through the same PredictorAdapter shape used elsewhere in this prototype
(`score_batch(sequences) -> list[float]`), so Component 3's audit logic doesn't need to
change to point at a different predictor.

Two fixes were required to run this checkpoint on CPU, both applied here rather than by
editing the original files under Research/my:
  1. seq_model_def.py: xlstm's non-CUDA backend is named "vanilla", not "cpu" (see that
     file's docstring).
  2. This file: the CUDA sLSTM backend stores its recurrent-kernel weight in a different
     physical layout than the vanilla backend. xlstm defines an exact, doctested
     ext2int/int2ext conversion between backends' internal layouts and a shared "external"
     layout (xlstm/blocks/slstm/cell.py, sLSTMCell_cuda vs sLSTMCell_vanilla) -- applied
     below. This is a lossless layout remap, not an approximation: the model's outputs
     should match the original CUDA inference exactly (up to floating-point associativity).
"""
from pathlib import Path

import torch

from .aop_def import CombinedModel
from .features import build_batch

CHECKPOINT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "multiaop_best_combined_model.pth"

# sLSTM config from seq_model_def.py: num_heads=4, embedding_dim=128 -> head_dim=32, and
# sLSTM's 4 gates (i, f, z, o) -> num_gates=4.
_NUM_HEADS, _HEAD_DIM, _NUM_GATES = 4, 32, 4


def _remap_cuda_to_vanilla(state_dict: dict) -> dict:
    for key in list(state_dict.keys()):
        if key.endswith("_recurrent_kernel_"):
            cuda_internal = state_dict[key]
            external = cuda_internal.reshape(_NUM_HEADS, _HEAD_DIM, _NUM_GATES, _HEAD_DIM)
            vanilla_internal = external.permute(0, 2, 3, 1).reshape(_NUM_HEADS, _NUM_GATES * _HEAD_DIM, _HEAD_DIM)
            state_dict[key] = vanilla_internal
    return state_dict


class MultiAOPPredictor:
    """Real pretrained AOP predictor (sequence xLSTM + molecular-graph MPNN), CPU inference."""

    name = "MultiAOP_CombinedModel_pretrained"

    def __init__(self, checkpoint_path: Path = CHECKPOINT_PATH, batch_size: int = 32):
        self.device = torch.device("cpu")
        self.batch_size = batch_size

        self.model = CombinedModel()
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        state_dict = _remap_cuda_to_vanilla(checkpoint["model_state_dict"])
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

        self.reported_val_metrics = checkpoint.get("val_metrics", {})
        self.reported_epoch = checkpoint.get("epoch")

    def score_batch(self, sequences: list[str]) -> list[float]:
        scores = []
        with torch.no_grad():
            for i in range(0, len(sequences), self.batch_size):
                chunk = sequences[i:i + self.batch_size]
                seq_t, x, edge_index, edge_attr, batch = build_batch(chunk)
                _, _, _, _, _, outputs = self.model(seq_t, x, edge_index, edge_attr, batch)
                probs = outputs.squeeze(-1)
                scores.extend(probs.tolist() if probs.dim() > 0 else [probs.item()])
        return scores

    def score(self, sequence: str) -> float:
        return self.score_batch([sequence])[0]
