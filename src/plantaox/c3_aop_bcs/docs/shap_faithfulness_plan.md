# SHAP-faithfulness preparation (Task 3.36)

**Schema:** `c3_aop_bcs_shap_faithfulness_v1`  
**PP1 scope:** schema and module boundary only; no SHAP experiment or scientific SHAP result is claimed.

## Record meaning

one record links one predictor's SHAP value at one redox residue to the matching P1 alanine-scan DeltaScore.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | fixed schema version |
| `sequence_id` | string | stable peptide identifier |
| `sequence` | string | uppercase original peptide sequence |
| `predictor_id` | string | common-interface predictor identifier |
| `predictor_version` | string | frozen predictor/model version |
| `residue_position` | integer | one-based P1 residue position |
| `residue` | string | original redox residue at residue_position |
| `p1_variant_id` | string | linked alanine-scan variant identifier |
| `shap_value` | number | signed per-residue KernelSHAP value |
| `absolute_shap_value` | number | abs(shap_value) |
| `p1_delta_score` | number | signed Score(original) - Score(P1 variant) |
| `absolute_p1_delta_score` | number | abs(p1_delta_score) |
| `kernel_shap_backend` | string | stable backend identifier |
| `kernel_shap_version` | string | backend/dependency version |
| `background_dataset_version` | string | frozen SHAP background version |
| `random_seed` | integer | seed used by explanation procedure |

## Planned comparison

The later analysis compares `|SHAP_i| vs |DeltaScore_i|` using Pearson correlation r at matched P1 redox-residue positions for each predictor. Signed SHAP and DeltaScore values remain available for directional interpretation.

## KernelSHAP boundary

`KernelShapRequest` carries sequence, predictor, background-version, and seed metadata. A future `KernelShapBackend` receives that request plus the Task 3.19 predictor interface and must return a `KernelShapExplanation` containing exactly one finite value per sequence position. `pair_kernel_shap_with_p1_deltas` performs the validated P1 join.

No concrete backend and no `shap` dependency are required for Task 3.36.

## Deferred after PP1 preparation

- select and freeze a scientifically justified KernelSHAP background
- implement and verify a concrete KernelSHAP backend
- run real integrated predictors
- calculate and statistically interpret faithfulness correlations
