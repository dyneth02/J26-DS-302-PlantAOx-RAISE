# FR3 Feature Pipeline Demonstration (Bucket 3.5)

A small, fast, fully offline demonstration of the **already-accepted**
Tasks 3.1–3.4 feature pipeline, built entirely from real pipeline
artifacts and the real shared implementations — no new formulas, no
synthetic data, and no live ESM-2/WSL inference anywhere in its path.

## Prerequisites

Tasks 3.1–3.4 must have already been run **once** in this checkout (they
produce large, gitignored `.npz` caches this demo reads from — see
`AGENTS.md` / `IMPLEMENTATION_STATUS.md` for why those aren't committed):

```bash
python -m plantaox.c2_pu.run fr3-descriptors
python -m plantaox.c2_pu.run fr3-embeddings      # needs WSL (one time)
python -m plantaox.c2_pu.run fr3-feature-fusion
python -m plantaox.c2_pu.run fr3-feature-cache
```

If any of these haven't been run, `fr3-demo` raises a `FileNotFoundError`
naming exactly which file is missing and which command produces it —
nothing is silently skipped or faked.

## Running the demonstration

One command, offline, no GPU, no WSL, no internet, completes in ~1–2
seconds:

```bash
python -m plantaox.c2_pu.run fr3-demo
```

## What it demonstrates

Using 7 fixed, real peptide IDs already present in the accepted pipeline
outputs (not fabricated) — one FR1 positive from GraphPart fold 0's
training split, one from fold 0's held-out split, one C1, one C2, two C3
sequences that are fold 0's real rank-1 and rank-2 hard challenges, and
one AnOxPePred external control:

1. **Input validation** — each sequence checked against the standard
   20-amino-acid alphabet and the 3–50 AA length window
   (`common.sequence.is_valid_peptide`).
2. **Descriptor extraction** — the real `common.descriptors.
   compute_descriptors_batch()` is called live (fast, pure numpy, no
   GPU/WSL) and cross-checked against the frozen `fr3_descriptor_table.
   parquet` values for these same peptides.
3. **Embedding loading** — the 480-dim ESM-2 vectors are **loaded from
   the existing `fr3_embeddings.npz` cache**, never recomputed; no ESM-2
   inference or WSL call happens anywhere in this demonstration.
4. **Feature-cache loading** — the fold-0 scaled 495-dim feature cache
   (`fr3_fold0_scaled_features.npz`) is loaded through `common.
   feature_cache.load_fold_feature_cache()`, with its usual strict
   SHA-256/shape/dtype/schema checks (see Bucket 3.4).
5. **Pool / fold selection** — training rows, held-out rows, C1, C2, and
   fold 0's real C3 hard-challenge selection (via `curation.c3.
   load_fold_challenges`, never by filtering `pool == "C3"`) are all
   pulled from the loaded cache and their counts reported.
6. **External-control separation** — confirmed disjoint from every
   fold's training and held-out sets.

## Expected output (reference)

Running the command above overwrites `data/processed/c2_pu/
fr3_demo_output.json`, which is **committed to the repository** and
serves as the exact expected-output reference — re-running the
demonstration against an unchanged pipeline reproduces this file
byte-for-byte (verified in `tests/c2_pu/test_fr3_demo_acceptance.py`).

The pool-coverage section (stable across any unchanged pipeline run)
should read:

```json
{
  "FR1_positives_training": 710,
  "FR1_positives_held_out": 124,
  "C1": 3788,
  "C2": 2000,
  "C3_union_in_cache": 2325,
  "C3_fold0_challenge_selection": 2000,
  "external_control": 38
}
```

...and every entry under `"validation"` should read `true`. If any entry
is `false`, or the command raises an exception, the demonstration has
failed and Task 3.5 is not accepted.

## Scope

This demonstrates the existing, already-accepted feature pipeline for a
PP1 presentation. It does **not** implement classifier training (Bucket
4) and does not claim FR3 itself is complete — FR3 additionally requires
the four classification baselines (PN, nnPU, Two-Step PU, PU-Bagging)
and their evaluation, which have not been started.
