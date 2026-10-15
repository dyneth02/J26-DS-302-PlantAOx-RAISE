# FR4 Task 4.6 — C1 → C2 → C3 Curriculum Prototype

**Status:** PASS (technical prototype)  
**Fold:** 0  
**Learner:** corrective beta/gamma nnPU, π=0.10, β=0, γ=1

## Learner and design decision

The prototype uses the existing corrective-nnPU BinaryMlp. It supports separate positive and unlabeled streams, carries meaningful unlabeled-risk gradients on corrective updates, and can warm-start one model through the curriculum. The accepted direct-clamped model was not selected because 98–99% of its updates suppressed the unlabeled gradient. This is an engineering choice, not a claim that corrective nnPU is biologically superior; Task 4.5 found weak assay-supported discrimination for every baseline.

The Planner's evidence weighting is implemented as normalized positive expectations with E1 weight 1.0 and E2 weight 0.5. E3 is excluded. The positive-class prior remains the provisional π=0.10. Every stage uses corrective nnPU with β=0 and γ=1.

## Data and leakage controls

| Stage | Positive training rows | Unlabeled training rows | Validation used for selection |
|---|---:|---:|---|
| C1 | 331 E1 + 273 E2 = 604 | 3,220 C1 training rows | Fixed 106 E1+E2 validation positives + fixed 568 C1 validation rows |
| C2 | same 604 | all 2,000 C2 rows | same fixed validation surrogate |
| C3 | same 604 | 2,000 fold-0 C3 rows | same fixed validation surrogate |

C1/C2/C3 remain unlabeled. C2 and C3 never receive supervised-negative labels. Fold-0 C3 membership was independently checked against `curation.c3.load_fold_challenges(ranking_path, 0)`; the 2,325-sequence cross-fold union was not used. The shared leakage report found no ID or sequence overlap among training, validation, held-out-positive, challenge, and external-control subsets.

GraphPart-held-out positives and the 38 external controls were used only after each stage's best checkpoint had been selected from the fixed PU surrogate validation risk. They did not control stopping, transitions, or hyperparameters.

## Training configuration

The run reads the accepted corrective baseline's actual resolved configuration: fused 495-dimensional features; BinaryMlp 495→128→64→1; Adam; learning rate 0.001; weight decay 0.0; batch size 32; maximum 100 epochs per stage; seed 42; device `auto` (resolved to CPU). A stage transitions after five consecutive epochs without a validation-risk improvement of at least `1e-4`.

Model weights continue from each stage's best checkpoint. Optimizer state is reset at a stage boundary. This isolates each pool's optimization schedule while retaining learned model parameters. Each checkpoint records its parent path and SHA-256.

## Stage-wise results

| Condition | Epochs | Best epoch | Best validation risk | Corrective updates | Held-out recovery | C1 >0.5 | C2 >0.5 | C3 >0.5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Accepted corrective baseline | 27 | 16 | 0.06302 | 53.25% | 55.65% | 1.40% | 14.40% | 1.15% |
| After C1 | 9 | 3 | 0.06144 | 52.70% | 59.68% | 2.22% | 13.05% | 0.50% |
| After C2 | 14 | 8 | 0.07664 | 44.22% | 38.71% | 2.35% | 3.30% | 0.60% |
| After C3 | 6 | 0 | 0.06766 | 51.85% | 67.74% | 4.65% | 12.20% | 0.60% |

The accepted baseline did not use the Planner's E1/E2 weights, so its surrogate-risk value is contextual rather than numerically interchangeable with the weighted curriculum risks. Stage risks are comparable with each other because all three use the same weighted validation protocol.

Stage C2 substantially lowered C2 scores, but it also reduced held-out-positive recovery. Stage C3's best checkpoint was its first epoch: subsequent C3 epochs worsened the fixed validation surrogate and triggered the five-epoch plateau transition. Stage C3 restored positive recovery but also raised C1/C2 score fractions relative to Stage C2. This is a tradeoff, not monotonic improvement.

## Read-only assay-supported evaluation

| Condition | MCC | AP | AUROC | Recall | TP / TN / FP / FN |
|---|---:|---:|---:|---:|---:|
| Accepted corrective baseline | -0.2498 | 0.6827 | 0.3224 | 0.5565 | 69 / 6 / 32 / 55 |
| After C1 | -0.2929 | 0.6282 | 0.2334 | 0.5968 | 74 / 3 / 35 / 50 |
| After C2 | -0.1641 | 0.6600 | 0.3171 | 0.3871 | 48 / 16 / 22 / 76 |
| After C3 | -0.2338 | 0.6252 | 0.2381 | 0.6774 | 84 / 3 / 35 / 40 |

No stage resolves Task 4.5's external-control limitation. Stage C2 rejects more controls at threshold 0.5 but loses many held-out positives; Stage C3 restores recall while again accepting most controls. These metrics were calculated only after training and were not used to choose a stage or revise the curriculum.

