# FR4 Task 4.5 Follow-Up — External-Control Diagnostic

**Conclusion:** No blocking implementation, label-orientation, or feature-row alignment defect was identified. The unexpectedly poor assay-control ranking is broad across the 38 controls and is consistent with source/assay and descriptor-distribution mismatch, although the available data cannot establish a causal explanation.

## Checks performed

- Loaded the same five accepted best checkpoints used in Task 4.5 and reproduced the recorded MCC/AUROC values without training or threshold changes.
- Verified that every prediction interface returns class-1 support: higher values mean stronger model support for positive/AOP status. For sklearn models, the probability-column order is `[0, 1]`; BinaryMlp scores are sigmoid outputs for its positive logit.
- Verified labels: 124 GraphPart-held-out positives are `1`; 38 assay-inactive controls are `0` under their recorded assay definitions.
- Verified exact peptide-ID/sequence correspondence among the fold-0 feature rows, FR3 descriptor table, and external-control metadata. No missing, duplicated, or reordered sequence was found.
- Retained all controls, including the two BIOPEP-UWM conflicts. No threshold was optimized and no score was reversed.

## Score pattern

| Model | Held-out E1 median | Held-out E2 median | Control median | Control mean | Primary AUROC |
|---|---:|---:|---:|---:|---:|
| PN | 0.9773 | 0.8148 | 0.9925 | 0.9560 | 0.2541 |
| Direct-clamped nnPU | 1.0000 | 0.9999 | 1.0000 | 0.9999 | 0.3235 |
| Corrective nnPU | 0.6329 | 0.4768 | 0.7023 | 0.6583 | 0.3224 |
| Two-Step PU (bounded) | 1.0000 | 0.9640 | 1.0000 | 0.9508 | 0.2818 |
| PU-Bagging | 0.9504 | 0.7284 | 0.9878 | 0.8966 | 0.3005 |

The issue is not driven by one or two controls. Thirty-two of 38 controls score above 0.5 under all five models, and 36 score above 0.5 under at least four. Removing any one control changes AUROC by at most 0.014–0.017 across models; no leave-one-control-out result approaches 0.5. Several very short controls (`RWF`, `RWS`, `RWM`, `LWL`, `RWV`, `RWK`) rank above most held-out positives under every model.

The 36-control sensitivity analysis that excludes `AOP-37BD4B4933` (`FCM`) and `AOP-DDCD54E4BA` (`YPQLLPNE`) also retains negative MCC and sub-0.5 AUROC. Those annotation conflicts therefore do not explain the primary result.

## Descriptor and provenance differences

| Group | n | Length mean / median | Molecular weight mean | Charge mean | Aromaticity mean | GRAVY mean | Hydrophobic moment mean | Proline fraction mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Held-out E1 | 59 | 6.24 / 5.0 | 716.45 | -0.582 | 0.150 | -0.193 | 0.364 | 0.065 |
| Held-out E2 | 65 | 8.29 / 8.0 | 928.64 | 0.004 | 0.119 | -0.269 | 0.338 | 0.083 |
| External controls | 38 | 4.79 / 3.5 | 587.55 | 0.211 | 0.190 | -0.281 | 0.481 | 0.093 |

The controls are shorter and lighter than both positive tiers and have higher mean aromaticity and hydrophobic moment. They come from 11 publications and assay contexts recorded only through source DOI and AnOxPePred inactive status. These differences support the existing shortcut/source-mismatch concern: models may score motifs or physicochemical patterns that are common in assay-inactive controls but correlated with positive training sources. They do not prove that any one descriptor causes the ranking failure.

## Interpretation and unresolved questions

The result appears to be a real limitation of the present model/data/evaluation combination rather than a score-direction or alignment bug. “Inactive” is assay-specific; it does not mean universally non-antioxidant across mechanisms or protocols. Conversely, the controls cannot be relabeled positive merely because models score them highly. The available metadata does not provide harmonized assay conditions, concentration, substrate, or mechanism labels needed to separate assay mismatch from source shortcuts.

The diagnostic remains limited to 38 controls and one fold. A stronger scientific evaluation needs more assay-matched inactive controls and multi-fold models, with assay provenance retained. The external controls must remain evaluation-only and must not guide curriculum checkpoint selection.

Machine-readable evidence is stored in `fr4_external_control_diagnostic.json` and `fr4_external_control_scores.csv`. The accepted Task 4.5 artifacts and checkpoints were read-only throughout this diagnostic.
