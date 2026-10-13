# Implementation Status — Component 02 (PU-AOP)

**Last updated:** 14 October 2026
**Update rule:** Any agent (Claude Code, Codex) or person completing, starting, or blocking on a task MUST update this file in the same session the change happens. Do not let this file go stale — it is the single source of truth for "what's actually done" versus the aspirational task list in `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`.

**Target dates (unofficial, confirm against actual schedule):** PP1 presentation 26 Oct 2026, checklist submission 30 Oct 2026.

---

## ✅ Completed tasks

*(None yet. A task moves here only once its acceptance evidence exists — see `AGENTS.md` §Validation. Partial/in-progress work stays in the section below, not here.)*

## 🔄 Current work in progress

### Bucket 1, Tasks 1.1–1.4 — Positive Pool Acquisition, Cleaning, and Evidence Tiering
- **Status:** Raw sources acquired and placed (`data/raw/c2_pu/Multi-AOP/combined_data.csv`,
  `data/raw/c2_pu/AnOxPePred/Supplementary_Data_S1_Marcatili.csv`). Standardization, cross-source
  conflict resolution, and E1/E2 tiering implemented and run end-to-end
  (`plantaox.c2_pu.curation.{adapters,standardize,tiers}`, orchestrated by
  `plantaox.c2_pu.run.run_fr1_positives`). **Not yet done: CD-HIT 90% dedup (1.5), GraphPart 40%
  split (1.6), 1.7 freeze.** The output below is provisional, pre-clustering, pre-split.
- **What the pipeline does:**
  - Loads Multi-AOP (label==1 only, per AGENTS.md) and AnOxPePred (FRS/Chelator independent assay
    columns — either flag being 1 counts as confirmed antioxidant activity per the proposal's
    background section, p.12).
  - Resolves cross-source conflicts: a sequence Multi-AOP calls positive but AnOxPePred's own assay
    reports inactive on BOTH mechanisms (FRS=0 AND Chelator=0) is excluded from the positive pool,
    logged in full with provenance in `data/interim/c2_pu/label_conflicts_anox_vs_multiaop.csv`, and
    flagged as an external-control *candidate* pending manual review — never silently dropped, never
    auto-reclassified as E3, never auto-added to the control set.
  - Assigns E1 (AnOxPePred assay-confirmed) vs E2 (Multi-AOP-only, no per-record assay metadata
    available — tier is explicitly provisional, `assay_verified="unknown"`).
  - Applies the shared 3–50 AA length window to positives (matching C1/C2/C3), logging exclusions.
