# Implementation Status — Component 02 (PU-AOP)

**Last updated:** 14 October 2026
**Update rule:** Any agent (Claude Code, Codex) or person completing, starting, or blocking on a task MUST update this file in the same session the change happens. Do not let this file go stale — it is the single source of truth for "what's actually done" versus the aspirational task list in `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`.

**Target dates (unofficial, confirm against actual schedule):** PP1 presentation 26 Oct 2026, checklist submission 30 Oct 2026.

---

## ✅ Completed tasks

### Bucket 1, Tasks 1.1–1.7 — FR1 Positive Pool: Curation, Conflict Resolution, CD-HIT, GraphPart, Freeze
- **Status: technical acceptance passed, frozen as `pp1_baseline_v1` (2026-10-14).** Full detail,
  methodology, every number, and the acceptance-checklist mapping live in
  **[`fr1_acceptance_report.md`](fr1_acceptance_report.md)** — this entry is a pointer + headline
  numbers, not a duplicate of that report.
- **Important distinction (AGENTS.md rule #3):** "technical acceptance passed" is not "FR1 is
  scientifically signed off." Four items are explicitly pending supervisor approval (see
  `fr1_acceptance_report.md` §10) and are **not** blocking — they're documented limitations a
  defensible PP1 baseline is allowed to carry, not things silently glossed over.
