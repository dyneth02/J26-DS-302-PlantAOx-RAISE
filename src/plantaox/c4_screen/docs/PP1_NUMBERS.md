# Component 4 PP1 — verified numbers

**Snapshot:** 19 October 2026 · **Presentation:** 21 October 2026. Values below were generated from reviewed UniProt inputs and the supplied ESM-2 handoff. The reference cloud and all Function B signals are MOCK.

## Candidate funnel

| Plant | Retained proteins | Excluded proteins | Raw fragments | Length 3–20 | Composition-filtered | Unique plant candidates |
|---|---:|---:|---:|---:|---:|---:|
| Soybean | 410 | 29 | 44,028 | 18,869 | 18,843 | 13,468 |
| Rice | 4,180 | 17 | 551,252 | 239,881 | 239,483 | 140,813 |
| Rapeseed | 152 | 7 | 13,992 | 6,356 | 6,343 | 4,910 |
| Olive | 106 | 4 | 3,508 | 1,692 | 1,692 | 565 |

The cross-plant candidate table has **152,259 unique sequences**. All 152,259 supplied embeddings were imported (1,280 dimensions); zero were unembedded. The reference cloud has **500 sequences**, `source=mock_cloud`.

## AD parameters and baseline tier fractions

`d_AD = 1 − cosine(candidate, cloud centroid)`. Cloud calibration uses leave-one-out centroid distances and population standard deviation, SD multiplier 1.0.

| Parameter | Verified value |
|---|---:|
| μ cloud | 0.0185099002 |
| σ cloud | 0.0097886926 |
| t1 = μ + σ | 0.0282985928 |
| t2 = μ + 2σ | 0.0380872854 |

| Plant | Tier 1 | Tier 2 | Tier 3 |
|---|---:|---:|---:|
| Olive (n=565) | 51.50% | 33.45% | 15.04% |
| Rapeseed (n=4,910) | 50.12% | 32.69% | 17.19% |
| Rice (n=140,813) | 56.99% | 25.37% | 17.64% |
| Soybean (n=13,468) | 55.22% | 29.63% | 15.15% |

### Baseline tier fractions by plant and peptide length

| Plant | Length bin | n | Tier 1 | Tier 2 | Tier 3 |
|---|---|---:|---:|---:|---:|
| Olive | 3–10 | 460 | 46.52% | 39.35% | 14.13% |
| Olive | 11–20 | 105 | 73.33% | 7.62% | 19.05% |
| Rapeseed | 3–10 | 4,345 | 49.21% | 34.15% | 16.64% |
| Rapeseed | 11–20 | 565 | 57.17% | 21.42% | 21.42% |
| Rice | 3–10 | 114,692 | 57.90% | 26.84% | 15.26% |
| Rice | 11–20 | 26,121 | 53.01% | 18.90% | 28.08% |
| Soybean | 3–10 | 11,763 | 53.90% | 31.19% | 14.91% |
| Soybean | 11–20 | 1,705 | 64.34% | 18.83% | 16.83% |

## Additional diagnostics

| Plant | n | Spearman ρ (`d_AD`, sequence length) |
|---|---:|---:|
| Olive | 565 | −0.4223 |
| Rapeseed | 4,910 | −0.3222 |
| Rice | 140,813 | −0.0623 |
| Soybean | 13,468 | −0.3424 |

The reference cloud's mean sequence length is **12.14 AA** (N=500); all candidate sequences average **7.631 AA** (N=152,259). The length-specific distributions are in `data/interim/c4_screen/diagnostics/cloud_vs_candidate_length_distribution.csv`. The per-plant correlations are descriptive associations against this MOCK cloud, not inferential biological evidence.

No plant exceeded the >95% single-tier degeneracy criterion (largest baseline fraction: rice Tier 1, 56.99%). A separate joint mean-centering sensitivity recomputed cloud calibration (μ=0.4238381, σ=0.2141557, t1=0.6379938, t2=0.8521495): overall tiers shifted to 9.41% / 18.87% / 71.73% (T1/T2/T3). This is sensitivity-only; production tier assignments and thresholds were not modified. Full plant/bin comparisons are in `data/interim/c4_screen/diagnostics/mean_centering_tier_fraction_sensitivity.csv`.

## What this does NOT show

- The 500-sequence reference cloud is a **synthetic MOCK placeholder** (`source=mock_cloud`), not a validated AOP-positive biological reference set. AD distances, calibration, tiers, and related diagnostics are therefore provisional and cloud-dependent.
- SIM_C1, PROB_C2, and BCS values are **mock signals** (`source=mock`). Cards, scores, and rankings do not establish retrieval or biological performance.
- These numbers do not establish causal AOP relevance, experimental activity, plant safety, or clinical/agricultural efficacy. They do not report PARRS, Recall@K, MRR, EF@1%, ARR, or PDSS.
- The ESM-2 layer-33 mean-residue pooling recipe is a C4 working assumption awaiting C1 confirmation.

## Reproducibility evidence

Two consecutive `python -m plantaox.c4_screen.run all` executions produced identical SHA-256 hashes for all **32 compared pipeline output files**. The generated output manifest is `data/interim/c4_screen/c4_output_manifest.json`; it includes SHA-256-only entries for the five supplied handoff files while leaving those large inputs out of Git. Only `pytest tests/c4_screen` was run: **12 passed**.
