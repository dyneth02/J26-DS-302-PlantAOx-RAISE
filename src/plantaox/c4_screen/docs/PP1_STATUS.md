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
- Injected mock examples are demonstrations, not findings. No retrieval-evaluation results are present for mock inputs. The PDSS method remains deferred pending a meaningful real-reference definition.

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

No plant exceeded the >95% single-tier degeneracy criterion (maximum fraction: rice 56.99%). The separately requested joint mean-centering sensitivity was run; its overall T1/T2/T3 fractions were 9.41%/18.87%/71.73%. Production thresholds and tiers remain unchanged. All signal sources are `mock`; cloud source is `mock_cloud`. Ten injected demonstration sequences were tagged, all among rice Tier 3 abstentions. They are demonstrations, not evidence; no retrieval-performance result is reported from mock inputs.

Three highest-CS card examples (MOCK signals/cloud):

| Plant | Sequence | Tier | d_AD | CS | SIM_C1 | PROB_C2 |
|---|---|---:|---:|---:|---:|---:|
| Soybean | `MAHQWV` | 1 | 0.012657 | 0.812150 | 0.991582 | 0.947628 |
| Rice | `LMTCYVR` | 1 | 0.009272 | 0.804253 | 0.982838 | 0.827003 |
| Rice | `GIHCMA` | 1 | 0.010808 | 0.803665 | 0.984122 | 0.870134 |

Abstained examples (Tier 3, RED, CS=0): olive `AEATDAQ`; olive `AEG`; rice `AGMEEVDMDEEVRPEF` (injected demonstration case).

`tests/c4_screen` passed **15 tests**. Two consecutive `python -m plantaox.c4_screen.run all --reuse-inputs --signals mock` runs matched SHA-256 for all 35 compared generated files (34 output-manifest entries plus the manifest). The manifest `data/interim/c4_screen/c4_output_manifest.json` checksums generated output files and records SHA-256 only for each of the five handoff inputs; none of the binary handoff files are copied into the manifest or Git. Diagnostics include per-plant Spearman `d_AD`/length correlations and length distributions. A separate joint mean-centering sensitivity yielded overall T1/T2/T3 fractions 9.41%/18.87%/71.73%; baseline tiers and thresholds were not changed. `pytest tests/c4_screen`: 15 passed; the full repository suite was not run. See `PP1_NUMBERS.md` for slide-ready figures.


## C4 PP1 follow-up freeze work — 19 October 2026

- A read-only search found C2 frozen PP1 CD-HIT representatives. A 912-sequence E1/E2, standard-alphabet, 3–20 AA list is staged at `data/interim/c4_screen/embeddings_staging/ref_cloud_sequences_real.csv` (E1=478, E2=434). Source label is provisional C2 baseline v1, pending replacement by C1 AOP-BenchPos. Its SHA-256 is recorded in `decision_log.md`. These sequences are not embedded yet; production remains on MOCK cloud N=500.
- Cached rice performance (N=140,813): AD tiering 18.562604 s; mock-signal scoring/ranking 1.644521 s; total 20.207124 s. This is one host/run, below the five-minute NFR2 target.
- `all --reuse-inputs --signals mock` and `all --reuse-inputs --signals dummy` are supported; dummy aliases mock. Two mock runs had matching SHA-256 across 35 files. The `--reuse-inputs` mode skips network proteome download and candidate regeneration, preserving Gate 1 outputs.
- C4-only tests: 15 passed. A seeded 2,000-row synthetic cloud-near-positive sandbox and mock/real signal-source swap fixture are tests only. Mock signal correlations were measured without tuning; details are in the technical report.
- Freeze docs, acceptance reports and handoff draft are listed in `C4_PP1_HANDOVER.md`; integrity hashes are in `C4_PP1_FREEZE_MANIFEST.json`. No external message has been sent.
- Checkout branch is `feat/c4-Screen1`; the requested `c4/pp1-final` branch was not checked out, and branch switching was prohibited. Release tag `c4-pp1-v2` points to this current branch's freeze commit.
