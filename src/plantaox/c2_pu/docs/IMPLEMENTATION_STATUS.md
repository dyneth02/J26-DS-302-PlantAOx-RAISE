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

### Bucket 2, Task 2.3 — C3 ESM-2 Hard-Challenge Pool (fold-safe construction)
- **Status: core pool built and acceptance-tested; AODB/DFBP/BIOPEP-UWM screen explicitly not done
  (same gap as C2).** 2,325 unique hard-challenge sequences (the deduplicated union of 5 fold-specific
  top-2,000 selections), standard alphabet, 3–50 AA, zero exact-sequence overlap with FR1's 1,205
  positives, the 179 conflicts, C1, or C2.
- **Fold-safety is the methodological core of this task, confirmed explicitly with the project owner
  before implementation began.** A naive single global centroid (mean of all 834 training positives)
  would let fold *k*'s own held-out positives influence which candidates get selected as fold *k*'s
  "hard challenges" — a selection-leakage channel that survives even when no C3 sequence exactly or
  near-exactly matches a held-out positive, because the *choice* of which candidates look hard was
  itself informed by the thing being held out. Fixed by computing **5 separate centroids**
  (`curation/c3.py::compute_fold_centroids`), each the mean of only the 4 *other* training folds'
  positives, and ranking/selecting the shared candidate universe separately per fold. Verified
  empirically on the real cached embeddings (not just the synthetic unit tests): fold 0's centroid
  used exactly 710 of 834 positives (excluding fold 0's own 124), matched `compute_fold_centroids`'s
  output exactly, and differs measurably (cosine distance ≈4.15e-05 — small in magnitude here, but a
  real, non-zero leakage channel that the fold-safe design eliminates by construction rather than by
  hoping it's negligible) from the naive all-positives centroid.
- **Candidate universe: UniRef50 via UniProt's REST API**, not the ~13GB bulk FASTA (same reasoning
  already rejected for C1 — see `PU_AOP_RESEARCH_CONTEXT.md` §4). Query `identity:0.5 AND length:[3 TO
  50]`, sorted `id asc` for deterministic pagination, paginated via UniProt's cursor-based `Link`
  header. 25,000 candidates fetched (confirmed via `X-Total-Results`: 870,941 total clusters exist in
  this length window, so 25,000 is a bounded, documented sample, not the full space). **UniRef50's
  search index has no `keyword:` field** (confirmed empirically — the API returns "'keyword' is not a
  valid search field" for this endpoint) — unlike C1's UniProtKB query, so the bioactivity exclusion
  relies entirely on the secondary free-text blocklist already used for C1/C3, applied to UniRef
  cluster names. Expected to catch fewer matches here (most UniRef50 representatives are
  unreviewed/generically-named TrEMBL entries), not a bug.
- **Network resilience, learned from this session's own failures:** the first fetch attempt hit an SSL
  handshake timeout partway through pagination (this connection has now truncated two different
  large downloads this session — see Bucket 2.2's Zenodo dump). Added retry/backoff
  (`curation/uniref.py::fetch_uniref50_page`) before re-running rather than hoping it wouldn't
  recur; the retried fetch completed successfully (214s, absorbing at least one transient failure).
- **Embedding architecture reuses Bucket 3.2's WSL-subprocess pattern, extended (not replaced) to
  cache raw vectors.** `esm2_cli.py` gained an optional `save_embeddings_path` field (unused by the
  existing smoke test, which still writes summary-only output) that writes a compressed `.npz` of the
  raw embedding matrix — needed here because centroid construction and ranking genuinely require the
  vectors, not just summary statistics. These caches
  (`data/interim/c2_pu/c3_{positive,candidate}_embeddings.npz`) are gitignored, same "don't commit
  large embedding arrays" rule as model weights; shapes/counts are recorded in `c3_build_report.json`
  instead.
- **A real bug caught by code review before it ran:** `run_fr2_c3_build(force_cpu=...)` initially
  accepted the parameter but never passed it through to the embedding helper, which hardcoded
  `force_cpu=False` — silently making the parameter a no-op. Fixed before the first real run, not
  after.
- **Export design reinterprets the Planner's "export C3 FASTA/CSV" as fold-aware, not a single
  unlabeled pool** — flagging this explicitly as a deliberate reinterpretation, not a silent
  deviation: `stage_c3_esm2_hard_challenges.fasta` is the deduplicated union of all 5 folds'
  selections (2,325 records from 5×2,000=10,000 selection-rows — substantial overlap across folds,
  expected since removing 1/5 of 834 positives barely moves an 834-point mean), while
  `c3_similarity_ranking.csv` records every (fold, peptide, rank, cosine similarity) row explicitly.
  **Any future FR3/FR4/FR6 training code must filter this ranking file to its own fold's rows before
  using C3 as that fold's hard-challenge set** — using a different fold's selection, or the union
  FASTA without the per-fold filter, would silently reintroduce the exact leakage this construction
  exists to prevent. Flagging this contract clearly here since it's easy to get wrong later.
- **Tests:** 11 unit tests (`test_c3.py` for fold-centroid/ranking logic including the fold-exclusion
  property itself; `test_uniref.py` for the paginated fetch against a mocked API) plus 7 full-file
  acceptance tests (`test_fr2_c3_build_acceptance.py`, including byte-identical reproducibility and a
  per-fold rank/sort-order check), all gated to skip cleanly when the (gitignored) raw candidates or
  built pool aren't present locally.
- **Known gap, explicitly not done:** same as C2 — the Planner's "screen against AODB, DFBP,
  BIOPEP-UWM" item. Only the FR1 positive pool, 179 conflicts, C1, and C2 are screened for exact-
  sequence overlap (Known Issue #11, now also covering C3).

### Bucket 2, Task 2.4 — Pool Contamination and Leakage Audit
- **Status: audit complete and re-runnable; NOT technically accepted — two findings require a
  project-owner decision before FR2 can be marked complete (see below). `ready_for_technical_acceptance:
  false` is written directly into `fr2_pool_audit_report.json` so this can't be silently glossed over
  in a later summary.**
- **Authoritative sources used (verified, not assumed):** `pp1_baseline_v1`'s own checksummed copies
  of `aop_positives_provisional.parquet` (1,205), `label_conflicts_anox_vs_multiaop.csv` (179), and
  `anoxpepred_inactives_clean.csv` (38) — `verify_frozen_baseline()` re-confirmed all 10 frozen files
  match their recorded SHA-256 before anything else ran. `stage_c1_decoys_v2.fasta` (not v1),
  `stage_c2_bioactive_unlabeled.fasta`, and `stage_c3_esm2_hard_challenges.fasta` (the union, plus
  `c3_similarity_ranking.csv` for fold-level detail).
- **Full sequence-integrity audit (`curation/audit.py::sequence_integrity_report`), all 6 pools:**
  zero duplicate IDs and zero non-standard-alphabet sequences everywhere. **C1 confirmed to retain
  1,215 record-level duplicates by design** (5,000 records / 3,785 unique sequences) — this was
  already a confirmed decision, re-verified here, not a new finding. **4 of the 179 conflict records
  are 2 AA long** (KP, IR, PP, LK), outside the project's own 3–50 AA window — a benign inconsistency
  (the conflict log was built before the length window was applied to the positive pool; these 4 were
  never valid positive-pool candidates regardless of their conflict status) rather than a bug with
  consequences, since conflicts are only ever used as an exclusion/screen set, not a training source.
- **Full pairwise exact-sequence overlap matrix, all 6 pools** (`audit_exact_overlap_matrix.csv` +
  `audit_exact_overlap_detail.csv`): **FR1 positives have zero exact overlap with C1, C2, or C3** (the
  one invariant that must never fail — independently re-verified, not just trusted from construction
  time). **Finding requiring a decision: C1 and C2 share 8 exact-sequence duplicates** — neither pool's
  construction ever checked against the other (C1 screened against FR1 positives/conflicts only; C2
  likewise). None of the 8 are antioxidant-tagged in C2 (tags are Therapeutic/Metabolic/Hormone/
  Molecular binding/Antimicrobial/Other) and none are themselves FR1 positives or conflicts — so this
  is not a labeled-positive leak, but it is a correctness issue for treating C1 and C2 as independent
  "challenge" populations. **Not fixed — pending your decision** (see proposed options in the report).
- **External known-AOP screening:** **BIOPEP-UWM: done, 990 standard-alphabet antioxidative reference
  peptides, scraped from its open-access "search by activity" page (no API exists; citation:
  Minkiewicz et al. 2019, Int J Mol Sci 20(23):5978) — zero hits in C1, C2, or C3.** 700/1,205 FR1
  positives and 22/179 conflicts independently corroborated as antioxidative by BIOPEP-UWM (a positive
  validation signal for FR1, not a problem). 2 external-control ("experimentally inactive") peptides
  also hit BIOPEP-UWM's antioxidative set — the same "contradictory labels across databases"
  phenomenon already documented for the 179 conflicts, worth noting not acting on. **AODB: genuinely
  inaccessible** — `https://aodb.idruglab.cn` returned HTTP 502 from its own nginx plus an expired TLS
  certificate, confirmed via direct `curl` with and without certificate verification. **DFBP: no
  working hosting URL discoverable** (paper found, PubMed 35552640, but neither the paper's page nor
  web search surfaced an access link; its own PubMed page is itself blocked by a cookie wall to
  automated access). Neither substituted with an unrelated database, per explicit instruction.
- **Homology/leakage analysis beyond exact match — the single most important methodological finding
  of this audit.** A first CD-HIT pass at 40% identity (GraphPart's own threshold) produced 685
  "cross-pool" clusters — but inspection showed this is dominated by a known artifact: CD-HIT's
  percent-identity for a short/long pair is computed over the SHORTER sequence's length, so a random
  3-AA fragment (only 8,000 possible tripeptides exist) will, by chance, be a 100%-identical substring
  of *some* unrelated 50-mer across a ~9,500-sequence pool almost every time. Confirmed concretely: the
  single largest 40%-identity cluster (351 members) bundled "CQC" (3 AA) together with clearly
  unrelated 37–41 AA ribosomal-protein-family sequences via chained greedy matching — not biological
  homology. **Re-ran at 90% identity with an explicit length floor (≥15 AA on both sides) for anything
  to count as an interpretable homology candidate** (`cross_pool_homology_clusters`,
  `length_floor_for_interpretation` parameter) — of 470 raw cross-pool clusters, 455 are short-fragment
  artifacts (reported, not hidden) and **15 are genuine candidate homology pairs**, saved in full in
  `audit_cross_pool_homology_clusters.csv`. **Finding requiring a decision: one of these 15 is a
  near-duplicate of an assay-confirmed FR1 positive sitting in C2.** `C2-EFDBC5460B`
  ("LYQEPVLGPVRGPFP", tagged Therapeutic/Metabolic/Anti-diabetic) is 90–100% identical (≥15 AA) to four
  FR1 positives including `AOP-032318CCA7` ("YQEPVLGPVRGPFPIIV", evidence_tier **E1**,
  assay-confirmed) — a casein/whey-derived antioxidant peptide family. This is a homology-based
  leakage risk that the construction-time exact-sequence screens could not catch by design. The other
  14 candidates are mostly C1↔C2 (cysteine-rich/protamine-like and zinc-finger-like peptide families
  independently drawn from overlapping UniProtKB/Peptipedia source material) — see the CSV for the
  full list, not reproduced here. **Not fixed — pending your decision.**
- **Cross-fold positive homology:** GraphPart's own zero-residual-violation guarantee (already
  established in Bucket 1.6/1.7) covers homology *within* the positive pool across folds — this audit
  does **not** re-derive that, and explicitly does not treat it as proof that C1/C2/C3 are
  homology-independent *from* the positive pool (that's the separate check immediately above, which
  found the one real hit).
- **C3 fold-specific contract: formally re-verified against the real, full artifacts (not re-trusted
  from Bucket 2.3), via `curation/c3.py::validate_c3_fold_contract`.** All 5 folds confirmed to have
  exactly 2,000 ranking rows each, ranks forming a contiguous unique 1–2,000 sequence per fold, every
  one of the 5 centroids reconstructed from exactly that fold's OTHER 4 folds' positives (fold sizes:
  124/134/137/173/266 held out, 710/700/697/661/568 used for training — all 5, not just fold 0 as
  spot-checked in Bucket 2.3), and the union FASTA's peptide IDs set-equal to the ranking CSV's unique
  peptide IDs in both directions. **A new safe accessor, `curation/c3.py::load_fold_challenges(path,
  fold_id)`, is now the only sanctioned way to read C3 for training** — `fold_id` has no "give me
  everything" default, and there is deliberately no function anywhere in the module that returns the
  cross-fold union; a test (`test_there_is_no_function_in_this_module_that_returns_all_folds_at_once`)
  guards against one being added later without deliberate renaming.
- **Tests:** 13 unit tests for `curation/audit.py` + `curation/biopep.py` combined, 9 new C3-contract/
  accessor tests, 9 full-file acceptance tests (`test_fr2_pool_audit_acceptance.py`), all gated to skip
  cleanly when inputs aren't present. Full suite: 131 passed, 1 skipped, zero regression.
  `pp1_baseline_v1` and all accepted C1/C2/C3 artifacts confirmed untouched via `git status` — this
  audit stage is read-only by construction (never writes to any pool file, only to new `audit_*`
  report files).
- **Not yet done, explicitly out of this pass's scope:** no dataset change has been made in response
  to either finding above — both are reported with proposed options and await your decision per the
  explicit "pause before a material dataset change" instruction.

### Bucket 2, Task 2.4 — Contamination and Leakage Audit Resolution (Decisions A & B)
- **Status: both approved findings resolved; audit rerun against the corrected canonical pools;
  `ready_for_technical_acceptance: true`.** Canonical artifacts for all future consumption are now
  **`stage_c1_decoys_v3.fasta`** and **`stage_c2_bioactive_unlabeled_v2.fasta`** — v1/v2 C1 and the
  original C2 remain on disk, untouched, as historical evidence (confirmed via `git status` and a
  dedicated preservation test).
- **Decision A (C1/C2 exact overlap) — resolved via `clean_c1_cross_pool_overlap` /
  `run_fr2_c1_cross_pool_fix`.** The 8 unique overlapping sequences corresponded to **11 actual C1
  FASTA records** (one sequence appeared 3× and one 2× among C1's intentional natural duplicates) —
  confirmed empirically, not assumed, exactly matching the explicit warning that unique-sequence and
  record counts can differ. All 11 removed from C1 (C2 keeps every one, per the approved "preserve
  C2's biological-annotation precedence" policy) and replaced 1:1 from the same
  `uniprotkb_candidates.fasta` universe used by every prior C1 fix, now screened against FR1
  positives, the 179 conflicts, C2, **and C3** (the new requirement). 1,799 eligible replacements were
  available against 11 needed — no shortfall. Result: still exactly 5,000 records; unique-sequence
  count shifted from v2's 3,785 to **3,788** (removing 8 unique duplicate-bearing sequences, adding 11
  new unique replacements), standard alphabet, 3–50 AA, zero exact overlap with
  positives/conflicts/C2/C3 (all re-verified directly against the output file, not inferred from the
  fix logic alone).
- **Decision B (C2 homologous to an E1 positive) — resolved via `run_fr2_c2_cross_pool_fix`.**
  **Alignment evidence obtained before deciding anything**, per instruction: EMBOSS `needle`
  (EBLOSUM62, gapopen=10, gapextend=0.5) global alignment of `C2-EFDBC5460B` ("LYQEPVLGPVRGPFP", 15
  AA) against `AOP-032318CCA7` ("YQEPVLGPVRGPFPIIV", 17 AA, evidence_tier **E1**, assay-confirmed)
  gives **14/18 identical aligned positions = 77.8% full-length identity, 22.2% gaps** (a 1-residue
  N-terminal offset and a 3-residue C-terminal truncation around a 14-residue identical core) — a
  materially different number from CD-HIT's own 93.33% (computed over the shorter sequence only),
  both reported rather than picking one. This is not a borderline call: 14 contiguous identical
  residues is overwhelming evidence of the same underlying biological peptide, not chance. Excluded
  **as a conservative leakage-risk decision only** — the exclusion log explicitly states this is NOT
  a claim that the peptide is experimentally antioxidant-active, and preserves the original Peptipedia
  evidence (activity tags, predicted/experimental flag) in full. Replaced 1:1, deterministically (seed
  42), from the same experimentally-reported Peptipedia tier Task 2.2 drew from (64,122 eligible after
  the expanded screen — still comfortably sufficient), screened against FR1 positives, 179 conflicts,
  the remaining 1,999 C2 sequences, **C1 v3** (run after Decision A, specifically so this replacement
  could never collide with Decision A's own replacements), and C3. Result: still exactly 2,000 unique
  records, standard alphabet, 3–50 AA, zero exact overlap with positives/conflicts/C1 v3/C3.
- **The remaining 14 "other" homology candidates were reviewed individually, not bulk-excluded by CD-HIT
  cluster membership** (per explicit instruction). **3 resolved automatically as a side effect of
  Decision A** (their shared member was one of the 8 exact duplicates, now gone from C1); **11 remain**
  as genuine (≥15 AA, not short-fragment-artifact) near-duplicate C1↔C2 pairs. All 11 are C1↔C2 only —
  **none involve FR1 positives**, so there is no label-leakage mechanism, unlike Decision B. Inspected
  each family: ribosomal bL36-type zinc-ribbon proteins, protamine-like cationic peptides, an
  Antennapedia-homeodomain-type cell-penetrating peptide, a β-actin fragment, a proline-rich
  gliadin/gluten-like repeat, and cysteine-rich defensin-like peptides — none are antioxidant-
  mechanism peptide families (no Trp/Tyr/His/Cys free-radical-scavenging motif pattern consistent with
  the FR1 positive pool's own composition). **Recommendation (not unilaterally acted on): accept and
  document as a known, bounded limitation**, the same treatment already given to C1's intentional
  record-level duplicates — excluding near-duplicate *families* (not just exact matches) from two
  mutually-unlabeled pools has no established precedent in this project and risks an unbounded,
  ever-tightening exclusion spiral (AGENTS.md's "don't keep iterating indefinitely" principle).
  Flagged for the project owner to override if a stricter policy is wanted; not applied unilaterally.
- **Audit fully rerun against the corrected pools** (`fr2-pool-audit`), canonical pool labels updated
  to `C1_v3`/`C2_v2` throughout every output file — not a hand-edited flag flip.
  `bucket_2_4_resolution_status` in `fr2_pool_audit_report.json` records both decisions as RESOLVED
  with pointers to the fix reports; `contamination_requiring_decision` is now `{}`.
  `ready_for_technical_acceptance` is computed from the live artifacts (both decisions' post-conditions
  checked directly), not a stored boolean someone could forget to flip back.
- **A real bug caught by the post-fix test run, fixed before being called "acceptance-tested":**
  with zero overlaps left to report, `pd.DataFrame([])` wrote a column-less, unreadable
  `audit_exact_overlap_detail.csv` — caught immediately by the acceptance test suite (not manually),
  fixed by passing explicit column names so the empty-case CSV still has a valid header.
- **AODB/DFBP remain recorded as inaccessible** (unchanged from the first audit pass — re-confirmed,
  not re-attempted, since nothing about their availability would have changed); **BIOPEP-UWM remains
  screened** against the same 990-sequence reference, zero hits in C1 v3/C2 v2/C3; the **2
  BIOPEP-UWM-vs-AnOxPePred-inactive-control annotation conflicts are preserved as documented
  uncertainties**, not resolved or acted on, per instruction.
- **C3 was NOT rebuilt.** Decided and verified, not assumed: both fixes proactively screened their
  replacement candidates against C3's existing 2,325-sequence union before writing anything, so C3's
  own membership, ranking, and fold-safety guarantees needed no changes — confirmed directly (zero
  exact overlap between C3 and both new canonical C1 v3/C2 v2) rather than inferred. `load_fold_
  challenges(path, fold_id)` is unchanged and remains the only sanctioned downstream accessor.
- **Tests:** 10 new/updated audit-acceptance tests (now asserting the resolved, zero-contamination
  state) + 10 new cross-pool-fix acceptance tests (2 unit in `test_pools.py`, 8 full-file, including
  byte-identical reproducibility for both fixes — the C2 fix's reproducibility test re-parses the full
  Peptipedia dump, ~86s). Full suite: 142 passed, 1 skipped (torch), zero regression.
- **Evidence-based recommendation: Task 2.4 is ready for technical acceptance.** Both project-owner-
  approved findings are resolved and independently re-verified against the output artifacts (not
  trusted from the fix logic alone); the one open methodological judgment call (the 11 remaining
  C1↔C2 near-duplicate families) is surfaced with full evidence and a clear recommendation, not
  silently decided or hidden. AODB/DFBP remain the only incomplete external checks, both for
  documented access reasons outside this project's control.

### Bucket 2, Task 2.5 — Biological Distribution and Shortcut-Bias Checks
- **Status: complete.** Compared FR1's 1,205 accepted positives against the corrected canonical
  C1 v3 (5,000)/C2 v2 (2,000)/C3 union (2,325) on length, amino-acid composition, and 4 independently-
  computed descriptors (molecular weight, net charge at pH 7, GRAVY hydrophobicity, aromaticity).
- **Not Bucket 3.1's descriptor pipeline, deliberately.** `curation/distribution_audit.py` implements
  its own small, documented descriptor set (standard Kyte-Doolittle/Expasy-style formulas) purely for
  this comparison — Bucket 3.1's `common/descriptors.py` (the project's canonical 15-descriptor
  feature-extraction module) remains an empty scaffold stub, untouched, so this task doesn't silently
  do Bucket 3.1's job or create two divergent descriptor implementations.
- **Every pool differs significantly from FR1 positives on every descriptor tested** (two-sample
  Kolmogorov-Smirnov, FR1 positives vs. each of C1/C2/C3): KS statistics 0.63–0.86 on
  length/molecular-weight, 0.27–0.42 on net charge, 0.14–0.27 on GRAVY, 0.25–0.34 on aromaticity, all
  with p-values effectively zero (smallest reported ~1e-322, i.e. below double-precision resolution).
  This is a real, quantified shortcut-bias risk, not a surprising discovery that invalidates the
  pools — length/charge/hydrophobicity differences between positives (short, often Pro-rich food-
  derived fragments) and the challenge pools (built from entirely different source distributions:
  reviewed UniProtKB, Peptipedia's broad bioactive corpus, UniRef50) were always structurally likely
  given how differently each pool was constructed; this task is what turns that intuition into a
  measured number for the FR2/FR6 report. Full per-pool/per-descriptor table:
  `distribution_ks_comparison.csv`.
- **Amino-acid composition confirms a specific, biologically-sensible signal, not noise:** FR1
  positives are markedly Proline-enriched (10.6%) vs. C1 (4.1%), C2 (5.6%), C3 (5.1%) — consistent
  with food-derived antioxidant/ACE-inhibitory peptide literature (casein/collagen-derived fragments).
  C2 is notably Cysteine-enriched (5.5%) vs. positives (1.4%), C1 (2.3%), C3 (2.6%) — consistent with
  Peptipedia's heavy representation of disulfide-stabilized antimicrobial/defensin peptides (Bucket
  2.2's own activity-tag distribution: Antimicrobial 805/2,000, Antibacterial 535/2,000). Full table:
  `distribution_aa_composition.csv`.
- **Shortcut-bias scan:** C1's 5,000 records span 1,708 distinct organisms (`c1_accession_map_v3.csv`),
  no single organism exceeding 2.1% share (*E. coli* K12) — no obvious single-organism shortcut. C2's
  2,000 records span 123 distinct activity tags, "Therapeutic" the largest at 14.4% (an expected broad
  parent category, not a narrow shortcut signal). **FR1 positives have no organism metadata at all**
  (Multi-AOP/AnOxPePred carry no per-record source-organism field) — explicitly documented as an
  unchecked gap, not assumed clean.
- **No exploratory UMAP/t-SNE produced this pass** — the Planner marks this step optional
  ("do not claim they prove separation"), and the KS-test results already give a more precise, directly
  interpretable answer to the same underlying question (are the pools distributionally distinct) than
  a 2D projection would; flagged as deferred, not silently skipped.
- **Length-stratified sampling was NOT implemented** — the Planner's checklist offers this as an
  alternative to "report residual mismatches," and report-the-mismatch is what was done here (hard
  re-sampling any of C1/C2/C3 by length now would be yet another dataset-version change, outside this
  task's read-only, report-only scope, and not requested).
- **Tests:** 9 unit tests (`test_distribution_audit.py`, including a sanity check that KS correctly
  distinguishes identical vs. obviously-different synthetic distributions) + 4 full-file acceptance
  tests. Full suite: 155 passed, 1 skipped, zero regression.

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
11. **C2 and C3 are not cross-referenced against AODB, DFBP, or BIOPEP-UWM** (Planner Bucket 2.2/2.3
    checklist items). Peptipedia v2.0 integrates 76 named source databases, confirmed by direct
    inspection of its `source` table — neither AODB nor DFBP is among them. C2's only antioxidant
    screen is Peptipedia's own internal "Anti oxidative" activity tag; C3's only screen is exact-
    sequence overlap against FR1 positives/179 conflicts/C1/C2. Acquiring and cross-referencing
    AODB/DFBP/BIOPEP-UWM specifically is unstarted, separate follow-up work for both pools.
12. **C3's fold-specific selections overlap heavily (2,325 unique sequences from 5×2,000=10,000
    selection-rows)**, because removing 1/5 of 834 training positives barely shifts the centroid
    (empirically measured cosine distance ≈4e-5 between a fold-safe and the naive all-positives
    centroid). This is expected given the pool's size, not a bug — but it does mean the fold-safe
    design's practical effect on final C3 membership is small even though the leakage channel it
    closes is real and structural. Worth noting in the FR2/FR6 report as a measured effect size, not
    just a methodological footnote.
13. **RESOLVED 2026-10-14 (Decision A).** C1 and C2's 8 exact-sequence duplicates (11 actual C1
    records) were removed from C1 and replaced, screened against FR1 positives/179 conflicts/C2/C3.
    Canonical C1 artifact is now `stage_c1_decoys_v3.fasta`. See Bucket 2.4 resolution section above.
14. **RESOLVED 2026-10-14 (Decision B).** `C2-EFDBC5460B` ("LYQEPVLGPVRGPFP") excluded as a
    conservative leakage-risk decision (needle-alignment-confirmed 77.8% full-length identity to an
    E1 positive) and replaced. Canonical C2 artifact is now `stage_c2_bioactive_unlabeled_v2.fasta`.
    **11 of the 14 other candidate C1↔C2 homology pairs remain** (3 resolved as a side effect of
    Decision A) — reviewed individually, recommended to accept as a documented limitation (no
    FR1-positive involvement, no plausible antioxidant mechanism in any of the peptide families
    involved); not unilaterally acted on, open to project-owner override. See Bucket 2.4 resolution
    section above.
15. **AODB and DFBP remain unscreened**, for a documented access reason rather than an unstarted
    task: AODB's server returned HTTP 502 + an expired TLS certificate; DFBP has no discoverable
    hosting URL. BIOPEP-UWM **is** screened (zero hits in C1 v3/C2 v2/C3). Revisit if either resource
    comes back online or a hosting URL for DFBP is found.

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
4. **Task 2.2 (C2) and Task 2.3 (C3) core pools are both built** — see Completed tasks above.
   Remaining for both: acquire and cross-reference AODB/DFBP/BIOPEP-UWM specifically (Known Issue
   #11), low/medium priority depending on how much the PP1 report leans on that specific checklist
   line versus the broader antioxidant-exclusion/leakage-screen arguments already satisfied.
5. **Bucket 2.4 is resolved and technically accepted** (`ready_for_technical_acceptance: true` in
   `fr2_pool_audit_report.json`, re-derived from the live artifacts). Canonical C1/C2 artifacts are
   now `stage_c1_decoys_v3.fasta` / `stage_c2_bioactive_unlabeled_v2.fasta` — update any new code to
   read these, not v2/the original C2. One open, non-blocking item: whether to act further on the
   11 remaining C1↔C2 near-duplicate families (recommended to accept as documented limitation; see
   Known Issue #14).
6. **Task 2.5 is complete** — see Completed tasks above. Every challenge pool differs significantly
   from FR1 positives on length/MW/charge/GRAVY/aromaticity (quantified via KS-test); this is a
   known, measured shortcut-bias risk for FR3/FR4 modeling to be aware of, not a defect to fix in
   FR2. UMAP/t-SNE and length-stratified resampling both deliberately deferred (see above).
7. **Bucket 2.6 (External Inactive-Control Preparation)** is next per the Planner sequence — the
   38-record AnOxPePred external control already exists (frozen in `pp1_baseline_v1`) but this
   bucket's own homology-boundary check against the positive pool hasn't been run as a dedicated
   stage yet. Not started.
8. **Bucket 3.1 (15 physicochemical descriptors)** can start any time in parallel — not blocked on
   anything above.
9. **FR3/FR4 training code consuming C3 must use `curation/c3.py::load_fold_challenges(path, fold_id)`**
   (not read the union FASTA or filter the ranking CSV by hand) to get that fold's hard-challenge set —
   flagging this contract here since it's the single easiest way to silently reintroduce C3's
   selection-leakage risk later.
10. Continue down the Bucket 1 → Bucket 2 → Bucket 3 → Bucket 4 sequence as defined in `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`, respecting the FR1+FR2-first priority.

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

| 2026-10-14 | C3 candidate-to-positive-centroid ranking uses 5 separate fold-specific centroids (one per GraphPart training fold, each excluding that fold's own held-out positives), not one global centroid over all 834 positives | Explicit project-owner instruction, confirmed before implementation: a global centroid would let a fold's own held-out positives influence which candidates get selected as that fold's "hard challenges," a selection-leakage channel distinct from ordinary sequence-identity leakage (survives even with zero exact/near-exact sequence overlap). Verified empirically on the real cached embeddings that the fold-safe and naive centroids measurably differ (cosine distance ≈4e-5), confirming the leakage channel is real, not merely theoretical. |
| 2026-10-14 | C3's exported FASTA is the deduplicated union of 5 independent fold-specific top-2,000 selections, with per-fold membership/rank/similarity recorded in a separate `c3_similarity_ranking.csv`, rather than a single unlabeled top-2,000 pool | Direct consequence of the fold-safety requirement above -- a single global "top 2,000" would have to be ranked by some single centroid, reintroducing the leakage the fold-specific design exists to prevent. Reinterprets the Planner's literal "select the top 2,000" wording as "top 2,000 per fold," flagged explicitly rather than silently narrowed. Downstream FR3/FR4/FR6 code must filter to its own fold's rows. |
| 2026-10-14 | C3's candidate universe is a 25,000-sequence UniRef50 REST query snapshot (`identity:0.5 AND length:[3 TO 50]`, sorted `id asc`), not UniRef50's ~13GB bulk FASTA or the full 870,941-cluster result set | Same reasoning already applied to C1 (AGENTS.md rule 6) -- a filtered, paginated REST query avoids an unnecessary multi-gigabyte download. 25,000 is a documented, bounded sample sufficient to supply 5×2,000 fold-specific selections (24,732 survived alphabet/length/blocklist/screen filtering) without needing the full space. |
| 2026-10-14 | `esm2_cli.py` gained an optional `save_embeddings_path` field that writes raw embedding vectors to a gitignored `.npz` cache, used only by C3 -- the existing smoke-test call path is unchanged (still summary-only) | C3's centroid/ranking logic genuinely needs the vectors themselves, unlike the smoke test which only needed to confirm shape/finiteness/determinism. Keeping it an opt-in field (rather than always saving vectors) preserves Bucket 3.2's explicit "never commit large embedding arrays" guarantee for the default path. |
| 2026-10-14 | The UniRef50 fetch and the full embed-and-select C3 build both needed a mid-run retry after a transient network failure (SSL handshake timeout; this is the second large download this session to hit this connection's instability, after Bucket 2.2's Zenodo dump) | Added explicit retry/backoff to `curation/uniref.py::fetch_uniref50_page` (5 attempts, exponential backoff) before re-running, rather than re-attempting the exact same fragile call and hoping. Both the candidate fetch and the embedding build subsequently completed successfully. |

| 2026-10-14 | Bucket 2.4's cross-pool homology scan uses CD-HIT at 90% identity with an explicit ≥15 AA length floor for a cluster to count as an interpretable "real" homology candidate, rather than a single global threshold applied uniformly | A first attempt at 40% identity (GraphPart's own threshold) produced 685 cross-pool clusters, confirmed on inspection to be dominated by a short-peptide artifact: CD-HIT's percent-identity for a short/long pair is computed over the shorter sequence, so random tripeptides (only 8,000 possible) trivially match as "100% identical" substrings of unrelated 50-mers by chance. The 90%+/≥15AA combination reduced 470 raw cross-pool clusters to 15 defensible candidates, confirmed by direct inspection to include real biological signal (e.g. a casein-derived antioxidant peptide family) rather than noise. |
| 2026-10-14 | BIOPEP-UWM's antioxidative reference set was acquired by scraping its own "search by activity" result page (990 standard-alphabet sequences), not via an API (none exists) or a bulk download (none offered) | Confirmed open-access, no registration required; the site's single-page search-result table for the "antioxidative" activity code (1,039 rows) is the only practical access path. Citation recorded (Minkiewicz et al. 2019) per the site's own request, not a formal redistribution license (none was found published). |
| 2026-10-14 | AODB and DFBP are documented as genuinely inaccessible rather than silently skipped or substituted with an unrelated database | AODB: confirmed via direct `curl` (with and without TLS verification) that its server returns HTTP 502 from its own nginx, plus an expired TLS certificate — a hard access failure, not a missed search. DFBP: no hosting URL discoverable via web search or its own PubMed record (itself blocked by a cookie wall to automated access). Per explicit instruction, not substituted with a different database without approval. |
| 2026-10-14 | Two findings (C1∩C2 8-sequence exact overlap; a C2 peptide's homology to an E1 FR1 positive) are reported with proposed options but NOT acted on, and FR2/Bucket 2.4 is marked `ready_for_technical_acceptance: false` in the audit report itself | Explicit instruction: request approval before a material dataset change, and a discovered issue must not be hidden merely to preserve an accepted record count. Both findings are real (independently verified, not probabilistic false positives) but resolving them changes accepted artifact counts, so the decision belongs to the project owner, not this audit. |
| 2026-10-14 | `curation/c3.py::load_fold_challenges(ranking_path, fold_id)` is the only sanctioned way to read C3 for FR3/FR4/FR6 training code; no function anywhere in the module returns the cross-fold union, and a test guards against one being added later under a confusable name | Explicit "mandatory" Step 5 instruction: prevent accidental misuse of the fold-safe construction by a future helper that "conveniently" loads the whole union as one fold's challenge set, which would silently reintroduce the exact selection-leakage the fold-specific centroids exist to prevent. |

| 2026-10-14 | Decision A: C1/C2's 8 exact-overlap sequences removed from C1 only (C2 keeps them), replaced 1:1 from the UniProtKB candidate universe, screened against FR1 positives/179 conflicts/C2/C3; canonical C1 is now `stage_c1_decoys_v3.fasta` | Project-owner-approved: "preserve C2's biological-annotation precedence." Confirmed the 8 unique sequences corresponded to 11 actual C1 FASTA records (some were among C1's intentional natural duplicates) before removing anything -- record-vs-unique counts verified empirically, not assumed equal. |
| 2026-10-14 | Decision B: `C2-EFDBC5460B` ("LYQEPVLGPVRGPFP") excluded from C2 as a conservative leakage-risk decision (not claimed inactive), replaced 1:1 from the experimentally-reported Peptipedia tier, screened against FR1 positives/179 conflicts/remaining C2/C1 v3/C3; canonical C2 is now `stage_c2_bioactive_unlabeled_v2.fasta` | Project-owner-approved, backed by a real EMBOSS needle alignment (77.8% full-length identity, 14/18 identical aligned positions, 22.2% gaps) against the E1-confirmed positive YQEPVLGPVRGPFPIIV -- not a borderline call. C1 v3 (not v2) was used as the cross-screen specifically so Decision B's replacement could never collide with Decision A's. |
| 2026-10-14 | The 14 other candidate C1<->C2 homology pairs found by the audit are NOT bulk-excluded by CD-HIT cluster membership; 3 resolved as a side effect of Decision A, 11 reviewed individually and recommended as an accepted, documented limitation rather than further exclusion | Explicit instruction: distinguish genuinely concerning biological similarity from short-sequence chance matches, and do not auto-exclude whole clusters. All 11 are C1<->C2 only (no FR1-positive involvement, so no label-leakage mechanism) and from peptide families (ribosomal/zinc-ribbon, protamine-like, homeodomain CPP, actin/gliadin fragments, defensin-like) with no plausible antioxidant mechanism. Presented with full evidence for project-owner override rather than silently decided either way. |
| 2026-10-14 | C3 was not rebuilt in response to Decisions A/B -- both fixes proactively screened their replacement candidates against C3's existing union before writing anything, confirmed by re-verifying zero exact overlap between C3 and the new C1 v3/C2 v2 | Avoids the cascading C3 rebuild the instructions flagged as a possible consequence, by preventing the problem at its source (the replacement-candidate screen) rather than reactively detecting and fixing it after the fact. `load_fold_challenges(path, fold_id)` needed no changes. |

| 2026-10-14 | Task 2.5's distribution comparison uses a small, independently-computed descriptor set (`curation/distribution_audit.py`: molecular weight, net charge at pH 7, GRAVY, aromaticity), not Bucket 3.1's 15-descriptor pipeline | Bucket 3.1's `common/descriptors.py` is still an empty scaffold stub (not started). Implementing it properly belongs to Bucket 3.1; Task 2.5 only needed enough descriptors to detect distributional shortcuts, so a narrower, clearly-labeled, independent implementation avoided either blocking on Bucket 3.1 or creating two divergent "canonical" descriptor implementations later. |
| 2026-10-14 | Distributional mismatch between FR1 positives and C1/C2/C3 reported via two-sample KS-test statistics, not solely via plots | Quantifies "how different" precisely (statistic + p-value per pool per descriptor) rather than relying on visual judgment of histogram overlays, which the Planner's own "do not claim [UMAP/t-SNE] prove separation" caution suggests is exactly the kind of imprecision this task should avoid. matplotlib was not installed for this (no plotting library was in the environment); one summary chart was rendered directly for the user via the session's visualization tool instead of adding a new project dependency for a single exploratory comparison. |

*(Add new rows here, do not delete old ones — this is a historical log.)*
