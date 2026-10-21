# Scientific results: MCC improvement v1

The negative-MCC issue remains **unresolved** under the tested protocols: no selected method has consistently positive MCC across the 15 fold/seed runs. The isolated favorable PN run is not a successful method.

All new external results are **retrospective**, using the same 38 assay-inactive controls. They are not independently validated. Selection and thresholds were frozen using development data only.

## Matched historical membership: fold 0 / seed 42 / threshold .5

New training uses stricter GraphPart inner validation, training-only scaling, and bounded regularization. Accepted and new training recipes differ; this is not a one-variable historical comparison.

| Model | Original MCC | New MCC | AUROC | Sensitivity | Specificity | Status |
|---|---:|---:|---:|---:|---:|---|
| PN (fused) | -0.1833 | -0.1565 | 0.2542 | 0.8548 | 0.0263 | Unresolved on historical benchmark |
| Direct (esm) | -0.0436 | -0.0460 | 0.2498 | 0.9516 | 0.0263 | Unresolved on historical benchmark |
| Corrective (fused) | -0.2498 | -0.1635 | 0.2519 | 0.8468 | 0.0263 | Unresolved on historical benchmark |
| TwoStep (descriptors) | -0.1694 | -0.1566 | 0.2689 | 0.9032 | 0.0000 | Unresolved on historical benchmark |
| Bagging (esm) | -0.2495 | -0.2668 | 0.2653 | 0.6694 | 0.0526 | Unresolved on historical benchmark |

## Five folds x three seeds: selected representations

| Model | Mean MCC ± SD | Range | MCC >0 | AUROC mean | Recall mean | Specificity mean |
|---|---:|---|---:|---:|---:|---:|
| PN | -0.1659 ± 0.1205 | -0.3954 to 0.0622 | 1/15 | 0.3196 | 0.7317 | 0.0965 |
| Direct | -0.1294 ± 0.0773 | -0.2895 to -0.0460 | 0/15 | 0.2923 | 0.8599 | 0.0316 |
| Corrective | -0.2006 ± 0.1148 | -0.4081 to -0.0435 | 0/15 | 0.2873 | 0.6894 | 0.0860 |
| TwoStep | -0.2022 ± 0.1616 | -0.5130 to -0.0484 | 0/15 | 0.3018 | 0.7633 | 0.0298 |
| Bagging | -0.2555 ± 0.1761 | -0.5666 to -0.0484 | 0/15 | 0.2720 | 0.6589 | 0.0561 |

SD describes dependent runs; it is not a confidence interval. Controls repeat across all folds/seeds. Outer positive fold sizes differ (124/134/137/173/266), so mean fold metrics are not pooled metrics. Representation selection is fold-specific using its separate inner validation; no external labels were used.

## Corrections and interpretation

- Fresh scaling fits actual optimization positives only; separate GraphPart validation fold prevents inner homology mixing.
- Reuse cached raw ESM/descriptors with strict identity, pool, finite-value and membership checks.
- Existing training implementations, risk equations, checkpoint persistence and evidence-tier policies are retained.
- Capacity (32 hidden units), weight decay .001, lr .0003 and batch256 form a bounded compound regularization experiment.
- All five algorithms retrained; all representation candidates and prior/batch/recipe sensitivity runs remain in the ledger.
- Checkpoint hashes, scaler parameters/fit IDs, membership, seeds, runtime, code/input hashes and restored inference are recorded.

No negative label is manufactured. C1 validation AP is explicitly a proxy; PU validation risk relies on an unmeasured prior and representativeness assumptions. C2/C3 are descriptive challenge pools only. No curriculum is retrained: its C1-only selection limitation remains, and no reliable assay validation exists to select a better stage.

See THRESHOLD_INVESTIGATION.md, ROOT_CAUSE_DIAGNOSTIC.md, descriptor_shift_statistics.csv, all_evaluations.csv, conditional bootstrap intervals, matched sensitivity and provenance for detailed evidence.

## Feature and optimization findings

Across the five seed42 folds, every method/representation combination retains negative mean MCC and mean AUROC below .5. Removing either feature block does not resolve discrimination. Representation preferences differ across development folds. See feature_comparison_five_folds_seed42.csv.

Training histories and training_configuration_and_optimization.csv separate direct clamping from corrective branch frequency. Reduced saturation did not repair ranking; meaningful corrective gradients did not establish biological validity.

Corrective prior sensitivity, the batch32 comparator and historical-capacity recipe are retained in all_evaluations.csv. No prior is selected from these external results. The C1+C2 follow-up and matched C1-only fused comparator are reported separately in FOLLOWUP_UNLABELED_MIXTURE_REPORT.md; neither validation policy is chosen using external results.

## Limitations and next work

Biological generalization remains unproven even if a few MCC values are positive. Small, repeatedly inspected, assay-specific controls, incomplete assay metadata, E2 provisional annotation, source/family dependence, unmeasured class prior and C1 sampling mismatch limit conclusions. The pre-existing release-inventory mismatch is recorded separately; no checksum or accepted file was changed to hide it.

Acquire genuinely new assay-matched active/inactive peptides with concentration, mechanism, source publication and assay conditions. Screen sequence/homology overlap against every training source before freezing. Review the 179 historical annotation conflicts with the supervisor; do not silently relabel them. Use assay-specific endpoints and source-held-out validation where metadata permit. Only then estimate specificity, identify MCC-optimal thresholds, and claim independent improvement.
