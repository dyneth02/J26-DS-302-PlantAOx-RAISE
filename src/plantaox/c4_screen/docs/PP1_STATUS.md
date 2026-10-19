# Component 4 PP1 status: real, provisional, and mock

**Snapshot:** 19 October 2026. PP1 presentation target: **21 October 2026** (supersedes the earlier 26 October draft). This records repository evidence, not supervisor approval.

## Real and verified

- Gate 1 candidate generation is complete and remains unchanged.
- The candidate table contains 152,259 unique sequences from the four reviewed proteomes. Gate 1 funnel and provenance evidence are recorded in `SCREEN_PP1_Deployment_Progress.md`.
- Synthetic unit coverage verifies the downstream interfaces and algorithms listed below; it does not substitute for full-data acceptance.

## C4-provisional assumptions

- ESM-2 representation: `esm2_t33_650M_UR50D`, layer 33, mean of residue embeddings with BOS/EOS/PAD excluded. This recipe is not confirmed with C1.
- AD calibration uses leave-one-out cloud-member cosine distances; `d_norm=min(d_AD/t2,1)` and default SD multiplier 1.0.
- BCS LOW/MEDIUM/HIGH flags use C4 config cutoffs 0.5 and 0.7 and are explicitly `C4-provisional`.
- The C4 interface spec and join key are provisional where marked; do not attribute these choices to C1/C2/C3.

## MOCK only

- The reference cloud is a 500-sequence, composition-biased synthetic placeholder with seed 42 and source `mock_cloud`.
- C1 SIM, C2 probability, and C3 BCS stand-ins have source `mock`. Any dashboard/card/summary generated from these values must display a permanent mock notice.
- Injected mock examples are demonstrations, not findings. Do not report PARRS, Recall@K, MRR, EF@1%, or ARR on mock signals. PDSS is not implemented; its denominator concern remains open.

## Current execution state

The project owner reports these five files are supplied, but the embedding directory is absent from this checkout. The ordered production attempt therefore remains blocked:

- `c4_esm2_t33_650M.npy`
- `c4_embedding_index.parquet`
- `c4_embedding_manifest.json`
- `ref_cloud.npy`
- `ref_cloud_sequences.csv`

`embed-import` stopped before row-ID hash validation, so no hash formula comparison was needed. `cloud` failed on the missing sequence CSV; downstream `ad`, `signals`, `score`, `cards`, and `dashboard` stages lacked their required inputs/artifacts. No local ESM-2 load/download was attempted. Consequently, actual embedded counts, mu/sigma/t1/t2, tier fractions, real-data cards, and full downstream checksum freeze are unavailable. A blocked-state [checksum manifest](../../../../data/interim/c4_screen/c4_output_manifest.json) hashes the nine existing Gate 1 outputs and lists the missing inputs.

Verification: `tests/c4_screen` passed **12** tests. Full repository `pytest -q`: **552 passed, 38 skipped, 32 failed, 98 errors** (17 subtests passed). Failures/errors include unrelated C2 artifact/model-dependent tests; C2 ESM tests attempted to download their 35M checkpoint but could not write to the configured user cache (`PermissionError`). Six tracked C2 data outputs modified by that test run were restored afterward.