- **Headline numbers:** 1,205 accepted positives (670 E1 + 535 E2) → 925 CD-HIT 90%-identity
  clusters (0 dropped) → 834 GraphPart 40%-identity 5-fold-split sequences (91 excluded for
  cross-fold homology, zero residual violations in GraphPart's own convergence report).
- **Reproducibility re-verified 2026-10-14:** full pipeline re-run from raw inputs produces
  byte-identical outputs (automated via `tests/c2_pu/test_fr1_reproducibility.py`, not just a manual
  check) — confirmed no stochastic steps exist in Buckets 1.1–1.6.
- **Provenance chain verified end-to-end:** every retained sequence traces to a named, typed source
  (`tests/c2_pu/test_fr1_provenance_acceptance.py`, 13 tests); peptide IDs form an unbroken,
  duplicate-free chain from the raw-source merge through every stage boundary.
- **Known gap, explicitly not fixed here (out of 1.7's scope):** Bucket 1.1/1.2's formal
  `data_registry.csv` was never created as a standalone artifact. SHA-256 checksums of the two raw
  source files are recorded in `fr1_acceptance_report.md` §4 as a stopgap, not a substitute — flagged
  for separate follow-up, not silently treated as done.
- **Frozen baseline:** `data/processed/c2_pu/frozen/pp1_baseline_v1/` (10 files + checksummed
  `MANIFEST.json`, via `plantaox.c2_pu.curation.freeze`). Per AGENTS.md rule #4, do not regenerate or
  mutate this directory in place — a genuine future change gets a new version ID (`pp1_baseline_v2`),
  logged with a reason for superseding this one.

### Bucket 2, Task 2.1 — C1 Random Decoy Construction (close-out)
- **Status: closed out.** The original Colab-run pipeline (query + secondary blocklist + seed-42
  sample) was ported into tested, reproducible repo code (`pools.py`), not just re-described —
  verified to reproduce the documented 8,830 → 8,233 blocklist result and the saved
  `stage_c1_decoys.fasta` exactly before any cleanup logic was written
  (`test_original_construction_is_reproducible_from_scratch`).
- **"5,000 records" interpretation (confirmed with the project owner):** satisfied at the FASTA-entry
  level (5,000 records, 3,786 unique sequences) — not resampled for uniqueness. Duplication among
  short 4–50 AA fragments across species is retained and explicitly documented, not hidden; flag the
  unique-vs-record distinction if this dataset's size is cited in the FR2 report or presentation.
- **Leakage resolved, screened conservatively:** every C1 sequence was checked against all 1,205 FR1
  positives *and* the 179 cross-source conflicts (not just the 834-sequence frozen split), per
  explicit instruction. Found exactly one contaminated entry: `DRVYIHPF` (an Angiotensin-like peptide
  fragment, UniProt `Q10582`) — an assay-confirmed E1 positive that happened not to be CD-HIT's chosen
  representative for its cluster, so it was absent from the frozen `pp1_baseline_v1` split but still
  sitting in the raw "unlabeled" C1 pool, which AGENTS.md's leakage rules don't allow regardless.
- **Resolution: swap, not resample.** Removed the 1 contaminated entry and deterministically selected
  1 replacement (seed 42) from the untouched portion of the already-saved `uniprotkb_candidates.fasta`
  candidate universe (2,246 eligible candidates available after excluding anything blocklisted,
  already-sampled, or itself contaminated) — no live UniProt query needed. Final pool: still 5,000
  records, 3,786 unique sequences (coincidentally unchanged), 0 remaining contamination.
- **Raw data preserved as historical evidence, per instruction:** `data/raw/c2_pu/UniProt_decoys/*`
  (including the still-contaminated original `stage_c1_decoys.fasta`) is untouched. The corrected pool
  is a new artifact under the same canonical filename at the **processed** tier:
  `data/processed/c2_pu/stage_c1_decoys.fasta`. `pp1_baseline_v1` (FR1) was not touched.
- **New artifacts:** `c1_accession_map.csv` (all 5,000 records, UniProt accession/entry/organism/
  fragment-flag parsed from each header — addresses the Planner's "accession/fragment-coordinate
  mapping" item; see note below on why there are no literal fragment coordinates),
  `c1_leakage_exclusion_log.csv` (1 row), `c1_leakage_replacement_log.csv` (1 row),
  `c1_clean_report.json`, `fr2_c1_provenance.jsonl`.
- **"Fragment-coordinate mapping" note:** C1 decoys are naturally short, complete UniProt entries
  (`length:[3 TO 50]` selects whole short reviewed proteins), not fragments cut by us from longer
  ones — a few are independently flagged `(Fragment)` by UniProt itself (parsed into
  `is_fragment`), but there are no fragment start/end coordinates to map because none were generated
  by this pipeline. Documenting this explicitly rather than inventing coordinates that don't exist.
- **Manual spot-check status:** the six historical rounds of 25-record manual review (documented in
  `PU_AOP_RESEARCH_CONTEXT.md` §6) still cover 4,999 of these 5,000 records unchanged; the one new
  replacement (`RL34_XANVE`, a bacterial large-ribosomal-subunit protein) was read by this agent as
  part of generating the replacement log and shows no bioactivity-adjacent signal, but has not had an
  independent fresh-sample human/agent review of its own — noting this rather than silently claiming
  AGENTS.md validation rule #2 is fully satisfied for the one new record.
- **Reproducibility:** `test_rerunning_c1_clean_is_reproducible` re-invokes the live cleanup and diffs
  SHA-256 hashes of every output file — byte-identical. 13 new tests total (`test_pools.py`,
  `test_fr2_c1_clean_acceptance.py`), all passing alongside the full existing suite (73 total).

### Bucket 2, Task 2.1 — C1 standard-alphabet policy fix (follow-up, 2026-10-14)
- **Policy approved by the project owner:** all curated peptides entering the ESM-2 and
  physicochemical modeling pipelines must use the standard 20-amino-acid alphabet. Sequences
  containing X, B, Z, or U are ineligible for the current pipeline — never silently substituted or
  translated. This resolves Known Issues #9 and #10 for C1; the same requirement now applies to C2/C3
  at initial curation (see Next tasks).
- **Inspected the 260 affected records empirically before changing anything** (not just trusted the
  prior count): 260 records / 259 unique sequences (one legitimate natural duplicate) in
  `stage_c1_decoys.fasta` (v1). Residue breakdown confirmed by direct computation: X=251 (249
  X-only + 2 combined with B/Z), B=7 (5 B-only + 2 combined), Z=3 (all combined with B/X), U=3
  (all U-only) — matches the previously documented Known Issue #9 numbers exactly.
  Lengths range 5–50 AA, nothing outside the shared 3–50 window.
- **Eligible replacement pool checked before any fix was written:** 2,082 standard-alphabet,
  non-blocklisted, non-screened candidates available in the untouched portion of
  `uniprotkb_candidates.fasta` against 260 needed — no shortfall, so no need to consult the project
  owner about changing source/criteria (the documented stop-and-ask condition didn't trigger).
- **Resolution: swap, not resample — starting from the v1 leakage-clean pool, not the raw original.**
  `clean_c1_alphabet()` (`pools.py`) removes the 260 non-standard records and deterministically
  (seed 42) replaces them 1:1 from `uniprotkb_candidates.fasta`, re-screened against the secondary
  bioactivity blocklist, all 1,205 FR1 positives, the 179 cross-source conflicts, **and** the
  alphabet requirement itself (a replacement can never itself be non-standard). Verified empirically
  that FR1's positive pool, the 179 conflicts, and the external control already contain zero
  non-standard-alphabet sequences — this was a C1-only problem, not a project-wide one.
- **Separately versioned, not overwritten:** per explicit instruction, the existing accepted v1
  artifacts (`stage_c1_decoys.fasta`, `c1_accession_map.csv`, `c1_leakage_*_log.csv`,
  `c1_clean_report.json`) are untouched (confirmed via `git status` showing no diff). The corrected
  pool is a new artifact set: `stage_c1_decoys_v2.fasta`, `c1_accession_map_v2.csv`,
  `c1_alphabet_exclusion_log.csv`, `c1_alphabet_replacement_log.csv`, `c1_alphabet_fix_report.json`.
  **`stage_c1_decoys_v2.fasta` is now the canonical artifact for all future C1 consumption**
  (embedding extraction, descriptor generation, C3 screening) — v1 is kept only for historical
  diffing, and any future code reading `stage_c1_decoys.fasta` without the `_v2` suffix is reading
  the superseded, alphabet-contaminated version.
- **Unique-sequence count shifted slightly (3,786 → 3,785), documented not hidden:** removing 259
  unique non-standard sequences and adding 260 replacement records (258 unique — two replacement
  pairs share a sequence under different UniProt accessions, the same natural-duplication pattern
  already accepted for C1 generally) nets to 3,785 unique sequences among the 5,000 records. Still
  5,000 FASTA records, the project owner's confirmed acceptance unit.
- **Full-file validation (not a sample):** all 5,000 v2 records confirmed standard-alphabet, 3–50 AA,
  zero exact-sequence overlap with the 1,205 positives + 179 conflicts, accession map covers all 5,000
  records with 0 missing accessions, exclusion/replacement logs are disjoint and match the report
  counts exactly (`test_fr2_c1_alphabet_acceptance.py`, 7 new tests).
- **Reproducibility:** `test_rerunning_alphabet_fix_is_reproducible` re-invokes the live fix and diffs
  SHA-256 hashes of every output file — byte-identical. 9 new tests total (`test_pools.py` +2,
  `test_fr2_c1_alphabet_acceptance.py` +7), full suite now 84 passed, 1 skipped (unchanged skip
  reason: `test_embeddings.py` needs torch, runs for real inside WSL — 12 passed there separately).
  `pp1_baseline_v1` and the v1 C1 artifacts confirmed untouched via `git status` before and after.

### Bucket 2, Task 2.2 — C2 Bioactive Unlabeled Pool Construction
- **Status: core pool built and acceptance-tested; AODB/DFBP cross-reference explicitly not done
  (see gap below).** 2,000 unique, standard-alphabet, 3–50 AA peptides with ≥1 reported
  non-antioxidant Peptipedia bioactivity, zero exact-sequence overlap with FR1's 1,205 positives or
  the 179 conflicts, zero antioxidant-tagged records.
- **Source: Peptipedia v2.0 Zenodo dump**, not the web app (DOI `10.5281/zenodo.21488992`,
  `peptipedia.20240323.sql.gz`, 281MB gzip, ODbL-1.0 licensed). **Decision, confirmed with the project
  owner:** the web app's "download by activity" button calls an undocumented endpoint behind
  Cloudflare bot protection that an automated session couldn't trigger even with a real browser
  session (verified: button clicks registered, selection persisted, but no corresponding network
  request was ever captured) — not scriptable/reproducible, so the versioned, checksummable full
  dump was used instead despite AGENTS.md rule 6's general preference for filtered queries over bulk
  downloads. The dump is a **plain-text** `pg_dump` (confirmed via `gzip -t` + inspecting its `COPY`
  blocks directly), not a binary dump, so it's parsed in pure Python
  (`curation/peptipedia.py::iter_copy_rows`) without installing or running any PostgreSQL server —
  keeping the "don't stand up unneeded infrastructure" spirit of rule 6 even though the download
  itself is the larger, bulk option.
- **281MB raw dump NOT committed to git** (`data/raw/c2_pu/Peptipedia/*.sql.gz` added to
  `.gitignore`) — would fail a GitHub push outright (100MB-per-file limit, no Git LFS configured),
  same "don't commit large binary artifacts" principle already applied to ESM-2's pretrained weights.
  Its SHA-256 (`d8ff0e082874bb8e5a6b67543273f05c127dd96fc3f1937da3463cf8c407fb8f`, confirmed matching
  the Zenodo-published MD5 `0605886c33919b5c756b66200024ef1c` after a first attempt was silently
  truncated at 9.8% by a dropped connection — caught by `gzip -t` failing, not assumed complete from
  a 200-exit-code background download) and DOI are recorded in `c2_build_report.json` and
  `fr2_c2_provenance.jsonl`, so the exact same file can be re-downloaded and the pool reproduced
  byte-for-byte.
- **Inclusion policy** (`curation/peptipedia.py::build_c2_pool`): a peptide must have ≥1 *reported*
  activity tag (Peptipedia's own `peptide_has_activity` table; absence of an antioxidant tag alone
  isn't eligibility — AGENTS.md requires a *documented* non-antioxidant bioactivity, not merely an
  unlabeled one), must not itself carry Peptipedia's antioxidant tag (activity id 41, "Anti
  oxidative" — confirmed by direct inspection of the `activity` table, not a name-string guess),
  standard 20-AA alphabet + shared 3–50 AA window (same policy as C1/positives), and no exact-sequence
  match against the 1,205 FR1 positives + 179 conflicts (same conservative screen as C1's leakage
  check). Of ~3.8M standard-alphabet/length-windowed Peptipedia sequences, 2.73M have ≥1 non-
  antioxidant activity tag and pass the screen; of those, 66,506 have at least one
  *experimentally-reported* (not merely ML-predicted) tag.
- **Experimental evidence preferred over predicted-only, mirroring E1>E2 precedence:** the 2,000-record
  sample was drawn entirely from the 66,506-strong experimental tier (seed 42) — the 2.66M
  predicted-only tier wasn't needed and wasn't used. Documented as a tier-preference decision, not
  silently defaulted.
- **Deduplicated by sequence** (Peptipedia assigns multiple internal IDs to identical sequences
  reported by different source databases) — one record per unique sequence, lowest `id_peptide` kept
  for determinism. Peptide IDs are content-addressed (`make_peptide_id(seq, prefix="C2")`), consistent
  with the FR1 positive-pool convention.
- **Known gap, explicitly not done:** the Planner's "cross-reference AODB and DFBP" checklist item.
  Peptipedia integrates 76 named source databases (`source` table, inspected directly) — neither AODB
  nor DFBP is among them, so C2 is not yet cross-checked against those two specific AOP resources.
  Flagging rather than silently treating as covered by Peptipedia's internal antioxidant tag alone.
- **Tests:** 9 unit tests against synthetic fixtures (`test_peptipedia.py`) plus 6 full-file acceptance
  tests (`test_fr2_c2_build_acceptance.py`, including byte-identical reproducibility), all gated to
  skip cleanly when the (gitignored) raw dump or built pool isn't present locally. Full suite: 100
  passed, 1 skipped (torch).

### Bucket 3, Task 3.2 — ESM-2 Environment Setup and Smoke Test
- **Status: environment configured, interface built and tested, smoke test passing.** This is
  explicitly NOT full feature generation — embedding the full positive pool and C1/C2/C3 (Bucket
  3.2's later checklist items) is separate, deliberately out-of-scope work for next time.
- **Environment:** `torch` 2.14.1+cpu and `fair-esm` 2.0.0 installed into the existing `pu_aop`
  WSL micromamba environment (not a new env) alongside CD-HIT 4.8.1 / graph-part 1.0.2 / EMBOSS
  6.6.0.0, all confirmed still working afterward. `pytest` 9.1.1 was also added to `pu_aop` so the
  new torch-dependent tests can actually execute where torch lives (see architecture note below).
  numpy (2.4.6) and pandas (3.0.6) were unaffected — checked analytically before installing (torch's
  PyPI metadata declares no numpy/pandas version constraint at all) and confirmed empirically after.
- **CPU vs. GPU decision (confirmed with the project owner, 2026-10-14):** this machine has a real,
  WSL-passthrough-configured GPU (NVIDIA RTX 4050 Laptop, 6GB VRAM, driver 610.62) — not assumed,
  verified via `nvidia-smi` inside WSL. A full CUDA-enabled PyTorch install (`cu128`, ~2.5GB:
  torch + cuDNN + cuBLAS + the rest of the CUDA runtime stack) was measured at ~45-60 minutes over
  this connection's ~700KB/s throughput. Given `esm2_t12_35M_UR50D` is a 35M-parameter model whose
  actual workload (a few thousand short peptides) runs in well under a second on CPU alone (measured:
  0.096s for 5 sequences; see smoke test below), GPU acceleration would not meaningfully help this
  task or the eventual full C1/C2/C3+positives embedding pass. Installed CPU-only instead.
  `torch.cuda.is_available()` correctly reports `False` on this build — GPU acceleration is not
  claimed anywhere in this component, consistent with the explicit instruction not to claim it
  without verification. If a larger ESM-2 checkpoint (150M/650M) is adopted later for better C3
  hard-challenge quality, this trade-off should be revisited.
- **Architecture: embedding code runs inside WSL via subprocess, not imported into run.py directly.**
  `common/embeddings.py` imports `torch` at module level, and torch is *only* installed in the
  `pu_aop` WSL env — the Windows-side Python running `run.py` for every other stage does not have
  it. Importing `embeddings.py` directly into `run.py`'s top-level imports would have broken every
  existing command (`fr1-positives`, `fr1-cluster`, etc.) the moment Windows tried to import torch.
  Instead, `esm2_cli.py` is a standalone entrypoint that runs *inside* `pu_aop` (reads a small JSON
  input, writes a small JSON summary report — never raw embedding arrays), invoked from `run.py` via
  `common/wsl.py`'s `run_in_conda_env`, the exact same subprocess pattern already used for CD-HIT and
  GraphPart. `run.py` itself never imports `embeddings.py`.
- **Frozen embedding specification** (`common/embeddings.py` module docstring is the canonical
  reference — do not change without a new decision-log entry, since every cached embedding and C3
  centroid downstream will assume it):
  - Model: `esm2_t12_35M_UR50D`, loaded via `esm.pretrained.esm2_t12_35M_UR50D()`.
  - Representation layer: **12** — confirmed empirically (`model.num_layers == 12`) to be the
    model's actual final layer, not assumed from the checkpoint name alone.
  - Tokenization: the model's own `alphabet.get_batch_converter()`. Verified empirically (not
    assumed from fair-esm's docs) that `prepend_bos=True`, `append_eos=True`, and that a 4-residue
    and an 8-residue test sequence tokenize exactly as `[BOS, res..., EOS, PAD...]` — i.e., real
    residues occupy token positions `1..len(seq)`, confirmed by direct inspection of the token
    tensor, not inferred.
  - Pooling: mean over positions `1..len(seq)` only — BOS, EOS, and PAD are excluded by construction
    (using each sequence's own known length), not a padding-mask heuristic.
  - Output: float32 numpy array, shape `(480,)` per sequence — `480` confirmed empirically
    (`model.embed_dim == 480`) and asserted at load time (`load_embedder` raises if it ever differs).
  - Device: CUDA only if `torch.cuda.is_available()` **and** a real tensor op on it succeeds — never
    assumed from driver/`nvidia-smi` presence. Currently always resolves to CPU (CPU-only torch
    build installed).
  - Inference: `model.eval()` + `torch.no_grad()` — confirmed deterministic by running the same
    5-sequence smoke-test batch twice and diffing the output arrays (bit-identical).
- **Ambiguous residues (X/B/Z/U): explicitly NOT silently handled.** `embed_sequences()` validates
  every sequence against the 20-letter standard alphabet by default and raises
  `AmbiguousResidueError` (naming every offending peptide_id/sequence/residue) rather than silently
  embedding or silently dropping them — callers must pass `validate_alphabet=False` only after an
  explicit, documented policy decision. **That policy decision itself has not been made yet** — this
  is the same open question as Known Issues #9 (260/5,000 C1 decoys carry X/B/Z/U) and now also
  applies to whatever fraction of C1/C2/C3/positives carry these residues once full feature
  generation starts. Flagging here as a prerequisite for that later task, not resolving it now.
- **Smoke test (`python -m plantaox.c2_pu.run esm2-smoketest`):** 5 fixed, varied peptides
  (short/medium/long/charged/hydrophobic — mirroring Bucket 3.1's own testing convention). All 5
  produced finite, correctly-shaped `(480,)` float32 vectors with plausible norms (L2 norm ≈ 6.8-7.3)
  in 0.096s total on CPU. Report (shape/dtype/finiteness/mean/std/L2-norm per peptide — **no raw
  embedding vectors**, per the "don't commit large embedding arrays" constraint) written to
  `data/processed/c2_pu/esm2_smoketest_report.json`.
- **Tests:** 12 new tests (`tests/c2_pu/test_embeddings.py`) covering device resolution (forced-CPU
  and CUDA-unavailable paths), model/dimension verification, shape/finiteness, determinism,
  batch-size invariance (batching by 32 vs. by 1 gives numerically identical results), the
  ambiguous-residue rejection *and* its explicit opt-out, and input-validation errors (mismatched
  lengths, duplicate IDs). These import `torch` at module level and are gated by
  `pytest.importorskip("torch")`, so they run for real inside `pu_aop`
  (`micromamba run -n pu_aop python -m pytest tests/c2_pu/test_embeddings.py` — 12 passed) and skip
  cleanly (not fail) when the main suite runs from the Windows `.venv`, which has no torch
  (`pytest tests/c2_pu` — 73 passed, 1 skipped, confirming zero regression to the existing suite).
- **Forward note for C3 (not implemented yet, flagging per explicit instruction):** when C3
  hard-challenge selection is built, its embedding centroid must be fit on the training partition
  only and applied (not refit) elsewhere, per AGENTS.md rule #5 — this module's job stops at
  producing per-sequence embeddings; fold-safety is the caller's responsibility when that stage is
  built.

## 🔄 Current work in progress

*(Bucket 2, Task 2.1 and Bucket 3, Task 3.2's setup/smoke-test scope are both moved to Completed
above. Full feature generation — Bucket 3.2's remaining checklist items — is still open, see Next
tasks below.)*

## ⚠️ Known issues / open risks

1. **C1 source ambiguity (supervisor sign-off needed):** Proposal says "SwissProt" (FR2/SO2) vs "UniRef50" (§3.2.2). We've adopted UniProtKB `reviewed:true` (= SwissProt) as the working interpretation — see `PU_AOP_RESEARCH_CONTEXT.md` §4 for rationale. **This has not been confirmed with supervisors yet.** Flag in next consultation.
2. **Residual filtering imperfection is expected, not a bug.** Six rounds of manual review caught progressively more obscure contamination (toxins → hormones → AMPs → antioxidant enzymes → metallothionein → frog skin peptides). This is diminishing returns, not an unresolved defect. The agreed plan is to document it as a limitation in the FR2 report (see `PU_AOP_RESEARCH_CONTEXT.md` §7), **not** to keep iterating indefinitely. Do not reopen this unless full-file validation (above) finds something structurally different from the spot-check pattern.
3. **Full-file validation gap** (see Current Work above) — this is the one open item that *does* need closing before C1/FR2 can be marked complete, as distinct from #2 which is an accepted limitation.
4. **A real case-sensitivity bug occurred once already** (keyword added with a capital letter never matched because `.lower()` was only applied to the description, not the keyword). Fixed via the list-comprehension lowercasing pattern in `PU_AOP_RESEARCH_CONTEXT.md` §5. Any agent editing the blocklist should be aware this class of bug is easy to reintroduce.
5. **179 of 1,384 candidate positives (Multi-AOP ∩ AnOxPePred-inactive) are cross-source contradicted — resolved, but needs supervisor visibility.** See Bucket 1 section above. Excluded from both the positive pool and the external control pending manual review; logged in full in `label_conflicts_anox_vs_multiaop.csv`. This is the exact "contradictory labels across databases" phenomenon the proposal's own lit review (p.14, citing Isaac et al.) names as a field-wide problem — worth citing directly in the FR1 report as in-practice confirmation of the research motivation, not just a data-cleaning footnote.
6. **RESOLVED 2026-10-14.** C1's "5,000 records / 3,786 unique sequences" question was confirmed with the project owner as satisfied at the record level — see Bucket 2, Task 2.1 (close-out) above. Kept here for history; not an open item anymore.
7. **RESOLVED 2026-10-14.** The `DRVYIHPF` leakage was found, screened conservatively (against all 1,205 positives + 179 conflicts, not just the frozen 834), and fixed by a 1-for-1 deterministic swap — see Bucket 2, Task 2.1 (close-out) above. `pp1_baseline_v1` was unaffected (the sequence was never in the frozen split).
8. **The one new C1 replacement record (`RL34_XANVE`) has not had an independent manual spot-check**, distinct from the six historical rounds covering the other 4,999 unchanged records. Noted in the Task 2.1 close-out rather than silently assumed covered by the prior rounds.
9. **RESOLVED 2026-10-14.** 260 of 5,000 C1 decoys (5.2%) contained non-standard residue codes — X
   (251), B (7), Z (3), U (3). Fixed by `clean_c1_alphabet()` — see Bucket 2.1 "standard-alphabet
   policy fix" above. The corrected, canonical artifact is `stage_c1_decoys_v2.fasta`; v1 is kept only
   as historical evidence and is no longer the artifact any new code should read.
10. **RESOLVED for C1/C2, 2026-10-14. C3 still pending construction.** Project-owner-approved policy:
    all curated peptides entering the ESM-2 and physicochemical pipelines must use the standard
    20-amino-acid alphabet; X/B/Z/U sequences are ineligible, never silently substituted or translated.
    FR1's positive pool, the 179 conflicts, and the external control already contain zero
    non-standard-alphabet sequences. C1 was fixed (see above). C2 applied the filter at initial
    construction (`build_c2_pool`), not as a post-hoc patch. **C3 does not exist yet** (Task 2.3) — when
    built, its curation code must apply `is_standard_alphabet()` the same way. `embed_sequences()`'s
    `AmbiguousResidueError` default remains the structural backstop against ever skipping this silently.
11. **C2 is not cross-referenced against AODB or DFBP** (Planner Bucket 2.2 checklist item). Peptipedia
    v2.0 integrates 76 named source databases, confirmed by direct inspection of its `source` table —
    neither AODB nor DFBP is among them. C2's only antioxidant screen is Peptipedia's own internal
    "Anti oxidative" activity tag plus the FR1 positive-pool/conflict exact-sequence screen. Acquiring
    and cross-referencing AODB/DFBP specifically is unstarted, separate follow-up work.

## ⏭️ Next tasks (in order)

1. **Get supervisor sign-off on the four pending FR1 approvals** (`fr1_acceptance_report.md` §10) —
   the conflict-resolution policy, the E2 provisional-tier default, the C1 source ambiguity, and the
   missing formal `data_registry.csv`. None block continued FR2/FR3 work on `pp1_baseline_v1`, but
   FR1 isn't *scientifically* closed until these are addressed.
2. **Bucket 2.1 (C1) is closed out, including the standard-alphabet policy fix** — see Completed tasks
   above. Optional follow-ups, both low priority: an independent spot-check of the one new leakage
   replacement record (`RL34_XANVE`); a spot-check of a few of the 260 new alphabet-fix replacement
   records (none had an independent fresh review beyond the automated blocklist/screen checks).
3. **Bucket 3.2's environment/interface/smoke-test scope is closed out** — see Completed tasks above.
   The ambiguous-residue policy blocker (former Known Issues #9/#10) is now resolved for C1; full
   embedding extraction (the remaining Bucket 3.2 checklist items: "extract embeddings for remaining
   positives and C1/C2/C3," "verify dimensions/ordering/dtype/completeness") can read
   `stage_c1_decoys_v2.fasta` directly with `embed_sequences(..., validate_alphabet=True)` (the
   default) and expect zero `AmbiguousResidueError`s from C1. Not yet attempted — still separate,
   deliberately out-of-scope work.
4. **Task 2.2 (C2) core pool is built** — see Completed tasks above. Remaining: acquire and
   cross-reference AODB/DFBP specifically (Known Issue #11), low/medium priority depending on how much
   the PP1 report leans on that specific checklist line versus the broader antioxidant-exclusion
   argument already satisfied.
5. **Task 2.3 (C3 — ESM-2 hard challenges)** can start any time; not blocked on anything above. Must
   apply the standard-alphabet filter at initial curation (Known Issue #10), not as a later patch.
6. **Bucket 3.1 (15 physicochemical descriptors)** can also start any time in parallel with C3 —
   not blocked on the ESM-2 work.
7. Continue down the Bucket 1 → Bucket 2 → Bucket 3 → Bucket 4 sequence as defined in `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`, respecting the FR1+FR2-first priority.

## 📝 Experiment decisions log

| Date | Decision | Rationale |
|---|---|---|
| 2026-10-07 | Use UniProtKB `reviewed:true` instead of raw UniRef50 bulk FASTA for C1 sampling | Matches FR2/SO2 wording ("SwissProt"); UniRef50's `reviewed` field doesn't exist on that endpoint (confirmed via live 400 error); avoids an unnecessary ~13GB download | 
| 2026-10-07 | Random seed fixed at 42 for all C1 sampling | Reproducibility requirement — any re-run must produce an identical 5,000-record set from the same candidate pool |
| 2026-10-07 | Stopped iterating on keyword-filter perfection after round 6 | Diminishing returns — each round caught progressively more obscure single-digit-count contamination; agreed to document as a known limitation instead of open-ended chasing (see risk #2 above) |
| 2026-10-07 | Query-level keyword exclusions: Toxin, Hormone, Neuropeptide, Antimicrobial, Antibiotic, Antioxidant, "Amphibian defense peptide" | Based on UniProt's own controlled-vocabulary keywords (confirmed IDs: KW-0929 Antimicrobial, KW-0044 Antibiotic, KW-0049 Antioxidant, KW-0878 Amphibian defense peptide); chosen over trying to enumerate every peptide family name in Python alone |
| 2026-10-14 | Component 02 is self-contained under `src/plantaox/c2_pu/` (own `common/` and `curation/` subpackages) instead of using the shared top-level `src/plantaox/common/`/`curation/` | The shared top-level folders were empty scaffold stubs with no agreed interface and no other member had started using them yet; keeping PU-AOP self-contained avoids unilaterally defining a cross-component contract and keeps this component independently gradable. Flag for supervisor/team discussion if a genuinely shared utility layer is wanted later. |
| 2026-10-14 | `data_registry.csv` is kept component-scoped at `data/processed/c2_pu/data_registry.csv` for now, instead of a single shared top-level registry | AGENTS.md's "don't duplicate the registry" rule assumes one shared `data_registry.csv` already exists, but none does yet and no shared convention has been agreed with the other 3 members. Documented here rather than silently picked; flagged for consolidation once the team agrees on a shared registry convention. |
| 2026-10-14 | Cross-source conflict policy: a Multi-AOP positive contradicted by AnOxPePred's own assay (FRS=0 AND Chelator=0) is excluded from BOTH the positive pool and the external control, logged with full provenance, and flagged as a manual-review/external-control candidate — never silently dropped, never auto-reclassified as E3 | Assay-level evidence (AnOxPePred, per-sequence) outranks an undocumented benchmark annotation (Multi-AOP, no per-record assay metadata), matching the E1>E2 precedence the whole tiering scheme is built on. Confirmed with the project owner 2026-10-14; this resolved 179 of 1,384 candidate positives. Flag for supervisor sign-off — it materially affects both the positive-pool count and the external-control size. |
| 2026-10-14 | Multi-AOP-only positives (no AnOxPePred row) default to E2, explicitly provisional (`evidence_basis="benchmark_positive_annotation"`, `assay_verified="unknown"`), flagged for supervisor review and promotable to E1 later if primary-source assay evidence is recovered | Multi-AOP provides no per-record assay-type metadata — only a bare binary label (its `name` column is a leftover train/test split tag, not a provenance ID) — so E1 cannot be defensibly claimed for these. Confirmed with the project owner 2026-10-14; affects 553 of 1,205 accepted positives (pre-CD-HIT). |
| 2026-10-14 | Positive pool applies the shared 3–50 AA length window (same as C1/C2/C3), dropping 45 sub-3-AA sequences, rather than keeping the full literature-cited 2–50 AA range | Keeps positives and unlabeled pools on the same length distribution so the curriculum can't trivially shortcut on length; documented in the FR1 report rather than silently applied. Confirmed with the project owner 2026-10-14. |
| 2026-10-14 | `run_fr1_positives` output tables are sorted by `peptide_id` before writing, instead of leaving them in whatever order Python's internal `set` iteration happened to produce | The positive-pool build used set operations whose iteration order is randomized per Python process (hash-seed randomization) — harmless for a flat table, but CD-HIT's representative selection for exact-tie clusters depends on input FASTA order, so an undeterministic order would have broken task 1.7's "same seed -> same output" reproducibility check once CD-HIT (1.5) started consuming this file. Fixed before generating any CD-HIT input; re-ran, counts unchanged. |
| 2026-10-14 | CD-HIT word length set to `-n 2` instead of the officially recommended `-n 5` for 90% identity | 417 of 1,205 positives (35%) are under 5 AA; a 5-mer index cannot be built for shorter sequences, which would silently exclude over a third of the pool from clustering. A shorter word length only costs CD-HIT speed/sensitivity — the identity threshold itself is still enforced exactly, it is not relaxed. Confirmed with the project owner 2026-10-14 (explicit short-peptide-edge-case requirement). |
| 2026-10-14 | CD-HIT, GraphPart, and EMBOSS (needle/needleall) installed into a user-space `pu_aop` micromamba environment inside WSL Ubuntu, instead of `apt install` | No root access was available to this agent in this environment (no sudo password); `apt-cache policy` confirmed all three packages exist, but `sudo apt install` needs an interactive password. Micromamba installs entirely under `$HOME`, no root needed. All WSL tool invocations now go through `common/wsl.py`'s `run_in_conda_env`, which activates this env. |
| 2026-10-14 | GraphPart's identity denominator (`-dn`) set to `full` (GraphPart's own default), not `shortest` (which would have matched CD-HIT's own identity definition) | First attempt used `shortest` for cross-stage consistency with CD-HIT, and GraphPart failed outright ("Impossible to generate the desired 5 partitions... loss of 4 complete partitions"). Root cause, confirmed empirically: 71% of CD-HIT representatives are under 10 AA, and `shortest`-denominator identity for very short peptides is dominated by chance matches, collapsing the partition graph into one component. Tested length floors (7 AA still fails, 8 AA "succeeds" but gives a degenerate 357/2/5/1/1 split, 10 AA gives a clean split but throws away 71% of the pool) before trying `full`, which resolved the collapse cleanly on the complete 925-sequence pool with no data loss from a length floor. CD-HIT (90% identity, redundancy removal) and GraphPart (40% identity, leakage prevention) are different problems; they don't need the same identity definition. |
| 2026-10-14 | GraphPart splits are label-stratified by evidence tier (`-ln tier`, via `write_stratified_fasta`'s `\|tier=E1`/`\|tier=E2` FASTA headers), not left unstratified | An unstratified 5-fold split put 86% E1 in fold 0 vs 34% E1 in fold 4 — a real confound for any per-fold metric comparison in FR3/FR4/FR6. Stratifying narrowed the range to 44–64% E1 across folds, at the cost of less even fold sizes (124–266) and slightly more sequences excluded for homology (91 vs 84). Not requested explicitly, but cheap and clearly worth it; flagged here for visibility rather than silently applied. |
| 2026-10-14 | FR1 declared technically accepted and frozen as `pp1_baseline_v1`, with scientific/supervisor sign-off tracked as a separate, still-open item rather than bundled into the same status | AGENTS.md rule #3 requires acceptance evidence before marking a task complete, and that evidence (reproducibility, provenance chain, leakage checks, full-file tests) is now in hand — see `fr1_acceptance_report.md`. But conflating "the pipeline is correct and reproducible" with "the conclusions are supervisor-approved" would overclaim; the four pending-approval items (fr1_acceptance_report.md §10) are listed separately so neither status gets confused for the other. |
| 2026-10-14 | `data_registry.csv` (Bucket 1.1/1.2) is explicitly logged as NOT done, rather than fabricating one or quietly treating the per-stage provenance logs as a substitute | No formal source registry (IDs, license, access date, release/commit hash) was ever built; `fr1_positive_pool_provenance.jsonl` and this file capture run-level provenance, which is not the same artifact. Inventing placeholder registry content (e.g. a guessed access date) would be worse than naming the gap. Flagged in `fr1_acceptance_report.md` §4/§9 for separate follow-up, out of Bucket 1.7's scope. |
| 2026-10-14 | Fixed a real cross-platform reproducibility bug found while starting FR2: every CSV/JSON write in run.py/freeze.py now pins `lineterminator="\n"`/`newline="\n"` explicitly, and a new `.gitattributes` (`data/** -text`) stops git from re-expanding line endings on checkout. `pp1_baseline_v1` was regenerated in place (not re-versioned) to pick up the fix | pandas' `to_csv` and Python's default text-mode `open()` both translate `\n` to `os.linesep` on write, which is CRLF on Windows — so every checksummed artifact's SHA-256 depended on which OS happened to run the pipeline, silently breaking the freeze/reproducibility guarantee `curation/freeze.py` and `test_fr1_reproducibility.py` exist to provide. Caught via a routine fresh re-run on a new branch (`feat/challenge-pools-setup`), which failed `test_fr1_freeze_acceptance.py` and `test_fr1_reproducibility.py` — i.e., the acceptance tests built in Bucket 1.7 did their job. Regenerating `pp1_baseline_v1` in place (rather than minting `pp1_baseline_v2`) was judged correct per AGENTS.md rule #4's spirit: nothing had consumed v1 yet (it was one session old, pre-FR2), so there was no prior work to protect by versioning a bug fix — all file *contents* are unchanged, only their byte-level line-ending encoding was corrected. |
| 2026-10-14 | C1's "5,000 records" acceptance criterion is satisfied at the FASTA-entry level (3,786 unique sequences retained, not resampled for uniqueness) | Confirmed with the project owner. Short 4–50 AA fragments legitimately repeat across species; forcing uniqueness would mean a live UniProt resample, more work for a result the Planner doc doesn't clearly demand. Documented explicitly so the record-vs-unique distinction isn't silently glossed over if this dataset's size is cited later. |
| 2026-10-14 | C1 leakage (`DRVYIHPF`) resolved by a 1-for-1 deterministic swap from the already-saved candidate pool, screened against all 1,205 FR1 positives *and* the 179 conflicts (not just the 834-sequence frozen split) | Conservative screening confirmed with the project owner — a conflicted sequence might still be a real positive under a different reading of the evidence, so it's excluded from the "safe to use as a decoy" set too. No live UniProt query was needed since `uniprotkb_candidates.fasta` (the original 8,830-candidate universe) was already saved locally; re-applying the documented secondary blocklist to it reproduced exactly 8,233 kept / 597 excluded, matching `stage_c1_provenance.txt` precisely, before any new candidates were drawn. |
| 2026-10-14 | The corrected C1 pool is a new processed-tier artifact (`data/processed/c2_pu/stage_c1_decoys.fasta`) under the same canonical filename; the raw, still-contaminated original is left untouched at `data/raw/c2_pu/UniProt_decoys/stage_c1_decoys.fasta` | Explicit instruction: preserve the original as historical evidence, version the corrected artifact, rather than editing raw data in place. Mirrors the raw-vs-processed pattern already used for the FR1 positive pool (raw Multi-AOP/AnOxPePred CSVs vs. processed `aop_positives_*.parquet`). |
| 2026-10-14 | PyTorch installed CPU-only (not CUDA) in the `pu_aop` env, despite a real, verified GPU (RTX 4050, 6GB VRAM) being present | Confirmed with the project owner. A full CUDA build (`cu128` + cuDNN + cuBLAS, ~2.5GB) measured at ~45-60 min over this connection's ~700KB/s throughput; `esm2_t12_35M_UR50D`'s actual workload (a few thousand short peptides) runs in well under a second on CPU alone (measured: 0.096s for 5 sequences). GPU would not meaningfully help this task. `torch.cuda.is_available()` correctly reports `False` — no GPU acceleration is claimed anywhere. Revisit if a larger ESM-2 checkpoint is adopted later. |
| 2026-10-14 | `common/embeddings.py` (imports torch) is never imported directly into `run.py` (which runs on the Windows-side Python that has no torch) — the actual inference runs inside WSL's `pu_aop` env via a standalone `esm2_cli.py` entrypoint, invoked through `common/wsl.py`'s `run_in_conda_env` | Importing embeddings.py's module-level `import torch` into run.py's top-level imports would have broken every existing command (`fr1-positives`, `fr1-cluster`, etc.) the instant Windows tried to import torch. Mirrors the exact subprocess pattern already used for CD-HIT and GraphPart, which are also WSL-only. `pytest` was added to the `pu_aop` env specifically so the new torch-dependent tests (`test_embeddings.py`) can actually execute for real there, while still skipping cleanly (not failing) when the main suite runs from the Windows `.venv` via `pytest.importorskip("torch")`. |
| 2026-10-14 | `embed_sequences()` validates every sequence against the standard 20-letter alphabet by default and raises `AmbiguousResidueError` (naming every offending peptide_id/sequence/residue) rather than embedding or dropping non-standard residues (X/B/Z/U) silently; `validate_alphabet=False` is an explicit, named opt-out | Explicit instruction: ambiguous residues must never be silently translated. The actual *policy* (how C1's 260 non-standard sequences, and any future C2/C3/positives cases, should be handled) has NOT been decided — this only guarantees the decision can't be skipped accidentally once full feature generation starts (Known Issues #9/#10). |
| 2026-10-14 | Representation layer frozen at 12 and embedding dimension at 480, both confirmed by directly inspecting the loaded `esm2_t12_35M_UR50D` model's `num_layers`/`embed_dim` attributes (and `load_embedder` now asserts the dimension at load time) rather than assumed from the checkpoint name | The BOS/EOS/PAD token layout (`prepend_bos=True`, `append_eos=True`, residues at positions `1..len(seq)`) was likewise confirmed by tokenizing two real test sequences and inspecting the token tensor directly, not inferred from fair-esm's documentation. Matches the project's established practice (GraphPart's CLI/denominator semantics were verified the same way in Bucket 1.6) of verifying third-party tool behavior empirically before writing code against it. |

| 2026-10-14 | Standard-20-amino-acid-alphabet policy approved: X/B/Z/U sequences are ineligible for the ESM-2/physicochemical modeling pipeline project-wide, never silently substituted or translated | Explicit project-owner approval. Closes the policy gap `embed_sequences()`'s `AmbiguousResidueError` was deliberately left open pending (Known Issues #9/#10). Verified empirically that only C1 was affected (260/5,000 records) — FR1 positives, the 179 conflicts, and the external control already contain zero non-standard-alphabet sequences. |
| 2026-10-14 | C1's 260 non-standard-alphabet records fixed by `clean_c1_alphabet()`, starting from the v1 leakage-clean pool (not the raw original), swap-not-resample, seed 42, re-screened against the blocklist + all 1,205 positives + 179 conflicts + the alphabet requirement itself | Mirrors the exact pattern already used and accepted for the `DRVYIHPF` leakage fix. 2,082 eligible standard-alphabet replacements were available against 260 needed, confirmed before writing any replacement code — no shortfall, so the documented stop-and-ask condition never triggered. |
| 2026-10-14 | The alphabet-fix output is a separately versioned artifact set (`stage_c1_decoys_v2.fasta` + `c1_accession_map_v2.csv` + `c1_alphabet_*_log.csv` + `c1_alphabet_fix_report.json`); the existing accepted v1 artifacts are left untouched rather than overwritten, and `stage_c1_decoys_v2.fasta` is now the canonical artifact for all future C1 consumption | Explicit instruction: preserve the existing accepted version, don't overwrite it in place. Mirrors the raw-vs-processed and `pp1_baseline_v1`-vs-future-`v2` versioning patterns already established elsewhere in this component — old version kept for historical diffing, canonical "latest" reference moves forward, logged rather than silently swapped. |

| 2026-10-14 | C2 sourced from Peptipedia's full Zenodo database dump (281MB plain-text `pg_dump`), not the web app's per-activity download button | The web app's filtered download is a client-side button calling an undocumented endpoint behind Cloudflare bot protection — confirmed unreachable by an automated browser session (selection persisted, button click registered, but no corresponding network request was ever captured after multiple attempts). The Zenodo dump is versioned, checksummable, and -- being plain text, not a binary dump -- parseable in pure Python without installing a database server, so it doesn't actually require standing up new infrastructure despite being the "bulk" option AGENTS.md rule 6 generally cautions against. |
| 2026-10-14 | The 281MB Peptipedia raw dump is excluded from git (`data/raw/c2_pu/Peptipedia/*.sql.gz` in `.gitignore`); its SHA-256 and Zenodo DOI are recorded in the provenance log instead | Committing it would make `git push` fail outright on GitHub's 100MB-per-file limit (no Git LFS configured). Same "don't commit large binary artifacts" principle as ESM-2's pretrained weights — the checksum + DOI make it independently re-downloadable and byte-verifiable without needing it in version control. |
| 2026-10-14 | C2 excludes any peptide carrying Peptipedia's antioxidant activity tag (id 41, "Anti oxidative") regardless of whether that tag itself is predicted or experimentally reported | Mirrors C1's conservative leakage rule: a tag that might indicate real antioxidant activity is excluded outright rather than risk including a true positive in the "unlabeled, assumed non-antioxidant" pool, which would be a correctness violation of AGENTS.md rule 1, not just noise. |
| 2026-10-14 | C2's 2,000-record sample was drawn entirely from Peptipedia peptides with at least one *experimentally-reported* (non-predicted) non-antioxidant activity tag, not the much larger ML-predicted-only tier | Mirrors the project's existing E1>E2 evidence-tier precedence (real/primary evidence preferred over inferred). The experimental tier (66,506 eligible) comfortably supplied the full 2,000 without needing to fall back to the 2.66M predicted-only tier; documented as a deliberate tier choice, not a default. |
| 2026-10-14 | C2 is not yet cross-referenced against AODB or DFBP specifically (Planner Bucket 2.2 checklist item left open) | Peptipedia integrates 76 named source databases (confirmed by inspecting its `source` table directly) and neither AODB nor DFBP is among them. Acquiring and cross-checking those two resources is separate, unstarted follow-up work -- flagged rather than silently treated as covered by Peptipedia's internal antioxidant tag alone. |

*(Add new rows here, do not delete old ones — this is a historical log.)*
