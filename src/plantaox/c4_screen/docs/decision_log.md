# Decision log

## Component 4 — candidate generation

- **Proteome scope:** use UniProt Swiss-Prot reviewed entries selected by taxonomy ID. The proposal's proteome identifiers include unreviewed entries, so reviewed-only counts and exclusions are recorded separately.
- **Digestion implementation:** use the installed `pyteomics` Expasy-style rules rather than a BIOPEP-UWM batch workflow. Installed `pyteomics 5.0.1` provides the exact rule names `pepsin ph1.3` and `trypsin`; pepsin pH 1.3 is the nearest available rule to proposed pH 1.2.
- **Deduplication:** exact sequence equality within and across plants; preserve every parent accession and 1-based inclusive position. CD-HIT is deferred. At 90% identity, peptides up to 9 residues cannot have a non-identical sequence meeting the threshold; optional clustering for lengths 10–20 remains a later decision.
- **Signals:** signal inputs remain mock-only and must retain `source="mock"`. The config's BCS flag thresholds are explicitly `C4-provisional`; this Gate 1 does not generate or evaluate signals.

## Component 4 — embeddings, AD, and mock integration (19 October 2026)

- **Embedding recipe:** the Colab notebook uses `esm2_t33_650M_UR50D`, layer 33, mean pooling over residue embeddings after excluding BOS/EOS/PAD. This is a **C4 working assumption**, not confirmed by C1. No ESM-2 weights were loaded or downloaded locally. The Colab embedding and cloud handoff files are absent from the repository workspace.
- **Reference cloud:** the planned 500-sequence cloud is a composition-biased synthetic placeholder with seed 42 and source `mock_cloud`. It is not a biological reference set; all derived AD outputs must say MOCK. C4 must not generate or embed a replacement cloud.
- **AD calibration:** compute `d_AD = 1 - cosine(x, centroid)` and calibrate `mu_cloud` and population `sigma_cloud` on leave-one-out distances, where each cloud member is compared with a centroid recomputed without that member. Freeze `t1 = mu + sd_multiplier*sigma` and `t2 = mu + 2*sd_multiplier*sigma`; default multiplier is 1.0. Normalize with `d_norm = min(d_AD/t2, 1)`. Tier boundaries follow the provisional C4 contract.
- **Degeneracy diagnostic:** if >95% of a plant falls in one tier, compare mean-centered cosine geometry and report it. This diagnostic must not tune or replace the frozen thresholds. Production diagnostics cannot be evaluated until the embedding handoff exists.
- **Signal and score contract:** use the existing `tests/c4_screen/fixtures/mock_signals.py`; join by sequence, retain `source="mock"`, score with configured 0.5/0.5 weights, and force Tier 3 CS to zero. Never report PARRS, Recall@K, MRR, EF@1%, or ARR for mock signals.
- **PDSS:** the denominator/baseline can be near zero and make PDSS unstable. This remains an open supervisor decision; no PDSS is implemented or reported here.