- **Latest run stats (full files, 2026-10-14):**
  - E1 (assay-confirmed): 697 → 670 after length filter
  - E2 (provisional, Multi-AOP-only): 553 → 535 after length filter
  - **Accepted positive pool: 1,205** sequences (pre-CD-HIT) — comfortably clears the SO1 floor of
    ≥800, with headroom for shrinkage during CD-HIT 90% clustering.
  - **Conflicts excluded: 179** sequences (82.5% of AnOxPePred's 217 true-inactive sequences are
    contested by Multi-AOP — see Known Issues #5). 141 of the 179 (79%) are exact tripeptides,
    consistent with short-fragment sequence collision across unrelated source studies rather than a
    data-entry error.
  - **Clean external-control set: 38** sequences (AnOxPePred inactive, uncontested) — much smaller
    than the ~217 the proposal cites, because most of that 217 turns out to be contested once
    cross-referenced against Multi-AOP. Flag this shrinkage for supervisor awareness: the external
    control used in later RNIS/calibration work will be this smaller, cleaner 38, not ~217.
  - Length-excluded from positive pool: 45 (all <3 AA).
  - 156 sequences in Multi-AOP appear under both label=0 and label=1 on different rows; per the
    existing "ignore Multi-AOP's negative labels" rule this doesn't block their label=1 assertion,
    but it's logged here as a data-quality note.
- **Outputs:**
  - `data/processed/c2_pu/aop_positives_provisional.parquet` (1,205 rows; NOT the frozen FR1
    artifact — name says "provisional" deliberately, see AGENTS.md rule #4)
  - `data/interim/c2_pu/label_conflicts_anox_vs_multiaop.csv` (179 rows, full provenance)
  - `data/processed/c2_pu/anoxpepred_inactives_clean.csv` (38 rows — external control, Bucket 2.6
    input, still needs its own homology check against positives before freeze)
  - `data/processed/c2_pu/fr1_positive_pool_provenance.jsonl` (run provenance log)
- **What's NOT done:** CD-HIT 90% clustering (1.5), GraphPart 40% split (1.6), the 179 conflicts'
  manual/supervisor review, the 553 provisional-E2 records' supervisor sign-off, and the FR1
  acceptance freeze (1.7). CD-HIT and GraphPart are external bioinformatics tools not yet installed
  in this environment — flagged as a decision/setup item, not started.

### Bucket 1, Task 1.5 — CD-HIT 90% Clustering
- **Status:** Code complete and tested (`curation/dedup.py`, `run.py::run_fr1_cluster`), **not yet
  executed against real data** — blocked on a one-time manual setup step (see below). Fails fast with
  a clear, actionable error (not a raw subprocess traceback) when cd-hit isn't available yet.
- **Short-peptide handling (explicitly required, see decision log):** 417 of 1,205 positives (35%)
  are under 5 AA. CD-HIT's officially recommended word length for 90% identity (`-n 5`) cannot build
  a k-mer index for anything shorter than 5 residues, which would silently exclude over a third of
  the pool from clustering. Using `-n 2` (CD-HIT's minimum) instead — this costs clustering
  speed/sensitivity, not correctness; the 90% identity threshold itself is still enforced exactly.
- **Reproducibility fix applied before this could be built safely:** `run.py::run_fr1_positives` now
  sorts every output table by `peptide_id` (a content-derived hash) before writing. The positive pool
  was previously built via Python `set` operations whose iteration order is randomized per-process —
  harmless for a flat table, but CD-HIT's representative selection for exact-identity ties depends on
  input FASTA order, so this needed fixing before generating CD-HIT input. Re-ran `fr1-positives`
  after the fix: identical counts, now deterministically ordered.
- **Environment blocker (needs the project owner to run one command):** WSL Ubuntu 24.04 is present
  with network access, but has no `cd-hit`, `pip3`, or working `python3 -m venv` — all three need
  `sudo apt install`, which needs an interactively-typed password an agent can't supply. One-time fix:
  `wsl -d Ubuntu -e sudo apt install -y cd-hit python3-pip python3.12-venv`.
- **Outputs once run:** `data/interim/c2_pu/aop_positives_provisional.fasta` (CD-HIT input),
  `data/processed/c2_pu/cdhit_clusters.tsv` (canonical registry name per AGENTS.md), full
  before/after report (`cdhit_before_after_report.json`), and a reduced
  `aop_positives_cdhit90.parquet` carrying forward one representative row per cluster. Still not the
  FR1 freeze — GraphPart (1.6) runs next.

### Bucket 1, Task 1.6 — GraphPart 40% Homology Split
- **Status:** Not started. GraphPart's exact CLI (flag names, output format) will be verified against
  `graphpart --help` once it's actually installed, rather than implemented from memory — the
  AnOxPePred inactive-count exercise (Bucket 1.4) already turned up a real correctness issue in an
  assumption that looked right at first glance, so unverified tool-interface guesses aren't worth the
  risk here. Blocked on the same WSL setup step as 1.5 (needs `pip3` to `pip3 install --user
  graph-part`).

### Bucket 2, Task 2.1 — C1 Random Decoy Construction
- **Status:** Pipeline built and functioning; full-file validation **not yet done**.
- **What exists:** A Colab/Python script that queries UniProtKB REST (`reviewed:true AND length:[3 TO 50]` plus keyword exclusions), applies a secondary Python keyword blocklist, randomly samples 5,000 records (seed 42), and writes a provenance log.
- **Latest run stats:** 8,830 candidates after query filter → 8,233 after secondary filter → 5,000 sampled.
- **What's NOT done:**
  - The full 5,000-record `stage_c1_decoys.fasta` has never been directly inspected — only six rounds of 25-record random previews.
  - No automated test yet exists to re-check the *entire* final file against the blocklist (as opposed to a random slice).
  - Reproducibility hasn't been formally re-verified (re-running from scratch and diffing against the saved file).
  - Task 2.1's remaining checklist items (accession/fragment-coordinate mapping, exclusion log formatting) per the Planner breakdown are not yet done.
- **Next action:** see Next Tasks below — full-file validation script, then formal close-out of 2.1.

## ⚠️ Known issues / open risks

1. **C1 source ambiguity (supervisor sign-off needed):** Proposal says "SwissProt" (FR2/SO2) vs "UniRef50" (§3.2.2). We've adopted UniProtKB `reviewed:true` (= SwissProt) as the working interpretation — see `PU_AOP_RESEARCH_CONTEXT.md` §4 for rationale. **This has not been confirmed with supervisors yet.** Flag in next consultation.
2. **Residual filtering imperfection is expected, not a bug.** Six rounds of manual review caught progressively more obscure contamination (toxins → hormones → AMPs → antioxidant enzymes → metallothionein → frog skin peptides). This is diminishing returns, not an unresolved defect. The agreed plan is to document it as a limitation in the FR2 report (see `PU_AOP_RESEARCH_CONTEXT.md` §7), **not** to keep iterating indefinitely. Do not reopen this unless full-file validation (above) finds something structurally different from the spot-check pattern.
3. **Full-file validation gap** (see Current Work above) — this is the one open item that *does* need closing before C1/FR2 can be marked complete, as distinct from #2 which is an accepted limitation.
4. **A real case-sensitivity bug occurred once already** (keyword added with a capital letter never matched because `.lower()` was only applied to the description, not the keyword). Fixed via the list-comprehension lowercasing pattern in `PU_AOP_RESEARCH_CONTEXT.md` §5. Any agent editing the blocklist should be aware this class of bug is easy to reintroduce.
5. **179 of 1,384 candidate positives (Multi-AOP ∩ AnOxPePred-inactive) are cross-source contradicted — resolved, but needs supervisor visibility.** See Bucket 1 section above. Excluded from both the positive pool and the external control pending manual review; logged in full in `label_conflicts_anox_vs_multiaop.csv`. This is the exact "contradictory labels across databases" phenomenon the proposal's own lit review (p.14, citing Isaac et al.) names as a field-wide problem — worth citing directly in the FR1 report as in-practice confirmation of the research motivation, not just a data-cleaning footnote.
6. **C1 decoy pool has only 3,786 unique sequences across its 5,000 FASTA records** (checked directly against the full file, not a sample). Short 3–50 AA fragments repeat across species for biologically ordinary reasons (conserved motifs), so this isn't necessarily a defect, but it means the "5,000 records" acceptance criterion (Bucket 2.7, FR2 checklist) is satisfied at the record level, not the unique-sequence level — needs an explicit decision on which one the acceptance checklist actually means before FR2 sign-off.
7. **One known AOP positive sequence (`DRVYIHPF`) was found inside the existing C1 decoy FASTA** — direct sequence-identity leakage between Stage C1 and the positive pool. Expected: C1 was built (2026-10-07) before the FR1 positive pool existed, so its only contamination screen was the generic bioactivity keyword blocklist, not a direct identity check. This is exactly what Bucket 2.4 ("Find and resolve overlap among challenge pools and curated positives") is for — flagging here so it isn't missed, not proposing a new policy.

## ⏭️ Next tasks (in order)

1. **Run the one-time WSL setup command** (see Bucket 1.5 above) — blocks both 1.5 and 1.6.
   `wsl -d Ubuntu -e sudo apt install -y cd-hit python3-pip python3.12-venv`. Once done:
   `python -m plantaox.c2_pu.run fr1-cluster` runs CD-HIT end-to-end; GraphPart's wrapper gets
   written next, against its real `--help` output.
2. **Get supervisor/manual eyes on the two provisional buckets** before treating FR1 as close to done:
   the 179 logged conflicts (`label_conflicts_anox_vs_multiaop.csv`) and the 553 provisional-E2
   records (`aop_positives_provisional.parquet`, `evidence_tier == "E2"`). Both are usable for
   continued pipeline development now, but neither should be presented as final without that review.
3. **Close out 2.1 (C1) properly**, now with two new concrete findings to fold in:
   - Decide whether "5,000 records" (Bucket 2.7 acceptance criterion) means 5,000 FASTA entries or
     5,000 unique sequences — currently 3,786 unique (see Known Issues #6).
   - Run Bucket 2.4's positive-vs-C1 identity check now that the FR1 positive pool exists; at least
     one known positive (`DRVYIHPF`) is currently sitting inside the C1 decoy file (Known Issues #7).
   - Confirm record count, length range 3–50 AA, re-run reproducibility, and finish the
     accession/fragment-coordinate mapping and exclusion log artifacts still outstanding from the 2.1
     checklist.
4. **In parallel: begin ESM-2 environment setup** (Bucket 3, task 3.2) since C3 (task 2.3) depends on
   it and it's a known multi-day setup risk (GPU/CPU fallback, model download, tokenization config).
5. **Task 2.2 (C2 — Peptipedia bioactive pool)** can start any time; not blocked on anything above.
6. Continue down the Bucket 1 → Bucket 2 → Bucket 3 → Bucket 4 sequence as defined in `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`, respecting the FR1+FR2-first priority.

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

*(Add new rows here, do not delete old ones — this is a historical log.)*
