# AOP-ProCon (Component 1) — integration contract, release v1

**Benchmark version:** S2 build v3, fingerprint `47d9c2a2fff63eb1` (1389 unique peptides, 714 mechanism-active).  **Embedding model:** ESM-2 650M (`esm2_t33_650M_UR50D`), last layer; max-pool over residues for < 10 aa, mean-pool for >= 10 aa.

## Input
* A list / column of peptide sequences: upper-case, the 20 canonical amino acids only, length 3–49 (the range present in the benchmark; other lengths are accepted but flagged).
* Python: `aop_procon.score_peptides(list_of_sequences)`; the optional argument `embeddings` takes a precomputed `(n, 1280)` array aligned with the input.

## Output — one row per input peptide, same order (`pandas.DataFrame`, also writable as CSV)
| column | type | meaning |
|---|---|---|
| `sequence`, `length` | str, int | the input |
| `valid`, `problems` | bool, str | `False` if non-canonical residues or empty; length outside (3, 49) is reported in `problems` but the row is still scored |
| `in_benchmark` | bool | the sequence is one of the 1389 benchmark peptides |
| `benchmark_labels`, `fold`, `homology_group`, `strict_evidence` | str, float, float, bool | only if `in_benchmark`: `FRS` / `MC` / `FRS;MC` / `GEN` (GEN = mechanism **unknown**, not inactive; `strict_evidence` is `None` for `GEN`) |
| `mc_score_strict`, `mc_score_extended` | float in (0, 1) | probability-like score for "MC-active" vs "FRS-only" from the two probes (ESM-2 650M, logistic regression) |
| `oof_mc_score_strict`, `oof_mc_score_extended` | float | **out-of-fold** score (grouped by `homology_group`) for benchmark peptides — use these, not the `mc_score_*` columns, to judge the probe on benchmark data |
| `score_is_in_sample_strict`, `score_is_in_sample_extended` | bool | `True` if the peptide was in the pool that probe was fitted on (mechanism-active; for `strict` also `strict_evidence`), so the matching `mc_score_*` is optimistic. `GEN` peptides are in neither pool |
| `warning` | str | fixed text: the signal is weak |

Embeddings (`embeddings/esm2_{35M,150M,650M,3B}.npy`, row order in the `*_sequences.txt` files) are the other usable output; they are frozen ESM-2 vectors, not a trained projection.

**Provenance of the cached embeddings** (`step2_manifest.json`: {'35M': 'already aligned', '150M': 'already aligned', '650M': 'extracted', '3B': 'extracted'}). Files marked "already aligned" or "re-aligned" were reused from earlier extraction runs whose checkpoint, layer and pooling settings were not recorded; "extracted" files were produced by the Step 2 code. A fresh-vs-cached ESM-2 650M comparison was **not** run for this release (`RUN_ESM_SMOKETEST = False`).

## Performance that may be quoted (repeated homology-grouped CV: 5 folds × 10 fold assignments, fold-mean AUROC, MC-active vs FRS-only)
| probe | n (MC-active / FRS-only) | ESM-2 650M AUROC [95 % CI] (range over the 10 repeats) | amino-acid composition | **source_group only** | composition + length + source | paired ΔAUROC: ESM-2 650M − composition | ESM-2 650M − source only | ESM-2 650M + (comp. + length + source) − (comp. + length + source) |
|---|---|---|---|---|---|---|---|---|
| `strict` | 669 (104 / 565) | 0.606 [0.559, 0.724] (0.559-0.651) | 0.597 [0.550, 0.713] | 0.639 [0.598, 0.713] | 0.696 [0.645, 0.822] | +0.009 [-0.046, +0.061] (no difference detected) | -0.033 [-0.107, +0.079] (no difference detected) | +0.005 [-0.039, +0.041] (no difference detected) |
| `extended` | 714 (149 / 565) | 0.671 [0.621, 0.762] (0.656-0.714) | 0.683 [0.636, 0.776] | 0.747 [0.704, 0.818] | 0.798 [0.751, 0.896] | -0.013 [-0.057, +0.029] (no difference detected) | -0.077 [-0.141, +0.001] (no difference detected) | -0.007 [-0.039, +0.021] (no difference detected) |

Chance reference = fold-mean AUROC of pure-noise features over 20 noise seeds: strict 0.511 [0.430, 0.567], extended 0.501 [0.455, 0.555]. The CIs are group bootstraps with the fitted models held fixed; they are narrower than the true uncertainty.

**Confounds (read before quoting any number above).** Every FRS-only peptide in the benchmark comes from AnOxPePred, while 28 % of the strict MC-active peptides come from external literature, so the single feature `source_group` already separates the two classes at least as well as ESM-2 650M (table above). Length acts through the share of tripeptides (FRS-only 43 %, MC-active 16 % in `strict`), not through the mean length (5.75 vs 5.86 aa). The probe scores therefore **cannot** be read as mechanism evidence; with source and length controlled, ESM-2 adds nothing measurable (paired ΔAUROC CIs include 0), and in a single-source, length-matched subset every representation falls to AUROC ≈ 0.58-0.62 (STEP 08).

A **single** `GroupKFold` split moved the strict ESM-2 650M AUROC between 0.59 and 0.66 depending on the scikit-learn release (the value 0.593 quoted in earlier builds is one such split); the pooled out-of-fold AUROC is biased by fold-specific intercepts. Use the fold-mean values above.

With random (leaky) folds the same probe reaches 0.792 (strict) and 0.808 (extended): **never quote an AUROC from a split that is not grouped by `homology_group`, nor from a single split.**

## What the other components must not assume
1. The probes are **not** antioxidant-activity, toxicity or safety predictors; they only separate MC-active from FRS-only labels, weakly.
2. `GEN` means "antioxidant mechanism not established", not "inactive". The 27 peptides in `data/AOP-Inactive.csv` with `db_conflict == False` are the only clean negatives.
3. Benchmark labels combine assay-level and database-level evidence; `strict_evidence == True` marks per-peptide evidence only.
4. The trained contrastive heads in `models/` are research artefacts (worse than the untrained baselines); do not load them for scoring.
5. Scores outside 3–49 aa, or for non-plant-derived sequences, are extrapolation.
6. **Source and length are confounded with the label** (see the performance section): a model can learn "which database / how many tripeptides" instead of "which mechanism". New benchmark peptides from other sources are outside what the probes were validated on.

## Versioning
`MANIFEST.json` lists the SHA-256 of every file and the S2 / embedding / pair-file fingerprints. A change of any input changes the fingerprint; consumers should assert it.
