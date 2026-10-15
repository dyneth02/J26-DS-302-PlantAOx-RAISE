# FR2 Acceptance Report — Component 02 (PU-AOP)

**Status:** Technical acceptance passed. Scientific sign-off is a separate, still-open item (see §10),
consistent with how FR1 was closed (`fr1_acceptance_report.md`).

**Scope:** FR2's three unlabeled "challenge" pools (C1, C2, C3) and the AnOxPePred external inactive
control, built on top of FR1's frozen `pp1_baseline_v1`.

---

## 1. Methodology summary

FR2 was built and audited across Buckets 2.1–2.6, in this order:

1. **C1 (random decoys)** — UniProtKB `reviewed:true` query, seed-42 sampling, then two follow-up
   fixes: an alphabet-policy fix (Bucket 2.1 follow-up, v1→v2) and a cross-pool exact-overlap fix
   (Bucket 2.4 Decision A, v2→v3). **Canonical: `stage_c1_decoys_v3.fasta`.**
2. **C2 (bioactive unlabeled)** — Peptipedia v2.0 Zenodo dump, parsed as plain-text SQL, experimentally-
   reported-tier sampling (Bucket 2.2), then one follow-up fix: a homology-to-an-E1-positive exclusion
   (Bucket 2.4 Decision B, v1→v2). **Canonical: `stage_c2_bioactive_unlabeled_v2.fasta`.**
3. **C3 (ESM-2 hard challenges)** — UniRef50 REST query candidate universe, embedded via
   `esm2_t12_35M_UR50D`, ranked per-fold against 5 fold-safe training-only centroids (Bucket 2.3).
   **Canonical: `stage_c3_esm2_hard_challenges.fasta` (union) + `c3_similarity_ranking.csv`
   (fold-specific membership/rank/similarity — mandatory for any downstream fold-safe use, see
   `curation/c3.py::load_fold_challenges`).**
4. **Pool contamination and leakage audit** (Bucket 2.4) — full sequence-integrity audit, pairwise
   exact-overlap matrix, external known-AOP screening (BIOPEP-UWM/AODB/DFBP), cross-pool homology
   scan (EMBOSS-grade length-floor discipline), and formal C3 fold-contract re-verification. Found
   and resolved two contamination findings (Decisions A/B above); 11 residual C1↔C2 near-duplicate
   families accepted as a documented limitation (project-owner approved, conditional on no
   FR1-positive involvement — re-verified).
5. **Biological distribution and shortcut-bias checks** (Bucket 2.5) — quantified (KS-test, not
   eyeballed) distributional mismatch between FR1 positives and each challenge pool on length,
   molecular weight, net charge, GRAVY, and aromaticity; amino-acid composition comparison;
   organism/activity-tag shortcut scan.
6. **External inactive-control validation** (Bucket 2.6) — integrity-checked the frozen baseline's
   38-record AnOxPePred external control, ran a dedicated EMBOSS `needleall` homology audit against
   the FR1 positive pool (not a CD-HIT shortcut), and reconciled 2 BIOPEP-UWM annotation conflicts.

No stochastic step in this chain lacks a fixed seed (42, used consistently for every sampling/
replacement draw); CD-HIT, GraphPart, and `needleall` are all seed-free, deterministic given fixed
inputs. "Reproducible" below means exactly that: same inputs → byte-identical outputs, verified
directly by re-running each stage, not inferred.

---

## 2. Final counts

| Pool | Records | Unique sequences | Canonical artifact |
|---|---|---|---|
| FR1 positives (frozen) | 1,205 | 1,205 | `frozen/pp1_baseline_v1/aop_positives_provisional.parquet` |
| 179 cross-source conflicts (frozen) | 179 | 179 | `frozen/pp1_baseline_v1/label_conflicts_anox_vs_multiaop.csv` |
| External inactive control | 38 | 38 | `anoxpepred_external_control_validated.csv` |
| C1 (random decoys) | 5,000 | 3,788 | `stage_c1_decoys_v3.fasta` |
| C2 (bioactive unlabeled) | 2,000 | 2,000 | `stage_c2_bioactive_unlabeled_v2.fasta` |
| C3 (ESM-2 hard challenges, union) | 2,325 | 2,325 | `stage_c3_esm2_hard_challenges.fasta` |
| C3 fold-specific selections | 5×2,000 = 10,000 rows | — | `c3_similarity_ranking.csv` |

