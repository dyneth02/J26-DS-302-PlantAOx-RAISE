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

The project owner reports these five files are now supplied in `data/interim/c4_screen/embeddings/`; validation and production execution are pending:

- `c4_esm2_t33_650M.npy`
- `c4_embedding_index.parquet`
- `c4_embedding_manifest.json`
- `ref_cloud.npy`
- `ref_cloud_sequences.csv`

No local ESM-2 load/download is needed or permitted. Until the ordered production run completes, actual embedded counts, AD parameters, tier fractions, cards, and output checksums are unreported. Prior synthetic tests passed: 7 tests in `tests/c4_screen/test_downstream_pipeline.py`; the `tests/c4_screen` suite passed 12 tests before the supplied handoff was available.
