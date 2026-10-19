# Component 4 PP1 status: real, provisional, and mock

**Snapshot:** 19 October 2026. PP1 presentation target: **21 October 2026** (supersedes the earlier 26 October draft). This records repository evidence, not supervisor approval.

## Real and verified

- Gate 1 candidate generation is complete and remains unchanged.
- The candidate table contains 152,259 unique sequences from the four reviewed proteomes. Gate 1 funnel and provenance evidence are recorded in `SCREEN_PP1_Deployment_Progress.md`.
- Synthetic unit coverage verifies the downstream interfaces and algorithms listed below; it does not substitute for full-data acceptance.

## C4-provisional assumptions

- ESM-2 representation: `esm2_t33_650M_UR50D`, layer 33, mean of residue embeddings with BOS/EOS/PAD excluded. This recipe is not confirmed with C1.
- AD calibration uses leave-one-out cloud-member cosine distances; `d_norm=min(d_AD/t2,1)` and default SD multiplier 1.0.
- BCS LOW/MEDIUM/HIGH flags use C4 config cutoffs 0.5 and 0.7 and are explicitly `C4-provisional`.
- The C4 interface spec and join key are provisional where marked; do not attribute these choices to C1/C2/C3.

## MOCK only

- The reference cloud is a 500-sequence, composition-biased synthetic placeholder with seed 42 and source `mock_cloud`.
- C1 SIM, C2 probability, and C3 BCS stand-ins have source `mock`. Any dashboard/card/summary generated from these values must display a permanent mock notice.
- Injected mock examples are demonstrations, not findings. Do not report PARRS, Recall@K, MRR, EF@1%, or ARR on mock signals. PDSS is not implemented; its denominator concern remains open.

## Production verification — 19 October 2026

The supplied handoff passed `embed-import`: 152,259/152,259 candidates embedded, 1,280 dimensions, float16 source arrays, all finite, candidate/index order matched by peptide_id and sequence, and manifest row hash matched. Distance calculations used float32. Reference cloud: **500 sequences**, source `mock_cloud`.

| AD parameter | Verified value |
|---|---:|
| `mu_cloud` | 0.0185099002 |
| `sigma_cloud` (population SD) | 0.0097886926 |
| `t1` (mu + sigma) | 0.0282985928 |
| `t2` (mu + 2 sigma) | 0.0380872854 |
| SD multiplier | 1.0 |

Tier fractions (counts and fractions; all plants have 100% embedding coverage):

| Plant | Tier 1 | Tier 2 | Tier 3 |
|---|---:|---:|---:|
| Olive | 291 (51.50%) | 189 (33.45%) | 85 (15.04%) |
| Rapeseed | 2,461 (50.12%) | 1,605 (32.69%) | 844 (17.19%) |
| Rice | 80,252 (56.99%) | 35,718 (25.37%) | 24,843 (17.64%) |
| Soybean | 7,437 (55.22%) | 3,990 (29.63%) | 2,041 (15.15%) |

Tier fractions by plant and length bin:

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

No plant exceeded the >95% single-tier degeneracy criterion (maximum fraction: rice 56.99%). Therefore the conditional mean-centering check was **not triggered**; thresholds were unchanged. All signal sources are `mock`; cloud source is `mock_cloud`. Ten injected demonstration sequences were tagged, all among rice Tier 3 abstentions. They are demonstrations, not evidence; no PARRS, Recall@K, MRR, EF@1%, ARR, or PDSS was computed.

Three highest-CS card examples (MOCK signals/cloud):

| Plant | Sequence | Tier | d_AD | CS | SIM_C1 | PROB_C2 |
|---|---|---:|---:|---:|---:|---:|
| Soybean | `MAHQWV` | 1 | 0.012657 | 0.812150 | 0.991582 | 0.947628 |
| Rice | `LMTCYVR` | 1 | 0.009272 | 0.804253 | 0.982838 | 0.827003 |
| Rice | `GIHCMA` | 1 | 0.010808 | 0.803665 | 0.984122 | 0.870134 |

Abstained examples (Tier 3, RED, CS=0): olive `AEATDAQ`; olive `AEG`; rice `AGMEEVDMDEEVRPEF` (injected demonstration case).

`tests/c4_screen` passed **12 tests**. The checksummed manifest is `data/interim/c4_screen/c4_output_manifest.json`: it covers 29 generated/available output files, has run status `complete_mock_cloud_production`, and has SHA-256 `85439e8a6b13268f4a630c686ba4a17c5b9307d4b35122dd57fe838ae0f28860`. The five `.npy`/handoff inputs are excluded from the output manifest; the copied embedding manifest is included.