C1's unique-sequence count (3,788, down from the original pipeline's 3,786/3,785 across versions) is
expected, not a defect — see §9, "C1 record-vs-unique-sequence distinction."

---

## 3. Cross-pool integrity and exact overlap

Re-verified directly against the final canonical artifacts (`fr2-pool-audit`, re-run fresh for this
report, not reused from an earlier log):

- Zero duplicate peptide IDs and zero non-standard-alphabet sequences in any of the 6 pools audited.
- **FR1 positives have zero exact-sequence overlap with C1, C2, C3, or the external control** — the
  one invariant that must never fail.
- C1↔C2 exact overlap: **0** (was 8 unique sequences / 11 records before Decision A; resolved).
- External control: zero exact overlap with positives, conflicts, C1, C2, or C3.

Full detail: `audit_integrity_report.json`, `audit_exact_overlap_matrix.csv`, `audit_exact_overlap_detail.csv`.

## 4. Cross-pool and external-control homology

- **C1↔C2 near-duplicate families:** 11 real (≥15 AA, ≥90% CD-HIT identity) candidates remain,
  reviewed individually, approved by the project owner as a documented limitation (see §9).
- **C2↔FR1-positive homology:** 1 confirmed hit (Decision B), resolved by exclusion and replacement.
  Zero remaining after the fix.
