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
  as genuine (≥15 AA, not short-fragment-artifact) near-duplicate C1↔C2 pairs. **Re-verified precisely
  2026-10-14 (Task 2.6 follow-up):** 2 of these 11 CD-HIT clusters also contain short (3 AA) FR1-
  positive fragments as incidental members — but strictly as the same short-fragment chance-match
  noise already established (below the 15 AA interpretability floor), never as part of the ≥15 AA
  "real" homology relationship itself, which in all 11 clusters is C1↔C2 only. **Approved 2026-10-14
  by the project owner as a documented PP1 limitation**, conditional on exactly this confirmation
  (that the real, length-qualifying relationship never involves FR1 positives) — condition verified,
  not assumed. No label-leakage mechanism exists here, unlike Decision B. Inspected
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

### Bucket 2, Task 2.6 — External Inactive-Control Preparation
- **Status: complete and technically accepted.** Validated the frozen `pp1_baseline_v1`'s 38-record
  AnOxPePred external inactive-control set (re-confirmed count directly from the frozen artifact, not
  assumed) and ran a dedicated homology audit against the FR1 positive pool using real pairwise
  alignments (EMBOSS `needleall`), not CD-HIT percent identity.
- **Integrity confirmed:** 38 records, 38 unique IDs, 38 unique sequences, standard alphabet, all
  within 3–50 AA, stored lengths match actual sequence lengths exactly. **Zero exact-sequence overlap**
  with FR1 positives, the 179 conflicts, C1 v3, C2 v2, or C3 (re-verified independently here, not just
  carried over from Bucket 2.4's audit).
- **A real completeness bug caught and fixed before trusting any result:** EMBOSS `needleall`'s own
  default `-minscore 1.0` silently DROPS any aligned pair scoring below it from the output entirely —
  confirmed empirically (the first real run returned only 35,076 of the expected 38×1,205=45,790
  pairs). Fixed by setting `-minscore` far below any realistic score (`curation/homology_alignment.py`);
  the corrected run returned all 45,790 pairs, verified by an explicit count check that raises if any
  are missing (`run_fr2_external_control_build` now hard-fails rather than silently accepting a
  short result).
- **Homology audit result: zero genuine hits.** Using the same length-floor discipline established in
  Bucket 2.4 (≥15 AA for a percent-identity to be biologically interpretable, since shorter alignments
  are dominated by chance substring matches), **no external-control/positive pair reaches both ≥15 AA
  alignment length and ≥40% identity** (the Planner's proposed boundary) — the highest identity among
  length-≥15 AA pairs is 33.3%, well below threshold. 394 pairs *do* exceed 40% identity, but every one
  of them is a ≤12 AA short-fragment chance match (max alignment length 12), the same artifact already
  documented for Bucket 2.4's cross-pool scan — reported in full for transparency
  (`ext_control_homology_pairs.csv`, all 45,790 pairs), not hidden, but explicitly not counted as real
  homology.
- **Held-out evaluation-fold independence confirmed, not merely assumed:** since the global screen
  (all 1,205 positives) found zero real hits, and any GraphPart fold's held-out positives are a strict
  subset of those 1,205, there is structurally no possible fold-specific violation either — stated
  explicitly in the report with that reasoning, plus a per-hit fold lookup column that would have
  populated if any real hit existed.
- **The 2 BIOPEP-UWM-vs-AnOxPePred conflicts reconciled, not silently resolved.** `AOP-37BD4B4933`
  ("FCM") and `AOP-DDCD54E4BA` ("YPQLLPNE") are reported inactive by AnOxPePred's own FRS/Chelator
  assays (traceable to specific DOIs: 10.1007/s13594-015-0226-5 and 10.1016/j.foodchem.2016.02.119)
  but independently listed as "Antioxidative peptide" in BIOPEP-UWM (a database annotation with no
  per-record assay/reference metadata visible in the scraped table). **Recommendation presented, not
  unilaterally applied:** retain both in the primary external control, per the same assay-outranks-
  undocumented-annotation precedent already established for FR1's own Multi-AOP/AnOxPePred conflict
  policy (Bucket 1) — flagged explicitly (`has_biopep_antioxidative_conflict` column in the validated
  artifact) rather than excluded or quietly ignored.
- **Versioned, not overwritten:** `anoxpepred_external_control_validated.csv` is a new artifact (same
  38 records as the frozen original, plus 2 validation columns) — the frozen `pp1_baseline_v1` copy is
  confirmed untouched via `git status`.
- **Critical labeling rule maintained throughout:** every output explicitly states these 38 records are
  inactive *under the AnOxPePred FRS/Chelator assay definitions*, not proven universally non-
  antioxidant — and remain structurally separate from C1/C2/C3 (never merged into the unlabeled
  training pools, consistent with AGENTS.md rule 2).
- **Tests:** 3 new unit tests (`test_homology_alignment.py`, including a regression test pinning the
  `-minscore` fix) + 9 full-file acceptance tests (`test_fr2_external_control_acceptance.py`, including
  byte-identical reproducibility of a full re-run). Full suite: 166 passed, 1 skipped, zero regression.

### Bucket 2, Task 2.7 — FR2 Final Acceptance Audit and Freeze
- **Status: technical acceptance passed, frozen as `pp2_baseline_v1` (2026-10-14).** Full detail,
  methodology, every number, and the acceptance-checklist mapping live in
  **[`fr2_acceptance_report.md`](fr2_acceptance_report.md)** — mirrors `fr1_acceptance_report.md`'s
  structure. This entry is a pointer + headline result, not a duplicate of that report.
- **Independent, end-to-end re-verification performed, not a summary of prior logs.** `fr2-pool-audit`
  was rerun fresh against the final canonical pools (not reused from an earlier run) immediately
  before freezing, and the **complete** test suite — including every byte-identical-reproducibility
  check (C1/C2 cross-pool fixes, the full C3 re-embed, the external-control homology re-run, the
  full Peptipedia-dump C2 reproducibility test) — was run in full, not just the fast subset used
  during iterative development: **177 passed, 1 skipped (torch, runs separately inside WSL), 0
  failed, in 16m34s.**
- **Headline numbers:** C1 5,000 records (3,788 unique) / C2 2,000 / C3 2,325-sequence union with
  5×2,000 fold-specific rankings / 38-record validated external control — all re-confirmed directly
  from the frozen files, not carried over from memory.
- **`fr2_pool_audit_report.json` confirmed `ready_for_technical_acceptance: true`** (re-derived from
  the live artifacts at report-generation time) before the freeze was attempted — `run_fr2_freeze()`
  hard-fails if this flag is false, so the freeze cannot proceed past an unresolved finding by
  mistake.
- **Frozen baseline: `pp2_baseline_v1`** (`data/processed/c2_pu/frozen/pp2_baseline_v1/`, 28 files,
  checksummed `MANIFEST.json`, 6.8MB). Bundles: canonical C1 v3/C2 v2/C3-union+ranking, the validated
  external control, every Bucket 2.4 audit report, and every Bucket 2.5 distribution report. Declares
  its `pp1_baseline_v1` dependency explicitly in the manifest rather than re-copying FR1's own files.
  Large raw sources (Peptipedia dump, 281MB) are referenced by SHA-256 + DOI, not copied, per AGENTS.md's
  "don't commit large raw datasets" rule — the smaller UniRef50 snapshot and BIOPEP-UWM scrape are
  both already committed elsewhere in the repo and referenced the same way for completeness.
- **`pp1_baseline_v1` confirmed untouched, both before and after the freeze** (`verify_frozen_baseline`
  called at both points inside `run_fr2_freeze`, not just assumed from "we didn't write to that
  path") — all 10 of its files still checksum-match.
- **Scientific sign-off is explicitly NOT claimed.** Per AGENTS.md rule #3 and the same distinction
  already drawn for FR1: passing every automated acceptance check is not the same as supervisor
  approval. `fr2_acceptance_report.md` §10 lists every outstanding approval (FR1's 4 carried-over
  items, plus the new BIOPEP-UWM external-control retention recommendation) separately from the
  technical-acceptance result.
- **Tests:** 6 new acceptance tests (`test_fr2_freeze_acceptance.py`) verifying manifest completeness,
  checksum integrity, count consistency, and FR1-baseline non-interference.

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

### Bucket 3, Task 3.2 (remaining work) — Full ESM-2 Embedding Extraction
- **Status: technical acceptance passed.** The environment/interface/smoke-test scope above was
  already closed out; this entry covers the remaining checklist items — extracting embeddings for
  the full positive pool and C1/C2/C3/external-control, verified against the Task 3.1 descriptor
  contract. No existing code was rebuilt: `common/embeddings.py`, `esm2_cli.py`, and the WSL subprocess
  mechanism are reused exactly as-is.
- **`run.py::_embed_via_wsl` generalized to a public `embed_via_wsl` helper** (used by Bucket 2.3's C3
  build and now this stage) rather than duplicated — added optional `embed_input_path`/
  `summary_report_path`/`timeout` parameters, with defaults matching the original C3 call sites
  exactly (confirmed via `git diff` that the two existing C3 calls are behaviorally unchanged).
- **Embeddings computed once per unique sequence, in `fr3_descriptor_table.parquet`'s exact row
  order** — alignment with the descriptor table is true by construction (the embedding stage reads
  peptide_id/sequence directly from that table), not a separately-maintained convention to drift out
  of sync.
- **Existing Bucket 2.3 caches reused, not re-embedded — reported, not assumed compatible.** Of 9,356
  total unique sequences, **3,159 (2,325 C3-union + 834 GraphPart-retained FR1 positives) were
  already covered exactly** by `c3_candidate_embeddings.npz`/`c3_positive_embeddings.npz` (confirmed
  by exact peptide_id-set membership before reuse, not just existence of the file) — only the
  remaining **6,197** (3,788 C1 + 2,000 C2 + 371 FR1 positives outside the 834-retained split + 38
  external control) needed fresh ESM-2 inference, completing in 175s on CPU. Every reused vector is
  additionally shape/dtype/finiteness-checked before being trusted (`incompatible_cached_vectors_
  excluded` in the manifest — empty on this run, but a real cache failure would be reported and that
  vector re-embedded, never silently kept).
- **A real idempotency bug found and fixed before acceptance:** the first implementation only checked
  Bucket 2.3's two caches for reuse, not this stage's own prior output — re-running `fr3-embeddings` a
  second time therefore re-embedded all 6,197 "fresh" sequences again instead of reusing the file it
  had just written. Fixed by adding `fr3_embeddings.npz` itself to the reuse-source list. Verified via
  the full acceptance suite: a second run now reports `freshly_embedded: 0`, `reused_from_existing_
  caches: 9356`, and byte-identical `peptide_id_order_sha256`/`embeddings_cache_sha256` to the first
  run (555s → 20s for the full acceptance suite after the fix).
- **A real, quantified floating-point finding (not a bug, but worth recording precisely):** re-
  embedding the identical single sequence in an isolated batch of 1 is bit-identical across repeated
  WSL subprocess invocations (confirmed directly) — true determinism holds for a *fixed* batch
  composition, consistent with `test_embeddings.py`'s existing `batch_size=32` vs. `batch_size=1`
  check (which already uses `atol=1e-5`, not exact equality). What's new here is a direct,
  isolated measurement of *why*: embedding the same 20-residue test sequence alone vs. padded
  alongside a longer sequence in one batch changes its mean-pooled vector by up to ~9.5e-7 absolute
  per element — PAD-token presence measurably perturbs floating-point summation/kernel-selection
  order in self-attention for the *other*, real tokens in that batch, even though the pooling code
  mathematically excludes PAD positions from the mean. Practical consequence: **`fr3_embeddings.npz`
  is a mixed-provenance artifact** — vectors reused from Bucket 2.3's caches were computed under
  *that* stage's own batch grouping, while freshly-embedded vectors used this stage's `batch_size=64`
  grouping of a different sequence set. Both are internally reproducible given their own batch
  composition, and agree with any independent re-embed to within ~1e-6 — many orders of magnitude
  below any plausible downstream classifier signal for a 480-dim mean-pooled feature — but the
  combined cache is not bit-reproducible from a hypothetical "embed all 9,356 in one giant batch"
  alternative construction. Documented rather than glossed over, mirroring the project's existing
  CD-HIT multi-threading non-determinism note (Known Issue #17).
- **Outputs:** `fr3_embeddings.npz` (gitignored, 9,356×480 float32 + peptide_ids + pools, same row
  order as `fr3_descriptor_table.parquet`), `fr3_embeddings_manifest.json` (model spec, reuse/fresh
  counts, SHA-256 of both the peptide-ID order and the cache file, per-pool coverage), `fr3_embeddings_
  validation_report.json` (shape/dtype/finiteness/order checks, L2-norm range), `fr3_embeddings_
  provenance.jsonl`.
- **C3 fold-safety preserved, not touched.** This cache holds exactly one embedding per C3-union
  peptide_id — it is not a fold-specific accessor and `curation/c3.py::load_fold_challenges(path,
  fold_id)` remains the only sanctioned way to get a fold's C3 membership; fold-specific training must
  join that function's output against this cache by `peptide_id`.
- **Tests:** 11 full-file acceptance tests (`test_fr3_embeddings_acceptance.py`) — exact row-count/
  order/shape/dtype/finiteness match against the real descriptor table, per-pool coverage, manifest
  correctness, meaningful-reuse-fraction check, idempotent-rerun reproducibility, a true bit-identical
  determinism check (fixed batch composition), and the justified-tolerance differently-batched
  spot-check described above. Frozen `pp1_baseline_v1`/`pp2_baseline_v1` confirmed untouched via
  `git status` before and after every run.
- **No new dependencies.** No cross-dataset statistic fit anywhere (same scope boundary as Task 3.1).
  Feature fusion (Bucket 3.3) and model training are explicitly out of scope for this session.

### Bucket 3, Task 3.3 — Feature Fusion and Leakage-Safe Preprocessing
- **Status: technical acceptance passed.** Fuses Task 3.1's descriptor table and Task 3.2's embedding
  cache into a 495-dim raw feature matrix (schema `fusion_v1`), then fits one leakage-safe z-score
  scaler per GraphPart fold. Neither Task 3.1 nor Task 3.2 is recomputed — `curation/feature_fusion.py`
  only loads, validates, concatenates, and fits/applies scalers.
- **The one load-bearing design decision, made and documented rather than asked about again:** a
  fold's scaler is fit **exclusively on that fold's training-positive rows** (the 4 other GraphPart
  folds' retained positives), then applied (transform only) to everything else under that fold's
  condition — its own held-out positives, C1, C2, that fold's C3 selection, and the external control.
  This directly mirrors the project's own already-approved C3 fold-safe-centroid precedent
  (`curation/c3.py`, AGENTS.md rule 5), rather than opening a new approval round for what is really the
  same leakage-prevention principle applied to a second statistic. The rejected alternative (one global
  scaler fit on all 1,205 FR1 positives) was ruled out because it would let fold k's own held-out
  positives influence the statistics later used to transform those same held-out positives — the exact
  leakage channel the C3 centroid's fold-safe design already exists to close. Flagged here explicitly
  since it determines downstream experiment comparability (every PN/PU/curriculum condition in FR4
  must use its OWN fold's scaler, never a shared one) — override at next review if a different scheme
  is wanted, but this is the scheme implemented and tested.
- **Verified against the real data, not assumed:** per-fold training sizes 710/700/697/661/568 — exact
  match to the GraphPart split documented at Bucket 2.3/3.1. Every fold's own training rows
  standardize to mean ≈0 (max abs ≤1.2e-5, floating-point floor) and std ≈1 (0.9999976–1.0000027)
  after applying that fold's own scaler — confirms the fit is correct, not just "ran without erroring."
  Training and held-out peptide_id sets never overlap for any fold (checked directly); training+
  held-out always sums to exactly 834 (the GraphPart-retained total) with zero contamination from
  C1/C2/C3/external-control peptide_ids (checked by exact set membership, not assumed from pool
  labels).
- **Independent, from-scratch validation of Task 3.1/3.2's correspondence contract** (not re-trusted
  from their own test suites): peptide_id sets, row order, and pool assignments between
  `fr3_descriptor_table.parquet` and `fr3_embeddings.npz` are re-checked here and hard-fail
  (`FeatureAlignmentError`) on any mismatch — including the subtle "same ID set, different order" case,
  which is deliberately never silently reconciled by reindexing (that would mask a real pipeline bug
  rather than surface it). `fr3_fusion_validation_report.json`'s `peptide_id_order_sha256` matches
  `fr3_embeddings_manifest.json`'s hash exactly, confirming cross-stage alignment empirically.
- **`run.py`'s `embed_via_wsl` pattern was not needed here** (fusion is pure numpy/pandas, no ESM-2
  inference) — no new dependency, no new WSL call.
- **Outputs:** `fr3_fusion_schema.json` (committed — 495 feature names in their frozen concatenation
  order, schema version), `fr3_fused_raw.npz` (gitignored, 9,356×495 float32 — same "don't commit large
  arrays" rule as the embeddings cache, fully regeneratable from the two small committed inputs),
  `fr3_fusion_scalers.json` (committed — per-fold mean/std/training-peptide-id-list/held-out-peptide-
  id-list, so "which training samples were included in the scaler fit" is answerable by inspection, not
  just by count), `fr3_fusion_validation_report.json`, `fr3_fusion_provenance.jsonl`.
- **Scope boundary respected:** this task does NOT materialize 5 separate full scaled feature caches
  (one per fold) — only the raw fused matrix plus the small per-fold scaler *parameters* and a tested
  `apply_scaler()` function. Materializing fold-specific scaled caches ready for training is Task 3.4's
  responsibility; duplicating it here was explicitly out of scope. Model training (Bucket 4) untouched.
- **Tests:** 16 unit tests (`test_feature_fusion.py` — schema order, every `FeatureAlignmentError` path,
  concatenation-order correctness, scaler fit/apply including the zero-variance-column guard, fold
  training/held-out partitioning, empty-fold rejection) + 12 full-file acceptance tests
  (`test_fr3_feature_fusion_acceptance.py` — Task 3.1/3.2 outputs confirmed byte-unchanged by SHA-256
  before/after, frozen baselines untouched, exact fold-size/overlap/contamination checks against the
  real data, embedding/descriptor column blocks verified identical to their source arrays, and
  bit-identical rerun reproducibility for both the raw matrix and the scalers).
- **No new dependencies.** scikit-learn is already installed in this environment but unused here —
  the z-score scaler (mean/std, zero-variance guard) is ~10 lines of numpy, fully transparent and
  consistent with this project's existing hand-rolled-formula style (same reasoning as Task 3.1's
  descriptor implementations) rather than a dependency for something this simple.

### Bucket 3, Task 3.4 — Feature Cache and Reproducibility
- **Status: technical acceptance passed.** Materializes 5 fold-specific scaled feature caches by
  applying Task 3.3's already-fitted per-fold scalers (never refit) to Task 3.3's already-built raw
  fused matrix (never recomputed). New module `common/feature_cache.py` — deliberately minimal
  imports (numpy/pandas/json/hashlib only, zero `torch`/`esm`/WSL anywhere in its import chain) so
  loading a cache for training genuinely never requires ESM-2 inference, a WSL environment, or
  recomputing Task 3.1's descriptors.
- **Each of the 5 caches covers all 9,356 rows** (every pool), scaled under that fold's own scaler —
  a row's presence in fold k's cache is NOT a claim it belongs to fold k's curriculum. C1/C2 pool
  membership is a plain filter; **C3's fold-specific hard-challenge selection still requires
  `curation/c3.py::load_fold_challenges(path, fold_id)`**, joined against the cache by `peptide_id` via
  the new `get_c3_fold_challenge_rows()` helper — which additionally refuses (raises `ValueError`) if
  asked for a different fold's C3 selection than the cache's own fold_id, since scoring one fold's
  challenge candidates under a different fold's scaler would silently mix two folds' leakage-safety
  guarantees. There is deliberately no function anywhere in this module that returns "the whole C3
  union as fold k's challenge set."
- **Strict, checksum-verified loading, not just file-existence trust:** `load_fold_feature_cache()`
  computes the cache file's SHA-256 and compares it to the manifest's recorded hash **before** reading
  any array, then separately re-checks shape, dtype, schema version, and a scaler-identity fingerprint
  (SHA-256 of the embedded mean+std bytes) against the manifest — raising `CorruptedCacheError` with
  the specific mismatch on any failure. Verified against 6 distinct corruption modes in tests (missing
  file, flipped bytes, wrong shape, wrong dtype, wrong schema version, wrong scaler identity), plus an
  end-to-end acceptance test that corrupts one of the 5 REAL generated caches (not a synthetic one) and
  confirms rejection.
- **Verified against the real data:** per-fold training-row standardization (mean≈0, std≈8.4e-6 to
  1.2e-5 max-abs; std 0.9999976–1.0000027) survives the float32 downcast essentially unchanged from
  Task 3.3's float64 validation. Every cache's C3-pool row count is exactly 2,325 (the full union,
  confirming it is NOT silently fold-filtered). External-control peptide_ids confirmed disjoint from
  every fold's training AND held-out sets (re-checked independently here, not re-trusted from Task
  3.3). `peptide_id_order_sha256` matches Task 3.2/3.3's own hash exactly across all three stages.
- **Real end-to-end C3 integration test, not mocked:** `get_c3_fold_challenge_rows()` is exercised
  against the actual `c3_similarity_ranking.csv` for all 5 folds, confirming exactly 2,000 rows
  returned per fold (matching `C3_TOP_N_PER_FOLD`) and that requesting fold k's cache with a different
  fold's `fold_id` argument is rejected.
- **Smoke test (requirement #9), run in a genuinely fresh subprocess** (not just "torch wasn't imported
  in this test file," which other already-torch-importing tests in the same session could mask):
  imports only `common/feature_cache.py`, asserts `"torch"`/`"esm"` are absent from `sys.modules`
  both before AND after loading a real 9,356×495 cache, and completes in well under 10 seconds —
  several orders of magnitude faster than a real ESM-2 model load, let alone inference.
- **Outputs:** `fr3_fold{0..4}_scaled_features.npz` (gitignored, ~9MB each — fully regeneratable from
  the already-committed `fr3_fused_raw.npz`-regenerating inputs + `fr3_fusion_scalers.json`),
  `fr3_feature_cache_manifest.json` (committed — per-fold cache path/SHA-256/shape/dtype/schema
  version/scaler-identity-fingerprint/`n_training_samples`, plus the three input files' own SHA-256 so
  the whole provenance chain is checksummed), `fr3_feature_cache_validation_report.json`,
  `fr3_feature_cache_provenance.jsonl`.
- **Tests:** 15 unit tests (`test_feature_cache.py` — scaler-identity/hash determinism, happy-path
  load, all 6 corruption-rejection modes, pool/training/held-out row accessors, the C3-fold-mismatch
  rejection, and a real-schema C3 integration test against a synthetic ranking CSV) + 12 full-file
  acceptance tests (`test_fr3_feature_cache_acceptance.py` — Task 3.1–3.3 outputs and frozen baselines
  confirmed byte-unchanged, all 5 real caches round-trip-load and are fully finite, real
  `c3_similarity_ranking.csv` integration across all 5 folds, real-cache corruption rejection,
  bit-identical rerun reproducibility, and the subprocess smoke test).
- **No new dependencies.** Model training (Bucket 4) and Task 3.5 are untouched — this task stops at a
  loadable, checksummed, leakage-safe feature cache plus the reusable loader utilities.

### Bucket 3, Task 3.5 — Feature Pipeline Demonstration (Bucket 3 CLOSED OUT)
- **Status: technical acceptance passed. Bucket 3 (Feature Engineering Pipeline) is now fully
  complete.** `run_fr3_demo()` (CLI `fr3-demo`) is a small, fast (~1.6s), fully offline walkthrough of
  the already-accepted Tasks 3.1–3.4 pipeline — no reimplementation, no new formulas, no live ESM-2/WSL
  inference anywhere in its path. Full usage doc: **[`FR3_FEATURE_PIPELINE_DEMO.md`](FR3_FEATURE_PIPELINE_DEMO.md)**.
- **Explicitly NOT a claim that FR3 is complete.** FR3 additionally requires the four classification
  baselines (PN, nnPU, Two-Step PU, PU-Bagging) and their evaluation — unstarted, out of this task's
  scope per explicit instruction. This entry closes Bucket 3 (the feature-engineering prerequisite),
  not FR3 itself.
- **7 fixed, REAL peptide_ids, not synthetic data** — chosen deterministically from the accepted
  pipeline outputs to cover every pool plus both sides of GraphPart fold 0's split and two of fold 0's
  real C3 top-2000 hard challenges (verified by rank, not assumed): `AOP-002DDE226A` (FR1 positive,
  fold-0 training), `AOP-0089BF570C` (FR1 positive, fold-0 held-out), `C1-00174EE65A`, `C2-00316810B4`,
  `C3-8A629D6877`/`C3-73E12D123B` (fold-0 ranks 1–2), `AOP-053EB70717` (external control).
- **Input validation (requirement 1):** all 7 sequences checked against the standard 20-AA
  alphabet/3–50 AA window via the real, shared `common.sequence.is_valid_peptide` — no reimplemented
  validation logic.
- **Descriptor + embedding path, using existing implementations exactly as instructed (requirement 2):**
  descriptors are computed **live** via `common.descriptors.compute_descriptors_batch()` (fast, pure
  numpy, no GPU/WSL) and cross-checked bit-for-bit against the frozen `fr3_descriptor_table.parquet`
  values for these same peptides. ESM-2 embeddings are the "heavy extraction" the task brief explicitly
  allows precomputing — they are **loaded from the existing `fr3_embeddings.npz` cache**, never
  recomputed; no ESM-2 model load or WSL subprocess call occurs anywhere in this demonstration,
  verified not just by inspection but by a subprocess-isolated smoke test (see below).
- **Feature-cache loading, not recomputation (requirement 3):** the fold-0 scaled 495-dim cache is
  loaded through Bucket 3.4's own `load_fold_feature_cache()` (full checksum/shape/dtype/schema
  verification included, not bypassed for the demo).
- **Correct pool/fold selection, verified against the real data (requirement 4):** training (710),
  held-out (124), C1 (3,788), C2 (2,000), C3 union-in-cache (2,325), and fold-0's real C3 challenge
  selection (2,000, resolved via `curation.c3.load_fold_challenges` — never by filtering `pool=="C3"`)
  — every count matches the documented, previously-verified values exactly.
- **External control confirmed separate (requirement 5):** re-checked independently here (not
  re-trusted from Task 3.4) that none of the 38 external-control peptide_ids appear in fold 0's
  training or held-out sets.
- **Concise, presentation-ready summary (requirement 6):** schema versions (all 3: descriptor/fusion/
  cache), shapes at every stage, pool coverage, per-demo-peptide scaled-feature preview (first 5 of
  495 dims), and an explicit `validation` block where every check must read `true` or the whole run
  raises — no partial-success reporting.
- **One-command, documented, with a literal expected-output reference (requirement 7):**
  `python -m plantaox.c2_pu.run fr3-demo`. Output is written to the **committed**
  `fr3_demo_output.json`, which doubles as the exact expected-output reference (re-running against an
  unchanged pipeline reproduces it byte-for-byte — verified in tests, not just asserted in prose).
- **Tests (requirement 8):** 11 full-file acceptance tests (`test_fr3_demo_acceptance.py`) — Tasks
  3.1–3.4 outputs and frozen baselines confirmed byte-unchanged by SHA-256 before/after, exact
  pool-coverage match, every validation check passes, correct descriptor/embedding/cache shapes, the
  two demo C3 peptides independently re-verified as fold-0's real ranks 1–2 (not just trusted from the
  demo's own output), on-disk output file matches the returned summary, bit-identical rerun
  reproducibility, a clear `FileNotFoundError` for a missing prerequisite (tested via a deliberately
  nonexistent `fold_id=99`), and a subprocess-isolated smoke test proving the full demo path needs no
  `torch`/`esm` import and completes in well under the 10-second budget.
- **No new dependencies, no dashboard.** Nothing beyond the existing `run.py` CLI-stage pattern was
  needed — a new UI/dashboard was judged unnecessary for a PP1 presentation given a clear, versioned
  JSON summary plus this markdown write-up already satisfies "concise, presentation-ready."

### Bucket 3, Task 3.1 — 15-Dimensional Physicochemical Descriptor Extraction
- **Status: technical acceptance passed.** The canonical 15-descriptor schema is frozen as
  `descriptors_v1` in `common/descriptors.py`; `common/descriptors.py` is no longer an empty stub
  (Known Issue cross-reference: resolves the decision-log entry below about Task 2.5's narrower set).
- **No prior document in the repo enumerated the 15 descriptors** — the Planner's Task 3.1 bullet
  ("define the exact 15 descriptors") was itself the authoring task, confirmed by direct inspection of
  `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`, `PU_AOP_RESEARCH_CONTEXT.md`, and the Proposal
  Report PDF (which only confirms the count "15" and, in Component 01's architecture diagram box,
  "via BioPython" — not itemized for Component 02). A proposed 15-descriptor list was presented to
  the project owner with explicit trade-offs and **approved before implementation**, per AGENTS.md's
  "when in doubt" policy.
- **The frozen 15:** `length`, `molecular_weight`, `net_charge_ph7`, `isoelectric_point`, `gravy`,
  `aromaticity`, `instability_index`, `aliphatic_index`, `hydrophobic_moment`, `frac_charged`,
  `frac_polar`, `frac_hydrophobic`, `frac_positive`, `frac_negative`, `frac_proline` — covering both
  the proposal's own named AOP mechanism axes (FRS ← hydrophobicity/aromaticity; chelation ← charge).
- **Mid-implementation substitution, flagged not silently made:** the originally-approved 9th feature
  (Boman index) was dropped after no independently verifiable source for its per-residue scale could
  be located (two targeted searches turned up only unverified/possibly-confused tables) — reproducing
  an unverifiable 20-value constant into a frozen scientific schema was judged a worse risk than a
  documented substitution. Replaced with `frac_proline`: trivially self-verifying (a residue count)
  and directly motivated by this project's own Task 2.5 finding that FR1 positives are proline-enriched
  (10.6%) vs. every challenge pool (4.1–5.6%) — a project-evidenced choice, not just a textbook one.
- **Numerical provenance, not hand-transcribed:** the instability-index dipeptide weight table (`DIWV`,
  Guruprasad et al. 1990, 400 cells) was downloaded directly from Biopython's
  `Bio.SeqUtils.ProtParamData` (BSD/Biopython-licensed) rather than reconstructed from memory, since a
  silently-wrong entry in a 400-cell table would not be caught by ordinary unit tests. The Eisenberg
  (1984) hydrophobic-moment scale and the Ikai (1980) aliphatic-index coefficients (a=2.9, b=3.9) were
  verified against ExPASy ProtScale / the original citation before use.
- **Single source of truth, no divergent copies:** `curation/distribution_audit.py`'s 4 Task-2.5
  formulas (molecular weight, GRAVY, aromaticity, net charge at pH 7) now import from
  `common/descriptors.py` instead of defining their own copies — the two modules can no longer
  silently diverge. `distribution_audit.py`'s public API (function names/signatures) is unchanged, so
  its existing 9 tests pass unmodified.
- **Net charge / pI reuse the exact pKa table already validated in Task 2.5** (Expasy/EMBOSS-style),
  for cross-task consistency. Isoelectric point is a genuine new bisection root-find on the same
  charge function (always well-defined for a 3–50 AA peptide, since every peptide has both a basic
  N-terminus and acidic C-terminus ionizable group).
- **Pipeline (`curation/descriptor_extraction.py` + `run.py::run_fr3_descriptors()`, CLI stage
  `fr3-descriptors`), run against the real frozen baselines, not a sample:** reads
  `frozen/pp1_baseline_v1/aop_positives_provisional.parquet` (1,205 records) and
  `frozen/pp2_baseline_v1/{stage_c1_decoys_v3.fasta, stage_c2_bioactive_unlabeled_v2.fasta,
  stage_c3_esm2_hard_challenges.fasta, anoxpepred_external_control_validated.csv}` exclusively — never
  the superseded working-tree copies. Computed and recorded counts match the frozen manifests exactly:
  FR1 1,205 records → 1,205 unique sequences; **C1 5,000 records → 3,788 unique sequences** (descriptor
  rows, not 5,000 — record-level duplication does not multiply the feature table, verified directly);
  C2 2,000; C3 2,325 (the fold-UNION, per the Planner's explicit "acceptable to compute once per unique
  sequence" allowance — fold-specific training must still go through `c3.py::load_fold_challenges` and
  join by `peptide_id`, never read descriptors "by fold" from this table directly); external control 38
  (kept in its own `pool="external_control"`, never merged with C1/C2/C3, confirmed disjoint by test).
- **C1 peptide IDs, newly assigned:** C1's frozen FASTA headers are raw UniProt deflines, not peptide
  IDs, and `c1_accession_map_v3.csv` has no `peptide_id` column either — content-addressed `C1-`-
  prefixed IDs (`common.sequence.make_peptide_id`, consistent with the project's existing `C2-`/`C3-`/
  `AOP-` convention) were generated from sequence, with every one of the 5,000 source accessions
  preserved in a separate `fr3_record_map.csv`, joinable by `peptide_id`.
- **FR1 GraphPart fold/evidence-tier provenance preserved, not re-derived by hand:** `fr3_record_map.csv`
  attaches `graphpart_fold`/`graphpart_retained` via `curation/splits.py::load_graphpart_splits()` —
  verified directly against the real artifact: 834 retained (matches `pp1_baseline_v1` exactly), 371
  excluded, per-fold held-out sizes 124/134/137/173/266 (byte-for-byte match to the frozen split
  summary, not re-trusted from the manifest).
- **Numerical validation against the complete real dataset (9,356 descriptor rows, not a sample):**
  zero missing values, zero non-finite values, zero near-constant features across all 15 descriptors.
  Diagnostic-only correlation scan flags exactly one pair ≥|0.9|: `length`/`molecular_weight` (r=0.99,
  expected and already documented as the project's primary known confound by Task 2.5) — reported, not
  acted on (no feature selection performed, per explicit Task 3.1 scope).
- **No cross-dataset statistic fit anywhere** (no scaling, centering, PCA) — every value is a raw,
  per-sequence physicochemical property; learned preprocessing is explicitly deferred to Bucket 3.3.
- **Outputs** (flat files under `data/processed/c2_pu/`, matching the project's established
  non-nested, stage-prefixed convention — NOT the Planner Deliverable Registry's aspirational
  `descriptors.npy + ID map` naming, since the project's actual established convention for every other
  feature/report table is CSV/parquet, consistent with "use the repository's existing preferred file
  formats" from the task brief): `fr3_descriptor_schema.json` (versioned name list),
  `fr3_descriptor_table.parquet` (peptide_id/sequence/pool + 15 columns, one row per unique sequence
  per pool), `fr3_record_map.csv` (every source record, including C1's 5,000), `fr3_coverage_report.json`,
  `fr3_validation_report.json`, `fr3_descriptors_provenance.jsonl`.
- **Tests:** 29 unit tests (`test_descriptors.py` — schema contract, reference-value correctness,
  length boundaries, representative short/long/charged/aromatic/hydrophobic/cysteine-rich/proline-rich
  sequences, invalid-alphabet/length rejection, batch==single numerical equivalence, determinism,
  no-input-mutation, 300-sequence finite-value sweep) + 12 full-file acceptance tests
  (`test_fr3_descriptors_acceptance.py` — exact frozen-count matching, no duplicate peptide IDs within
  a pool, record-preservation, GraphPart fold-size matching, schema-order column check, full-dataset
  finiteness, external-control disjointness, byte-for-byte rerun reproducibility), all gated to skip
  cleanly when frozen inputs aren't present. `distribution_audit.py`'s existing 9 tests pass unmodified
  after the refactor. `pp1_baseline_v1` and `pp2_baseline_v1` confirmed untouched via `git status`
  before and after every run (frozen directories show zero diff).
- **Scientific vs. technical acceptance:** technically complete and passing every stated acceptance
  criterion. Scientific sign-off on the descriptor-list substitution (Boman index → `frac_proline`) and
  on the overall 15-feature composition should still be confirmed by the project owner/supervisor at
  the next review, consistent with this project's standing distinction between the two.

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
    **RESOLVED (accepted as a documented limitation) 2026-10-14.** 11 of the 14 other candidate C1↔C2
    homology pairs remain (3 resolved as a side effect of Decision A) — reviewed individually, no
    plausible antioxidant mechanism in any peptide family involved. **Explicitly approved by the
    project owner** as a documented PP1 limitation, conditional on the audit confirming no FR1-
    positive involvement in the real (≥15 AA) homology relationship — condition re-verified precisely
    (2 of the 11 clusters contain incidental short FR1-positive fragments as the same already-
    documented chance-match noise, never part of the ≥15 AA relationship itself). No further
    exclusion applied. See Bucket 2.4 resolution section above.
15. **AODB and DFBP remain unscreened**, for a documented access reason rather than an unstarted
    task: AODB's server returned HTTP 502 + an expired TLS certificate; DFBP has no discoverable
    hosting URL. BIOPEP-UWM **is** screened (zero hits in C1 v3/C2 v2/C3). Revisit if either resource
    comes back online or a hosting URL for DFBP is found.
16. **AWAITING PROJECT-OWNER CONFIRMATION (non-blocking): the 2 BIOPEP-UWM-vs-AnOxPePred
    external-control conflicts** (`AOP-37BD4B4933`/"FCM", `AOP-DDCD54E4BA`/"YPQLLPNE") are flagged
    (`has_biopep_antioxidative_conflict`) and retained in the primary external-control set, per a
    presented recommendation (assay-outranks-undocumented-annotation precedent) — not yet explicitly
    confirmed. Does not block FR2 technical acceptance or the `pp2_baseline_v1` freeze (no dataset
    change is pending on this one either way: the default state, retain-and-flag, is already applied).
17. **CD-HIT's raw `.clstr` intermediate output is not perfectly run-to-run stable**, discovered while
    independently re-verifying FR2 for the freeze (Task 2.7): re-running `fr2-pool-audit` a second time
    on unchanged pool inputs produced a `audit_combined_pools_cdhit90.clstr` that differed from the
    first run in a handful of cluster groupings/ID numbers (confirmed via `git diff`, not assumed).
    Root cause: CD-HIT is invoked with `-T 0` ("use all available threads"), and multi-threaded
    processing order can affect which representative/cluster a borderline sequence is assigned to.
    **The DERIVED, audited conclusions were empirically confirmed unaffected** — `audit_cross_pool_
    homology_clusters.csv`, `audit_cross_pool_homology_summary.json`, and `fr2_pool_audit_report.json`
    were all byte-identical across the rerun (verified via `git diff`, zero changes) — so this does not
    change any reported finding or the 11-vs-15 real-homology-candidate counts anywhere in this
    document. Flagged here as a genuine, newly-discovered reproducibility nuance in a third-party tool
    invocation, not swept under the "everything is byte-identical" claim made elsewhere for this
    project's own code. Not fixed (would require forcing `-T 1`, a performance/determinism tradeoff
    outside this task's scope) — noted for awareness if a future rerun's raw CD-HIT file is compared
    byte-for-byte and appears to differ.

## ⏭️ Next tasks (in order)

1. **Get supervisor sign-off on the four pending FR1 approvals** (`fr1_acceptance_report.md` §10) —
   the conflict-resolution policy, the E2 provisional-tier default, the C1 source ambiguity, and the
   missing formal `data_registry.csv`. None block continued FR2/FR3 work on `pp1_baseline_v1`, but
   FR1 isn't *scientifically* closed until these are addressed.
2. **Bucket 2.1 (C1) is closed out, including the standard-alphabet policy fix** — see Completed tasks
   above. Optional follow-ups, both low priority: an independent spot-check of the one new leakage
   replacement record (`RL34_XANVE`); a spot-check of a few of the 260 new alphabet-fix replacement
   records (none had an independent fresh review beyond the automated blocklist/screen checks).
3. **RESOLVED 2026-10-14. Bucket 3.2 is now fully complete** (environment/interface/smoke-test, AND
   the remaining full-embedding-extraction checklist items) — see Completed tasks above (`fr3_
   embeddings.npz`, `fr3_embeddings_manifest.json`, CLI stage `fr3-embeddings`). Kept here for
   history; not an open item anymore.
4. **FR2 (Buckets 2.1–2.7) is complete, technically accepted, and frozen as `pp2_baseline_v1`.** See
   `fr2_acceptance_report.md` for the full account. Canonical artifacts for ALL future consumption:
   `stage_c1_decoys_v3.fasta`, `stage_c2_bioactive_unlabeled_v2.fasta`, `stage_c3_esm2_hard_
   challenges.fasta` + `c3_similarity_ranking.csv`, `anoxpepred_external_control_validated.csv`.
   Scientific sign-off is explicitly NOT claimed — see Known Issues and `fr2_acceptance_report.md` §10
   for every outstanding approval.
5. **AODB/DFBP/BIOPEP-UWM cross-reference:** BIOPEP-UWM done (zero hits in C1/C2/C3/external
   control). AODB/DFBP remain unscreened for documented access reasons (Known Issue #15), not an
   unstarted task — revisit only if either resource becomes reachable or a DFBP hosting URL surfaces.
6. **RESOLVED 2026-10-14. Bucket 3.1 (15 physicochemical descriptors) is complete** — see Completed
   tasks above (`common/descriptors.py`, schema `descriptors_v1`, CLI stage `fr3-descriptors`). Kept
   here for history; not an open item anymore.
6b. **RESOLVED 2026-10-14. Bucket 3.3 (feature fusion and leakage-safe preprocessing) is complete** —
   see Completed tasks above (`curation/feature_fusion.py`, schema `fusion_v1`, CLI stage
   `fr3-feature-fusion`). Kept here for history; not an open item anymore.
6c. **RESOLVED 2026-10-14. Bucket 3.4 (feature cache and reproducibility) is complete** — see Completed
   tasks above (`common/feature_cache.py`, schema `feature_cache_v1`, CLI stage `fr3-feature-cache`).
   Kept here for history; not an open item anymore.
6d. **RESOLVED 2026-10-14. Bucket 3.5 (feature pipeline demonstration) is complete — Bucket 3 (Feature
   Engineering Pipeline) is now fully closed out.** See Completed tasks above (`fr3-demo` CLI stage,
   `FR3_FEATURE_PIPELINE_DEMO.md`). **FR3 itself is explicitly NOT complete** — it still requires the
   four classification baselines (PN, nnPU, Two-Step PU, PU-Bagging) and their evaluation, which have
   not been started. **FR4/Bucket 4 model training is the next item** — training code should load
   features exclusively via `common/feature_cache.py`'s `load_fold_feature_cache`/`get_training_rows`/
   `get_held_out_rows`/`get_pool_rows`/`get_c3_fold_challenge_rows`, never by re-deriving scaled
   features by hand.
7. **FR3/FR4 training code consuming C3 must use `curation/c3.py::load_fold_challenges(path, fold_id)`**
   (not read the union FASTA or filter the ranking CSV by hand) to get that fold's hard-challenge set —
   flagging this contract here since it's the single easiest way to silently reintroduce C3's
   selection-leakage risk later.
8. **Outstanding, non-blocking approval:** the BIOPEP-UWM external-control retention recommendation
   (Known Issue #16) — presented, not yet confirmed. Does not block FR3 work on `pp2_baseline_v1`.
9. Continue down the Bucket 1 → Bucket 2 → Bucket 3 → Bucket 4 sequence as defined in `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`. FR3/FR4 classifier implementation was explicitly out of
   scope for this session's work and has not been started.

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

| 2026-10-14 | The 11 remaining C1↔C2 near-duplicate homology families are accepted as a documented PP1 limitation, no further exclusion applied | Explicit project-owner approval, conditional on the audit confirming zero FR1-positive involvement in the real (≥15 AA) homology relationship. Re-verified precisely (not just re-asserted): 2 of the 11 clusters contain short FR1-positive fragments, but strictly as already-documented short-fragment chance-match noise below the 15 AA interpretability floor, never part of the qualifying relationship. |
| 2026-10-14 | Bucket 2.6's external-control-vs-positive homology audit uses EMBOSS `needleall` (real global alignment, all 45,790 pairs) instead of CD-HIT percent identity | Explicit instruction: CD-HIT's shorter-sequence-normalized identity is already known (Bucket 2.4) to be unreliable for very short peptides. `needleall` reports identity, similarity, gaps, and alignment length directly per pair, batched in one call rather than one `needle` call per pair. |
| 2026-10-14 | `needleall`'s default `-minscore 1.0` is overridden to a very low value (−10,000) in `curation/homology_alignment.py::run_needleall` | Found empirically: the default silently drops any pair scoring below it from the output entirely (a 38×1,205 run returned only 35,076 of the expected 45,790 pairs at the default). A completeness-audited homology scan must account for every pair, including irrelevant low/negative-score ones, so results can be trusted as complete rather than silently partial. |
| 2026-10-14 | The 2 BIOPEP-UWM-vs-AnOxPePred external-control conflicts (`AOP-37BD4B4933`/"FCM", `AOP-DDCD54E4BA`/"YPQLLPNE") are flagged (`has_biopep_antioxidative_conflict`) but NOT excluded from the primary external-control set — a recommendation presented for approval, not yet confirmed by the project owner | Per explicit instruction to seek approval before a primary-vs-sensitivity-set policy change -- this row records the proposal and its rationale (AnOxPePred's FRS/Chelator assay results are per-sequence, DOI-traceable experimental evidence; BIOPEP-UWM's listing is a database annotation with no per-record assay/reference metadata visible in the scraped table; the project's own established precedent favors assay evidence), not a decision. Update this row once the project owner responds. |

| 2026-10-14 | FR2 frozen as `pp2_baseline_v1` after an independent end-to-end re-verification (fresh `fr2-pool-audit` rerun + the COMPLETE test suite, 177 passed/1 skipped/16m34s, not just the fast development subset) | Per explicit instruction: do not rely only on previous acceptance-report summaries; re-run the full reproducibility-inclusive suite as the final gate. `run_fr2_freeze()` hard-fails if `fr2_pool_audit_report.json`'s `ready_for_technical_acceptance` is False, so the freeze cannot silently proceed past an unresolved finding. |
| 2026-10-14 | `pp2_baseline_v1`'s manifest declares its `pp1_baseline_v1` dependency explicitly and references (rather than copies) the large Peptipedia raw dump by SHA-256 + DOI | Mirrors the project's established "don't commit large raw datasets" rule (already applied to ESM-2 weights and the Peptipedia dump itself); `verify_frozen_baseline` was run against `pp1_baseline_v1` both immediately before and immediately after the FR2 freeze, confirming zero interference rather than assuming it from "we didn't write to that path." |
| 2026-10-14 | Bucket 3.1's 15-descriptor schema's 9th feature, originally approved as Boman index, was substituted with `frac_proline` mid-implementation | Two targeted web searches for Boman (2003)'s per-residue solubility scale turned up only unverified/possibly-confused tables, not the original paper's Table 2. Freezing an unverifiable 20-value constant into a schema every downstream FR3/FR4 experiment depends on was judged a worse risk than a documented, project-owner-flagged substitution. `frac_proline` is trivially self-verifying (a residue count) and is itself motivated by this project's own Task 2.5 finding (FR1 positives are Pro-enriched at 10.6% vs. 4.1–5.6% in C1/C2/C3). Flagged for the project owner to confirm or override at next review — not silently decided. |
| 2026-10-14 | The instability-index dipeptide weight table (Guruprasad et al. 1990, 400 cells) was downloaded verbatim from Biopython's `Bio.SeqUtils.ProtParamData` source file rather than hand-transcribed from training-data memory | A single wrong entry in a 400-cell lookup table would not be caught by a handful of reference-sequence unit tests, and this schema is meant to be frozen project-wide — verified provenance was judged worth the extra step over reconstructing the table from memory. Eisenberg (1984) hydrophobic-moment values and Ikai (1980) aliphatic-index coefficients were independently cross-checked against ExPASy ProtScale / the original citation for the same reason. |
| 2026-10-14 | Bucket 3.1's descriptor cache uses flat CSV/parquet files directly under `data/processed/c2_pu/` (`fr3_descriptor_table.parquet`, `fr3_record_map.csv`, etc.), not the Planner Deliverable Registry's literal `descriptors.npy + ID map` naming | The Planner's `.npy`-based registry entry predates this project's actual established artifact convention — FR1's own positive pool is `.parquet`, every Task-2.5 descriptor/report table is `.csv`, and the task brief itself says to prefer the repository's existing preferred formats. Matching the registry's literal filename would have meant inventing a second, inconsistent feature-storage convention alongside the one every other stage already uses. |
| 2026-10-14 | `run.py`'s private `_embed_via_wsl` (Bucket 2.3) was renamed to a public `embed_via_wsl` and generalized with optional `embed_input_path`/`summary_report_path`/`timeout` parameters, instead of writing a second, near-duplicate WSL-embedding helper for Bucket 3.2 | The WSL subprocess/caching mechanics (shell out to `esm2_cli.py`, save vectors to a `.npz`, read them back) don't differ between the C3 build and the full feature-cache extraction — only the input batch and cache path do. New parameters default to the exact values the two existing C3 call sites already used, confirmed via direct inspection that their behavior is unchanged. |
| 2026-10-14 | Bucket 3.2's `fr3_embeddings.npz` directly reuses Bucket 2.3's `c3_positive_embeddings.npz`/`c3_candidate_embeddings.npz` wherever their peptide_ids already cover what's needed (3,159 of 9,356 sequences), only freshly embedding the remaining 6,197 | Confirmed by exact peptide_id-set membership check before reuse (not just file existence), and each reused vector is additionally shape/dtype/finiteness-checked, with any failure excluded from reuse and re-embedded instead — "reuse" is verified compatible, not assumed. Cut fresh ESM-2 inference from ~9,356 to ~6,197 sequences (175s on CPU). |
| 2026-10-14 | Fixed a real idempotency bug found during acceptance testing: `run_fr3_embeddings()`'s initial implementation only checked Bucket 2.3's two caches for reuse, not its own prior output (`fr3_embeddings.npz` itself), so a second run re-embedded all 6,197 "fresh" sequences again | Caught by the acceptance suite's reproducibility test, not assumed correct from the first green run. Fixed by adding the stage's own output path to the reuse-source list; re-verified a second run now reports `freshly_embedded: 0` and byte-identical `peptide_id_order_sha256`/`embeddings_cache_sha256` to the first run (acceptance suite: 555s → 20s). |
| 2026-10-14 | A spot-check acceptance test comparing a freshly re-embedded 5-sequence sample against `fr3_embeddings.npz` uses `atol=1e-5` (justified, not loosened-until-green), not exact equality | A direct diagnostic (embedding one fixed test sequence alone vs. padded alongside a longer sequence in the same batch, in two separate WSL calls) measured a real ~2.7e-7-9.5e-7 absolute per-element difference — PAD-token presence perturbs floating-point summation order in self-attention for the other real tokens in that batch, even though pooling mathematically excludes PAD positions. Repeated calls with the IDENTICAL batch composition (verified separately) ARE bit-identical, so this is padding-dependent numerical noise, not true non-determinism. Tolerance set two orders of magnitude above the measured noise floor. Consistent with (and quantifies more precisely than) `test_embeddings.py`'s existing `batch_size=32` vs. `batch_size=1` check, which already used `atol=1e-5` rather than exact equality. |
| 2026-10-14 | Bucket 3.3's per-fold scaler is fit exclusively on that fold's GraphPart training-positive rows (never on held-out positives, C1, C2, C3, or the external control), rather than one global scaler fit on all 1,205 FR1 positives | Mirrors the already-approved C3 fold-safe-centroid design (`curation/c3.py`, AGENTS.md rule 5) rather than opening a new approval round for the same leakage-prevention principle applied to a second statistic. A global scaler would let fold k's own held-out positives influence the statistics later used to transform those same held-out positives at evaluation time — a real, if subtle, leakage channel. Verified directly: each fold's own training rows standardize to mean≈0/std≈1 after applying that fold's scaler; training/held-out peptide_id sets never overlap and always sum to exactly 834 per fold, with zero C1/C2/C3/external-control contamination. Flagged explicitly since it determines downstream experiment comparability — every FR4 condition must use its own fold's scaler, never a shared one. |
| 2026-10-14 | Bucket 3.3 materializes only the raw 495-dim fused matrix plus small per-fold scaler parameters (mean/std/training-peptide-id-list) and a tested `apply_scaler()` function — it does NOT write 5 separate fully-scaled feature caches (one per fold) | Reserved for Task 3.4 per the task's own explicit scope boundary ("do not duplicate the feature-cache responsibilities assigned to Task 3.4"). A fold-specific scaled cache is trivially derivable from the committed scaler parameters + the raw fused matrix via `apply_scaler()`, so nothing is lost by not precomputing it here, and it avoids ~5x the storage for an artifact nobody asked this task to own. |
| 2026-10-14 | Bucket 3.3's z-score scaler is hand-implemented (~10 lines of numpy: mean/std with a zero-variance-to-1.0 guard) rather than using scikit-learn's `StandardScaler`, even though scikit-learn 1.7.2 is already installed in this environment | Consistent with this project's existing hand-rolled-formula style (same reasoning already applied to Task 3.1's descriptor formulas over Biopython) — the operation is simple enough that a transparent, fully-auditable implementation is preferable to a library dependency that isn't declared in `requirements.txt`/`pyproject.toml` anyway. No new dependency added or declared. |
| 2026-10-14 | Bucket 3.4's `common/feature_cache.py` imports only numpy/pandas/json/hashlib (plus a lazy, same-constraint import of `curation/feature_fusion.py`'s `apply_scaler` and, only inside the C3-specific helper, `curation/c3.py`) — never `common/embeddings.py`, `esm`, or `torch` | The whole point of a "feature cache" is that an FR4 training script can load it without an ESM-2 model load, a WSL subprocess, or GPU/CPU inference — verified empirically in a genuinely fresh subprocess (not just "this test file never imported torch"), since other tests in the same pytest session already import torch and would mask a real accidental import if checked in-process. |
| 2026-10-14 | Each of Bucket 3.4's 5 fold caches holds the SCALED version of every one of the 9,356 rows (the full C3 union included), not a fold-filtered subset | Matches Task 3.3's own validation pattern (apply each fold's scaler to every row) and keeps the cache's job purely about *scaling*, not about *selection* — C3's fold-specific hard-challenge membership is a separate, already-solved problem (`curation/c3.py::load_fold_challenges`) that this task must not reimplement or shortcut. `get_c3_fold_challenge_rows()` enforces this by construction: it resolves membership via that function and additionally refuses a cache/fold_id mismatch, so a caller cannot accidentally score fold k's candidates under fold j's scaler. |
| 2026-10-14 | The scaled feature cache is stored as float32 (one explicit downcast from the scaler's float64 fit/apply arithmetic), not float64 | Halves on-disk size (5 × ~9MB vs. ~18MB) for an error on the order of 1e-7 relative, many orders of magnitude below any meaningful downstream classifier signal — consistent with the embeddings cache's own float32 convention (Bucket 3.2) and the project's established tolerance-setting precedent for floating-point rounding that doesn't change scientific conclusions. Verified directly: each fold's training rows still standardize to mean≈0/std≈1 after the downcast, matching Task 3.3's float64-precision validation closely. |
| 2026-10-14 | `load_fold_feature_cache()` verifies the cache file's SHA-256 against its manifest entry BEFORE reading any array, then separately re-verifies shape/dtype/schema-version/scaler-identity after loading, raising a specific `CorruptedCacheError` naming the exact mismatch rather than a generic exception | Satisfies the explicit "corrupted-cache rejection" acceptance requirement with real teeth — a cache that merely fails to parse would be caught by numpy regardless, but a cache that parses fine yet silently drifted (wrong fold's scaler embedded by a copy-paste mistake, a truncated-but-still-valid-zip file, a stale manifest after a partial regeneration) would not be, without this layered check. Verified against 6 distinct corruption modes in unit tests plus one real-file corruption in the acceptance suite. |
| 2026-10-14 | Bucket 3.5's demo uses 7 fixed, real peptide_ids read live from the accepted pipeline outputs, instead of bundling a small synthetic/precomputed fixture dataset | A parallel toy dataset would need its own maintenance and could silently drift from the real pipeline's actual behavior, undermining the point of a pipeline *demonstration*. Operating directly on the real (if gitignored) large-array outputs means the demo only runs after Tasks 3.1-3.4 have actually been executed in this checkout — judged the correct tradeoff, since the task brief frames this as demonstrating the *existing* pipeline, not a standalone fresh-clone showcase. A clear `FileNotFoundError` naming the exact missing file and which command produces it covers the "not yet run" case rather than failing confusingly. |
| 2026-10-14 | ESM-2 embeddings are loaded from `fr3_embeddings.npz` in the demo rather than re-invoked live via `embed_via_wsl`, even though WSL is available in this dev environment | Directly satisfies "independent of internet/GPU access" and "heavy extraction may be precomputed for the offline presentation" from the task brief — a presenter without WSL/GPU set up (or presenting from a different machine) can still run the demo as long as Tasks 3.1-3.4's artifacts are present. Verified empirically, not just by code inspection, via a subprocess-isolated smoke test confirming `torch`/`esm` never enter `sys.modules` anywhere in the demo's execution. |
| 2026-10-14 | The demo's output file (`fr3_demo_output.json`) is committed and doubles as the literal expected-output reference, rather than a separate static example written by hand | A hand-written example could silently drift from what the real code actually produces. Committing the live output and asserting byte-identical reproducibility in tests means the "expected output" can never go stale without a test catching it. |

*(Add new rows here, do not delete old ones — this is a historical log.)*
