# PP1 pre-freeze methodological audit — Component 02

**Date:** 15 October 2026  
**Decision:** **READY WITH LIMITATIONS** for a technical PP1 presentation. This is not evidence of validated antioxidant classification or scientific sign-off.

## Scope and preservation

This audit followed Task 4.6 to resolve the meaning of its Stage-C3 `best_epoch=0`, identify a matched evidence-weighted C1 reference, check the weighted corrective-nnPU objective, and verify stage lineage and validation. It read the accepted fold-0 run and checkpoints. It performed no training, threshold selection, dataset change, or scaler fit. The accepted Task 4.5/4.6 summaries and checkpoint files remain the historical record.

The source for the matched table is `data/processed/c2_pu/fr4_curriculum_fold0_summary.json` (SHA-256 `cc1e0833df9a85f67aa0a2f46aa5d789d0e40470b67f5cf9a56cb804958c4ddf`). The derived, three-row table is `data/processed/c2_pu/fr4_pp1_matched_curriculum_fold0.csv` (SHA-256 `7deb35413f90e941474b4e920038c602b065e58b420e2a2f4d99d4543800b89b`); its companion figure is `fr4_pp1_matched_curriculum_fold0.svg` (SHA-256 `b86dc2af4ad2d7af190a8b4ff63b0b41bf43ac508c00880b16dd84755d490eee`). The table records the source summary hash and each stage's best-checkpoint hash. No checkpoint is duplicated under the comparison alias.

## Stage C3 epoch 0: post-update checkpoint

The curriculum loop numbers each stage's epochs from zero. It does **not** evaluate or save the incoming model before optimization. In C3 epoch 0, it shuffled the fold-0 C3 rows, executed **63 optimizer updates** (`ceil(2,000/32)`), then evaluated the fixed validation set and saved the best checkpoint. Its global epoch was 23. The C3 best-checkpoint payload records epoch 0 and the same validation risk as the first stage-history and JSONL records: **0.06765890121459961**. The checkpoint's SHA-256 matches the accepted summary (`f2775fa2855454098b58e35431a18cbb6081f9c777bd7880720bb25dfd715aa6`).

All six saved parameter tensors differ from the Stage-C2 selected parent; the largest absolute element difference is **0.0307472**. The C3 checkpoint's recorded parent hash equals the actual Stage-C2 best-checkpoint hash (`d5ccb8712d93876a0d7e67f43e8758761fcc4c921ac3823c3d574afaba6afd44`). Thus the selected C3 model **does contain C3 training updates**. It is a **post-update checkpoint**, specifically after the first complete C3 epoch. Five later C3 epochs did not improve the fixed validation surrogate by the required `1e-4`; final validation risk was **0.2055795193** after six executed epochs. `best_epoch=0` does not mean an untrained C3 stage.

The stage histories, checkpoint payloads, and summary agree. The Task 4.6 report's phrase “first epoch” is correct but is explicitly clarified here as “after 63 C3 updates.”

## Matched weighted C1-only reference

The existing **Stage-C1 best checkpoint** satisfies the matched reference conditions and is designated **`weighted_c1_only_curriculum_reference`** for PP1 comparison. This is a metadata/comparison label for the same file, not a new trained model. Its best-checkpoint SHA-256 is `f566c06314e1b243124abf49e660b3979f3d086e51b19ad9f2d1b0929494f7d4` (zero-based best epoch 3, after 404 C1 optimizer updates).

Stage C1 starts with a newly constructed `BinaryMlp` after the recorded seed 42 is set. It uses the same 604 E1+E2 training positives (331 E1, 273 E2), E1/E2 weights 1.0/0.5, 3,220 C1 training rows, fold-0 scaled 495-dimensional features, corrective nnPU at π=0.10/β=0/γ=1, Adam at 0.001 with weight decay 0.0, group batch size 32, and the same fixed weighted validation surrogate and five-epoch plateau rule that govern later stages. The Stage-C1 selected checkpoint is the incoming model for Stage C2. It is therefore the matched **starting condition for the observed C2/C3 curriculum sequence**. No redundant C1-only run was needed.