- **External control↔FR1-positive homology:** 0 genuine hits out of 45,790 pairs checked via real
  EMBOSS `needleall` global alignment (not CD-HIT). No pair reaches both ≥40% identity (the Planner's
  proposed boundary) and a biologically-interpretable ≥15 AA alignment length; the 394 pairs above
  40% identity are all ≤12 AA short-fragment chance matches. Held-out-fold independence follows
  structurally (any fold's positives are a subset of the full 1,205 screened).
- **Short-peptide identity caveat, applied consistently throughout FR2:** CD-HIT and raw percent-
  identity are unreliable for alignments under ~15 AA (chance substring matches dominate given the
  small size of amino-acid-sequence space at that length) — every homology conclusion in this report
  applies that floor explicitly rather than treating all high-identity matches as meaningful.

Full detail: `audit_cross_pool_homology_summary.json`/`_clusters.csv`, `ext_control_homology_pairs.csv`.

## 5. External known-AOP screening

- **BIOPEP-UWM: screened.** 990 standard-alphabet antioxidative reference peptides (scraped from its
  open-access search page, no API/bulk export exists). Zero hits in C1, C2, or C3. 700/1,205 FR1
  positives and 22/179 conflicts independently corroborated (a positive validation signal, not a
  problem). 2 external-control records independently flagged (see §9).
- **AODB: inaccessible**, not screened — confirmed via direct `curl` (with and without TLS
  verification) that its server returns HTTP 502 from its own nginx, plus an expired TLS certificate.
- **DFBP: inaccessible**, not screened — no working hosting URL discoverable via web search or its
  own PubMed record (35552640), which is itself blocked by a cookie wall to automated access.

**This is a coverage limitation, not a coverage claim:** absence of a BIOPEP-UWM/Multi-AOP/AnOxPePred
hit does not prove a sequence is non-antioxidant under some other, unchecked database or the primary
literature. Stated explicitly, not implied.

## 6. C3 fold-specific construction and contract

Re-verified formally (`curation/c3.py::validate_c3_fold_contract`) against the live cached embeddings,
not re-trusted from Bucket 2.3's own build log:

- All 5 folds have exactly 2,000 ranking rows, ranks forming a contiguous unique 1–2,000 sequence.
- Every fold's centroid is reconstructed exactly from that fold's OTHER 4 folds' training positives
  (fold sizes 124/134/137/173/266 held out, 710/700/697/661/568 used for training) — confirmed for
  all 5 folds, not spot-checked on one.
- The union FASTA's peptide IDs are set-equal to the ranking CSV's unique peptide IDs in both
  directions.
- **`load_fold_challenges(ranking_path, fold_id)` is the only sanctioned way to read C3** for FR3/
  FR4/FR6 training code — no function anywhere in `curation/c3.py` returns the cross-fold union, and
  a test (`test_there_is_no_function_in_this_module_that_returns_all_folds_at_once`) guards against
  one being added later without deliberate renaming.

## 7. Biological distribution and shortcut-bias findings (Task 2.5)

Quantified via two-sample KS-test (FR1 positives vs. each challenge pool), not visual judgment alone:

| Descriptor | C1 | C2 | C3 |
|---|---|---|---|
| Length | 0.858 | 0.627 | 0.793 |
| Molecular weight | 0.859 | 0.663 | 0.802 |
| Net charge (pH 7) | 0.419 | 0.418 | 0.269 |
| GRAVY | 0.140 | 0.144 | 0.265 |
| Aromaticity | 0.330 | 0.245 | 0.336 |

*(KS statistic, 0=identical distributions, 1=maximally different; every value above has p < 1e-13.)*

**Every challenge pool differs significantly from FR1 positives on every descriptor tested.** This is
a real, measured shortcut-bias risk for FR3/FR4 classifier training to be aware of — **it does NOT
establish an empirically validated C1-to-C2-to-C3 difficulty ordering** (the KS statistics are not
monotonic across pools or descriptors: C3 is the largest mismatch on length/MW/aromaticity, but C2 is
largest on net charge and C1 on none), and is not a defect requiring a fix in FR2 — the pools were
always structurally likely to differ given how differently each was constructed (different source
databases entirely). Amino-acid composition shows biologically sensible signal, not noise: FR1
positives are Proline-enriched (10.6% vs. 4–6% elsewhere, consistent with food-derived antioxidant
peptide literature); C2 is Cysteine-enriched (5.5% vs. 1.4–2.6% elsewhere, consistent with its heavy
antimicrobial/defensin representation).

**FR1 positives have no organism metadata available** (Multi-AOP/AnOxPePred carry no per-record
source-organism field) — an unchecked shortcut-risk gap, documented not assumed clean. C1 spans 1,708
organisms (no single organism >2.1% share); C2 spans 123 activity tags ("Therapeutic" largest, 14.4%).

Full detail: `distribution_ks_comparison.csv`, `distribution_aa_composition.csv`,
`distribution_shortcut_report.json`.

## 8. External inactive control (Task 2.6)

- 38 records, integrity-verified (IDs, sequences, lengths, alphabet all consistent).
- Zero exact overlap and zero genuine homology (≥15 AA, ≥40% identity) against the FR1 positive pool
  — see §4.
- **Labeling rule, stated in every output:** these records are inactive *under AnOxPePred's FRS/
  Chelator assay definitions specifically* — not a universal claim of proven non-antioxidant status.
  Kept structurally separate from C1/C2/C3 at all times (never merged into the unlabeled training
  pools).
- 2 BIOPEP-UWM-vs-AnOxPePred annotation conflicts reconciled: both records (`AOP-37BD4B4933`/"FCM",
  `AOP-DDCD54E4BA`/"YPQLLPNE") are flagged (`has_biopep_antioxidative_conflict`) but retained in the
  primary set — a recommendation presented for project-owner confirmation (not yet confirmed as of
  this report), per the established assay-outranks-undocumented-annotation precedent from FR1.

## 9. Documented limitations (technical, not blocking)

1. **11 remaining C1↔C2 near-duplicate families** (ribosomal/zinc-ribbon proteins, protamine-like
   peptides, a homeodomain cell-penetrating peptide, actin/gliadin fragments, defensin-like
   peptides) — approved by the project owner as a documented limitation, conditional on (and
   re-verified as) zero FR1-positive involvement in the real, length-qualifying homology relationship.
2. **AODB and DFBP remain unscreened** for documented access reasons (HTTP 502 + expired cert; no
   discoverable hosting URL), not as an unstarted task.
3. **2 BIOPEP-UWM-vs-AnOxPePred external-control annotation conflicts** — flagged, retention
   recommended, not yet explicitly confirmed by the project owner.
4. **C1's record-vs-unique-sequence distinction:** 5,000 FASTA records / 3,788 unique sequences by
   design (confirmed project-owner decision) — any future train/validation/test split MUST group
   identical sequences together to avoid sequence-level leakage; this is a data-loader design
   requirement for FR3/FR4, not something this audit enforces by itself.
5. **C3's fold-specific selection constraint:** the union FASTA is NOT a valid "one fold's challenge
   set" on its own — FR3/FR4/FR6 must use `load_fold_challenges(path, fold_id)`.
6. **Significant FR1-vs-C1/C2/C3 distribution shifts** (§7) — a measured shortcut-bias risk, not an
   ordering claim, not a defect.
7. **FR1 positives have no organism metadata** — an unchecked (not assumed-absent) shortcut-risk gap.
8. **Outstanding supervisor approvals carried over from FR1** (`fr1_acceptance_report.md` §10): the
   conflict-resolution policy, the E2 provisional-tier default, the C1 source ambiguity (SwissProt vs.
   UniRef50), and the missing formal `data_registry.csv`. None of these block FR2's technical
   acceptance; all remain open pending supervisor sign-off, same status as reported for FR1.
9. **No formal `data_registry.csv`** covering FR2's own new external sources (Peptipedia Zenodo dump,
   UniRef50 REST snapshot, BIOPEP-UWM scrape) — same gap already flagged for FR1's sources, now also
   applying to FR2's. SHA-256 checksums and DOIs/URLs are recorded in each stage's own provenance
   JSONL instead, a stopgap not a substitute, consistent with how FR1's equivalent gap was handled.

