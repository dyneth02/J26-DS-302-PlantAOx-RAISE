"""Sequence -> (token, molecular graph) feature construction, extracted unchanged from
Research/my/data/raw/Multi-AOP/predict/aop_dataloader.py. The "graph" here is each residue's
amino-acid SMILES concatenated as disconnected fragments (not a folded 3D structure) --
that's the original authors' design, reproduced exactly, not a simplification made here.
"""
import torch
from rdkit import Chem
from torch_geometric.data import Data

AA_TO_INT = {
    "A": 0, "R": 1, "N": 2, "D": 3, "C": 4, "E": 5, "Q": 6, "G": 7, "H": 8, "I": 9,
    "L": 10, "K": 11, "M": 12, "F": 13, "P": 14, "S": 15, "T": 16, "W": 17, "Y": 18, "V": 19,
}

AA_TO_SMILES = {
    "A": "CC(N)C(=O)O", "R": "NC(=N)NCCCC(N)C(=O)O", "N": "NC(=O)CC(N)C(=O)O",
    "D": "OC(=O)CC(N)C(=O)O", "C": "SC(C(N)C(=O)O)", "E": "OC(=O)CCC(N)C(=O)O",
    "Q": "NC(=O)CCC(N)C(=O)O", "G": "NCC(=O)O", "H": "NC(Cc1c[nH]cn1)C(=O)O",
    "I": "CC(C)CC(N)C(=O)O", "L": "CC(C)CC(N)C(=O)O", "K": "NCCCCC(N)C(=O)O",
    "M": "CSCCC(N)C(=O)O", "F": "NC(Cc1ccccc1)C(=O)O", "P": "O=C(O)C1CCCN1",
    "S": "OCC(N)C(=O)O", "T": "CC(O)C(N)C(=O)O", "W": "NC(Cc1c[nH]c2ccccc12)C(=O)O",
    "Y": "NC(Cc1ccc(O)cc1)C(=O)O", "V": "CC(C)C(N)C(=O)O",
}


def aa_to_int(sequence: str) -> list[int]:
    return [AA_TO_INT.get(aa.upper(), -1) for aa in sequence]


def aa_to_smiles(sequence: str) -> str:
    smiles_list = [AA_TO_SMILES.get(aa.upper(), "") for aa in sequence]
    return ".".join(s for s in smiles_list if s)


def get_atom_features(atom) -> list:
    return [
        atom.GetAtomicNum(),
        atom.GetDegree(),
        atom.GetFormalCharge(),
        atom.GetNumRadicalElectrons(),
        atom.GetIsAromatic(),
        int(atom.GetHybridization()),
        atom.GetNumImplicitHs(),
        int(atom.GetChiralTag()),
        len(atom.GetNeighbors()),
        atom.IsInRing(),
        atom.GetMass(),
        atom.GetTotalValence(),
    ]


def mol_to_graph(mol) -> Data:
    atom_features = [get_atom_features(atom) for atom in mol.GetAtoms()]
    x = torch.tensor(atom_features, dtype=torch.float)

    edges, edge_features = [], []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        edges.append([i, j])
        edges.append([j, i])
        feature = [bond.GetBondTypeAsDouble(), bond.GetIsConjugated(), bond.GetIsAromatic()]
        edge_features.extend([feature, feature])

    if edges:
        edge_index = torch.tensor(edges, dtype=torch.long).t()
        edge_attr = torch.tensor(edge_features, dtype=torch.float)
    else:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, 3), dtype=torch.float)
    return Data(x=x, edge_index=edge_index, edge_attr=edge_attr)


def build_batch(sequences: list[str], seq_length: int = 50):
    """Build the (sequences, x, edge_index, edge_attr, batch) tuple CombinedModel expects."""
    seq_tensors = []
    for s in sequences:
        ints = aa_to_int(s)[:seq_length]
        ints = ints + [0] * (seq_length - len(ints))
        seq_tensors.append(torch.tensor(ints, dtype=torch.long))
    sequences_t = torch.stack(seq_tensors)

    x_list, edge_index_list, edge_attr_list, batch_idx = [], [], [], []
    offset = 0
    for i, s in enumerate(sequences):
        mol = Chem.MolFromSmiles(aa_to_smiles(s))
        g = mol_to_graph(mol)
        n = g.x.size(0)
        batch_idx.extend([i] * n)
        x_list.append(g.x)
        if g.edge_index.size(1) > 0:
            edge_index_list.append(g.edge_index + offset)
            edge_attr_list.append(g.edge_attr)
        offset += n

    x = torch.cat(x_list, dim=0)
    if edge_index_list:
        edge_index = torch.cat(edge_index_list, dim=1)
        edge_attr = torch.cat(edge_attr_list, dim=0)
    else:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, 3), dtype=torch.float)
    batch = torch.tensor(batch_idx, dtype=torch.long)
    return sequences_t, x, edge_index, edge_attr, batch
