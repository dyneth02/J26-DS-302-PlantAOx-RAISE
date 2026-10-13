# FR1 Acceptance Report — Component 02 (PU-AOP)

**Scope:** Bucket 1 (Tasks 1.1–1.7) — Evidence-tiered positive pool curation, conflict resolution, CD-HIT 90% redundancy reduction, GraphPart 40% homology-controlled splitting.
**Baseline identifier:** `pp1_baseline_v1` (frozen 2026-10-14, see §8).
**Status:** Technical acceptance passed (§7). Supervisor approvals pending on four named items (§9) — this report documents a reproducible, defensible PP1 dataset baseline, not a scientifically final one. See AGENTS.md rule #3: a task is only "done" against its own acceptance checklist, and this report is that checklist's evidence, not a claim that every open question is resolved.

---

## 1. Methodology summary

1. **Source merge** (`curation/adapters.py`): Multi-AOP's `label == 1` rows and AnOxPePred's FRS/Chelator assay rows are loaded independently. Multi-AOP's `label == 0` rows are never used as negatives (AGENTS.md rule #1).
2. **Conflict resolution** (`curation/tiers.py`): a sequence Multi-AOP calls positive but AnOxPePred's own assay reports inactive on both mechanisms (FRS=0 AND Chelator=0) is excluded from both the positive pool and the external control, logged with full provenance, flagged for manual review — never silently dropped or reclassified.
3. **Evidence tiering**: AnOxPePred-corroborated positives → **E1**; Multi-AOP-only positives (no per-record assay metadata available) → **E2**, explicitly provisional.
4. **Length filter**: shared 3–50 AA window applied to positives (matching C1/C2/C3).
5. **CD-HIT 90%** (`curation/dedup.py`): near-duplicate redundancy reduction, `-n 2 -l 2` (not the "recommended" `-n 5`/default `-l 10`) to avoid excluding this pool's many sub-5-AA sequences.
6. **GraphPart 40%** (`curation/splits.py`): cross-fold homology-controlled 5-fold partitioning, label-stratified by evidence tier, `-dn full` (re-derived empirically after `-dn shortest` collapsed the partition graph — see §6).
7. **Freeze** (`curation/freeze.py`): checksummed snapshot of every output under `pp1_baseline_v1`.

All seven stages are reproducible CLI commands:
```
python -m plantaox.c2_pu.run fr1-positives
python -m plantaox.c2_pu.run fr1-cluster
python -m plantaox.c2_pu.run fr1-split
python -m plantaox.c2_pu.run fr1-freeze
```

## 2. Final counts

| Stage | Count | Notes |
|---|---|---|
| Multi-AOP raw positives (label==1, deduplicated) | 1,418 | 2,597 raw rows → 1,418 unique sequences |
| AnOxPePred assay-active (FRS=1 or Chelator=1) | 697 | → **E1** |
| AnOxPePred assay-inactive (FRS=0 AND Chelator=0) | 217 | external-control candidates |
| **Cross-source conflicts excluded** | **179** | Multi-AOP-positive ∩ AnOxPePred-inactive |
| Multi-AOP-only positives (no AnOxPePred row) | 553 | → **E2**, provisional |
| Accepted positives, pre-length-filter | 1,250 | 697 E1 + 553 E2 |
| Dropped for length (<3 AA) | 45 | |
| **Accepted positive pool (provisional)** | **1,205** | 670 E1 + 535 E2 — clears SO1's ≥800 floor |
| Clean external control (uncontested) | 38 | of AnOxPePred's 217; 179 are contested (see §6) |
| **CD-HIT 90% clusters** | **925** | 0 sequences dropped (see §5) |
| **GraphPart 40%, retained across 5 folds** | **834** | 91 excluded for cross-fold homology (9.8%) |

## 3. Evidence-tier breakdown

| Stage | E1 | E2 | Total |
|---|---|---|---|
| Provisional pool (post length-filter) | 670 | 535 | 1,205 |
| CD-HIT representatives | 491 | 434 | 925 |
| GraphPart-retained, by fold | | | |
| — Fold 0 | 59 | 65 | 124 |
| — Fold 1 | 60 | 74 | 134 |
| — Fold 2 | 60 | 77 | 137 |
| — Fold 3 | 90 | 83 | 173 |
| — Fold 4 | 169 | 97 | 266 |

Fold 4's E1 share (64%) is noticeably higher than folds 0–3 (44–52%) — a residual imbalance after label stratification, not a defect (§6, §9).

## 4. Provenance completeness

Every row in the frozen positive pool traces to a named, typed source — verified by `tests/c2_pu/test_fr1_provenance_acceptance.py` (13 tests), not asserted narratively:

