# C4 PP1 Freeze Report — PlantAOP-Screen

**Freeze ID:** `c4_pp1_freeze_v1`  
**Snapshot:** 2026-10-19  
**Verified implementation revision:** `e8b75ad965a188e274e60cb53be7f6224ba7a558` (pre-freeze-doc commit)  
**Release tag:** `c4-pp1-v2` (annotated local tag on the freeze documentation commit; existing `c4-pp1-v1` was not moved or deleted)  
**Decision:** **FROZEN FOR PP1 WITH LIMITATIONS** — validated on the current MOCK cloud and mock signals; the staged real-positive sequence list is awaiting Colab embedding.

## Freeze contents

- FR1 reviewed-proteome candidate generation, provenance, candidate FASTA/tables and funnel.
- FR2 validated candidate embedding handoff, 500-row `mock_cloud`, AD parameters, tiers and diagnostics.
- FR4 mock signal integration, deterministic combined score and ranking.
- FR7 mock evidence cards, abstained cases, summary and offline dashboard.
- C4-only suite (15 passed), deterministic cached rerun evidence (35 SHA-256 comparisons), NFR2 timing, technical report, acceptance reports, demo script, slide draft, logbook draft, FASTA handoff draft, and checksummed release manifest.

## Verified quantitative evidence

- Candidate count: 152,259 globally unique sequences; 152,259/152,259 embeddings imported.
- Production cloud: N=500, `source=mock_cloud`. Function B signal sources are `mock`.
- AD parameters: μ=0.0185099002; σ=0.0097886926; t1=0.0282985928; t2=0.0380872854; SD multiplier 1.0. See `PP1_NUMBERS.md` for tier fractions, length bins and sensitivity.
- NFR2 cached rice run: N=140,813; tiering=18.562604 s, scoring/ranking=1.644521 s, combined=20.207124 s on this host.
- `pytest tests/c4_screen`: 15 passed. Two `all --reuse-inputs --signals mock` runs matched all 35 compared generated-file SHA-256 values.
- Real-cloud staging: 912 C2 PP1 CD-HIT representative sequences after evidence/length/alphabet filtering, E1=478/E2=434. The handoff file and checksum are in `decision_log.md`; corresponding embedding arrays are not available, so it does not replace the production cloud.

## Integrity and Git boundary

`C4_PP1_FREEZE_MANIFEST.json` identifies the implementation parent revision and hashes C4 source/docs plus the generated output manifest entries. Large data, embedding arrays, FASTAs and weights are not committed; local availability/checksum status is separately recorded. The current checkout is `feat/c4-Screen1`, not the requested `c4/pp1-final`; branch switching was prohibited, so the local v2 tag references the current branch. No non-C4 paths were staged.

## Limitations and deferred work

- The production reference cloud is synthetic MOCK data; all Function B signal inputs, score/rank values, and card examples are mock. They are not biological evidence.
- ESM layer-33 mean pooling remains a C4 assumption pending C1 confirmation. The real cloud sequence file needs Colab embeddings, validation and a later explicit production refresh.
- PDSS, BIOPEP spot-check, local ESM benchmark, chunked checkpointing, and C2 fold-0 scoring are deferred for the stated scope/dependencies. No retrieval evaluation metric was computed from mock inputs.
- Supervisor acceptance, external FASTA delivery, live presentation, and rehearsal are not claimed by this technical freeze.
