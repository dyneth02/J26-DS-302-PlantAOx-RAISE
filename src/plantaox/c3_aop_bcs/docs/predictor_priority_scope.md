# PP1 Predictor Integration Scope (Task 3.21)

**Decision version:** `1.0`  
**Decision date:** `2026-10-19`  
**PP1 floor:** At least one primary predictor must produce retained real scores through the C3 interface; otherwise PP1 may demonstrate only the software pipeline and must not claim a predictor audit.  
**PP1 comparison target:** Integrate at least two primary predictors if both pass environment reproduction, score-semantic review, and a retained real-score smoke test before the PP1 cutoff.

| Order | Predictor | Tier | Readiness | Current integration | Rationale |
|---:|---|---|---|---|---|
| 1 | AOPxSVM | primary | best_first-integration_candidate | not_integrated | The public repository bundles the SVM, scaler, selected-feature table, and inference code; it exposes one unambiguous positive-class probability and has a reachable web form. Its main risk is reproducing the legacy Python 3.7/scikit-learn 1.0.2 joblib environment. |
| 2 | AnOxPePred | primary | model-available_semantics-decision-needed | not_integrated | Public source and TensorFlow checkpoint files are available and the DTU service is reachable, but the legacy TensorFlow environment must be reproduced and the two-output FRS/Chelator model requires a frozen scalar-score choice for C3. |
| 3 | PU-AOP (Component 2) | primary | conditional_on_frozen_handoff | not_integrated | PU-AOP is scientifically central to the project and local source/manifests exist, but Component 2 must select the frozen model and provide the ignored checkpoint, compatible feature resources, runtime contract, and reference score before C3 integration. |
| 4 | Multi-AOP | secondary | deferred_environment-and-licence-risk | not_integrated | Code and checkpoints exist, but the PyTorch Geometric/RDKit/xLSTM environment, hard-coded paths, 2-30 versus 50-residue behavior, and missing repository licence create more PP1 risk than the primary candidates. |
| 5 | AOP-DRL | secondary | blocked_missing-inference-assets | not_integrated | The public repository lacks a trained checkpoint and complete inference package, the published endpoint is not serving AOP-DRL, and the stated non-commercial restriction requires clarification. |

## Scope rules

- If only one real predictor is ready, label the result a single-predictor pilot and do not present cross-predictor conclusions.
- Do not spend PP1 critical-path time on Multi-AOP or AOP-DRL unless the primary path is blocked and the secondary candidate first becomes fully reproducible and licence-compatible.
- A predictor remains not_integrated until its adapter produces a finite real score and the sequence, predictor version, score, runtime, and artifact hashes are retained.
- The Task 3.22 dummy predictor is software-test-only and cannot satisfy the real-predictor floor.

## Unresolved access issues

| Issue | Predictor | Severity | Status | Exit criterion |
|---|---|---|---|---|
| AOPX-ENV-001 | AOPxSVM | high | open | A pinned environment loads the scaler and model and reproduces one retained finite positive-class probability. |
| AOPX-LIC-001 | AOPxSVM | medium | open | Permitted research use is documented or supervisor approval records the accepted limitation. |
| ANOX-SEM-001 | AnOxPePred | high | open | The protocol identifies FRS, Chelator, or a prespecified combination before any experimental scores are generated. |
| ANOX-ENV-001 | AnOxPePred | high | open | Local or controlled-service inference returns and retains one versioned finite score. |
| PU-HANDOFF-001 | PU-AOP (Component 2) | blocking | open | Every required PU-AOP handoff item is verified_for_handoff and the reference score reproduces through C3. |
| MULTI-ENV-001 | Multi-AOP | medium | deferred | A pinned, licensed environment produces a retained real score with frozen input semantics. |
| DRL-ASSET-001 | AOP-DRL | blocking | deferred | A permitted checkpoint plus complete inference procedure or restored service produces a retained real score. |