- Every **E1** row carries `in_anoxpepred=True`, a non-null `anoxpepred_frs`/`anoxpepred_chelator`/`anoxpepred_source`, and `evidence_basis="anoxpepred_assay"`.
- Every **E2** row carries `in_multiaop=True`, `multiaop_label=1`, `in_anoxpepred=False`, `evidence_basis="benchmark_positive_annotation"`, and `assay_verified="unknown"` (never inferred as confirmed).
- No row is sourceless: `in_multiaop OR in_anoxpepred` holds for all 1,205 rows.
- Peptide IDs form an unbroken chain with no gaps or duplicates: provisional pool (1,205) → CD-HIT cluster membership (1,205, exact set match) → CD-HIT representatives (925, exact set match) → GraphPart retained ∪ excluded (834 + 91 = 925, exact set match).
- The 179 conflicted sequences and the 38 (and 179 contested) external-control sequences are confirmed absent from the final 925-sequence CD-HIT/GraphPart pool by sequence identity, not just by ID.

**Raw-source checksums** (SHA-256, computed 2026-10-14):
| File | SHA-256 |
|---|---|
| `Multi-AOP/combined_data.csv` | `f4ef313fdbd7692a2b0ed5c24e639ef18f3a5369075c474e74ba92ff6a3e6578` |
| `AnOxPePred/Supplementary_Data_S1_Marcatili.csv` | `a985123d1fbf99b1f624d42dd86c647c855a61e8ec0adcce631fb16a086b5995` |

**Known gap (not an FR1 acceptance blocker, but real):** Bucket 1.1/1.2's formal `data_registry.csv` (source IDs, license, access date, release/commit hash) was never created as a standalone artifact — the checksums above are a partial substitute computed for this report, not the registry Bucket 1.2 specifies. Flagged in §9.

## 5. CD-HIT 90% clustering summary

- Config: `-c 0.9 -n 2 -l 2 -d 0 -M 0 -T 0` (CD-HIT 4.8.1).
- `-n 2` (not the recommended `-n 5`) and `-l 2` (not the default `-l 10`): 417 of 1,205 positives (35%) are under 5 AA, and CD-HIT's default throw-away length would have silently discarded most of the pool.
- Result: **1,205 → 925 clusters, 0 sequences dropped** — confirms the parameter choice worked, not just compiled.
- Cluster-size distribution: 758 singletons, 115 pairs, 32 triples, down to one cluster of 14. Representative split: 491 E1 / 434 E2.

## 6. GraphPart 40% split summary and homology validation