The accepted stand-alone corrective-nnPU baseline used **unweighted** E1+E2 evidence and patience 10. It is historical context, not a controlled comparator for the weighted curriculum. The matched C1 checkpoint is one run within the sequential experiment, not an independent replicate or an estimate of run-to-run variation.

## Weighted nnPU mathematics

The implemented per-group risk uses stable `softplus` on logits. For positive weights `w`, it calculates both `R⁺P,w = Σw·softplus(−fP)/Σw` and `R⁻P,w = Σw·softplus(fP)/Σw`; the unlabeled term is the separate mean `R⁻U = mean(softplus(fU))`. It then calculates `r = R⁻U − πR⁻P,w`. The reported/validation surrogate is `πR⁺P,w + max(0,r)`. The optimizer minimizes `πR⁺P,w + r` when `r ≥ −β`, and `−γr` otherwise. The prior appears once in each positive contribution. The branch-specific optimizer loss and reported nonnegative risk are separate values.

`_positive_weights` assigns exactly 1.0 to E1 and 0.5 to E2 and rejects unsupported tiers. The shared nnPU dataset assembly selects E1/E2 explicitly, excluding E3. The same weight conversion and risk function are applied to the fixed 106 positive validation rows (48 E1, 58 E2), along with 568 C1 validation rows. Tests using independent float64 reference arithmetic cover both branches, component values, prior placement, the unlabeled gradient sign, evidence weights, and finite gradients. The existing risk calculation returns an error on non-finite results and the training loop checks gradients. **No material risk-estimator defect was found.** Mini-batch positive expectations normalize by the weights present in that batch; validation uses the whole validation group.

## Stage lineage and data boundary

The accepted run manifest is `completed`, with fold 0, seed 42, fused 495-dimensional features, and git revision `72feafb69602d1e91040dbcb4ce8ae3d50ef62cb`. A fresh model is constructed once for C1. Model weights are loaded from each preceding stage's selected best checkpoint before the next stage, while a new Adam optimizer is created at every stage. All three stages have distinct best/last checkpoints. The parent hashes in their summaries and checkpoint payloads match the actual source files. Every best checkpoint reloads, and recalculating its weighted full-validation risk gives **exactly** the recorded selection value.

The reconstructed training membership is C1=3,220; C2=2,000; and C3=2,000 for fold 0. C3 IDs match `curation.c3.load_fold_challenges(ranking_path, 0)` in order. The feature loader verified the fold-0 cache against its manifest and used its existing scaler. The 604 training positives, 106 validation positives, and 568 C1 validation rows remain fixed at all stages. The shared cross-subset ID/sequence leakage report found no overlap with GraphPart-held-out positives or the external controls.

The accepted summary stores counts and deterministic source/configuration provenance, but not a separate per-stage list of every training ID. Membership was therefore reconstructed from the frozen sources and accepted split seeds, then checked against the loader and fold-specific C3 accessor; the historical run's individual sample-order sequence cannot be independently recovered from a checkpoint alone. This does not affect the checkpoint or risk checks above.

The validation unlabeled distribution stays **C1 even during C2 and C3 training**. This was the pre-specified surrogate checkpoint criterion, not a ground-truth measure of C2/C3 classification. Held-out positives and 38 assay-inactive controls were scored only after **each stage's own** best checkpoint had been selected; those scores did not enter gradients, stopping, transitions, or parameter choice. Consequently, Stage-C1 evaluation happened before later stages finished, although no evaluation result was used to alter later training. A later study should evaluate alternative checkpoint criteria without revising this accepted run.

## PP1 matched stage comparison

All score fractions below use the same fold-0 evaluation membership and fixed 0.5 threshold. “Positive recovery” is recall on 124 known held-out positives. C1/C2/C3 are **unlabeled**, so their fractions are descriptive scores, not confirmed false-positive rates. The weighted validation risks are a surrogate under the assumed π and fixed C1 validation distribution.

