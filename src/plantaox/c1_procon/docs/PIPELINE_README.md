# AOP-ProCon (Component 1) — pipeline guide

**Project:** J26-DS-302 · PlantAOx-RAISE · Component 1 **Owner:** Fernando W A A T (IT23144408)
**Benchmark:** S2 build v3, fingerprint `47d9c2a2fff63eb1` — 1,389 unique peptides (FRS 565, FRS;MC 86, MC 63, GEN 675), 573 homology groups, strict-evidence pool 669 (104 MC-active / 565 FRS-only).

This guide explains how the notebooks, data, results and documents of Component 1 fit together. The long history of the defects found along the way is in `found_errors.md`; the current state is in `progress_log.md`; the thesis and viva material is in `help_thesis.md`.

## 1. Where things are in the repository

| Path | Content |
|---|---|
| `notebooks/c1_procon/` | Steps 1–8 (Colab notebooks; Step 8 runs locally) |
| `data/processed/c1_procon/` | S2 benchmark, descriptors, manifests, positive-pair files (`pairs/`), results tables (`results/`) |
| `src/plantaox/c1_procon/docs/` | this guide, progress log, error register, thesis help, hypotheses and results, release contract, archive of the S1-era plan |

Not committed (team policy: no large binary artefacts): ESM-2 embedding arrays (`.npy`), trained checkpoints (`.pt`), the release zip. The SHA-256 of the 15 checkpoints is in `data/processed/c1_procon/results/checkpoint_sha256.csv`.

## 2. Notebooks

| Step | Notebook | Purpose | Status |
|---|---|---|---|
| 1 | `STEP01_V2_Dataset_Curation_FINAL` | Merge AnOxPePred / Multi-AOP / DFBP / Peptipedia into the multi-label S2 benchmark; homology groups; strict evidence; inactive set; read-only confound cell (v4) | Colab-verified |
| 2 | `STEP02_V2_Descriptors_Embeddings_FIXED` | 14 descriptors; ESM-2 35M / 150M / 650M / 3B embeddings (max-pool < 10 aa, mean-pool ≥ 10 aa) | Colab-verified |
| 3 | `STEP03_V2_Positive_Pairs_FIXED` | Positive pairs in three modes (strict / extended / strict_ge4) with percentile, k-NN, random and physico-chemical controls | Colab-verified |
| 4 | `STEP04_V2_Training_FIXED` | 15 contrastive heads (τ 0.2, λ 5, uniformity 1.5), collapse report | Colab-verified |
| 5 | `STEP05_V2_Evaluation_FIXED` | MC retrieval against baselines, paired confidence intervals, held-out collapse, supervised probe (v4: repeated grouped CV) | Colab-verified (v4) |
| 6 | `STEP06_V2_Seeds_Scale_Reverse` | 5 seeds, 4 model scales, reverse fold direction | Colab-verified |
| 7 | `STEP07_V2_Release_Package` | Probes, loader `aop_procon.py`, CONTRACT, MANIFEST, release zip | Colab-verified (v4) |
| 8 | `STEP08_Confound_Controls` | Source, length, split design, data size, ΔAUROC of ESM-2 over the confounds | Local run |

## 3. Run order and rules

`STEP01` (only the read-only confound cell) → `STEP02` → `STEP03` → `STEP04` → `STEP05` → `STEP06` → `STEP07`; `STEP08` locally on the release data. Every notebook asserts the S2 fingerprint and the SHA-256 of its inputs.

* **Never re-run Step 1 end to end** — it downloads one source from a live web archive and is not deterministic (N-13). The S2 data are frozen and fingerprint-checked.
* **Do not re-run Step 3** — the random-pair control would change and HP1-Random would become invalid (N-15).
* Step 6 does not need re-running after the Step 5 / 7 corrections (it evaluates retrieval only).

## 4. Headline results (strict mode)

* No trained contrastive head beats the untrained ESM-2 embedding, amino-acid composition or length (10 of 10 paired comparisons; 0 of 25 trained runs).
* The supervised probe (MC-active vs FRS-only) is weak: fold-mean AUROC 0.61; the single feature `source_group` gets 0.64; ESM-2 650M adds +0.005 [−0.039, +0.041] on top of composition + length + source.
* Random folds inflate AUROC by +0.13 … +0.19; a single grouped split can move it by up to 0.06.
* Source (all FRS-only peptides come from AnOxPePred) and tripeptide share (42.8 % vs 16.3 %) are the confounds; after controlling for them no ESM-2-specific mechanism signal remains.

Full tables: `data/processed/c1_procon/results/`. Use `help_thesis.md` §4 for the numbers that may be quoted and §6 for the wording rules.

## 5. Reproduction

Colab, `BASE = /content/drive/MyDrive/AOP-ProCon`. The Step 5 probe gives identical results on Colab (scikit-learn 1.6.1) and locally (1.9.1) because the fold assignment uses its own code, independent of the scikit-learn release.

## 6. Integration with Components 2–4

See `CONTRACT.md` (input, output, and "what the other components must not assume"). Short version: use the benchmark and the frozen embeddings; do not use the trained heads for scoring; do not read probe scores as mechanism evidence.