- Config: `graphpart needle -th 0.4 -tf one-minus -pa 5 -dn full -ln tier` (graph-part 1.0.2, EMBOSS needleall 6.6.0.0).
- **Identity denominator, explicitly documented:** `-dn full` (GraphPart's own default — alignment length including gaps, penalizing length-mismatched pairs). This was **re-derived empirically, not assumed**: a first attempt at `-dn shortest` (chosen to match CD-HIT's own identity definition, for apparent cross-stage consistency) made GraphPart fail outright — *"Impossible to generate the desired 5 partitions... loss of 4 complete partitions."* Root cause, confirmed not theorized: 657 of 925 CD-HIT representatives (71%) are under 10 AA, and `shortest`-denominator global-alignment identity for very short peptides is dominated by chance matches, collapsing the partition graph into one component. A minimum-length floor was tested as an alternative fix before switching denominators: floor=7 AA still failed; floor=8 AA "succeeded" but produced a degenerate 357/2/5/1/1 fold split (unusable for CV); floor=10 AA gave a clean split but discarded 71% of the pool. `-dn full` resolved the collapse cleanly on the **complete** 925-sequence pool, with no length floor and no data loss beyond the homology exclusions below. CD-HIT (90% identity, redundancy removal) and GraphPart (40% identity, leakage prevention) solve different problems and do not need to share an identity definition — matching them was the wrong simplification, not a neutral default.
- **Label stratification:** `-ln tier` (via `write_stratified_fasta`'s `|tier=E1`/`|tier=E2` FASTA headers) was added after an unstratified run put 86% E1 in fold 0 vs 34% in fold 4. Stratified result narrowed the range to 44–64% E1 (§3) — real improvement, not a full fix (§9).
- **Homology validation:** GraphPart's own self-report (`graphpart_splits_report.json`) is used directly as the cross-fold homology validation, rather than re-implementing pairwise alignment independently — GraphPart's job *is* computing this distance. The final removal round converges to **`Connectivity: 0, #Problematics: 0`** across all 63 rounds of its iterative removal procedure — zero residual cross-partition homology violations at the 40% threshold under the `full` denominator. Verified by `tests/c2_pu/test_fr1_cluster_split_acceptance.py::test_graphpart_converged_with_zero_residual_homology_violations`.
- Result: **834 of 925 retained (91 excluded, 9.8%)**, fold sizes 124/134/137/173/266. Every excluded sequence is named individually with its evidence tier in `graphpart_excluded_for_homology.csv` — never silently dropped or back-filled into a fold.

## 7. Technical acceptance (automated)

All of the following were re-verified on 2026-10-14 against the **full** artifacts, not samples (AGENTS.md validation rule #1), via `pytest tests/c2_pu` (55 tests, all passing):

| AGENTS.md validation requirement | Status | Evidence |
|---|---|---|
| 1. Automated check on the full artifact | ✅ Pass | `test_fr1_acceptance.py`, `test_fr1_cluster_split_acceptance.py`, `test_fr1_provenance_acceptance.py` run against complete files |
| 2. Manual spot-check beyond automated filters | ⚠️ Partial | Chain-of-custody and schema checks are automated and complete; a human spot-read of a fresh random sample of the 179 conflicts / 553 E2 records has **not** been done — deferred to supervisor review (§9), not silently skipped |
| 3. Reproducibility: same inputs → same output | ✅ Pass | `test_fr1_reproducibility.py` re-runs the full pipeline live and diffs SHA-256 hashes + GraphPart's self-report (minus wall-clock timing fields) — byte-identical |
| 4. Leakage checks pass or are documented exceptions | ✅ Pass | GraphPart converges to zero residual homology violations (§6); conflict/control sequences confirmed absent from the final pool by identity, not just ID |
| 5. Provenance log updated in the same change | ✅ Pass | `fr1_positive_pool_provenance.jsonl` (append-only) + this report + `IMPLEMENTATION_STATUS.md`, same session |
| 6. Stopping rule for iterative quality work | N/A | This rule targets iterative keyword-filter rounds (C1/FR2); FR1's pipeline is deterministic merge/threshold logic, not iterative filtering |

**No stochastic steps exist in Buckets 1.1–1.6** (worth stating explicitly, since the pipeline logs `seed=42` for interface consistency with FR2's C1 sampling but doesn't actually use it): positive-pool merge and conflict resolution are deterministic threshold logic; CD-HIT's greedy clustering and GraphPart's `slow-nn` partitioning are both seed-free. "Reproducibility" here means *same inputs → byte-identical outputs*, verified directly (§7, row 3), not *same seed → same random sample*.

## 8. Frozen baseline: `pp1_baseline_v1`

Snapshotted under `data/processed/c2_pu/frozen/pp1_baseline_v1/`, with a checksummed `MANIFEST.json` recording tool versions, CLI configuration, counts, and a SHA-256 per file (`curation/freeze.py`). Per AGENTS.md rule #4, this directory is not to be regenerated or mutated in place — a genuine future change (e.g., resolving the 179 conflicts) gets a new version ID (e.g. `pp1_baseline_v2`), logged with a reason for superseding this one. `tests/c2_pu/test_fr1_freeze_acceptance.py` re-verifies every checksum and is the tripwire against accidental drift.

## 9. Documented limitations (technical, not blocking)

1. **179 cross-source conflicts** (Multi-AOP positive vs. AnOxPePred assay-inactive) excluded from both the positive pool and the external control — logged in full in `label_conflicts_anox_vs_multiaop.csv`, pending manual/supervisor review.
2. **553 of 1,205 positives (post-length-filter: 535) are E2 "provisional"** — Multi-AOP-only, no per-record assay metadata, `assay_verified="unknown"` — pending supervisor review, promotable to E1 if primary-source assay evidence is later recovered.
3. **91 of 925 CD-HIT representatives (9.8%) were excluded by GraphPart** to resolve cross-fold homology violations at the 40% threshold — named individually in `graphpart_excluded_for_homology.csv`, not usable in the 5-fold CV framework at all.
4. **Residual fold-4 evidence-tier imbalance** (64% E1 vs. 44–52% in other folds) persists even after label stratification — a documented trade-off (fold-size uniformity vs. tier-balance uniformity), not a silently-accepted defect.

None of these block continued FR2/FR3 development on this baseline. All four must be named explicitly wherever this dataset's results are reported (AGENTS.md rule #3).

## 10. Pending supervisor approvals (kept separate from technical acceptance)

Technical acceptance (§7) is **not** scientific sign-off. The following require a human decision this report cannot make on its own:

1. **Conflict-resolution policy** (§6, item 1 in the decision log, 2026-10-14): assay evidence overriding Multi-AOP's label for the 179 conflicted sequences.
2. **E2 provisional-tier default** (decision log, 2026-10-14): treating all 553 Multi-AOP-only positives as E2 rather than seeking additional primary-source verification first.
3. **C1 source ambiguity** (SwissProt vs. UniRef50, `PU_AOP_RESEARCH_CONTEXT.md` §4) — not FR1 scope, but still open and relevant to the overall PP1 submission.
4. **Bucket 1.1/1.2 formal data registry** (§4): no `data_registry.csv` exists yet; the checksums in this report are a stopgap, not the registry artifact itself. Recommend scheduling this separately from the FR1 freeze.

---
*Generated 2026-10-14 against commit `02d0324365729684a401e147907561bd6f417ec6`. Re-run `pytest tests/c2_pu` to reverify any claim in this report.*