| Condition | Epochs | Best epoch | Weighted validation risk | Positive recovery | C1 >0.5 | C2 >0.5 | C3 >0.5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Weighted C1-only reference** | 9 | 3 | 0.0614415 | 59.68% | 2.22% | 13.05% | 0.50% |
| After C2 | 14 | 8 | 0.0766366 | 38.71% | 2.35% | 3.30% | 0.60% |
| After C3 | 6 | 0 | 0.0676589 | 67.74% | 4.65% | 12.20% | 0.60% |

Read-only evaluation against the same 124 held-out positives and 38 assay-inactive controls:

| Condition | MCC | AP | AUROC | Recall | TP / TN / FP / FN |
|---|---:|---:|---:|---:|---:|
| Weighted C1-only reference | −0.2929 | 0.6282 | 0.2334 | 0.5968 | 74 / 3 / 35 / 50 |
| After C2 | −0.1641 | 0.6600 | 0.3171 | 0.3871 | 48 / 16 / 22 / 76 |
| After C3 | −0.2338 | 0.6252 | 0.2381 | 0.6774 | 84 / 3 / 35 / 40 |

The historical unweighted corrective run had positive recovery 55.65%, C1/C2/C3 score fractions 1.40%/14.40%/1.15%, and external MCC/AP/AUROC −0.2498/0.6827/0.3224. Its validation risk is not directly comparable to the weighted risks above. Within the matched sequence, C2 lowered the C2 score fraction but also reduced positive recovery; C3 restored recovery while C1 and C2 score fractions rose. No stage separated these 38 controls reliably. Changes across stages include **both** further optimization and a changed unlabeled training population, so this single sequence cannot isolate a causal pool effect or establish improved calibration or biological reliability.

## Verification, integrity, and PP1 readiness

The focused regression command covering curriculum, nnPU risk/baseline, corrective optimization, experiment data, models, recorder, feature cache, C3, and baseline evaluation passed **160 tests, 0 failures**. It included new independent weighted-risk branch cases, E3 rejection, C3 epoch-0 tensor/step evidence, real fold membership, checkpoint reload, and table-to-source consistency. No real fold-0 model was retrained; the existing small synthetic curriculum smoke test ran. No upstream curation or embedding pipeline was rerun.

All 10 PP1 and 28 PP2 frozen-manifest files passed their recorded file checksums. Relevant SHA-256 values before and after this audit are:

| Accepted artifact | SHA-256 |
|---|---|
| PP1 `MANIFEST.json` | `88f14bb9ba99209a5482a08c2f82baa86434a4af1808f2e373e109efd74c27f2` |
| PP2 `MANIFEST.json` | `dbd8755a69b6f29655c03f5dfa6af5d22b72de32c0708b98c944e6541744e2b4` |
| FR3 cache manifest | `81c87075eec8643a3643a3b726268e35569a1a1f00b15f457d87e1ef3268d97a` |
| FR3 fold scaler | `83a414b29e1ba057e36a9de4fb1efb5858933ae2feb2c75713555fddcbb90169` |
| Accepted corrective summary | `4d85b396311aa20ef37cde2118cdffa1fa5e25388b6d31dd9a60028cd9a11099` |
| Accepted Task 4.5 evaluation | `23f0b8dac7e794f6c9a5e4a678df6607b19b17c1d7fba51d0c93302fc307a458` |
| Accepted Task 4.6 summary | `cc1e0833df9a85f67aa0a2f46aa5d789d0e40470b67f5cf9a56cb804958c4ddf` |

**READY WITH LIMITATIONS:** The curriculum is technically traceable and the matched stage comparison can be presented accurately. Scientific limitations remain substantial: π=0.10 is provisional rather than measured C1 prevalence; E2 positives are benchmark-annotated; positive and challenge pools differ by source; the C1-based validation surrogate may select C2/C3 checkpoints poorly; only one fold and seed were run; model scores are uncalibrated; and the 38 assay-specific controls show weak discrimination, with two annotation conflicts. PP1 material should frame these as preliminary technical results and retain the negative assay-control finding. Multi-fold evaluation, better assay-matched controls, and validation-policy study belong to later research work.
