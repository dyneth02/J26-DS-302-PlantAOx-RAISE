# C4 PP1 Logbook Draft (18–21 October 2026)

**Draft for owner review.** Entries below separate verified repository events from future prompts; edit these to match the actual personal logbook. Do not present the 20–21 October prompts as completed work before it occurs.

## 18 October 2026 — draft entry

- **Work:** Component 4 candidate-generation work used reviewed UniProt proteomes and the configured sequential pyteomics digestion/filter/dedup pipeline.
- **Verified record:** Source protein records: soybean 439, rice 4,197, rapeseed 159, olive 110; the C4 registry documents retrieval and checksums. Candidate generation outputs are in `data/interim/c4_screen/`.
- **Deviation/issue:** pyteomics `pepsin ph1.3` is used as the nearest installed rule to proposed pH 1.2. BIOPEP spot-check remains deferred.
- **Owner completion:** Add actual hours, questions asked, and supervisor feedback.

## 19 October 2026 — draft entry

- **Work:** Validated candidate embedding handoff (152,259 × 1,280); ran cloud, AD, mock signal, score, card, dashboard stages; checked deterministic output hashes and ran the C4 tests.
- **Verified record:** MOCK cloud N=500. Rice cached tiering + scoring/ranking measured 20.207124 seconds. C4 suite passed 15 tests. A C2 PP1 CD-HIT representative filter produced the staged 912-row real-cloud sequence handoff; embeddings remain pending.
- **Deviation/issue:** Local host has no CUDA; embedding work was performed in supplied Colab handoff. Layer-33 pooling remains a C4 assumption.
- **Owner completion:** Add actual hours, the handoff conversation status, and any feedback.

## 20 October 2026 — planned draft prompt

- Record rehearsal duration, hardware/browser validation, any dashboard issues, and corrections. Record status of Colab embedding request. Do not claim the real cloud was embedded unless its index, shape, hash, and finite-value checks pass.

## 21 October 2026 — planned presentation-day draft prompt

- Record actual presentation time, demo path used (live or offline fallback), panel questions, feedback, and follow-up actions. Do not pre-fill outcomes before the presentation.