## Checkpoints and reproducibility evidence

Run directory: `data/interim/c2_pu/fr4_curriculum_runs/fr4_curriculum_fold0__20261015T103556Z`

| Stage | Best checkpoint SHA-256 | Last checkpoint SHA-256 |
|---|---|---|
| C1 | `f566c06314e1b243124abf49e660b3979f3d086e51b19ad9f2d1b0929494f7d4` | `2f9e50232fd752f98cd53b0cbb4e90c198500f32341d2aced1afdcaee0591ecd` |
| C2 | `d5ccb8712d93876a0d7e67f43e8758761fcc4c921ac3823c3d574afaba6afd44` | `326b532ecb996be73d5787ce1a6483a563adc9370d796ced09cbce1fd0c628c3` |
| C3 | `f2775fa2855454098b58e35431a18cbb6081f9c777bd7880720bb25dfd715aa6` | `82f323d60011ef5605b5e5be4da066e0f7013fb8c6b8a766801b24931e718118` |

Best checkpoints reload through the accepted compatibility loader. Stage 2's recorded parent hash equals the Stage-1 best hash, and Stage 3's parent equals the Stage-2 best hash. The final checkpoint produces finite scores in `[0,1]`.

The first attempted run was correctly recorded as failed when Windows transiently locked an atomic checkpoint destination during Stage 2. A curriculum-local bounded retry around the existing atomic recorder was added; scientific settings were unchanged. The successful run used a new collision-safe directory.

## Validation and artifact integrity

The focused curriculum/evaluation/corrective checks first passed 13 tests. A broader relevant regression
run covering curriculum training, baseline evaluation, corrective and direct nnPU, experiment data,
models, the run recorder, feature-cache handling, C3, and CLI help then passed **154 tests, 0 failed** in 5.60 s.
Pytest emitted one cache-write permission warning; it did not affect test collection or execution. The
expensive upstream curation and embedding acceptance jobs were not repeated. Task 4.5's most recent
full-suite evidence remains 650 passed, 2 skipped, with no unresolved failures.

The frozen and accepted artifacts retained these SHA-256 values after the run:

| Artifact | SHA-256 |
|---|---|
| PP1 `MANIFEST.json` | `88f14bb9ba99209a5482a08c2f82baa86434a4af1808f2e373e109efd74c27f2` |
| PP2 `MANIFEST.json` | `dbd8755a69b6f29655c03f5dfa6af5d22b72de32c0708b98c944e6541744e2b4` |
| FR3 feature-cache manifest | `81c87075eec8643a3643a3b726268e35569a1a1f00b15f457d87e1ef3268d97a` |
| Accepted corrective summary | `4d85b396311aa20ef37cde2118cdffa1fa5e25388b6d31dd9a60028cd9a11099` |
| Accepted Task 4.5 evaluation | `23f0b8dac7e794f6c9a5e4a678df6607b19b17c1d7fba51d0c93302fc307a458` |
| External-control diagnostic | `cb81054cbe807e19ce22f2f0857e1b7401d625b9611978f3763ad24d8ccfb5b7` |

Binary stage checkpoints remain under the gitignored run directory. The committed summary records their
paths, hashes, parent links, resolved configuration, data counts, and complete epoch histories.

## Limitations and recommendation

This is one fold, one seed, one prior, one fixed stage order, and no hyperparameter search. E2 remains provisional. The fixed C1 validation surrogate may be imperfect for selecting C2/C3 checkpoints because those pools have different source distributions. The curriculum's score changes on unlabeled pools are not false-positive measurements, and the 38 controls are small and assay-specific. Model scores remain uncalibrated.

Task 4.6 establishes the requested engineering prototype and stage provenance. It does not establish that curriculum training improves antioxidant reliability. Before FR6 or a final five-fold claim, the project should define a scientifically justified multi-fold evaluation with broader assay-matched controls and decide whether the fixed C1 surrogate is suitable for later-stage checkpoint selection. RNIS remains out of scope and was not implemented.

## Dated clarification — 15 October 2026

The subsequent [PP1 pre-freeze methodological audit](FR4_PP1_PRE_FREEZE_METHOD_AUDIT.md) verified that Stage C3's zero-based `best_epoch=0` is a **post-update** checkpoint. Its 63 C3 optimizer updates completed before validation and best-checkpoint saving; all six parameter tensors differ from the Stage-C2 parent. The Stage-C1 best checkpoint is the matched evidence-weighted C1-only reference for the C2/C3 sequence. The historical stand-alone corrective baseline above remains useful context but uses unweighted E1/E2 positives and a different patience setting, so it is not a controlled curriculum comparator. This clarification does not alter any Task 4.6 result or artifact.
