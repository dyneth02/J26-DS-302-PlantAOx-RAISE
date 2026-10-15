# Implementation Status — Component 02 (PU-AOP)

**Last updated:** 15 October 2026
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

### Bucket 4, Task 4.1 — Shared Experiment Infrastructure
- **Status: technical acceptance passed.** First Bucket 4 (Model Baselines) work — branch
  `feat/c2-model-baselines-setup`. Delivers configuration, model architecture, fold-aware data
  interface, seeding, and checkpoint/run-recording utilities shared by every FR3 baseline (PN, nnPU,
  Two-Step PU, PU-Bagging). **No risk estimator, training objective, or training loop is implemented —
  that is explicitly Task 4.2+'s job**, kept out of this task's scope on purpose so every baseline is
  later compared on identical architecture/data/reproducibility footing.
- **`torch` is now a declared dependency** (added to `requirements.txt`) — previously installed in the
  Windows `.venv` but undeclared (same gap already flagged for several other packages at Task 3.1).
  Unlike Bucket 3.2's ESM-2 extraction, Bucket 4 model code runs directly on Windows (CPU-only here,
  `torch.cuda.is_available()` is `False` in this environment) — there is no WSL subprocess indirection
  for model training, since nothing about an MLP forward/backward pass requires the WSL-only
  fair-esm/CD-HIT/GraphPart toolchain. **`run.py`'s module-level import graph remains torch-free**
  despite this: the new `fr4-infra-smoke-test` CLI stage lazily imports every torch-dependent Bucket-4
  module (`models.py`, `experiment_data.py`, `run_recorder.py`, `common/seeding.py`, and `torch` itself)
  INSIDE the stage function only — verified directly (`'torch' not in sys.modules` immediately after
  `import plantaox.c2_pu.run`), so every pre-existing FR1/FR2/FR3 CLI stage's behavior is provably
  unchanged.
