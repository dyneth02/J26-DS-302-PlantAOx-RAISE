# C1 experiments (early homology exploration)

These two notebooks are **exploration work from the first version of the pipeline (S1)**. They tried two homology tools on the old
`AOP-BenchPos.csv` (tiered labels, 1,573 rows) to decide how similar peptides should be kept on the same side of a split:

| Notebook | What it tried |
|---|---|
| `C1_CD-HIT.ipynb` | CD-HIT clusters at 40% identity (`cluster_40`) |
| `C1_GraphPart_HESTIA.ipynb` | GraphPart partitions at 40% identity, run twice to check that the assignments are stable |

They are kept as the record of that decision. They are **not part of the accepted pipeline** and they do not read the current
benchmark: the accepted homology groups are built in Step 1 (`../STEP01_V2_Dataset_Curation_FINAL.ipynb`) as the union of identical
sequences, CD-HIT 40% clusters and sequences at least 70% identical to a peptide of 4 or more amino acids. Do not quote numbers from
these notebooks.

They were run on Google Colab (paths such as `/content/drive/MyDrive/AOP-ProCon` are the Colab layout).
