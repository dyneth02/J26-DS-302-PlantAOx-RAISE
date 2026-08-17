"""Copy of Research/my/data/raw/Multi-AOP/predict/seq_model_def.py with one fix: the
original hardcodes sLSTM backend="cpu" as the non-CUDA fallback, but the installed xlstm
package (2.0.5) only accepts backend in {"cuda", "vanilla"} -- "cpu" raises
`RuntimeError: sLSTMCell unknown backend cpu`. Changed to "vanilla", which is xlstm's
actual CPU-compatible backend. No other changes; this still loads the original
CUDA-trained checkpoint correctly once the recurrent-kernel weights are remapped between
backend-specific layouts (see predictor.py) -- xlstm defines that remap as an exact,
doctested ext2int/int2ext round trip, not an approximation.
"""
import torch
import torch.nn as nn

from xlstm import xLSTMBlockStack, xLSTMBlockStackConfig, mLSTMBlockConfig
from xlstm import mLSTMLayerConfig, sLSTMBlockConfig, sLSTMLayerConfig, FeedForwardConfig

device = torch.device("cpu")
cfg = xLSTMBlockStackConfig(
    mlstm_block=mLSTMBlockConfig(
        mlstm=mLSTMLayerConfig(
            conv1d_kernel_size=4,
            qkv_proj_blocksize=8,
            num_heads=4
        )
    ),
    slstm_block=sLSTMBlockConfig(
        slstm=sLSTMLayerConfig(
            backend="vanilla",
            num_heads=4,
            conv1d_kernel_size=4,
            bias_init="powerlaw_blockdependent",
        ),
        feedforward=FeedForwardConfig(
            proj_factor=2.0,
            act_fn="gelu",
            dropout=0.5
        ),
    ),
    context_length=256,
    num_blocks=3,
    embedding_dim=128,
    slstm_at=[1, 2]
)


class SequenceModel(nn.Module):
    def __init__(self, vocab_size=21, seq_length=50):
        super(SequenceModel, self).__init__()
        self.embedding = nn.Embedding(vocab_size, cfg.embedding_dim, padding_idx=0)
        self.xlstm_stack = xLSTMBlockStack(cfg)
        self.seq_length = seq_length

    def forward(self, x):
        x = self.embedding(x)
        x = self.xlstm_stack(x)
        return x
