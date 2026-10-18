# Score Normalization Contract (Task 3.24)

**Schema:** `c3_aop_bcs_score_normalization_v1`  
**Created:** `2026-10-19`  
**Usable score range:** `[0,1]` with higher values meaning stronger AOP support.

Native scores are always retained. Every mapping is fixed and pointwise: the same native value produces the same usable value regardless of batch composition. Batch-wise min-max scaling is prohibited.

| Score contract | Native range | Mapping | Native retained unchanged | Status | Experimental use |
|---|---:|---|---:|---|---:|
| AnOxPePred FRS (`anoxpepred_frs`) | [0.0, 1.0] | `identity_0_1` | true | `documented_pending_real_score` | false |
| AnOxPePred Chelator (`anoxpepred_chelator`) | [0.0, 1.0] | `identity_0_1` | true | `documented_pending_real_score` | false |
| Multi-AOP antioxidant-class score (`multi_aop_probability`) | [0.0, 1.0] | `identity_0_1` | true | `documented_pending_real_score` | false |
| AOPxSVM positive-class probability (`aopxsvm_positive_probability`) | [0.0, 1.0] | `identity_0_1` | true | `documented_pending_real_score` | false |
| AOP-DRL prediction probability (`aop_drl_probability`) | [0.0, 1.0] | `identity_0_1` | true | `unavailable_pending_model_or_service` | false |
| PU-AOP M1 PN (`pu_aop_m1_pn`) | [0.0, 1.0] | `identity_0_1` | true | `documented_pending_component_2_handoff` | false |
| PU-AOP M2 Direct-clamped nnPU (`pu_aop_m2_direct_nnpu`) | [0.0, 1.0] | `identity_0_1` | true | `documented_pending_component_2_handoff` | false |
| PU-AOP M3 Corrective nnPU (`pu_aop_m3_corrective_nnpu`) | [0.0, 1.0] | `identity_0_1` | true | `documented_pending_component_2_handoff` | false |
| PU-AOP M4 Two-Step PU (`pu_aop_m4_two_step_raw`) | [0.0, unbounded] | `clip_0_1` | false | `documented_pending_component_2_handoff` | false |
| PU-AOP M5 PU-Bagging (`pu_aop_m5_bagging`) | [0.0, 1.0] | `identity_0_1` | true | `documented_pending_component_2_handoff` | false |
| C3 software smoke-test dummy (`c3_dummy_smoke_score`) | [0.0, 1.0] | `identity_0_1` | true | `verified_software_smoke_only` | false |

## Operational validation

The current validation status is `PASS_FOR_SOFTWARE_PREPARATION_REAL_PREDICTORS_PENDING`. The full dummy smoke dataset supplied 20,072 original/perturbed score values across 10,036 perturbation rows. Its native and usable ranges were both `0.075` to `1.0`, with zero out-of-range or transformed values.

This confirms the normalization software and `[0,1]` enforcement, not a scientific predictor. Every real predictor remains pending until a real C3 score is retained and checked against its contract.

## Predictor-specific decisions

- AnOxPePred's FRS and Chelator sigmoid channels remain separate; C3 must prespecify the scalar endpoint rather than silently averaging them.
- Multi-AOP, AOPxSVM, AOP-DRL, PU-AOP M1-M3, and PU-AOP M5 use identity mappings when their documented `[0,1]` outputs are eventually verified.
- PU-AOP M4 retains its raw Elkan-Noto corrected score and creates a separate fixed `clip(raw, 0, 1)` usable value. No batch-derived mapping is permitted.
- The dummy mapping is verified for software testing only and remains prohibited from experimental results.
