# Predictor Access Status (Task 3.20)

**Schema:** `1.0`  
**Checked:** `2026-10-19`  
**Integration rule:** A predictor remains `not_integrated` until a real score has been produced through the C3 predictor interface and retained as evidence.

| Predictor | Code/model availability | Expected input | Output | Batch scoring | License/access limitations | C3 integration |
|---|---|---|---|---|---|---|
| AnOxPePred | Public source notebooks and bundled TensorFlow weights; current DTU submission page reachable. | FASTA or sequence array; peptide length 2-30; one-hot encoded and padded to 30. | Two numeric sigmoid outputs: FRS and chelation. | Yes; multi-record FASTA and array prediction are supported. | Public access, but no repository code licence was found; reuse terms are unspecified. | `not_integrated`; real score verified: `false`. No AnOxPePred adapter or retained real C3 score exists. |
| Multi-AOP | Public local inference code and bundled PyTorch checkpoints; no documented web service. | FASTA converted to name/SEQUENCE CSV; standard amino acids; converter accepts length 2-30. | CSV columns probs and preds, with preds thresholded at >0.5. | Yes; supplied local loop uses batches of 500. | Public access, but no repository code licence was found; dependency setup is substantial. | `not_integrated`; real score verified: `false`. No Multi-AOP adapter or retained real C3 score exists. |
| AOPxSVM | Public inference code plus bundled scaler/SVM/features; live FASTA submission page reachable. | FASTA; CTD+BLOSUM62 features, saved selection/scaler, and 80-feature SVM input. | CSV pred_label plus positive-class pred_proba. | Yes; local multi-FASTA inference and web FASTA upload are supported. | Public access, but no repository code licence was found; legacy joblib environment is required. | `not_integrated`; real score verified: `false`. No AOPxSVM adapter or retained real C3 score exists. |
| AOP-DRL | Public training-oriented scripts, but no trained checkpoint/inference package; published web endpoint is not serving AOP-DRL. | Published UI: pasted sequence or TXT/FASTA, up to 500 peptides; repository: labelled CSV training input. | Published report contains prediction probabilities and physicochemical properties. | Documented for up to 500 peptides, but currently unavailable and therefore not operationally usable. | Non-commercial use only; no standalone licence file; high-resource and missing-artifact constraints. | `not_integrated`; real score verified: `false`. No usable checkpoint/service, C3 adapter, or retained real C3 score exists. |
| PU-AOP (Component 2) | Internal source/manifests available; required accepted checkpoint and feature-cache bytes are missing locally. | Peptide sequence via C2 preprocessing to a fold-scaled 495D vector (480 ESM-2 + 15 descriptors). | Positive-class support score; not a calibrated biological probability. | Yes in the upstream matrix-based pipeline, once the required model/cache artifacts are recovered. | Internal team access; no repository licence; formal frozen-model handoff and missing artifacts are required. | `not_integrated`; real score verified: `false`. Upstream historical inference is documented, but no score has been produced through the C3 interface. |

## Evidence notes

- Public repository availability does not prove that its environment reproduces or that C3 can score with it.
- A reachable submission page does not prove an automatable API or a verified result.
- Repository license status refers to the inspected repository files, not the publication's copyright licence.
- PU-AOP upstream reports and source code are present, but the accepted ignored checkpoints/cache and their documented external backup are absent from this checkout.
- The machine-readable registry contains the inspected revisions, URLs, local evidence paths, observations, and blockers.
