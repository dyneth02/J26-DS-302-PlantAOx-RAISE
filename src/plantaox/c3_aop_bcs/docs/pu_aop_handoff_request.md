# PU-AOP Frozen-Model Handoff Request

**From:** Component 3 (AOP-BCS)  
**To:** Component 2 (PU-AOP)  
**Status:** `request_prepared_handoff_pending`  
**Ready for C3 integration:** `false`

This checklist coordinates the frozen-model handoff without implying that PU-AOP is integrated. Component 3 will change that status only after every required item is verified and a retained reference sequence produces the supplied score through the C3 interface.

| Requirement | Required | Current status | Evidence/expected content |
|---|---|---|---|
| frozen_model_selection | true | decision_required_from_component_2 | Identify exactly one frozen PU-AOP model/version for the audit; the existing freeze manifest contains five baseline models and a three-stage curriculum, so C3 will not guess. |
| checkpoint_binary | true | missing_from_current_checkout | Provide the selected checkpoint binary. Existing accepted checkpoint paths point under ignored data/interim/c2_pu run directories that are absent here. |
| checkpoint_sha256 | true | pending_model_selection | Provide the selected checkpoint SHA-256 and confirm it against data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json. |
| feature_schema | true | verified_in_repository_not_yet_handed_off | data/processed/c2_pu/fr3_fusion_schema.json; SHA-256 397d0aaeacd3133271c08809fe5158f05dfa2a8abcc2fdb6c8f928419af1f17d; fusion_v1, 495 dimensions. |
| fold_scaler | true | verified_in_repository_not_yet_handed_off | Confirm the selected model's fold and scaler from data/processed/c2_pu/fr3_fusion_scalers.json; file SHA-256 83a414b29e1ba057e36a9de4fb1efb5858933ae2feb2c75713555fddcbb90169. |
| embedding_contract | true | verified_in_repository_not_yet_handed_off | Confirm esm2_t12_35M_UR50D, representation layer 12, 480-dimensional residue-mean embedding, exact dependency/runtime, and model-weight provenance. |
| descriptor_contract | true | verified_in_repository_not_yet_handed_off | Confirm descriptors_v1, all 15 ordered descriptor names, implementation commit, and any dependency versions. |
| inference_entry_point | true | request_required_from_component_2 | Provide a read-only sequence-to-score command/function or exact steps that do not retrain, refit a scaler, or rewrite accepted Component 2 artifacts. |
| score_semantics | true | partially_documented_confirmation_required | Confirm positive-class orientation, native range, threshold if applicable, whether any clipping occurs, and the required statement that the score is not a calibrated biological probability. |
| reference_score_fixture | true | request_required_from_component_2 | Provide at least one valid peptide sequence, expected native score, numerical tolerance, model/scaler/checkpoint hashes, and runtime versions for cross-component verification. |
| batch_and_failure_contract | true | request_required_from_component_2 | Specify supported sequence lengths/alphabet, practical batch size, deterministic settings, and failure behavior for invalid or unscorable inputs. |
| use_authorization | true | request_required_from_component_2 | Confirm internal research use, redistribution/storage rules for ignored model artifacts, and the approved handoff location. |

## Acceptance gate

- Every required item must be marked verified_for_handoff, all supplied hashes must match, and the supplied reference sequence must reproduce its expected finite score through the C3 predictor interface within the declared tolerance.
- Scientific limitation to preserve: Component 2 reports weak assay-supported discrimination and states that model scores are not calibrated biological probabilities; C3 must preserve this limitation in every result.
