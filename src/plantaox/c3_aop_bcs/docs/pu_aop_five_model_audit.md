# Component 2 PU-AOP Five-Model Audit

**Audit date:** 2026-10-19

**Scope:** Read-only inspection of Component 2; this report and its JSON evidence are owned by Component 3.

**Decision:** Not ready for verified C3 scoring. Component 2 documents five technically accepted fold-0 configurations, but none is integrated in C3.

## Model-by-model result

| ID | Model | Native output | Checkpoint here | MCC | AUROC | C3 status |
|---|---|---|---:|---:|---:|---|
| M1 | PN | sigmoid probability-like output from the single logit | no | -0.183 | 0.254 | not_integrated |
| M2 | Direct-clamped nnPU | sigmoid probability-like output from the single logit | no | -0.044 | 0.324 | not_integrated |
| M3 | Corrective nnPU | sigmoid probability-like output from the single logit | no | -0.250 | 0.322 | not_integrated |
| M4 | Two-Step PU | Elkan-Noto corrected class-1 score; finite values can exceed 1 | no | -0.169 | 0.282 | not_integrated |
| M5 | PU-Bagging | class-1 predict_proba output | no | -0.250 | 0.301 | not_integrated |

The metrics above use the common fold-0 assay-supported comparison of 124 held-out positives and 38 assay-inactive controls at threshold 0.5. All five MCC values are negative and all five AUROC values are below 0.5. This is a scientifically important limitation; technical acceptance is not evidence of reliable antioxidant discrimination.

C1, C2, and C3 are unlabeled assumption pools. Any metrics that temporarily assign them a negative label are proxy diagnostics only and must not be described as confirmed-negative performance.

## What is already documented

- All models use fold 0 and the 495-dimensional `fusion_v1` representation.
- Feature order is 480 mean-pooled ESM-2 values followed by the 15 frozen descriptors.
- The ESM model is `esm2_t12_35M_UR50D`, layer 12; BOS, EOS, and padding are excluded from mean pooling.
- Fold-0 scaler parameters and descriptor/fusion schemas are present and checksum-pinned.
- Higher scores mean stronger support for the positive/AOP class; the evaluation threshold is 0.5.
- M1-M3 return sigmoid outputs; M5 returns bounded class-1 `predict_proba` output.
- M4 returns an Elkan-Noto-corrected raw score that can exceed 1; its clipped copy is used only for threshold and Brier calculations.

## Missing or unresolved information

- **C2-HANDOFF-01 (blocking; M1, M2, M3, M4, M5):** The five checkpoint binaries are absent from the current checkout Required resolution: Provide the exact checkpoint files and verify each against the frozen SHA-256
- **C2-HANDOFF-02 (blocking; M1, M2, M3, M4, M5):** No per-model reference fixture gives a peptide, expected native score, and numerical tolerance Required resolution: Export at least one independently generated reference score for every accepted model
- **C2-HANDOFF-03 (blocking_for_new_sequence_features; M1, M2, M3, M4, M5):** fair-esm is not declared in requirements.txt and is not installed in the current project environment Required resolution: Freeze the fair-esm package/version and make the ESM-2 model weights available reproducibly
- **C2-HANDOFF-04 (high; M1, M2, M3, M4, M5):** The pretrained ESM-2 weight identity/hash and portable cache provenance are not included in the freeze manifest Required resolution: Record the exact pretrained weight artifact identity, retrieval method, and checksum
- **C2-HANDOFF-05 (high; M5):** PU-Bagging estimator count conflicts across accepted run evidence and planning/status documentation Required resolution: Component 2 must confirm that the frozen M5 checkpoint is the 10-estimator run or replace/correct the handoff evidence
- **C2-HANDOFF-06 (high; M1, M2, M3, M4, M5):** There is no frozen, read-only sequence-to-five-scores inference entry point Required resolution: Provide or approve a wrapper that performs validation, feature extraction, fold-0 scaling, model loading, and native-score output
- **C2-HANDOFF-07 (decision_required; M1, M2, M3, M4, M5):** No model is designated as the single PU-AOP handoff model, and no naming policy says whether all five should be exposed separately Required resolution: Choose one model or approve five separately named predictor configurations
- **C2-HANDOFF-08 (high; M1, M2, M3, M4, M5):** A formal batch-size, per-sequence failure, and resource policy is not frozen Required resolution: Document batch behavior, CPU/GPU expectations, invalid-input handling, and partial-failure behavior
- **C2-HANDOFF-09 (decision_required; M1, M2, M3, M4, M5):** Internal project use, redistribution, and publication authorization for model and ESM-2 artifacts is not recorded Required resolution: Record the permitted C3/PP1 use and artifact-sharing boundary
- **C2-HANDOFF-10 (scientific_limitation; M1, M2, M3, M4, M5):** Reliable biological discrimination, calibration, and five-fold validation have not been established Required resolution: Retain the fold-0/technical-baseline label; do not claim validated AOP probability or superiority

## Artifact availability finding

The freeze inventory says the checkpoint and cache artifacts were available locally in the freeze author's environment, but all five recorded checkpoint paths and `fr3_fold0_scaled_features.npz` are absent from this checkout. The documented backup path belongs to `C:/Users/metal/...` and does not exist on the current machine. The small descriptor-only prototype artifact is explicitly marked as prototype mode and is not a substitute for any accepted model.

## PU-Bagging contradiction

The accepted M5 run summary records `n_estimators=10` and `max_samples=1.0`. Component 2's implementation-status decision log and PP1 planner state `n_estimators=100`. Until Component 2 confirms which setting belongs to the frozen checkpoint, the run summary and checkpoint hash must be treated as the closest evidence, but M5 cannot pass the handoff gate.

## Minimum handoff needed by C3

- All selected checkpoint bytes are present and hash-verified
- The exact feature-extraction environment and ESM-2 weights are reproducible
- Each selected model reproduces its independent reference score within tolerance
- The PU-Bagging estimator-count contradiction is resolved
- The model-selection/naming and use-authorization decisions are recorded

After these conditions are met, C3 can wrap each approved configuration behind the Task 3.19 predictor interface, reproduce its reference score, and only then change its status from `not_integrated`.
