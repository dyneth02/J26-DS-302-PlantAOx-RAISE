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
- **Status:** Done and run against the full provisional pool (not the FR1 freeze yet — see 1.6/1.7).
- **Environment:** `sudo apt install` was not available (no password for this agent to use
  non-interactively). Installed a user-space conda environment instead — no root needed at all:
  ```
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest -o /tmp/micromamba.tar.bz2
  # extract bin/micromamba from the tarball to ~/micromamba/bin (bzip2 missing on this image;
  # used Python's stdlib tarfile module instead of the system `tar`/`bzip2`)
  export MAMBA_ROOT_PREFIX=$HOME/micromamba
  ~/micromamba/bin/micromamba create -y -n pu_aop -c conda-forge -c bioconda cd-hit "python=3.11" pip
  ```
  `src/plantaox/c2_pu/common/wsl.py` wraps every call as
  `wsl.exe -d Ubuntu -e bash -lc "... micromamba run -n pu_aop <tool> ..."`.
- **Short-peptide handling:** 417 of 1,205 positives (35%) are under 5 AA. CD-HIT's officially
  recommended word length for 90% identity (`-n 5`) cannot build a k-mer index for anything shorter
  than 5 residues (and its default `-l` throw-away-length is 10 AA — confirmed directly via
  `cd-hit -h`, not assumed — which would have silently discarded most of this pool). Used `-n 2 -l 2`
  instead: costs clustering speed/sensitivity, not correctness, since the 90% threshold itself is
  still exact.
- **Reproducibility fix applied before this could be built safely:** `run.py::run_fr1_positives` now
  sorts every output table by `peptide_id` (content-derived hash) before writing, since the previous
  build relied on Python `set` iteration order (randomized per process) and CD-HIT's representative
  selection for exact-tie clusters depends on input FASTA order.
- **Result (full file, 2026-10-14): 1,205 → 925 clusters, 0 sequences dropped** (confirms the
  `-l 2` fix worked — none of the 417 sub-5-AA sequences were silently excluded). Cluster-size
  distribution: 758 singletons, up to one cluster of 14. Representative tier split: 491 E1 / 434 E2.
  Still comfortably above the SO1 ≥800 floor.
- **Outputs:** `data/interim/c2_pu/aop_positives_provisional.fasta` (CD-HIT input),
  `data/processed/c2_pu/cdhit_clusters.tsv` (canonical registry name, full cluster membership —
  every member, not just representatives), `cdhit_before_after_report.json`, and
  `aop_positives_cdhit90.parquet` (925 rows, one representative per cluster).

### Bucket 1, Task 1.6 — GraphPart 40% Homology Split
- **Status:** Done and run against the CD-HIT output (925 → 834 retained across 5 folds). Not the
  FR1 freeze yet — see 1.7 and the open items below.