## 10. Pending supervisor/project-owner approvals (kept separate from technical acceptance)

Per AGENTS.md rule #3, technical acceptance ("the pipeline is correct, reproducible, and every
mandatory check passes") is tracked separately from scientific/supervisor sign-off:

- FR1's 4 pending supervisor approvals (carried over, unchanged — see §9.8).
- The BIOPEP-UWM external-control retention recommendation (§9.3) — presented, not yet confirmed.

## 11. Technical acceptance (automated)

- Full test suite: **all tests pass** (unit + full-file acceptance across C1/C2/C3/external-control/
  audit/distribution modules), including byte-identical reproducibility re-runs for every stage with
  a stochastic-looking (seeded) or tool-mediated (CD-HIT/GraphPart/ESM-2/needleall) step.
- `fr2_pool_audit_report.json`: `ready_for_technical_acceptance: true`, computed from the live
  artifacts at report-generation time, not a hand-set flag.
- Re-running each stage from its frozen/versioned source inputs reproduces byte-identical outputs
  (verified directly, not assumed): C1 cross-pool fix, C2 cross-pool fix, C3 build (positives +
  candidates re-embedded), and the external-control homology audit all have dedicated reproducibility
  tests, all passing.

## 12. Frozen baseline

See `IMPLEMENTATION_STATUS.md` for the frozen `pp2_baseline_v1` manifest path and checksum summary,
written once this report was finalized. `pp1_baseline_v1` (FR1) was not touched, re-generated, or
re-checksummed as part of freezing FR2 — confirmed via `verify_frozen_baseline()` before and after.
