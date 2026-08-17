"""Copy of Research/my/data/raw/Multi-AOP/predict/aop_def.py. Only change: the two bare
imports below became package-relative (`from .x import *`) so this loads inside a proper
Python package instead of requiring its directory on sys.path. CombinedModel's
architecture is otherwise untouched."""
import torch
import torch.nn.functional as F
import torch.nn as nn
from .seq_model_def import *
from .graph_model_def import *

seq_length=50

# Sequence Feature Pooling Options
class SequencePooling(nn.Module):
    def __init__(self, embedding_dim, pooling_type='attention'):
        super(SequencePooling, self).__init__()
        self.pooling_type = pooling_type

        if pooling_type == 'attention':
            self.attention = nn.Sequential(
                nn.Linear(embedding_dim, embedding_dim // 2),
                nn.Tanh(),
                nn.Linear(embedding_dim // 2, 1)
            )

    def forward(self, x):
        # x: [batch_size, seq_len, embedding_dim]
        if self.pooling_type == 'max':
            # Max pooling over sequence length
            return torch.max(x, dim=1)[0]

        elif self.pooling_type == 'mean':
            # Mean pooling over sequence length
            return torch.mean(x, dim=1)

        elif self.pooling_type == 'attention':
            # Self-attention pooling
            attn_weights = F.softmax(self.attention(x).squeeze(-1), dim=1)  # [batch_size, seq_len]
            return torch.bmm(attn_weights.unsqueeze(1), x).squeeze(1)  # [batch_size, embedding_dim]

        else:
            raise ValueError(f"Unknown pooling type: {self.pooling_type}")

# Feature Fusion Modules
class HierarchicalFusion(nn.Module):
    def __init__(self, seq_dim=128, graph_dim=128, hidden_dim=128, dropout_rate=0.5):
        super(HierarchicalFusion, self).__init__()

        self.seq_pooling = SequencePooling(seq_dim, pooling_type='attention')

        # Projection layers for sequence and graph features
        self.seq_proj = nn.Linear(seq_dim, hidden_dim)
        self.graph_proj = nn.Linear(graph_dim, hidden_dim)

        # Feature fusion
        self.fusion = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate)
        )

    def forward(self, seq_features, graph_features):
        # Pool sequence features
        pooled_seq = self.seq_pooling(seq_features)
        # Project features to common space
        seq_proj = self.seq_proj(pooled_seq)
        graph_proj = self.graph_proj(graph_features)
        # Concatenate and fuse
        combined = torch.cat([seq_proj, graph_proj], dim=1)
        fused = self.fusion(combined)

        return fused


class CombinedModel(nn.Module):
    def __init__(self, fusion_method='hierarchical',
                 fusion_hidden_dim=128, dropout_rate=0.5):
        super(CombinedModel, self).__init__()

        # Sequence model (xLSTM)
        self.sequence_model = SequenceModel()
        # Graph model (MPNN)
        self.graph_model = MPNN()

        # Feature fusion
        self.fusion_module = HierarchicalFusion()

        # Separate classifier layers instead of Sequential
        self.fc1 = nn.Linear(fusion_hidden_dim, 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout_rate)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
        self.sigmoid = nn.Sigmoid()

        # Store fusion method for reference
        self.fusion_method = fusion_method

    def forward(self, sequences, x, edge_index, edge_attr, batch):
        # Process sequence data
        seq_features = self.sequence_model(sequences)
        # Process graph data
        graph_features = self.graph_model(x, edge_index, edge_attr, batch)

        # Pool sequence features (for PCA analysis)
        pooled_seq = self.fusion_module.seq_pooling(seq_features)

        # Fuse features
        fused_features = self.fusion_module(seq_features, graph_features)

        # Penultimate layer features
        x = self.fc1(fused_features)
        x = self.relu(x)
        x = self.fc2(x)
        last_hidden = self.relu(x)
        x = self.dropout(last_hidden)
        x = self.fc3(x)
        outputs = self.sigmoid(x)

        # Return all features of interest for PCA
        return seq_features, pooled_seq, graph_features, fused_features, last_hidden, outputs
