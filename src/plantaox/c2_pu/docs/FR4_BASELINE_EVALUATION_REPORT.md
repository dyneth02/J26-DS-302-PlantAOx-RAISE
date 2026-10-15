# FR4 Task 4.5 — Initial Baseline Evaluation (Fold 0)

**Status:** PASS (technical acceptance)  
**Executed:** 2026-10-15  
**Scope:** Inference-only evaluation of five accepted fold-0 configurations; no retraining, calibration, threshold selection, or curriculum training.

## Purpose and protocol

Task 4.5 compares the existing PN, direct-clamped nnPU, corrective nnPU, Two-Step PU, and PU-Bagging checkpoints under one leakage-safe fold-0 protocol. All models used the accepted 495-dimensional fold-scaled fused features and the same evaluation rows. Their training policies were intentionally not homogenized after the fact: PN used E1 positives and treated C1 as assumed negative, while the four PU configurations used E1+E2 positives and C1 as unlabeled. The neural and logistic-regression architectures also differ.

The primary assay-supported view combines 124 GraphPart-held-out positives (label 1) with 38 AnOxPePred assay-inactive controls (label 0 under their recorded FRS/Chelator assay definitions). Threshold metrics use the fixed threshold 0.5. Average precision (AP) and AUROC use raw finite scores. The control set is small and does not establish universal non-antioxidant status. `AOP-37BD4B4933` (`FCM`) and `AOP-DDCD54E4BA` (`YPQLLPNE`) retain their BIOPEP-UWM conflict flags; a 36-control sensitivity result is stored in the JSON output.

C1 (3,788), C2 (2,000), and fold-0 C3 (2,000) remain unlabeled challenge pools. Their descriptive scores are not errors or confirmed negative outcomes. The separately named proxy metrics provisionally assign challenge rows label 0 and are suitable only for engineering comparison.

## Model provenance

| ID | Configuration | Architecture | Positive training evidence | C1 policy | Prior |
|---|---|---|---|---|---:|
| M1 | PN | BinaryMlp 495→128→64→1 | E1 | assumed negative | N/A |
| M2 | Direct-clamped nnPU | BinaryMlp 495→128→64→1 | E1+E2 | unlabeled | 0.10 |
| M3 | Corrective nnPU (β=0, γ=1) | BinaryMlp 495→128→64→1 | E1+E2 | unlabeled | 0.10 |
| M4 | Two-Step PU | pulearn + LogisticRegression | E1+E2 | unlabeled | N/A |
| M5 | PU-Bagging | pulearn + LogisticRegression | E1+E2 | unlabeled | N/A |

The exact checkpoint paths and SHA-256 values are in `fr4_baseline_model_provenance.json`. Each hash was checked before inference. Two-Step PU's Elkan–Noto corrected score is retained raw for ranking metrics and separately clipped to `[0,1]` for threshold and Brier calculations. Across all evaluated pools, 6.35% of its raw corrected scores exceeded 1; clipping was explicit and recorded.

## Primary assay-supported results

| Model | MCC | AP | AUROC | Precision | Recall | F1 | Balanced accuracy | TP / TN / FP / FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PN | -0.1833 | 0.6392 | 0.2541 | 0.7397 | 0.8710 | 0.8000 | 0.4355 | 108 / 0 / 38 / 16 |
| Direct-clamped nnPU | -0.0436 | 0.6915 | 0.3235 | 0.7640 | 0.9919 | 0.8632 | 0.4960 | 123 / 0 / 38 / 1 |
| Corrective nnPU | -0.2498 | 0.6827 | 0.3224 | 0.6832 | 0.5565 | 0.6133 | 0.3572 | 69 / 6 / 32 / 55 |
| Two-Step PU | -0.1694 | 0.6466 | 0.2818 | 0.7333 | 0.7984 | 0.7645 | 0.4255 | 99 / 2 / 36 / 25 |
| PU-Bagging | -0.2495 | 0.6567 | 0.3005 | 0.7109 | 0.7339 | 0.7222 | 0.3801 | 91 / 1 / 37 / 33 |

All five MCC values are negative and all AUROCs are below 0.5. At threshold 0.5, PN and direct-clamped nnPU rejected none of the 38 controls; the other models rejected only 1–6 controls. Excluding the two disputed controls did not reverse the finding: MCC remained negative for every model (`-0.1796`, `-0.0427`, `-0.2381`, `-0.1628`, `-0.2433` for M1–M5). The controls often received higher scores than held-out positives, consistent with strong source-distribution or assay/domain mismatch. These values do not establish a ranking of biological performance.

## Positive recovery

| Model | Overall median | Overall >0.5 | E1 >0.5 | E2 >0.5 | Fraction >0.99 |
|---|---:|---:|---:|---:|---:|
| PN | 0.9017 | 87.10% | 96.61% | 78.46% | 29.03% |
| Direct-clamped nnPU | 1.0000 | 99.19% | 98.31% | 100.00% | 95.16% |
| Corrective nnPU | 0.5260 | 55.65% | 67.80% | 44.62% | 0.00% |
| Two-Step PU (bounded) | 1.0000 | 79.84% | 93.22% | 67.69% | 58.06% |
| PU-Bagging | 0.8718 | 73.39% | 88.14% | 60.00% | 24.19% |

This is recall on known positives, not accuracy. E1 recovery exceeds E2 recovery for four configurations; direct-clamped nnPU is saturated on both tiers. Two-Step PU's raw held-out median is 1.1752 and maximum is 1.4114, confirming why raw and bounded forms must remain distinct.