- **§A Configuration (`experiment_config.py::ExperimentConfig`):** a plain, frozen `dataclass` (no
  pydantic — not an existing project dependency, and the validation needed is simple range/membership
  checks, consistent with this project's hand-rolled-validation style elsewhere) with `__post_init__`
  raising a specific `ValueError` per invalid field. Covers every field the task brief lists:
  experiment identifier, baseline (`PN`/`nnPU`/`TwoStepPU`/`PUBagging`), frozen `pp1_baseline_v1`/
  `pp2_baseline_v1` identifiers, `fold_id` (0–4), `feature_representation` (`fused`/`esm`/`descriptors`,
  with `feature_dim` 495/480/15 derived automatically), train/eval seeds, architecture
  (`hidden_dims`/`activation`) and optimizer (`optimizer`/`learning_rate`/`weight_decay`)
  hyperparameters, `batch_size`/`max_epochs`/`device`/`checkpoint_dir`, and explicit
  positive/unlabeled/validation/evaluation pool selection. The remaining record-keeping half (source-
  artifact checksums, git revision, software versions, timestamps, run status) is assembled at run
  time by `run_recorder.py` from real files, rather than duplicated into the static config.
- **§B Model (`models.py::BinaryMlp`/`MlpArchitecture`):** the proposed initial architecture exactly
  (495 → 128 ReLU → 64 ReLU → 1 logit), with `hidden_dims`/`activation`/`input_dim` all configurable.
  `forward()` returns raw logits only (shape/dtype validated); `predict_proba()` applies sigmoid under
  `no_grad()` without permanently changing the model's train/eval mode. `architecture_signature()` +
  `load_compatible_state_dict()` give "compatible model-state loading": a checkpoint's recorded
  architecture is compared against the live model's own BEFORE `load_state_dict` is ever called,
  raising `ArchitectureMismatchError` on any mismatch. **Zero loss function, optimizer step, or risk
  estimator anywhere in this file** — confirmed by direct inspection, not just intent.
- **§C Data (`experiment_data.py::build_experiment_data`):** thin orchestration over the already-
  accepted `common/feature_cache.py` loader — reuses `load_fold_feature_cache`/`get_training_rows`/
  `get_held_out_rows`/`get_pool_rows`/`get_c3_fold_challenge_rows` directly, adding only what Task 4.1
  requires on top: (1) column-slicing the same scaled 495-dim matrix for `esm`/`descriptors`
  representations (a documented simplification — these are post-hoc slices of the SAME jointly-fitted
  scaling, not an independently-refit standardization; see decision log), (2) a validation split carved
  deterministically from training-side positive IDs ONLY (a local, unseeded-by-global-state
  `random.Random`, never touching GraphPart's held-out fold), (3) evidence-tier attachment for every
  positive-pool subset, and (4) a pairwise peptide-ID-AND-sequence overlap check across all 7 returned
  subsets (train/validation/held-out positives, C1, C2, fold-specific C3, external control) that raises
  `DataLeakageError` with full detail on the first violation. `WrongFoldError` rejects a cache/fold_id
  mismatch explicitly. Verified empirically against the REAL fold-0 cache: 604 train + 106 validation
  (=710, the documented fold-0 training total) + 124 held-out, 3,788 C1, 2,000 C2, 2,000 C3 (fold-0's
  actual selection, confirmed smaller than the 2,325-sequence union — not silently returning the whole
  union), 38 external control, zero overlap across all 21 subset pairs.
- **§D Seeding (`common/seeding.py::set_global_seed`/`resolve_device`):** seeds Python/NumPy/PyTorch
  (CPU and CUDA-if-present) from one int, sets `torch.use_deterministic_algorithms(True, warn_only=True)`.
  Verified bit-identical on CPU: same seed → identical `torch.randn` output, identical `BinaryMlp`
  initial weights, identical forward-pass logits. **Determinism claim scoped precisely, per explicit
  instruction:** CPU bit-identity is verified directly; GPU bit-identity is explicitly NOT claimed
  (no CUDA device exists in this environment to verify against, and cuDNN kernels are well documented
  as not bit-reproducible across GPU architectures even with this flag set) — the returned context dict
  records `cuda_available`/device name precisely so a later audit knows which execution context
  produced a given result, rather than asserting an unverifiable universal guarantee.
- **§E Checkpointing/logs (`run_recorder.py`):** `create_run_dir` is collision-safe (timestamp +
  numeric suffix on collision); `write_resolved_config` is write-once-immutable (raises on a second,
  differing write); `append_epoch_metrics` reuses `common/io.py::append_provenance_log` rather than a
  second JSONL-append implementation; `save_checkpoint` is atomic (temp file + `os.replace()`, cleaned
  up on any exception) with an explicit `checkpoint_best.pt`/`checkpoint_last.pt` filename distinction;
  `load_checkpoint` verifies architecture compatibility (via §B) before loading; `RunContext` is a
  context manager writing `run_manifest.json` through `initialized` (on construction) →
  `running` (on `with` entry) → `completed`/`failed` (on exit), capturing full exception
  type/message/traceback on failure and never swallowing the exception.
- **One-command offline infrastructure smoke test** (`python -m plantaox.c2_pu.run
  fr4-infra-smoke-test`): config validation → real fold-0 data loading → `BinaryMlp` construction →
  one forward pass on 8 real training-positive rows → full checkpoint save/load round-trip, all under
  one `RunContext`. **Explicitly labeled, in both the printed summary and a dedicated acceptance test,
  as an infrastructure check, never a trained-baseline result** — no loss function, no training loop,
  no fabricated performance metric (accuracy/MCC/AUPRC/AUROC/F1/precision/recall/RNIS) appears anywhere
  in its output; a dedicated test asserts this key set is absent.
- **Tests:** 89 new tests total — 31 unit (`test_experiment_config.py`), 16 unit (`test_models.py`),
  11 unit (`test_seeding.py`), 13 unit (`test_run_recorder.py`), 18 unit (`test_experiment_data.py`,
  including deliberately-injected repeated-sequence-leakage and external-control-overlap scenarios that
  must be caught), and 11 full-file acceptance (`test_fr4_infra_smoke_test_acceptance.py` — real fold-0
  pool-size matching, leakage-report confirmation, checkpoint round-trip, run-manifest completeness,
  missing-prerequisite error clarity, reproducible reruns, collision-safe run dirs, and confirmation
  that every one of Tasks 3.1–3.5's real artifacts plus `pp1_baseline_v1`/`pp2_baseline_v1` remain
  byte-unchanged by SHA-256 before/after). Full project suite confirmed green after this change (see
  decision log for the exact before/after counts).
- **No unnecessary abstraction introduced.** No new config/validation library, no new JSONL writer (the
  existing `append_provenance_log` is reused), no new checksum helper (the existing
  `common/feature_cache.py::sha256_of` is reused), no duplicate C3 fold-selection logic (the existing
  `load_fold_challenges`/`get_c3_fold_challenge_rows` are called directly).

### Bucket 4, Task 4.2 — PN (Positive-Negative) Baseline Implementation
- **Status: technical acceptance passed (PASS).** The first conventional supervised classifier for
  Component 02, trained entirely on Task 4.1's shared infrastructure — no second MLP, no second
  checkpointing system, no second data loader. New module: `pn_baseline.py`. CLI stage:
  `python -m plantaox.c2_pu.run fr4-pn-baseline`.
- **Scientific framing (non-negotiable, stated in the module docstring, every log record, and the run
  summary's `limitations` block):** C1 is this project's assumed-negative/PU-unlabeled pool — peptides
  with no reported antioxidant activity, never experimentally confirmed inactive. PN is the field's
  conventional-practice reference point this project's proposal explicitly critiques (§1.2.1: "no AOP
  classifier has been trained without confirmed negative labels"), not a validated antioxidant
  predictor.
- **Two small, justified public renames in `experiment_data.py`** (pure renames, zero logic change,
  verified by rerunning its own 18 existing tests unmodified): `_split_training_validation` →
  `split_ids_train_validation`, `_assert_no_cross_subset_overlap` → `assert_no_cross_subset_overlap`.
  Both are reused as-is by Task 4.2's C1 partition and its own independent leakage re-check, rather than
  writing a second shuffle-split algorithm or a second overlap-detection routine.
- **E1-only positive selection (§3.1):** `select_positive_evidence_tier()` filters an already
  fold-partitioned positive pool (Task 4.1's `train_positive`/`validation_positive`) down to one
  evidence tier, never relabeling or reweighting rows, never touching the underlying train/validation/
  held-out partition boundary. Verified against the real fold-0 cache: 331 E1 of 604 total training
  positives, 48 E1 of 106 validation positives (E2's 273/58 correctly excluded, available unchanged for
  Task 4.3+).
- **C1 train/validation partition (§4):** `split_c1_train_validation()` partitions C1's cache rows
  (already deduplicated to one row per unique sequence by Task 3.1/3.4) using the SAME authoritative
  `config.validation_fraction` (0.15) and `config.eval_seed` (42) Task 4.1 already uses for the positive
  split — no new config field introduced, since the repository already defines this authoritative
  fraction. Verified against real fold-0 C1 (3,788 unique sequences): 3,220 train / 568 validation
  (85.0%/15.0%, exact). Asserts C1 has no duplicate peptide_id before partitioning (a project-wide
  dedup invariant from Task 3.1, re-checked here rather than assumed) and reuses
  `split_ids_train_validation` rather than a second shuffle-split implementation.
- **`PnDataset` structurally prevents C2/C3/external-control leakage** — it has no field for them at
  all, so a future caller cannot accidentally wire them into PN training even by mistake; a dedicated
  test (`test_build_pn_dataset_only_draws_negatives_from_c1`) asserts the dataclass has no such
  attribute. `build_pn_dataset()` additionally re-runs `assert_no_cross_subset_overlap` across all 8
  relevant subsets (E1 train/validation, C1 train/validation, GraphPart held-out, C2, C3, external
  control) — independently of Task 4.1's own `ExperimentData.leakage_report`, not trusting it blindly.
- **A real bug found and fixed during test-writing, before any claim of acceptance:** the original
  `build_pn_dataset()` called `split_c1_train_validation()` before checking whether C1 was non-empty, so
  a zero-C1 scenario surfaced a generic `ValueError` from deep inside the shared split helper instead of
  this module's own `InsufficientDataError`. Fixed by moving the zero-C1 check before the split call —
  caught by `test_build_pn_dataset_raises_on_zero_c1_rows`, not assumed correct from a first green run.
- **Class imbalance (§5):** `compute_pos_weight()` derives `BCEWithLogitsLoss(pos_weight=...)` from
  TRAINING-set class counts only (verified: validation counts are structurally absent from the
  computation, not merely unused) — real fold-0 value: `3220/331 ≈ 9.728`. `use_class_weight=False`
  disables it entirely for future ablations, per explicit instruction, without any resampling,
  oversampling, or prevalence change anywhere in the pipeline.
- **Training loop (§6-§8):** manual seeded mini-batch iteration (a local `numpy.random.Generator`, not
  `torch.utils.data.DataLoader`, for easier exact-reproducibility verification), `BCEWithLogitsLoss` on
  raw logits (sigmoid is verified numerically equivalent to a separate `binary_cross_entropy` call, but
  never applied before the loss), Adam (or SGD) via `config.optimizer`, explicit finite-value checks on
  input features, logits (train AND validation), loss, and every parameter's gradient (raises
  `RuntimeError` naming the exact offending epoch/tensor, never silently continuing past a NaN/Inf).
  `save_checkpoint()` (Task 4.1) is called every epoch for `checkpoint_last.pt` and only on improvement
  for `checkpoint_best.pt` — both filenames reused exactly as Task 4.1 defined them, no new
  checkpoint-naming scheme. Optional early stopping (`patience=10`, `min_improvement=1e-4` by default)
  monitors validation loss only; disabling it (`early_stopping_patience=None`) runs the full
  `max_epochs` — both paths tested.
- **Real fold-0 result (Stage C), not fabricated:** 14 epochs executed before early stopping triggered
  (patience 10 after the last improvement), best epoch 3 (val loss 0.3138), final train loss 0.0723 vs.
  final val loss 0.6250 at epoch 14 — a genuine, reported overfitting pattern (train loss keeps
  dropping well past the point validation loss starts rising), consistent with §12.B's documented
  shortcut-bias/limited-E1-positive-count risk rather than evidence of a bug. Reported as-is, not
  cherry-picked or re-run until a "nicer" curve appeared.
- **Learning curve:** `render_loss_curve_svg()` is a ~40-line hand-rolled SVG line chart (no matplotlib
  — confirmed not installed, and this project already deliberately avoided adding it once before, for
  Task 2.5's single exploratory chart; same reasoning applied here for this single plot). Committed at
  `fr4_pn_baseline_fold0_learning_curve.svg` (text-based SVG, a few hundred bytes — not a "large binary
  artifact" under any reading of the repository's existing policy).
- **Checkpoint validation (§8):** after training, a FRESH `BinaryMlp` instance is constructed, loaded
  from `checkpoint_best.pt` via Task 4.1's compatibility-checked `load_checkpoint()`, and run through
  `predict_proba()` on real validation-fold feature rows — shape, finiteness, and `[0, 1]`-boundedness
  all verified directly on the reloaded model's own output (not merely "the file exists").
- **Reproducibility (§8):** two independent same-seed CPU training runs on the real fold-0 dataset
  produce a **bit-identical** per-epoch loss history and an identical best epoch — verified directly,
  not assumed from Task 4.1's forward-pass-only determinism check. This confirms training-loop
  determinism (backward pass + optimizer step across many iterations) holds in addition to the
  simpler forward-pass case Task 4.1 already verified.
- **Checkpoints are NOT committed** (gitignored under `data/interim/c2_pu/fr4_pn_baseline_runs/`,
  consistent with the project's established "don't commit large binary arrays" policy) — the committed
  summary records each checkpoint's SHA-256 instead, so integrity is auditable and the run is exactly
  regeneratable via `fr4-pn-baseline` without needing the binary file itself.
- **Tests:** 27 unit tests (`test_pn_baseline.py` — E1/E2 selection, C1 partition determinism and
  disjointness, two deliberately-injected cross-pool sequence-leakage scenarios correctly caught,
  zero-E1/zero-C1 rejection, training-only class weight, BCE-with-logits numerical equivalence to
  sigmoid-then-BCE, optimizer parameter updates, non-finite-feature rejection, best/last checkpoint
  correctness, bit-identical same-seed reproducibility, early-stopping on/off, and the SVG curve writer)
  + 16 full-file acceptance tests (`test_fr4_pn_baseline_acceptance.py` — real fold-0 Stage B smoke test
  and Stage C full run, GraphPart held-out isolation re-verified independently, real class counts,
  checkpoint reload verification, bit-identical full-run reruns, every prior task's real artifacts and
  the frozen FR1/FR2 baselines confirmed byte-unchanged by SHA-256 before/after, and a clear
  `FileNotFoundError` for a missing prerequisite). Full project suite confirmed green after this change
  (see decision log for the exact before/after counts).
- **Research limitations, stated in full (§12), not just referenced:** (A) C1's assumed-negative status
  is unverified — PN is a conventional supervised control, not a scientifically validated negative-label
  classifier. (B) FR2/Task 2.5 documented substantial FR1-positive-vs-C1 distributional differences
  (length, charge, GRAVY, aromaticity, composition); this fold-0 run's validation performance may
  reflect those shortcuts rather than genuine antioxidant-activity discrimination — not interpreted as
  proof of robust prediction anywhere in this task's code or docs. (C) E1 only is used for the positive
  class; E2 remains available, untouched, for Task 4.3+'s evidence-tiered experiments. (D) Full
  C1/C2/C3 cross-pool comparison, calibration, and RNIS are explicitly out of Task 4.2's scope
  (Task 4.5). (E) A successful fold-0 run is an initial implementation demonstration, not completed
  five-fold validation. (F) Technical acceptance here does not imply supervisor or scientific sign-off
  on PN as a methodology.
- **No new dependencies** (matplotlib deliberately avoided, per above). Tasks 4.3 (nnPU), 4.4 (Two-Step
  PU/PU-Bagging), 4.5 (cross-baseline evaluation), 4.6 (curriculum), and RNIS/FR6 are untouched.

### Bucket 4, Task 4.3 — Plain nnPU (Non-Negative Positive-Unlabeled) Baseline Implementation
- **Status: technical acceptance passed (PASS).** The first PU-learning classifier for Component 02,
  trained entirely on Task 4.1's shared infrastructure and reusing Task 4.2's deterministic C1
  train/validation partition unchanged — no second MLP, no second checkpointing system, no second data
  loader, no second C1-splitter. New modules: `nnpu_risk.py` (pure risk-estimator math, zero training
  loop), `nnpu_baseline.py` (dataset assembly + training loop). CLI stage:
  `python -m plantaox.c2_pu.run fr4-nnpu-baseline`.
- **Scientific framing (non-negotiable, stated in every module docstring, every log record, and the run
  summary's `limitations` block):** C1 is never assigned a binary negative label anywhere in this
  module — it is passed to the non-negative PU risk estimator as the UNLABELED group U. Unlike PN
  (Task 4.2), which trains E1-vs-C1-as-negative BCE, this baseline trains E1+E2-vs-C1-as-unlabeled
  under the non-negative PU risk. These are different estimators under different label assumptions;
  Section 16.F of the task brief (and this entry) explicitly forbid comparing their raw loss numbers as
  evidence one baseline "outperforms" the other.
- **Mathematical formulation implemented exactly as specified** (`nnpu_risk.py`):
  `R_nnPU = pi*R_p^+ + max(0, R_u^- - pi*R_p^-)`, with `l(f,+1)=softplus(-f)`/`l(f,-1)=softplus(f)`
  (sigmoid never applied before the loss), each of `R_p^+`/`R_p^-`/`R_u^-` a SEPARATE per-group mean
  (never a combined positive+unlabeled mean) so the pi/|P|/|U| weighting holds regardless of the
  positive/unlabeled mini-batch size ratio drawn by the training loop.
- **nnPU variant explicitly identified and scope-decided before implementation, not silently picked:**
  the ORIGINAL nnPU paper (Kiryo et al. 2017) also specifies a corrective training PROCEDURE (gradient
  ASCENT on the negative-risk estimate below a `-beta` threshold, scaled by `gamma`) that is related to
  but NOT the same algorithm as the displayed clamped risk's own gradient (which is exactly zero when
  clamped). `docs/PU_AOP_RESEARCH_CONTEXT.md`, `docs/PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`
  (Sections 4.3/4.6), the proposal's FR3/FR4 table, and every existing decision-log entry were inspected
  directly before writing any code — **none specifies the beta/gamma corrective procedure, nor a
  beta/gamma value.** Per the task brief's own explicit fallback instruction, this implementation uses
  ONLY the **direct-clamped objective** — backpropagating through `max(0, R_n)` itself — recorded as
  `nnpu_variant: "direct_clamped"` in every run's resolved config/manifest/summary. The beta/gamma
  corrective variant is NOT implemented anywhere in this component as of Task 4.3; this is a logged
  scope decision (see decision log below), not an oversight, and there is accordingly no "Test J" in
  `test_nnpu_risk.py` (that test is explicitly N/A per its own trailing comment).
- **Mandatory risk-estimator unit tests (Stage A, run and passing BEFORE any real training per the task
  brief's own gate): 32 tests in `test_nnpu_risk.py`** — known manual risk values cross-checked against
  an independent high-precision Python reference (not `torch.nn.functional.softplus` itself), the
  positive-negative-risk-positive case equaling the unbiased PU risk exactly, the negative case clamping
  to zero exactly, a DELIBERATELY algebraically-constructed (not accidental) zero-boundary case, gradient
  sign/zero-at-clamp verification, prior rejection (0/1/negative/>1/NaN/Inf/bool), numerical stability at
  logits up to 1e8, per-group-mean (not raw-count-weighted) semantics verified by a doubled-unlabeled-
  group invariance test, empty-positive/empty-unlabeled/both-empty rejection, non-finite-logit rejection,
  and (batch, 1)-shaped logit acceptance (matching `BinaryMlp.forward`'s own output shape).
- **E1+E2 positive selection (§6.1), preserving per-row evidence-tier provenance:**
  `select_e1_e2_positive_evidence()` filters an already fold-partitioned positive pool down to E1+E2
  ONLY (any other tier, including a hypothetical future E3 row, is excluded via an explicit
  tier-membership mask — never an "everything that isn't E1" catch-all). Verified against the real
  fold-0 cache: **331 E1 + 273 E2 = 604 training positives; 48 E1 + 58 E2 = 106 validation positives** —
  matching Task 4.2's own documented pre-tier-selection totals exactly (re-derived directly from the
  real cache, not trusted from the report). `NnPuDataset.train_positive_tiers`/
  `validation_positive_tiers` keep E1-vs-E2 provenance separately auditable; `e1_train_count`/
  `e2_train_count`/`e1_validation_count`/`e2_validation_count` are recorded in every run summary and
  resolved config. No evidence-tier weighting, soft labels, or confidence-driven curricula are applied
  (Section 6.2's explicit prohibition).
- **C1 unlabeled-group partition (§7): reuses `pn_baseline.split_c1_train_validation` UNCHANGED** — the
  IDENTICAL deterministic split (same `config.validation_fraction`=0.15/`config.eval_seed`=42 Task 4.1
  already defines) Task 4.2 uses for its own C1 partition, not a second C1-splitter. Verified against the
  real fold-0 C1 (3,788 unique sequences): **3,220 train / 568 validation**, byte-identical membership to
  PN's own C1 partition (re-derived and compared directly in `test_build_nnpu_dataset_c1_partition_matches_pn_shared_splitter`
  and the real-cache acceptance test). C1 is never joined into a single labeled array with the positive
  group anywhere in `NnPuDataset` — there is structurally no label field for it (a dedicated test asserts
  `NnPuDataset` has no `train_unlabeled_labels` attribute). C2, C3, and the external control are
  structurally absent from `NnPuDataset` (same discipline as `PnDataset`), so they cannot leak into an
  nnPU run even by accident. `build_nnpu_dataset()` independently re-runs
  `experiment_data.assert_no_cross_subset_overlap` across all 8 relevant subsets (E1+E2 train/validation,
  C1 train/validation, GraphPart held-out, C2, C3, external control) — not trusting Task 4.1's own
  `data.leakage_report` blindly.
- **Positive-class prior pi (§8): no pre-specified prior or estimation method exists anywhere in this
  project's documentation** — `docs/PU_AOP_RESEARCH_CONTEXT.md`, the Planner doc's FR3/FR4 rows and
  Sections 4.3/4.6, the proposal's abridged requirement table, and the full `IMPLEMENTATION_STATUS.md`
  decision log were inspected directly (not assumed) before choosing a default. Per the task brief's own
  explicit fallback instruction, `DEFAULT_PRIOR = 0.10` is used as a clearly-labeled **PROVISIONAL
  modeling/sensitivity-analysis anchor** — `PRIOR_PROVENANCE_NOTE` (recorded verbatim in every run's
  resolved config and summary `limitations` block) states this explicitly and states that the naive
  sampling ratio `n_labeled_positive / (n_labeled_positive + n_C1)` is deliberately NOT used as pi
  (Section 8.1's own prohibition — C1 was built from a structurally different source distribution than
  the positive pool, so that ratio is not a valid biological-prevalence substitute either).
  `PRIOR_SENSITIVITY_GRID = (0.05, 0.10, 0.20)` is defined and the risk estimator/dataset builder/
  training loop are verified to accept any value in `(0, 1)` (unit-tested directly); **full sensitivity
  TRAINING across all three values is explicitly deferred** (Section 8.3 permits this) — only the
  `pi=0.10` fold-0 run is this task's genuine baseline result. `pi` is validated (`InvalidPriorError` on
  `<=0`, `>=1`, `NaN`, `Inf`, or `bool`) before any data is touched.
- **Model architecture and feature compatibility (§9): reuses `BinaryMlp`/`MlpArchitecture`/
  `ExperimentConfig`/`build_experiment_data()`/`run_recorder.py` exactly as PN did** — same
  `495 → 128 ReLU → 64 ReLU → 1 logit` architecture, same accepted fold-0 495-dim scaled features (no
  scaler refitting, no embedding/descriptor recomputation, no column rearrangement). The model is
  initialized FRESH and seeded (`set_global_seed(config.train_seed)`) for every nnPU run — **never
  initialized from the trained PN checkpoint**, confirmed by direct code inspection (no checkpoint-load
  call anywhere before `train_nnpu_baseline`'s own fresh `BinaryMlp(...)` construction).
- **Training loop (§10), paired positive/unlabeled mini-batches:** `_CyclingIndexSampler` gives the
  smaller E1+E2 positive pool (604 train rows) a full-size, independently-shuffled mini-batch for EVERY
  larger C1-unlabeled (3,220 train rows) mini-batch step across one full unlabeled-pool pass per epoch —
  documented explicitly as the "full unlabeled pass with cycling positive batches" design named in the
  task brief's own menu of acceptable paired-batch strategies (Section 10.1), using an independent,
  seeded RNG stream (`config.train_seed + 1_000_003`) so same-seed reruns stay bit-identical. The risk
  objective itself (per-group means in `compute_nnpu_risk`) is agnostic to whatever batch-size ratio this
  particular loop happens to draw — verified directly in `test_nnpu_risk.py`'s batch-size-semantics
  tests, independent of this training-loop design choice. Every epoch logs every component Section 10.3
  requires (train/validation nnPU risk, positive-risk contribution, positive-as-negative risk,
  unlabeled-as-negative risk, unclamped and clamped negative-risk, clamped-update fraction, learning
  rate, prior, E1+E2/C1 counts, optimizer-update count, and `is_best`) to `epoch_metrics.jsonl` via the
  UNCHANGED `run_recorder.append_epoch_metrics`. Non-finite inputs/logits/risk/gradients all raise
  `RuntimeError` naming the exact offending epoch/tensor (Section 10.4), mirroring PN's own
  fail-loudly discipline exactly.
- **Checkpoint/validation/reload (§11-§12): reuses `run_recorder.save_checkpoint`/`load_checkpoint`
  unchanged** — `checkpoint_best.pt`/`checkpoint_last.pt`, best-checkpoint selection by MINIMUM
  validation nnPU risk only (never GraphPart held-out, C2, C3, or external control), early stopping
  (`patience=10` default) monitoring validation nnPU risk only. Validation nnPU risk is computed once per
  epoch over the FULL validation E1+E2 (106 rows) + validation C1 (568 rows) sets (no mini-batching
  needed at this scale) and is explicitly labeled, in the module docstring and the run summary's
  `limitations.validation_risk_is_a_surrogate`, as "a surrogate under the assumed prior and the C1
  sampling model, not an independently measured biological classification error." After training, a
  FRESH `BinaryMlp` is constructed, loaded from `checkpoint_best.pt` via the compatibility-checked
  `load_checkpoint()`, and run through `predict_proba()` on real validation-fold rows — shape,
  finiteness, and `[0,1]`-boundedness all verified directly on the reloaded model's own output.
- **Real fold-0 result (Stage D), not fabricated:** 26 epochs executed before early stopping triggered
  (patience 10 after the last improvement at epoch 15), best validation nnPU risk **≈1.843e-4** at epoch
  15, final train risk ≈8.45e-4, final validation risk ≈1.60e-3. **A genuine, reported stability
  observation (Section 10.4/16, not hidden):** the negative-risk term was clamped to zero in roughly
  98–100% of optimizer updates in EVERY epoch of this run (not just late epochs) — `mean_train_clamped_
  update_fraction` over the last 5 epochs ≈0.994, recorded per-epoch in `stability_diagnostics` and
  `epoch_metrics.jsonl`. This means `R_u^- - pi*R_p^-` was negative for nearly every mini-batch
  throughout training at `pi=0.10` on this fold/feature representation — for most updates, the direct-
  clamped objective's gradient reduces to the positive-risk term alone (the unlabeled-group gradient is
  exactly zero when clamped, per `test_gradient_is_zero_for_unlabeled_group_when_clamped`). This is
  reported as-is, not re-run with a different prior to produce a "nicer" clamping profile — see the Task
  4.3 research-limitations note below and `fr4_nnpu_baseline_fold0_summary.json`'s own
  `stability_diagnostics` field for the full per-run numbers. No divergence was detected
  (`diverging_risk_detected: false`) and validation predictions were not fully saturated (≈47% of
  validation rows scored <0.01, ≈18% scored >0.99 at the final epoch).
- **Learning curve:** reuses `pn_baseline.render_loss_curve_svg` (generalized with optional
  `train_key`/`val_key`/`title` parameters, defaulting to PN's original hardcoded BCE keys/title so every
  existing PN caller/test is byte-for-byte unaffected — re-verified: all 27 pre-existing `test_pn_
  baseline.py` tests pass unchanged after this change) rather than a second hand-rolled SVG writer.
  Committed at `fr4_nnpu_baseline_fold0_learning_curve.svg`.
- **Checkpoint validation and same-seed reproducibility (Stage E):** two independent same-seed CPU
  training runs on the real fold-0 dataset produce a **bit-identical** per-epoch risk history and
  identical best epoch (verified directly: `history == history`, `best_epoch == best_epoch`,
  `class_counts == class_counts`). The saved checkpoint FILES' SHA-256 differ between reruns (the
  `run_recorder.save_checkpoint` payload embeds a live `saved_at` timestamp — the same, pre-existing
  mechanism PN's own checkpoints already have), but the underlying model STATE_DICT tensors are
  confirmed bit-identical by direct tensor comparison across two independent reruns' best checkpoints
  (`test_reruns_produce_bit_identical_checkpoint_weights`) — this is the actual reproducibility claim,
  not the incidental file hash.
- **Checkpoints are NOT committed** (gitignored under `data/interim/c2_pu/fr4_nnpu_baseline_runs/`,
  same pattern as `fr4_pn_baseline_runs/`) — the committed summary records each checkpoint's SHA-256
  instead, so integrity is auditable and the run is exactly regeneratable via `fr4-nnpu-baseline` without
  needing the binary file itself.
- **Tests:** 32 unit tests for the risk estimator (`test_nnpu_risk.py` — Tests A-I of the task brief's
  mandatory list, all mathematically verified against independent reference computations, not merely
  "ran without crashing"; Test J is N/A, see above) + 33 unit tests for dataset assembly/training
  (`test_nnpu_baseline.py` — E1+E2 selection, E3 exclusion, C1-only unlabeled selection matching PN's own
  splitter, two deliberately-injected cross-pool sequence-leakage scenarios correctly caught, zero-E1E2/
  zero-C1 rejection, prior validation, the cycling positive sampler's determinism/wraparound/reshuffle
  behavior, optimizer parameter updates, non-finite-feature rejection, every required risk component
  present in the epoch log, best/last checkpoint correctness, checkpoint reload + bounded/finite
  inference, bit-identical same-seed reproducibility, early stopping on/off and monitoring validation
  risk only, and stability-diagnostics presence) + 21 full-file acceptance tests
  (`test_fr4_nnpu_baseline_acceptance.py` — real fold-0 Stage C smoke test, GraphPart held-out isolation
  re-verified independently, real E1/E2/C1 counts matching Task 4.2's documented totals exactly, prior
  configuration/validity, every required risk component present over a REAL run's full history,
  checkpoint reload verification, bit-identical full-run reruns (history AND underlying checkpoint
  weights), every prior task's real artifacts and the frozen FR1/FR2 baselines confirmed byte-unchanged
  by SHA-256 before/after, PN's own summary file confirmed at a genuinely separate path, and a clear
  `FileNotFoundError` for a missing prerequisite). Full project suite run after this change — see
  decision log for the exact before/after counts.
- **Research limitations, stated in full (§16), not just referenced:** (A) `pi=0.10` is an explicitly
  PROVISIONAL modeling assumption, not an independently estimated biological prevalence — see
  `PRIOR_PROVENANCE_NOTE`. (B) E2 positives are benchmark-annotated, provisional, not uniformly
  assay-confirmed; pooling E1+E2 (Task 4.3's baseline policy, unlike PN's E1-only) trades a larger
  labeled-positive count for a less uniformly verified one. (C) The labeled-positive population
  (literature/benchmark-derived) may not represent the true positive subpopulation present within C1 —
  nnPU does not automatically resolve this source-distribution bias. (D) C1 was not necessarily sampled
  from the same biological population as the labeled positives (FR2/Task 2.5's own KS-test distributional
  findings apply here unchanged — see that section above); standard PU mixture assumptions may be
  imperfect. (E) nnPU risk is NOT directly interchangeable with PN's BCE loss — the ≈1e-3-to-1e-4-scale
  nnPU risk numbers in this run must never be read as "nnPU outperforms PN" (PN's own BCE loss, Task 4.2,
  bottomed out at ≈0.31); they are different estimators of different targets under different label
  assumptions. (F) This is a working fold-0 baseline using the direct-clamped nnPU variant only, not a
  statistically validated five-fold comparison, and not an implementation of the original paper's
  beta/gamma corrective training procedure. (G) Technical acceptance does not imply supervisor approval
  of the chosen prior, the E1+E2 pooling policy, the direct-clamped-variant choice, or any scientific
  conclusion. (H) The persistent negative-risk clamping observed in this run (≈98–100% of updates per
  epoch) is reported as a genuine modeling observation requiring supervisor/scientific review before any
  claim that this nnPU configuration is "working as intended" in the PU-learning sense, rather than
  behaving close to positive-risk-only training for most of the run.
- **No new dependencies.** Tasks 4.4 (Two-Step PU/PU-Bagging), 4.5 (cross-baseline evaluation), 4.6
  (curriculum), and RNIS/FR6 remain untouched and unstarted, per this task's explicit scope boundary.

### Bucket 4, Task 4.3 — POST-ACCEPTANCE DIAGNOSTIC: π-sensitivity and negative-risk-clamping investigation
- **Status: diagnostic complete, PASS status of Task 4.3 itself unchanged.** The accepted π=0.10
  fold-0 run's own reported stability observation (≈98–100% of optimizer updates had their negative-risk
  term clamped to zero, logged in `stability_diagnostics` and the decision-log entry above) was
  investigated via a controlled π ∈ {0.05, 0.10, 0.20} sensitivity experiment, per explicit
  post-acceptance-diagnostic instructions. **This is an additional investigation, not a rebuild**: the
  direct-clamped nnPU estimator (`nnpu_risk.py`) and the accepted training loop
  (`nnpu_baseline.py::train_nnpu_baseline`) were NOT modified, and the beta/gamma corrective algorithm
  was NOT implemented (proposed as a follow-up only). Full report:
  **[`FR4_NNPU_PRIOR_SENSITIVITY_DIAGNOSTIC.md`](FR4_NNPU_PRIOR_SENSITIVITY_DIAGNOSTIC.md)**.
- **New modules, diagnostic-only, reusing the accepted estimator unchanged:** `nnpu_prior_diagnostics.py`
  (per-update risk-component instrumentation layered onto a training loop verified, by regression test,
  to reproduce `train_nnpu_baseline`'s own epoch aggregates exactly at the same prior/seed — i.e. the
  instrumentation changes nothing about what is trained) and `nnpu_prior_sensitivity_report.py`
  (comparison-table assembly + hand-rolled SVG plots, no new dependency, same precedent as
  `pn_baseline.render_loss_curve_svg`). New CLI stages: `fr4-nnpu-prior-sensitivity --prior <value>`
  and `fr4-nnpu-prior-sensitivity-report`.
- **Accepted π=0.10 baseline reused as the reference condition, not retrained.** Its committed summary's
  own recorded epoch history supplies every π=0.10 risk-trajectory comparison; its still-present best
  checkpoint (gitignored but present on disk in this checkout) was verified by SHA-256 against what the
  committed summary itself recorded, then loaded READ-ONLY (never resaved) to compute the
  prediction-distribution diagnostics Task 4.3's own run never recorded. Genuine new fold-0 training
  runs were performed only for π=0.05 (39 epochs, best epoch 28, best val nnPU risk ≈8.284e-4) and
  π=0.20 (21 epochs, best epoch 10, best val nnPU risk ≈1.726e-4) — all else held constant (same E1+E2/
  C1 partition, architecture, optimizer, seeds; verified identical membership across conditions by a
  dedicated test, not assumed from the shared code path).
- **Real finding: clamping is persistently near-universal across the entire declared sensitivity grid,
  not prior-dependent.** Mean per-update clamped-update fraction: 0.9825 (π=0.05), 0.9863 (π=0.10),
  0.9915 (π=0.20) — under 1 percentage point of spread across a 4x change in π. The epoch-aggregate
  unclamped negative risk R_n was negative in literally every epoch of every condition (39/39, 26/26,
  21/21). Clamping is present from epoch 1 (≈80% at the first epoch of the π=0.10 run) and intensifies
  toward ≈100% by the final epochs in all three conditions. **Classified as "Persistently clamped"**
  (see the diagnostic doc's §G for the full classification rationale) — not resolved by retuning π
  within this grid.
- **A genuinely prior-SENSITIVE secondary finding, reported separately so it is not conflated with the
  (prior-insensitive) clamping mechanism itself:** C1's own median predicted score (best checkpoint,
  validation-side) rises materially and monotonically with π — 0.0063 (π=0.05) → 0.0378 (π=0.10) →
  0.2977 (π=0.20). Labeled positives (E1/E2) remain confidently scored near 1.0 at every tested π (no
  all-positive/all-negative collapse detected in any condition, `diverging_risk_detected: false`
  throughout).
- **Accepted baseline and every frozen upstream artifact verified byte-unchanged throughout**, by
  SHA-256, both before this diagnostic's work began and after every new training run performed: the
  accepted π=0.10 summary JSON, its learning-curve SVG, its best/last checkpoint weights,
  `pp1_baseline_v1`/`pp2_baseline_v1` manifests, the FR3 feature-cache manifest/fusion scalers/record
  map, `c3_similarity_ranking.csv`, and the Task 4.2 PN baseline summary. Every new diagnostic artifact
  uses a `fr4_nnpu_prior_sensitivity_*` naming/path convention structurally distinct from
  `fr4_nnpu_baseline_*`, so it cannot collide with or overwrite the accepted baseline's own files.
- **Tests:** 18 unit tests (`test_nnpu_prior_diagnostics.py`) + 13 unit tests
  (`test_nnpu_prior_sensitivity_report.py`), both torch-free and always run, plus 14 gated acceptance
  tests (`test_fr4_nnpu_prior_sensitivity_acceptance.py`) covering real reduced-epoch smoke runs,
  same-seed reproducibility (epoch history AND underlying checkpoint weights bit-identical), the
  regression guard confirming zero change to the accepted training loop's own math, identical C1/
  positive-pool membership across all three prior conditions, missing-prerequisite error handling for
  the comparison-report stage, and full baseline/frozen-artifact preservation. **Full repository suite
  re-run after this change: 576 passed, 1 skipped, 0 failed** (`pytest tests/ -q`, 1171.16s) — up from
  the pre-diagnostic 531 passed/1 skipped, i.e. all 45 new tests pass and zero regression. See the
  diagnostic doc's §F for the full account of how the pre-existing Task 4.2/4.3 acceptance tests'
  own re-run side effects (timestamps/run-dir fields, provenance-log appends) were confirmed benign
  and restored to their committed state.
- **Recommendation (not unilaterally acted on): proceed to Task 4.4** — this diagnostic found no
  evidence of an implementation defect, only a documented, now-quantified, prior-insensitive stability
  characteristic of the direct-clamped objective under this fold/feature/data combination. A
  separately-scoped Variant A (direct-clamped, accepted) vs. Variant B (beta/gamma corrective, Kiryo et
  al.'s original procedure) comparison is recommended before relying on nnPU results in Task 4.5/4.6 —
  proposed as a follow-up only, not implemented here.

### Bucket 4, Task 4.3 — Corrective nnPU beta/gamma follow-up
- **Status: controlled follow-up complete. Task 4.3's accepted PASS and direct-clamped artifacts are
  unchanged.** Added `corrective_beta_gamma` as a separately named optimization variant; the accepted
  `direct_clamped` function and training loop retain their prior behavior. The corrective branch
  minimizes `-gamma * R_n` when `R_n < -beta`, while displayed/validation risk remains
  `pi*R_p^+ + max(0,R_n)` and is logged separately from optimizer loss.
- **Controlled run:** fold 0, π=0.10, β=0, γ=1, same E1+E2/C1 membership, fused 495-dimensional
  features, `BinaryMlp`, Adam, initialization and sample-order seeds, and early-stopping rule as the
  accepted run. A discrepancy was found between the brief (batch 64, weight decay 0.0001) and the
  accepted immutable resolved config (batch 32, weight decay 0.0); the latter was used so optimization
  variant remained the only changed factor.
- **Genuine result:** 27 epochs, best epoch 16, best validation nnPU surrogate risk 0.0630219. The
  corrective branch was used in 53.25% of all updates (52.87% over the final five epochs), versus the
  accepted direct run's 98.63% threshold/clamping frequency. This does not mean threshold frequency is
  itself a performance metric: the key difference is that corrective updates carry a C1-dependent
  gradient instead of suppressing it.
- **Best-checkpoint scores changed materially:** validation medians E1 1.000→0.682, E2 1.000→0.534,
  C1 0.0378→0.0168; fractions above 0.5 changed from 100%/100%/35.6% to 70.8%/53.4%/1.76%.
  Numerical training was stable, checkpoints reload, and scores are finite/bounded. These are
  diagnostic model scores, not calibrated biological probabilities; C1 remains unlabeled.
- **Artifacts/report:** `fr4_nnpu_corrective_fold0_summary.json`, separate gitignored best/last
  checkpoints, `fr4_nnpu_corrective_fold0_learning_curve.svg`, and
  [`FR4_NNPU_CORRECTIVE_COMPARISON.md`](FR4_NNPU_CORRECTIVE_COMPARISON.md). Corrective nnPU should be
  included as a distinct model in Task 4.5; no Task 4.5 evaluation was performed here.
- **Verification:** focused/relevant nnPU suite: 69 passed; complete repository suite:
  **646 passed, 1 skipped, 0 failed** (`python -m pytest tests -q`, 1249.45s). The skip is the existing
  environment-gated case, not a new failure. Frozen FR1/FR2 manifests and the FR3 cache manifest
  retained their accepted SHA-256 values.

### Bucket 4, Task 4.4 — Additional PU Baselines (Two-Step PU, PU-Bagging)
- **Status: technical acceptance passed (PASS).** Two more PU-learning baselines for Component 02,
  reusing Task 4.2/4.3's deterministic E1+E2 positive selection and C1 train/validation partition
  UNCHANGED, but trained on **scikit-learn/pulearn estimators, not `models.BinaryMlp`** -- a deliberate,
  documented architecture departure from PN/nnPU (see decision log). New modules: `pu_sklearn_common.py`
  (shared dataset assembly + sklearn-estimator checkpoint helper), `two_step_pu_baseline.py`,
  `pu_bagging_baseline.py`. CLI stages: `python -m plantaox.c2_pu.run fr4-two-step-pu-baseline` /
  `fr4-pu-bagging-baseline`.
- **Scientific framing, never to be weakened (same invariant as PN/nnPU):** C1 is this project's
  assumed-negative, PU-UNLABELED pool -- peptides with no reported antioxidant activity, never
  experimentally confirmed inactive. Both algorithms' own FIRST internal stage trains a classifier
  treating C1 rows AS IF negative (a label code of `y=0`, required by scikit-learn/pulearn's API, which
  has no three-way positive/unlabeled/negative label type) -- a standard, well-documented step of
  Two-Step PU (Elkan & Noto 2008) and PU-Bagging (Mordelet & Vert 2014) THEMSELVES, not a project-level
  reclassification of C1's status. `PU_SKLEARN_LABEL_ENCODING_NOTE` states this explicitly in every
  run's resolved config/summary.
- **Dependencies installed and verified working, not merely declared:** `scikit-learn` was already
  installed (1.9.0, confirmed via Task 4.1's dependency audit) but undeclared; now declared in
  `requirements.txt`. `pulearn` (0.2.0) was NOT installed -- installed via
  `.venv/Scripts/pip.exe install pulearn`, then verified end-to-end against a tiny synthetic P-vs-U
  example (`ElkanotoPuClassifier`, `WeightedElkanotoPuClassifier`, `BaggingPuClassifier`) BEFORE being
  used on real data, per the task brief's own gate. `pulearn` worked cleanly against the installed
  scikit-learn 1.9.0 (its own declared constraint is `scikit-learn<2,>=1.4.2`) -- no fallback
  hand-rolled implementation was needed. One API surprise caught during this verification:
  `BaggingPuClassifier`'s constructor parameter is `estimator=`, not the `base_estimator=` name used in
  pulearn's own prose documentation (a residual naming drift from upstream scikit-learn's own
  `base_estimator`-to-`estimator` rename in sklearn >=1.2) -- confirmed via `inspect.signature`, not
  assumed from the docstring.
- **Base-estimator decision (the real methodological choice this task required), recorded in full in
  `two_step_pu_baseline.BASE_ESTIMATOR_DECISION_NOTE` and reproduced in every run's summary:** no
  pre-specified base classifier/architecture for either algorithm was found in
  `PU_AOP_RESEARCH_CONTEXT.md`, the Planner doc, or the proposal (inspected directly before writing any
  code, not assumed). Chose `sklearn.linear_model.LogisticRegression(max_iter=2000,
  random_state=<train_seed>)` -- sklearn's own default L2/`C=1.0` -- for BOTH new baselines, over
  `RandomForestClassifier`, because it is the more common choice in the original Two-Step PU and
  PU-Bagging literature, is simpler to reason about and exactly reproduce, and keeps both new baselines
  on the SAME base-estimator family for a cleaner later comparison between them (Task 4.5). Wrapping the
  existing torch `BinaryMlp` as a scikit-learn estimator merely to force architectural uniformity with
  PN/nnPU was explicitly considered and REJECTED as a disproportionate engineering detour for a
  baseline-implementation task -- consistent with the task brief's own explicit instruction not to do
  this; no conflicting mandate for a BinaryMlp-wrapped estimator was found anywhere in the docs, so this
  is not flagged as an open conflict.
- **Shared PU dataset assembly (`pu_sklearn_common.py::build_sklearn_pu_dataset`), reused by BOTH new
  baselines, not duplicated:** E1+E2 labeled positives (same policy as nnPU, Task 4.3) vs. C1 partitioned
  via `pn_baseline.split_c1_train_validation` UNCHANGED (same `config.validation_fraction`=0.15/
  `config.eval_seed`=42 every prior Bucket-4 baseline uses). Verified against the real fold-0 cache: 331
  E1 + 273 E2 = 604 training positives, 48 E1 + 58 E2 = 106 validation positives, 3,220 C1 train / 568 C1
  validation -- matching Task 4.2/4.3's own documented totals exactly (re-derived directly, not
  trusted). `assert_no_cross_subset_overlap` independently re-verified across all 8 relevant subsets
  (same discipline as PN/nnPU); GraphPart's held-out fold (124 positives) confirmed disjoint from every
  trained subset by a dedicated acceptance test, exactly as for PN/nnPU.
- **A real, documented torch-import leak found and fixed before this module was called "torch-free":**
  `nnpu_baseline.py` imports `nnpu_risk.py` at module level, which imports `torch` (for the risk math
  itself) -- so a first draft of `pu_sklearn_common.py` that imported
  `nnpu_baseline.select_e1_e2_positive_evidence` directly transitively pulled `torch` into this module's
  import graph, contradicting this task's own "entirely scikit-learn/pulearn-based, no torch" framing.
  Fixed by duplicating the small (10-line) E1/E2 selection-masking function directly in
  `pu_sklearn_common.py` instead of importing it -- a deliberate, documented exception to this project's
  usual "reuse, don't duplicate" discipline, verified NOT to silently diverge via a dedicated equivalence
  test (`test_select_e1_e2_positive_evidence_matches_nnpu_baseline_implementation`) asserting identical
  output against `nnpu_baseline`'s own function on the same input. `nnpu_baseline.py`/`nnpu_risk.py`
  themselves were NOT modified (both are accepted, frozen Task 4.3 code).
- **Two-Step PU (Elkan & Noto 2008-style, `two_step_pu_baseline.py`, via `pulearn.ElkanotoPuClassifier`):**
  a single, non-iterative `.fit()` call -- hold out 10% of the combined P+C1 training array (pulearn's
  own published default, not retuned), fit the base classifier on the remainder, estimate the correction
  constant `c = P(s=1|y=1)` from the held-out positives. **Real fold-0 result:** `c ≈ 0.7085`. Validation
  diagnostics (descriptive only, NOT MCC/AUPRC -- Task 4.5's scope): base-estimator (bounded `[0,1]`)
  probability mean 0.728/median 0.920 for validation positives vs. mean 0.044/median 2.5e-6 for
  validation C1 -- positives score visibly higher, a basic sanity signal, not a biological-validity
  claim. **A real, load-bearing numerical property, reported not hidden:** the `1/c`-corrected estimate
  (the quantity Elkan & Noto's own paper defines) exceeded 1.0 for 12.0% of validation rows overall
  (`fraction_exceeding_one_overall`) -- expected and documented directly in pulearn's own
  `predict_proba` docstring (citing the original paper), not a bug. Both the raw unclipped and a
  clipped-to-`[0,1]` version are recorded in every summary, labeled as such.
- **PU-Bagging (Mordelet & Vert 2014-style, `pu_bagging_baseline.py`, via `pulearn.BaggingPuClassifier`):**
  `n_estimators=100` (a documented, literature-typical default -- NOT a tuned/selected value; no
  hyperparameter sweep was run, per this task's explicit scope boundary), `max_samples=1.0`. **Confirmed
  directly from pulearn's own source** (`bagging.py`: `unlabeled_count = count_nonzero(y == 0)`;
  `max_samples` is scaled against that count), not assumed from its prose docstring: this bootstraps
  ONLY the C1-unlabeled rows (to the full unlabeled-row count by default) while keeping EVERY labeled
  positive fixed in EVERY bootstrap member -- exactly Mordelet & Vert's prescribed procedure, not
  `pulearn`'s own simplification of it. **Real, documented consequence, verified on real fold-0 data:**
  because positives are never excluded from any bootstrap, all 604 training-positive rows have EXACTLY
  ZERO valid out-of-bag observations (`oob_decision_function_` is NaN for every one of them) -- this is
  a structural property of the algorithm, not a bug, and is asserted directly in this task's acceptance
  test (`test_all_training_positives_are_never_out_of_bag_on_real_data`). **Real fold-0 result:**
  `oob_score_ ≈ 0.795` (informative only about the 3,220 C1-unlabeled training rows, per the property
  above). Validation predict_proba (ordinary bounded-probability ensemble averaging -- NO `1/c`-style
  correction exists in this algorithm, confirmed bounded `[0,1]` directly, unlike Two-Step PU): mean
  0.766/median 0.909 for validation positives vs. mean 0.050/median 1.5e-5 for validation C1.
- **No learning-curve SVG for either new baseline, documented rather than silently omitted:** both
  algorithms' `.fit()` is a single, non-iterative procedure (Two-Step PU: one hold-out split, one
  classifier fit, one scalar `c`; PU-Bagging: one call that internally trains `n_estimators` bootstrap
  members) -- there is no per-epoch optimization trajectory to plot, unlike PN/nnPU's mini-batch
  training loops. Each training result records a `no_learning_curve_reason` string explaining this
  instead of a `learning_curve_path`. PU-Bagging's own internal validation signal (`oob_score_`) is
  reported in place of a held-out loss curve.
- **Checkpointing via `joblib`, not `torch.save`/`run_recorder.save_checkpoint`:** neither estimator is a
  `torch.nn.Module`, so `pu_sklearn_common.py::save_sklearn_checkpoint`/`load_sklearn_checkpoint`
  mirror `run_recorder`'s atomicity (temp file + `os.replace()`) and `checkpoint_best`/`checkpoint_last`
  filename convention (`.joblib`, not `.pt`) rather than reusing `run_recorder.save_checkpoint` directly
  (which is hardcoded to `torch.save`/`BinaryMlp`). Both baselines write IDENTICAL `checkpoint_best.joblib`/
  `checkpoint_last.joblib` content (there is only one fit to checkpoint) -- verified by comparing the
  reloaded estimators' own parameters/predictions directly, NOT by comparing raw file SHA-256 (each
  payload embeds its own live `saved_at` timestamp, so the two files' hashes can legitimately differ even
  though the underlying estimator is identical -- the exact same caveat already documented for PN/nnPU's
  own torch checkpoints). `append_epoch_metrics`/`RunContext`/`create_run_dir`/`write_resolved_config`
  (all torch-dependent at import time via `run_recorder.py`) ARE reused directly, lazily imported inside
  each training function exactly like PN/nnPU already do.
- **Checkpoints are NOT committed** (gitignored under `data/interim/c2_pu/fr4_two_step_pu_baseline_runs/`
  and `data/interim/c2_pu/fr4_pu_bagging_baseline_runs/`, same pattern as every other Bucket-4 baseline)
  -- the committed summaries record each checkpoint's SHA-256 instead.
- **Reproducibility:** two independent same-seed reruns of each baseline on the real fold-0 dataset
  produce identical scalar results (`estimated_c` / `oob_score_`) and identical validation-metric
  dictionaries, and reloaded checkpoints from both runs produce identical predictions on a held-out
  sample -- verified directly (not assumed), both in unit tests (synthetic data) and acceptance tests
  (real fold-0 data).
- **Tests:** 18 unit tests (`test_pu_sklearn_common.py` -- dataset assembly, E1/E2 selection equivalence
  with `nnpu_baseline`'s own function, leakage-injection catches, label encoding, score-distribution
  summary, sklearn-checkpoint round-trip, and a dedicated subprocess test confirming the module's import
  graph is torch-free) + 9 unit tests each for `test_two_step_pu_baseline.py` and
  `test_pu_bagging_baseline.py` (finite/bounded predictions, non-finite-feature rejection, checkpoint
  round-trip, same-seed bit-identical reruns, the documented "positives never OOB" property for
  PU-Bagging, the documented out-of-range corrected-probability property for Two-Step PU) + 14 full-file
  acceptance tests each (`test_fr4_two_step_pu_baseline_acceptance.py` /
  `test_fr4_pu_bagging_baseline_acceptance.py` -- real fold-0 counts matching Task 4.2/4.3 exactly,
  GraphPart held-out isolation re-verified independently, checkpoint reload verification, bit-identical
  reruns, every prior task's real artifacts (including PN's, nnPU's, and each other's own committed
  summaries) confirmed byte-unchanged by SHA-256 before/after, and a clear `FileNotFoundError` for a
  missing prerequisite) -- 66 new tests total. Full project suite re-run after this change -- see
  decision log for the exact before/after counts.
- **Research limitations, stated in full, not just referenced:** (A) C1 is an assumed-negative/
  PU-unlabeled pool, NEVER experimentally confirmed antioxidant-inactive; both algorithms' first internal
  stage trains a classifier treating C1 AS IF negative, a standard documented step of the algorithms
  themselves, not a project-level reclassification. (B) E1+E2 positives are pooled, identical policy to
  nnPU; E2 is not uniformly assay-confirmed. (C) Both baselines wrap `LogisticRegression`, NOT
  `models.BinaryMlp` -- a deliberate, documented architecture departure from PN/nnPU; any numerical
  comparison between these baselines and PN/nnPU must account for this, not just the label-assumption
  difference. (D) No MCC/AUPRC computation or cross-baseline comparison table is performed here -- that
  is Task 4.5's explicit scope. (E) FR2/Task 2.5's documented FR1-positive-vs-C1 distributional
  differences apply here unchanged; neither algorithm automatically eliminates shortcut-bias risk. (F)
  Fold-0-only initial baseline, not a five-fold validated conclusion. (G) Technical acceptance does not
  imply supervisor or scientific sign-off on the chosen base estimator, hyperparameters, or any
  scientific conclusion.
- **No curriculum (C1→C2→C3), no RNIS, no hard-negative mining, no hyperparameter sweep, and no
  multi-baseline comparison table were implemented here** -- all explicitly out of Task 4.4's scope
  (Tasks 4.5/4.6, FR6).

### Bucket 4, Task 4.5 — Initial Model Evaluation and Testing

**Status: COMPLETE — PASS (2026-10-15).**

- Added `baseline_evaluation.py` and CLI stage `fr4-baseline-evaluation`. The stage performs inference
  only: it loads the five accepted fold-0 best checkpoints, checks each SHA-256 against its saved
  summary, reuses the accepted fold-scaled 495-dimensional cache, and never refits a model or scaler.
- Common evaluation membership was verified as 124 GraphPart-held-out positives, C1=3,788, C2=2,000,
  fold-0 C3=2,000, and 38 external assay-inactive controls. The shared leakage report found no overlap.
  The two external-control BIOPEP-UWM conflicts remain flagged and a 36-control sensitivity view is
  recorded without changing the frozen control set.
- **Primary assay-supported results (held-out positives vs 38 controls; threshold 0.5):** PN
  MCC/AP/AUROC = `-0.1833/0.6392/0.2541`; direct-clamped nnPU =
  `-0.0436/0.6915/0.3235`; corrective nnPU = `-0.2498/0.6827/0.3224`; Two-Step PU =
  `-0.1694/0.6466/0.2818`; PU-Bagging = `-0.2495/0.6567/0.3005`. All MCC values are negative and all
  AUROCs are below 0.5; no model demonstrated reliable separation of this small, source-mismatched
  assay-supported set. This negative finding is retained rather than optimized away.
- Positive-recovery fractions at 0.5 were PN 87.10%, direct nnPU 99.19%, corrective nnPU 55.65%,
  Two-Step PU 79.84%, and PU-Bagging 73.39%. Direct nnPU remains highly saturated (95.16% of held-out
  positives above 0.99) and also scores 80.60% of C2 and 94.70% of C3 above 0.5. Corrective nnPU gives
  materially less saturated challenge scores, but its assay-supported metrics do not establish an
  improvement.
- C1/C2/C3 are still unlabeled. Their score distributions are descriptive; any MCC/AP/AUROC values in
  `fr4_baseline_proxy_challenge_summary.csv` are explicitly prefixed/named as assumed-negative proxies
  and are not biological specificity estimates.
- Two-Step PU's raw Elkan–Noto corrected values are preserved for AP/AUROC. An explicit clipped copy is
  used for fixed-threshold and Brier calculations; 6.35% of raw scores across evaluated pools exceeded
  1. No calibration model was fitted.
- Outputs: `fr4_baseline_evaluation_fold0.json`, `fr4_baseline_comparison_fold0.csv`,
  `fr4_baseline_proxy_challenge_summary.csv`, `fr4_baseline_model_provenance.json`, three lightweight
  SVGs, and `FR4_BASELINE_EVALUATION_REPORT.md`.
- Frozen integrity hashes captured during evaluation: PP1 manifest
  `88f14bb9ba99209a5482a08c2f82baa86434a4af1808f2e373e109efd74c27f2`, PP2 manifest
  `dbd8755a69b6f29655c03f5dfa6af5d22b72de32c0708b98c944e6541744e2b4`, and FR3 cache manifest
  `81c87075eec8643a3643a3b726268e35569a1a1f00b15f457d87e1ef3268d97a`. Previously accepted summaries
  and checkpoints were read-only and retained their recorded hashes.
- Limitations: fold 0 only; 38 assay-specific controls; two disputed annotations; C1/C2/C3 unlabeled;
  provisional nnPU prior; E1-only PN versus E1+E2 PU training; MLP versus LogisticRegression; persistent
  direct-nnPU clamping; distinct corrective optimization; known source-distribution and shortcut bias;
  uncalibrated scores. Technical PASS does not imply validated antioxidant prediction.
- Validation: `pytest tests/c2_pu/test_baseline_evaluation.py -q` → **5 passed**. The single full-suite
  invocation collected 652 tests and initially reported **644 passed, 2 skipped, 6 failed**: four
  WSL-backed upstream acceptance checks were denied by the sandbox and two fresh-subprocess checks used
  the temporary standalone interpreter without its dependency path. The two subprocess checks then
  passed (`2 passed`), and the same four WSL checks passed with approved WSL access (`4 passed in
  799.60s`). Effective verified result: **650 passed, 2 skipped, 0 unresolved failures**. No failure
  involved Task 4.5 code; all tracked historical outputs regenerated by acceptance tests were restored.

### Task 4.5 follow-up — External-control diagnostic

**Status: COMPLETE — NO BLOCKING IMPLEMENTATION DEFECT IDENTIFIED (2026-10-15).**

- Added `external_control_diagnostic.py` and CLI stage `fr4-external-control-diagnostic`. The diagnostic
  reused the accepted Task 4.5 predictions and caches read-only; it did not retrain, reverse scores,
  tune a threshold, relabel samples, or alter any accepted artifact.
- Verified that every model's score convention is positive-class oriented, held-out positives are
  label 1, assay-inactive controls are label 0, and peptide ID/sequence/cache-row correspondence is
  exact. The sklearn loaders now also reject a class order other than `[0, 1]` before selecting column
  1, making that convention explicit without changing any accepted prediction.
- The unexpected ranking is broad rather than driven by a few outliers: 32/38 controls scored above
  0.5 under all five models and 36/38 did so under at least four. Removing any one control changed
  AUROC by at most 0.0175. The already-recorded 36-control sensitivity excluding the two BIOPEP-UWM
  conflicts retained the same conclusion.
- Descriptor differences support source/assay mismatch as a material limitation: controls are shorter
  on average (4.79 residues versus 6.24 E1 and 8.29 E2), with different molecular-weight, charge,
  aromaticity, hydrophobic-moment, and proline-fraction distributions. These associations do not
  establish a biological cause for the scores.
- Outputs: `fr4_external_control_diagnostic.json`, `fr4_external_control_scores.csv`, and
  `FR4_EXTERNAL_CONTROL_DIAGNOSTIC.md`. The result supports proceeding to the pre-specified curriculum
  prototype while retaining Task 4.5's negative assay-supported finding unchanged.

### Bucket 4, Task 4.6 — Initial C1 → C2 → C3 curriculum prototype

**Status: COMPLETE — PASS (2026-10-15).**

- Added `curriculum_training.py` and CLI stage `fr4-curriculum`. The learner is the existing corrective
  beta/gamma nnPU MLP (`pi=0.10`, `beta=0`, `gamma=1`), selected because it preserves unlabeled-risk
  gradients below the correction threshold and supports checkpoint warm starts. This is an engineering
  choice, not evidence that corrective nnPU is biologically superior.
- The genuine fold-0 run used the accepted 495-dimensional cache, 604 training positives (331 E1 +
  273 E2), normalized positive-risk weights E1=1.0/E2=0.5, and stage pools C1 train=3,220, C2=2,000,
  fold-0 C3=2,000. C3 membership was loaded and independently checked through
  `curation.c3.load_fold_challenges`. The same 106 positive + 568 C1 validation rows were fixed across
  stages. Held-out positives and external controls were excluded from training and model selection.
- Model weights were passed from each selected stage checkpoint to the next stage; Adam state was reset
  at each stage. A validation-risk plateau of five stale epochs triggered each transition. Stage C1
  executed 9 epochs (best 3, risk 0.0614415), C2 14 (best 8, risk 0.0766366), and C3 6 (best 0,
  risk 0.0676589). Mean corrective-update fractions were 0.5270, 0.4422, and 0.5185.
- Held-out-positive recovery at threshold 0.5 changed from the accepted non-curriculum corrective
  reference's 0.5565 to 0.5968 after C1, 0.3871 after C2, and 0.6774 after C3. Fractions above 0.5 for
  `(C1,C2,C3)` were `(0.0222,0.1305,0.0050)`, `(0.0235,0.0330,0.0060)`, and
  `(0.0465,0.1220,0.0060)` after the three stages. The trajectory is non-monotonic and does not show
  a general reduction in scores across all unlabeled pools.
- Read-only post-selection external-control results were C1 stage MCC/AP/AUROC
  `-0.2929/0.6282/0.2334`, C2 `-0.1641/0.6600/0.3171`, and C3
  `-0.2338/0.6252/0.2381`. These values were never used for checkpoint selection or tuning; no stage
  resolves Task 4.5's weak assay-supported discrimination.
- Each stage has separately hash-recorded best/last checkpoints and a parent-checkpoint link. The first
  scratch execution encountered a transient Windows `os.replace` lock during Stage C2 and was marked
  failed. A bounded retry was added around the existing atomic save, with no scientific setting changed;
  the subsequent genuine run completed normally.
- Outputs: `fr4_curriculum_fold0_summary.json`, `fr4_curriculum_stage_comparison.csv`,
  `fr4_curriculum_score_trajectories.svg`, gitignored stage run/checkpoints, and
  `FR4_CURRICULUM_PROTOTYPE_REPORT.md`.
- Validation: focused curriculum/evaluation/corrective tests initially passed (**13 passed**). The
  broader relevant regression command covering curriculum, evaluation, corrective/direct nnPU,
  experiment data, models, recorder, feature cache, C3, and CLI help passed **154 tests, 0 failed** with one
  non-functional pytest-cache permission warning. Task 4.5's prior full-suite evidence remains
  **650 passed, 2 skipped, 0 unresolved failures**; expensive upstream curation/embedding acceptance
  jobs were not rerun for this focused prototype.
- Scientific limits remain: C1/C2/C3 are unlabeled, E2 is provisional, `pi=0.10` is assumed, stage
  surrogate risks use a fixed C1 sampling model, pools differ by source, and this is one fold. Apparent
  pool-score changes are not validated biological reliability improvements.

### PP1 pre-freeze methodological audit (Task 4.6 follow-up)

**Status: COMPLETE — READY WITH LIMITATIONS (2026-10-15).** The dated audit is
`FR4_PP1_PRE_FREEZE_METHOD_AUDIT.md`; the three-row comparison and figure are
`fr4_pp1_matched_curriculum_fold0.csv` and `fr4_pp1_matched_curriculum_fold0.svg`.

- C3 `best_epoch=0` is zero-based and **post-update**: 63 C3 optimizer steps occurred before validation
  and saving. All six parameter tensors differ from the selected C2 parent (maximum absolute element
  change 0.0307472). The selected C3 model therefore contains one complete C3 training epoch; the five
  later epochs did not beat its fixed C1-based validation surrogate. This clarifies the Task 4.6 report
  without replacing any checkpoint or summary.
- Stage C1 already satisfies the matched weighted C1-only reference requirements: same 604 E1+E2
  training positives, E1/E2 weights 1.0/0.5, 3,220 C1 training rows, corrective nnPU objective and
  settings, frozen fold-0 features, fresh seed-42 initialization, and fixed 106-positive/568-C1
  validation rule. Its existing best checkpoint, SHA-256
  `f566c06314e1b243124abf49e660b3979f3d086e51b19ad9f2d1b0929494f7d4`, is labeled
  `weighted_c1_only_curriculum_reference` for comparison; no control was retrained. The accepted
  stand-alone corrective baseline used unweighted E1/E2 and patience 10 and remains historical context.
- Mathematical audit verified normalized E1/E2 weights in both positive risks, an independent C1/C2/C3
  unlabeled group mean, one prior factor per positive term, correct normal/corrective branch losses,
  and a separate nonnegative reported risk. Independent float64 reference and gradient tests passed.
- Parent hashes, actual state tensors, stage JSONL histories, checkpoint metadata, exact recalculated
  full-validation risks, fold-0 C3 membership, cached scaler identity, and no-overlap checks agree.
  External scores were obtained after each stage's best checkpoint had been selected, but before later
  stages finished; they were never used for training or selection. This corrects the chronological
  wording of the earlier decision-log entry below without changing its leakage conclusion.
- Matched positive recovery was 59.68% after weighted C1, 38.71% after C2, and 67.74% after C3.
  External-control MCC remained negative (`-0.2929`, `-0.1641`, `-0.2338`). The 38 controls are
  assay-specific and small; C1/C2/C3 remain unlabeled. No biological improvement is claimed.
- Focused relevant regression: **160 passed, 0 failed**. All 10 PP1 and 28 PP2 frozen-file checksums
  passed; FR3 manifest/scaler, accepted Task 4.5/4.6 summaries, and all six stage checkpoint hashes
  remained unchanged. No real fold-0 model was retrained.

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
   not been started.
6e. **RESOLVED 2026-10-14. Bucket 4, Task 4.1 (shared experiment infrastructure) is complete** — see
   Completed tasks above (`experiment_config.py`, `models.py`, `experiment_data.py`,
   `common/seeding.py`, `run_recorder.py`, CLI stage `fr4-infra-smoke-test`). Kept here for history;
   not an open item anymore.
6f. **RESOLVED 2026-10-14. Bucket 4, Task 4.2 (PN baseline implementation) is complete (PASS)** — see
   Completed tasks above (`pn_baseline.py`, CLI stage `fr4-pn-baseline`). Kept here for history; not an
   open item anymore.
6g. **RESOLVED 2026-10-15. Bucket 4, Task 4.3 (plain nnPU baseline implementation) is complete (PASS)**
   — see Completed tasks above (`nnpu_risk.py`, `nnpu_baseline.py`, CLI stage `fr4-nnpu-baseline`). Kept
   here for history; not an open item anymore.
6h. **RESOLVED 2026-10-15. Bucket 4, Task 4.4 (Two-Step PU, PU-Bagging baselines) is complete (PASS)** —
   see Completed tasks above (`pu_sklearn_common.py`, `two_step_pu_baseline.py`, `pu_bagging_baseline.py`,
   CLI stages `fr4-two-step-pu-baseline`/`fr4-pu-bagging-baseline`). Kept here for history; not an open
   item anymore.
6i. **RESOLVED 2026-10-15. Bucket 4, Task 4.5 (initial five-configuration evaluation) is complete
   (PASS)** — see `FR4_BASELINE_EVALUATION_REPORT.md`. The common held-out-positive/external-control
   comparison and explicitly labeled C1/C2/C3 proxy summaries are complete.
6j. **RESOLVED 2026-10-15. Bucket 4, Task 4.6 (initial C1→C2→C3 curriculum prototype) is complete
   (PASS)** — see `FR4_CURRICULUM_PROTOTYPE_REPORT.md`. The fold-0 corrective-nnPU curriculum,
   stage checkpoints, fixed-boundary diagnostics, and one read-only post-training evaluation are
   complete. RNIS, full five-fold curriculum evaluation, calibration, and hyperparameter search remain
   later research milestones and were not started here.
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
| 2026-10-14 | `torch` added to `requirements.txt`; Bucket 4 model code imports it directly on Windows (CPU-only, no CUDA device in this environment) rather than going through the WSL subprocess pattern used for ESM-2 | Model training is pure PyTorch tensor math with no dependency on the WSL-only fair-esm/CD-HIT/GraphPart toolchain; routing it through a WSL subprocess the way Bucket 3.2 does for ESM-2 would add indirection for no reason. `torch` was already installed in the Windows `.venv` (confirmed during Task 3.1's dependency audit) but never declared — now declared since Bucket-4 modules import it at module level. |
| 2026-10-14 | `run.py`'s module-level import graph stays torch-free: the new `fr4-infra-smoke-test` stage lazily imports every torch-dependent Bucket-4 module (and `torch` itself) INSIDE the stage function, not at the top of `run.py` | Every pre-existing FR1/FR2/FR3 CLI stage must keep working exactly as before even if, hypothetically, torch were ever unavailable in a given environment — mirrors the exact reasoning already applied to keeping `common/embeddings.py` out of `run.py`'s top-level imports (Bucket 3.2). Verified directly: `'torch' not in sys.modules` immediately after `import plantaox.c2_pu.run`. |
| 2026-10-14 | Bucket 4.1's experiment-config validation is a hand-rolled `dataclass.__post_init__`, not pydantic (not an existing project dependency) | Consistent with this project's established preference for transparent, dependency-free validation over adding a schema library for range/membership checks this simple (same reasoning already applied to Task 3.3's hand-rolled z-score scaler over scikit-learn's `StandardScaler`). |
| 2026-10-14 | `esm`/`descriptors` feature representations in `experiment_data.py` are column slices of the SAME jointly-scaled 495-dim fused matrix, not an independently-refit standardization over just those 480 or 15 columns | The fold's scaler (Task 3.3) was fit once, jointly, across all 495 dimensions, on that fold's training positives. Refitting a second, narrower scaler specifically for `esm`-only or `descriptors`-only experiments would be a genuinely different (and currently unrequested) preprocessing design, and would silently diverge from the single frozen `fusion_v1` scaling contract every other part of this project assumes. Documented here as a simplification, not silently decided: if `esm`/`descriptors`-only baselines are later found to need independently-refit scaling, that is a new, explicit decision for whoever implements Task 4.2+, not something this task should have pre-empted. |
| 2026-10-14 | Bucket 4.1's validation-set carve-out uses a dedicated, local `random.Random(eval_seed)` instance (not the global Python/NumPy/PyTorch seed state `common.seeding.set_global_seed` configures) | Keeps the validation split's determinism independent of, and non-interfering with, whatever global seeding a training script does for model initialization/data shuffling/dropout elsewhere — the split should be reproducible from `eval_seed` alone, not incidentally depend on how many other random calls happened to run before it in a given training script. |
| 2026-10-14 | Task 4.2's C1 train/validation partition reuses `config.validation_fraction` (0.15) and `config.eval_seed` (42) — the SAME authoritative values Task 4.1 already uses for the positive-pool split — rather than introducing a second, C1-specific config field | The task brief explicitly asked to check for and reuse an existing authoritative validation fraction before adding a new one; `ExperimentConfig` already defines exactly one, and there is no stated reason for C1's split to use a different fraction or seed. Reusing it also means the two private helpers Task 4.1 wrote (the shuffle-split and the cross-subset overlap check) could be exposed and reused verbatim instead of duplicated — see the next two entries. |
| 2026-10-14 | `experiment_data.py`'s private `_split_training_validation`/`_assert_no_cross_subset_overlap` were renamed to public `split_ids_train_validation`/`assert_no_cross_subset_overlap` (pure rename, zero logic change) so Task 4.2 could reuse them directly for the C1 partition and its own leakage re-check | Avoids a second shuffle-split algorithm and a second overlap-detection routine for what is exactly the same operation applied to a different ID list. Verified the rename changed nothing: `experiment_data.py`'s own 18 existing tests pass unmodified after the rename. |
| 2026-10-14 | A real bug found while writing `test_build_pn_dataset_raises_on_zero_c1_rows`: `build_pn_dataset()` called `split_c1_train_validation()` before checking whether C1 was non-empty, so a zero-C1 scenario surfaced a generic `ValueError` from inside the shared split helper instead of this module's own `InsufficientDataError` | Caught by the test, not assumed correct from a first green run elsewhere. Fixed by moving the explicit zero-C1 check before the split call, giving a specific, correctly-typed error naming the fold_id and the actual problem ("zero C1 rows -- nothing to partition") rather than a generic validation_fraction arithmetic complaint from a lower-level helper. |
| 2026-10-14 | PN's learning curve is a ~40-line hand-rolled SVG line chart, not matplotlib | matplotlib is confirmed not installed and not declared as a project dependency; this project already deliberately avoided adding it once before for a single exploratory chart (Task 2.5's decision log, 2026-10-14: "matplotlib was not installed for this... one summary chart was rendered directly... instead of adding a new project dependency"). The same reasoning applies here: one simple train-vs-validation loss plot does not justify a new, fairly heavy dependency. |
| 2026-10-14 | PN checkpoints are stored as `.pt` files under `data/interim/c2_pu/fr4_pn_baseline_runs/` (gitignored) rather than committed, with only their SHA-256 recorded in the committed summary | Consistent with this project's established "don't commit large binary arrays" policy (embedding caches, feature caches, scaled-feature caches are all handled the same way) — the run is exactly regeneratable via `fr4-pn-baseline` from already-committed small inputs, and the SHA-256 makes any future regeneration's checkpoint verifiably identical or flags a real divergence. |
| 2026-10-14 | Two independent same-seed CPU training runs on the real fold-0 PN dataset were verified to produce a bit-identical per-epoch loss history (not just approximately close) | Task 4.1 had only verified forward-pass determinism (a single, non-iterative operation); training involves many sequential backward passes and optimizer steps, where floating-point non-associativity could in principle compound across iterations even under `torch.use_deterministic_algorithms(True)`. Verified directly rather than assumed: confirmed exact equality of the full `history` list (every epoch's train/validation loss) across two separately-constructed run directories. |
| 2026-10-15 | Task 4.3's nnPU implements ONLY the direct-clamped objective (`R_nnPU = pi*R_p^+ + max(0, R_n)`, backpropagated through directly), not the original Kiryo et al. (2017) paper's beta/gamma corrective training procedure (gradient ascent on the negative-risk estimate below a `-beta` threshold) | Inspected `PU_AOP_RESEARCH_CONTEXT.md`, `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md` (Sections 4.3/4.6), the proposal's FR3/FR4 requirement table, and every prior decision-log entry directly before writing any code — none specifies the corrective procedure or a beta/gamma value. Per the task brief's own explicit fallback instruction ("if neither is specified, use the direct clamped objective as the explicitly named initial baseline"), implemented and recorded this choice as `nnpu_variant: "direct_clamped"` in every run's resolved config/manifest/summary rather than silently conflating the two algorithms. The beta/gamma variant is unimplemented scope, not a gap discovered later. |
| 2026-10-15 | Task 4.3's positive-class prior is `pi=0.10` (`DEFAULT_PRIOR` in `nnpu_baseline.py`), a clearly-labeled PROVISIONAL modeling/sensitivity-analysis anchor, not a literature-established or measured biological prevalence | No pre-specified prior or estimation method was found anywhere in this project's documentation (same inspection as the row above). Per Section 8.2's explicit fallback instruction, `pi=0.10` was adopted with `PRIOR_SENSITIVITY_GRID = (0.05, 0.10, 0.20)` defined for future sensitivity analysis (full sensitivity training deferred, Section 8.3). The naive sampling ratio `n_labeled_positive/(n_labeled_positive+n_C1)` was deliberately NOT used as pi, per Section 8.1's explicit prohibition — C1 is a structurally different source distribution than the positive pool (Task 2.5's own KS-test findings), so that ratio is not a valid prevalence substitute either. |
| 2026-10-15 | Task 4.3 pools E1+E2 as the labeled-positive population (unlike PN's E1-only), per the task brief's explicit "agreed E1/E2 labeled-positive population" instruction, while keeping each row's evidence tier separately recorded (`e1_train_count`/`e2_train_count`/etc., never pooled into an anonymous count) | This is a genuine, documented difference from PN's own positive-evidence policy (Task 4.2), not an inconsistency — the task brief requires it explicitly so later PN-vs-nnPU comparisons do not conflate the loss-function change with a simultaneous positive-data change without that difference being visible in both runs' own recorded counts. |
| 2026-10-15 | `pn_baseline.render_loss_curve_svg` was generalized with optional `train_key`/`val_key`/`title` parameters (defaulting to the original hardcoded PN values) instead of writing a second, nearly-identical SVG line-chart function in `nnpu_baseline.py` | Reuses the existing hand-rolled SVG writer (no matplotlib dependency added) for nnPU's own `train_nnpu_risk`/`val_nnpu_risk` history keys. Verified zero behavior change for existing PN callers: all 27 pre-existing `test_pn_baseline.py` tests pass unmodified after the change, since the new parameters' defaults reproduce the exact original hardcoded strings. |
| 2026-10-15 | A genuine, reported (not hidden) stability finding from the real fold-0 nnPU run: the negative-risk term `R_u^- - pi*R_p^-` was clamped to zero in ≈98–100% of optimizer updates in every epoch of the run, not just late epochs, at `pi=0.10` | Section 10.4 requires monitoring and documenting (never silently hiding) persistent zero-clamped negative risk. For most updates under this configuration, the direct-clamped objective's gradient reduces to the positive-risk term alone (the unlabeled-group gradient is exactly zero when clamped — verified unit-test property, `test_gradient_is_zero_for_unlabeled_group_when_clamped`). Reported as-is in `stability_diagnostics` and this file rather than re-running with a different prior to produce a more favorable-looking clamping profile (explicitly prohibited by the task brief's §18 closing instruction). Flagged for supervisor/scientific review before any claim that this configuration is "working as intended" in the PU-learning sense. |

| 2026-10-15 | Task 4.3 post-acceptance diagnostic: investigated the accepted π=0.10 run's ≈98-100% negative-risk-clamping finding via a controlled π ∈ {0.05, 0.10, 0.20} sensitivity experiment (fold 0, all else held constant), WITHOUT modifying `nnpu_risk.py`/`nnpu_baseline.py` and WITHOUT implementing the beta/gamma corrective variant | Explicit post-acceptance-diagnostic brief: investigate, don't rebuild. Real finding: clamping is persistently near-universal across the whole declared grid (mean per-update clamped fraction 0.9825/0.9863/0.9915 for π=0.05/0.10/0.20) — classified "Persistently clamped," not resolved by retuning π. A genuinely prior-sensitive secondary finding (C1 median predicted score rises with π: 0.0063→0.0378→0.2977) is reported separately so it is not conflated with the clamping mechanism itself. See `FR4_NNPU_PRIOR_SENSITIVITY_DIAGNOSTIC.md` for the full report. |
| 2026-10-15 | The accepted π=0.10 run's best checkpoint (gitignored but present on disk in this checkout, under `data/interim/c2_pu/fr4_nnpu_baseline_runs/fr4_nnpu_baseline_fold0__20261014T183214Z/`) was verified by SHA-256 against what the committed summary itself recorded, then loaded READ-ONLY to compute prediction-distribution diagnostics Task 4.3's own run never recorded — never retrained, never resaved | Per the diagnostic brief's explicit instruction: reuse the accepted reference wherever its records are sufficient, and verify rather than assume a gitignored artifact is still the one the committed summary describes. Confirmed matching both before this diagnostic's work began and after every new π=0.05/0.20 training run. |
| 2026-10-15 | New diagnostic instrumentation (`nnpu_prior_diagnostics.py`'s `train_nnpu_with_diagnostics`) lives in a SEPARATE module from the accepted `nnpu_baseline.train_nnpu_baseline`, duplicating the training loop's structure rather than modifying the accepted function in place, with a regression test proving the two produce identical epoch-level aggregates at the same prior/seed | The accepted Task 4.3 training loop must remain byte-for-byte as accepted (AGENTS.md rule #4's spirit extended to accepted code, not just frozen data artifacts) — adding instrumentation via a parallel function, verified equivalent by test, avoids any risk of silently altering the accepted baseline's own reproducibility guarantee while still getting genuine per-update diagnostics. |
| 2026-10-15 | Implemented the separately named `corrective_beta_gamma` nnPU follow-up at π=0.10, β=0, γ=1; retain the accepted `direct_clamped` variant as the historical Task 4.3 baseline | The prior-sensitivity diagnostic found 98–99% direct-clamping across π=0.05/0.10/0.20. Kiryo et al.'s corrective procedure gives the unlabeled-risk term a gradient-ascent update below the threshold rather than zero gradient. One controlled fold-0 run was authorized before Task 4.5; no β/γ sweep was performed. |
| 2026-10-15 | Used batch size 32 and weight decay 0.0 for the corrective comparison, matching the accepted direct run's immutable `resolved_config.json`, despite the follow-up brief listing 64 and 0.0001 | A controlled optimization-rule comparison requires the accepted artifact's actual settings. Using the prose values would simultaneously change batch size and regularization, confounding the result. The mismatch is documented in the corrective run config, summary, and comparison report rather than silently ignored. |

| 2026-10-15 | Task 4.4's Two-Step PU and PU-Bagging baselines wrap `sklearn.linear_model.LogisticRegression` via `pulearn.ElkanotoPuClassifier`/`BaggingPuClassifier` respectively, NOT `models.BinaryMlp` | No pre-specified base classifier/architecture for either algorithm was found in `PU_AOP_RESEARCH_CONTEXT.md`, the Planner doc, or the proposal (inspected directly before writing any code). Per the task brief's own explicit instruction, wrapping the existing torch `BinaryMlp` as a scikit-learn estimator merely to force architectural uniformity with PN/nnPU was considered and rejected as a disproportionate engineering detour -- Two-Step PU/PU-Bagging are specific algorithms built around scikit-learn-compatible base estimators in both the originating literature and the only practical PU-learning library (`pulearn`). Logistic regression (over e.g. `RandomForestClassifier`) was chosen because it is the more common choice in the original Two-Step PU (Elkan & Noto 2008)/PU-Bagging (Mordelet & Vert 2014) papers, is simpler to reason about and exactly reproduce, and keeps both new baselines on the same base-estimator family for a cleaner Task 4.5 comparison between them. |
| 2026-10-15 | `pulearn==0.2.0` installed and used directly (no hand-rolled fallback implementation) | Verified end-to-end against a tiny synthetic P-vs-U example (`ElkanotoPuClassifier`, `WeightedElkanotoPuClassifier`, `BaggingPuClassifier`) BEFORE use on real data, per the task brief's own gate. Works cleanly against the already-installed scikit-learn 1.9.0 (pulearn's own declared constraint: `scikit-learn<2,>=1.4.2`). One API-naming surprise caught during verification, not assumed from pulearn's prose docs: `BaggingPuClassifier`'s constructor parameter is `estimator=`, not the `base_estimator=` name used in its own docstring (residual drift from upstream scikit-learn's `base_estimator`→`estimator` rename in sklearn >=1.2) -- confirmed via `inspect.signature` before writing any training code against it. |
| 2026-10-15 | `scikit-learn` and `pulearn` declared in `requirements.txt` only, not `pyproject.toml` | `pyproject.toml`'s `dependencies = []` is confirmed unused by this project's build (checked directly) -- `requirements.txt` is the established, already-used dependency declaration file (e.g. `torch` was added there, not `pyproject.toml`, at Task 4.1). Matching the existing convention rather than introducing a second one. |
| 2026-10-15 | `pu_sklearn_common.py` duplicates (does NOT import) a function logically identical to `nnpu_baseline.select_e1_e2_positive_evidence`, verified equivalent by a dedicated regression test | `nnpu_baseline.py` imports `nnpu_risk.py` at module level, which itself imports `torch` (needed for the risk-estimator math) -- importing `select_e1_e2_positive_evidence` from `nnpu_baseline` would therefore transitively pull `torch` into `pu_sklearn_common.py`'s import graph, contradicting Two-Step PU/PU-Bagging's own "entirely scikit-learn/pulearn-based, no torch" framing. The selection logic itself is ~10 lines of boolean masking with no torch dependency of its own; duplicating just that small function (not the whole module) and proving equivalence by test was judged the more honest choice than either silently accepting the torch leak or modifying the accepted, frozen `nnpu_baseline.py`. |
| 2026-10-15 | Two-Step PU's and PU-Bagging's fitted estimators are checkpointed via `joblib.dump`/`joblib.load` (`pu_sklearn_common.py::save_sklearn_checkpoint`/`load_sklearn_checkpoint`), a NEW, separate helper rather than reusing `run_recorder.save_checkpoint`/`load_checkpoint` | `run_recorder`'s existing checkpoint functions are hardcoded to `torch.save`/`BinaryMlp.state_dict()`/`BinaryMlp.load_compatible_state_dict()` -- neither new estimator is a `torch.nn.Module`, so calling them would fail outright. The new helper mirrors the SAME atomicity (temp file + `os.replace()`) and `checkpoint_best`/`checkpoint_last` filename convention (substituting `.joblib` for `.pt`) rather than inventing a different pattern; `run_recorder`'s other, estimator-agnostic helpers (`create_run_dir`, `write_resolved_config`, `append_epoch_metrics`, `RunContext`) ARE reused directly, unchanged. |
| 2026-10-15 | Two-Step PU and PU-Bagging each write exactly ONE checkpoint-worthy fit (both `checkpoint_best.joblib` and `checkpoint_last.joblib` hold the SAME single estimator, verified by comparing reloaded predictions/parameters, not by comparing raw file SHA-256) and record NO per-epoch learning-curve SVG | Both algorithms' `.fit()` is a single, non-iterative procedure (Two-Step PU: one hold-out split, one classifier fit, one scalar `c`; PU-Bagging: one call that internally trains `n_estimators` bootstrap members) -- there is no epoch-wise optimization trajectory analogous to PN/nnPU's mini-batch training loops, so forcing an artificial best-vs-last distinction or a fabricated epoch axis would misrepresent how these algorithms actually work. Each training result instead records a `no_learning_curve_reason` string; PU-Bagging's own internal out-of-bag score is reported as its native internal-validation signal. Raw checkpoint-file SHA-256 is NOT asserted equal between best/last in tests (each `joblib` payload embeds its own live `saved_at` timestamp, so the two files' hashes can legitimately differ even though the underlying fitted estimator is identical -- the same caveat already documented for PN/nnPU's own torch checkpoints, which likewise don't assert raw-file-hash equality across reruns). |
| 2026-10-15 | PU-Bagging uses `n_estimators=100` (documented literature-typical default) and `max_samples=1.0` (`pulearn`'s own default), neither tuned nor selected via any sweep | Explicit task-brief scope boundary: "hyperparameter tuning sweeps beyond reasonable, documented defaults" are out of scope for a baseline-implementation task (Task 4.5/future work, not 4.4). Confirmed directly from `pulearn`'s own source (`bagging.py`) that `max_samples=1.0` means bootstrapping the FULL C1-unlabeled row count (not the combined P+U row count) while keeping every labeled positive fixed in every bootstrap member -- i.e. this is Mordelet & Vert's actual prescribed procedure, not a looser adaptation, verified empirically on real fold-0 data: all 604 training positives have exactly zero valid out-of-bag observations as a direct, confirmed consequence. |
| 2026-10-15 | No MCC/AUPRC, score-vs-label classification metric, or cross-baseline comparison table is computed anywhere in Task 4.4 -- only descriptive score-distribution diagnostics (mean/median/min/max/fraction-near-0/fraction-near-1), explicitly labeled as such | Task 4.5 ("Initial Model Evaluation and Testing") is the explicitly scoped owner of MCC/AUPRC computation and the comparison table (Planner doc, Bucket 4.5). Computing it here would duplicate/pre-empt that task's own acceptance criteria and risk a second, possibly-inconsistent implementation of the same metric later. |
| 2026-10-15 | Task 4.5 reuses all five accepted best checkpoints read-only and fixes the primary evaluation at 124 fold-0 held-out positives versus 38 assay-inactive controls with threshold 0.5; no baseline is retrained or threshold-tuned | The task is an initial common inference comparison, and the held-out/control rows must remain evaluation-only. Reusing hash-verified checkpoints preserves the accepted Tasks 4.2–4.4 histories and avoids selecting models against the small control set. |
| 2026-10-15 | C1/C2/fold-0 C3 metrics are stored only as explicitly named assumed-negative proxies, while the primary conventional MCC/AP/AUROC table uses recorded positive/control labels | C1/C2/C3 are unlabeled by construction. Assigning them zero can support an engineering stress test, but cannot establish biological specificity; separating the tables prevents the assumption from being mistaken for ground truth. |
| 2026-10-15 | Two-Step PU uses raw finite Elkan–Noto corrected scores for AP/AUROC and an explicitly clipped `[0,1]` copy for threshold and Brier metrics | The accepted estimator can exceed 1 (6.35% across the evaluated pools in this run). Raw scores preserve ranking and avoid clipping-induced ties; bounded scores satisfy probability-domain metric requirements. Neither form is claimed calibrated. |
| 2026-10-15 | Task 4.5 is technically accepted despite uniformly weak assay-supported discrimination (all MCC < 0; all AUROC < 0.5) | Technical acceptance covers reproducible loading, leakage-safe common membership, valid score handling, and correct metrics. The observed external-control result is a scientifically important negative finding, not a reason to retune on 38 controls or conceal the result. It prevents claims of validated biological superiority and remains prominent in the report. |
| 2026-10-15 | The Task 4.5 external-control diagnostic preserves the original score orientation and labels after finding no checkpoint, class-order, ID, sequence, or feature-row alignment defect | The weak result is shared broadly across controls and models; reversing scores or relabeling controls would optimize against the evaluation data without evidence of an implementation error. Descriptor and provenance differences support source/assay mismatch as a limitation, while the causal explanation remains unresolved. |
| 2026-10-15 | Task 4.6 uses the existing corrective beta/gamma nnPU MLP as its single curriculum learner | Direct-clamped nnPU suppresses the unlabeled gradient on roughly 98–99% of updates. Corrective nnPU provides a defined unlabeled-risk update below the threshold and can be warm-started between stages. Its selection is an engineering decision and does not claim superior assay-supported classification. |
| 2026-10-15 | Curriculum positive-risk expectations use normalized evidence weights E1=1.0 and E2=0.5; E3 remains excluded | The Planner explicitly requires these weights. Normalization preserves group expectation semantics and avoids making the loss scale depend on batch composition. This makes curriculum validation risk different from the accepted unweighted corrective-baseline risk, so the values are not treated as directly comparable. |
| 2026-10-15 | Curriculum stages carry selected model weights C1→C2→C3 but reset Adam state at each transition; all stages use the same fixed positive+C1 surrogate validation boundary with plateau patience 5 | Weight transfer implements staged learning while optimizer reset keeps each stage's moments from encoding the preceding pool. The fixed validation boundary supplies one pre-specified selection rule without inventing labels for C2/C3 or consulting held-out positives/external controls. |
| 2026-10-15 | Held-out positives and assay-inactive controls are scored only after all stage checkpoints have been selected | They are evaluation-only under Tasks 4.5/4.6 and cannot inform transitions, early stopping, or hyperparameters. The resulting external-control metrics are reported faithfully even though none resolves the earlier negative finding. |
| 2026-10-15 | A bounded retry surrounds curriculum checkpoint atomic replacement on Windows | The first genuine scratch run hit a transient `PermissionError` when `os.replace` attempted to replace `checkpoint_last.pt`. The run was marked failed. Retrying the same atomic replacement addresses a filesystem-lock race only; it does not change data, objective, optimizer, seed, or selection behavior. |
| 2026-10-15 | PP1 pre-freeze audit designates the existing Stage-C1 best checkpoint `weighted_c1_only_curriculum_reference` | It is the fresh, evidence-weighted C1 starting condition of the same sequential run, with the same objective, membership, initialization, optimizer settings, and weighted validation rule as subsequent stages. Reusing its hash avoids redundant retraining. The accepted unweighted stand-alone corrective model remains historical context only. |
| 2026-10-15 | PP1 audit classifies C3 `best_epoch=0` as post-update and retains the accepted checkpoint | Epoch zero contained 63 C3 optimizer steps before evaluation/save. Its six parameter tensors differ from the Stage-C2 parent; checkpoint payload, JSONL history, and recomputed validation risk agree. The dated report clarifies this numbering without rewriting the experimental result. |
| 2026-10-15 | PP1 audit corrects the prior decision-log wording that said external scoring occurred only after **all** stage checkpoints were selected | Source code scores after **each stage's own** best checkpoint is selected, before later stages train. The scores are not used to choose any checkpoint, stage transition, or hyperparameter, so the evaluation-only boundary still holds. This is a chronology/documentation correction, not a new model-selection procedure. |
| 2026-10-15 | PP1 readiness is `READY WITH LIMITATIONS` | Risk weighting and stage lineage passed focused mathematical and artifact checks; 160 relevant tests passed. The fixed C1 validation surrogate, provisional prior and E2 labels, source shift, one-fold scope, and weak results on 38 assay-inactive controls prevent claims of validated biological performance. |

*(Add new rows here, do not delete old ones — this is a historical log.)*
