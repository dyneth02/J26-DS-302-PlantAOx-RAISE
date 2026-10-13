# Implementation Status — Component 02 (PU-AOP)

**Last updated:** 14 October 2026
**Update rule:** Any agent (Claude Code, Codex) or person completing, starting, or blocking on a task MUST update this file in the same session the change happens. Do not let this file go stale — it is the single source of truth for "what's actually done" versus the aspirational task list in `PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`.

**Target dates (unofficial, confirm against actual schedule):** PP1 presentation 26 Oct 2026, checklist submission 30 Oct 2026.

---

## ✅ Completed tasks

*(None yet. A task moves here only once its acceptance evidence exists — see `AGENTS.md` §Validation. Partial/in-progress work stays in the section below, not here.)*

## 🔄 Current work in progress

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

## ⏭️ Next tasks (in order)

1. **Close out 2.1 (C1) properly:**
   - Write a validation script that loads the *full* `stage_c1_decoys.fasta`, re-applies the blocklist, and reports any residual hits (expect a small nonzero number — document it, don't chase it to zero).
   - Confirm record count = 5,000, length range 3–50 AA, no duplicate accessions.
   - Re-run the full pipeline once from scratch with the same seed and diff against the saved file to confirm reproducibility.
   - Write the accession/fragment-coordinate mapping and exclusion log artifacts still outstanding from the 2.1 checklist.
2. **Start Bucket 1 (FR1 — positive pool), task 1.1:** Acquire Multi-AOP and AnOxPePred, register sources/versions/checksums. This is mandatory-path work that hasn't been touched yet and is a hard dependency for everything downstream (tiering, CD-HIT, GraphPart).
3. **In parallel once 1.1 is underway: begin ESM-2 environment setup** (Bucket 3, task 3.2) since C3 (task 2.3) depends on it and it's a known multi-day setup risk (GPU/CPU fallback, model download, tokenization config).
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

*(Add new rows here, do not delete old ones — this is a historical log.)*