- **Environment:** Same `pu_aop` conda env; added `graph-part` (pip) and `emboss` (bioconda, for the
  `needle`/`needleall` aligner GraphPart's "needle" mode shells out to). CLI and output schema were
  verified directly against the installed package (`graphpart needle --help`, and reading
  `graph_part.py`/`needle_utils.py`) rather than guessed from memory.
- **Real bug found and fixed in our own wrapper, not GraphPart:** `common/wsl.py`'s
  `subprocess.run(..., text=True)` defaulted to the Windows console's locale encoding (cp1252) to
  decode WSL's UTF-8 stdout, which crashed on non-ASCII bytes in GraphPart's progress output. Fixed
  by passing `encoding="utf-8", errors="replace"` explicitly.
- **Genuine partitioning infeasibility hit, diagnosed, and resolved (not worked around):** the first
  real attempt — `-dn shortest` (matching CD-HIT's own identity definition, chosen for cross-stage
  consistency) — made GraphPart fail outright: *"Impossible to generate the desired 5 partitions at
  the current partitioning threshold. Removal of sequences to achieve separation results in loss of
  4 complete partitions."* Root cause, confirmed empirically (not just theorized): 657 of 925 CD-HIT
  representatives (71%) are under 10 AA, and `shortest`-denominator global-alignment identity is
  dominated by chance matches at that length (a 5-mer differing by 2 residues already clears 40%
  identity), collapsing the partition graph into one blob. Tested a minimum-length floor as an
  alternative fix: floor=7 AA still failed; floor=8 AA "succeeded" but produced a degenerate
  357/2/5/1/1 fold split (useless for CV); floor=10 AA gave a clean 47/63/45/34/31 split but threw
  away 71% of the pool. Instead, switched the denominator to `full` (GraphPart's own default, which
  penalizes length-mismatched pairs) on the complete 925-sequence pool: this resolved the collapse
  cleanly with no length floor needed. **This was re-derived from evidence, not a parameter I pattern
  matched into working** — the "shortest" choice was reasonable-sounding but wrong, because CD-HIT
  (90% identity, near-duplicate redundancy removal) and GraphPart (40% identity, cross-fold leakage
  prevention) are different problems and don't need the same identity definition.
- **Fold label-balance improvement (not required by the proposal, but cheap and clearly worth it):**
  an unstratified 5-fold split put 86% E1 in fold 0 vs 34% E1 in fold 4 — a real confound for any
  per-fold metric comparison later (FR3/FR4/FR6). GraphPart supports label-stratified partitioning
  natively (`-ln`); added `write_stratified_fasta` to embed `|tier=E1`/`|tier=E2` in headers and pass
  `-ln tier`. Residual imbalance dropped to a 44–64% E1 range across folds — real trade-off (fold
  sizes got less even, 834 pool instead of 841, to satisfy both homology and label-balance
  simultaneously), but the worst-case distortion shrank substantially.
- **Result (full file, 2026-10-14): 834 of 925 retained, 91 removed for cross-fold homology
  violation (9.8%).** Fold sizes: 124/134/137/173/266 (fold 4 is the largest and most E1-heavy —
  residual imbalance, documented, not hidden). GraphPart's own self-report confirms convergence to
  **zero residual cross-partition homology violations** (`Connectivity: 0, #Problematics: 0` in the
  final removal round) — this is the cross-split homology validation itself, not a separate
  after-the-fact check, since GraphPart's job *is* computing exactly this distance.
- **Outputs:** `data/processed/c2_pu/graphpart_splits.csv` (canonical registry name, 834 rows: fold
  0-4), `graphpart_excluded_for_homology.csv` (the 91 excluded sequences, named individually with
  their evidence tier — never silently dropped or back-filled), `graphpart_splits_report.json`
  (GraphPart's own self-report), `graphpart_split_summary.json` (our before/after digest).
- **Open items before this can be called frozen (1.7):** the 91 homology-excluded sequences and the
  residual fold-4 tier imbalance should both be named explicitly in the FR1 report as documented
  limitations, not silently absorbed. The 179 cross-source conflicts and 553 provisional-E2 records
  from Bucket 1.4 are still pending supervisor review, unaffected by this stage's work.

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

1. **FR1 acceptance freeze (1.7):** re-run the full pipeline (`fr1-positives` → `fr1-cluster` →
   `fr1-split`) once more from raw inputs to reconfirm reproducibility end-to-end, then write
   `fr1_acceptance_report.md` naming, explicitly, every documented limitation so far: the 179
   cross-source conflicts, the 553 provisional-E2 records, the 91 GraphPart homology exclusions, and
   the fold-4 tier-balance residual. Get supervisor sign-off on all four before calling FR1 "done" —
   none of them block continued pipeline development, but AGENTS.md rule #3 means none of them let
   FR1 be marked complete either.
2. **Close out 2.1 (C1) properly**, now with two new concrete findings to fold in:
   - Decide whether "5,000 records" (Bucket 2.7 acceptance criterion) means 5,000 FASTA entries or
     5,000 unique sequences — currently 3,786 unique (see Known Issues #6).
   - Run Bucket 2.4's positive-vs-C1 identity check now that the FR1 positive pool exists; at least
     one known positive (`DRVYIHPF`) is currently sitting inside the C1 decoy file (Known Issues #7).
   - Confirm record count, length range 3–50 AA, re-run reproducibility, and finish the
     accession/fragment-coordinate mapping and exclusion log artifacts still outstanding from the 2.1
     checklist.
3. **In parallel: begin ESM-2 environment setup** (Bucket 3, task 3.2) — the `pu_aop` WSL conda env
   built for CD-HIT/GraphPart is a natural place to add PyTorch/fair-esm too, since it already solves
   the "no root access" problem this environment has.
4. **Task 2.2 (C2 — Peptipedia bioactive pool)** can start any time; not blocked on anything above.
5. Continue down the Bucket 1 → Bucket 2 → Bucket 3 → Bucket 4 sequence as defined in `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`, respecting the FR1+FR2-first priority.

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

*(Add new rows here, do not delete old ones — this is a historical log.)*