## Unlabeled challenge behavior

The table reports bounded score summaries. Raw Two-Step summaries and full proxy MCC/AP/AUROC results are retained in the JSON and CSV outputs.

| Model | Pool | Mean | Median | >0.5 | <0.01 | >0.99 |
|---|---|---:|---:|---:|---:|---:|
| PN | C1 | 0.0735 | 0.0002 | 6.10% | 72.94% | 0.13% |
| PN | C2 | 0.3314 | 0.1645 | 32.65% | 26.35% | 4.45% |
| PN | C3 | 0.1352 | 0.0462 | 8.25% | 23.00% | 0.00% |
| Direct-clamped nnPU | C1 | 0.3571 | 0.0397 | 35.08% | 36.11% | 15.81% |
| Direct-clamped nnPU | C2 | 0.7983 | 0.9881 | 80.60% | 2.00% | 48.65% |
| Direct-clamped nnPU | C3 | 0.8959 | 0.9713 | 94.70% | 0.00% | 28.40% |
| Corrective nnPU | C1 | 0.0800 | 0.0170 | 1.40% | 39.94% | 0.00% |
| Corrective nnPU | C2 | 0.2433 | 0.1724 | 14.40% | 4.45% | 0.00% |
| Corrective nnPU | C3 | 0.1924 | 0.1678 | 1.15% | 0.00% | 0.00% |
| Two-Step PU | C1 | 0.0474 | 0.0000 | 3.30% | 80.91% | 0.82% |
| Two-Step PU | C2 | 0.2925 | 0.0357 | 27.20% | 42.60% | 17.10% |
| Two-Step PU | C3 | 0.0796 | 0.0107 | 4.55% | 49.10% | 1.65% |
| PU-Bagging | C1 | 0.0439 | 0.0000 | 2.61% | 80.04% | 0.05% |
| PU-Bagging | C2 | 0.2785 | 0.0734 | 26.40% | 38.45% | 4.10% |
| PU-Bagging | C3 | 0.0745 | 0.0109 | 3.80% | 48.65% | 0.00% |

Direct-clamped nnPU behaves distinctly: it scores most C2 and C3 rows above 0.5 and shows strong saturation, matching the earlier observation that near-universal risk clamping reduced the unlabeled gradient. Corrective nnPU produces much less saturated outputs, consistent with C1-dependent corrective gradients, but the small assay-supported comparison does not show improved classification. C1/C2/C3 score differences may reflect pool construction and shortcut features rather than antioxidant activity.

## Visual summaries

- `fr4_baseline_mcc_fold0.svg`: assay-supported MCC only.
- `fr4_baseline_auprc_fold0.svg`: assay-supported average precision only.
- `fr4_baseline_challenge_scores_fold0.svg`: mean bounded scores on unlabeled C1/C2/fold-0 C3.

## Integrity and tests

The evaluation loaded every best checkpoint read-only, verified its SHA-256 against the accepted summary, and performed no fit or scaler operation. Dataset assembly reported no ID/sequence overlap across training, validation, held-out-positive, challenge, and external-control subsets. Fold-0 C3 came through the existing fold-aware experiment-data path. Frozen manifest hashes recorded with the run are:

- `pp1_baseline_v1/MANIFEST.json`: `88f14bb9ba99209a5482a08c2f82baa86434a4af1808f2e373e109efd74c27f2`
- `pp2_baseline_v1/MANIFEST.json`: `dbd8755a69b6f29655c03f5dfa6af5d22b72de32c0708b98c944e6541744e2b4`
- FR3 feature-cache manifest: `81c87075eec8643a3643a3b726268e35569a1a1f00b15f457d87e1ef3268d97a`

Focused Task 4.5 checks passed: `pytest tests/c2_pu/test_baseline_evaluation.py -q` reported **5 passed** (metric reference case, raw/bounded handling, saturation summaries, five-checkpoint reload/inference, and real-output membership/count checks). The one full-suite invocation initially reported **644 passed, 2 skipped, 6 failed**; four failures were sandbox-denied WSL commands and two were fresh subprocesses launched from a temporary standalone interpreter without its dependency path. The two subprocess checks passed on correction (`2 passed`) and the four identical WSL checks passed with approved access (`4 passed in 799.60s`). The effective verified result is **650 passed, 2 skipped, 0 unresolved failures**. All tracked historical outputs regenerated by acceptance tests were restored.

## Scientific limitations and conclusion

This is one fold and only 38 assay-inactive controls, including two disputed annotations. The inactive labels are assay-specific. C1/C2/C3 are unlabeled and cannot support confirmed specificity estimates. PN and PU models differ in evidence policy; MLP and LogisticRegression models differ in architecture. The nnPU prior is provisional, direct nnPU remains strongly clamped, and corrective nnPU follows a distinct optimization rule. Positive and challenge sources have known distribution differences and shortcut-bias risk. Scores are not calibrated biological probabilities.

Task 4.5 demonstrates reproducible loading, stable inference, explicit metric semantics, and a common comparison protocol. It does not demonstrate experimentally validated antioxidant classification or scientific superiority of any baseline. The technical task passes. Task 4.6 may proceed as an engineering prototype, but these weak external-control results should remain prominent and no curriculum result should be presented as resolving biological generalization without broader assay-matched controls and multi-fold evaluation.
