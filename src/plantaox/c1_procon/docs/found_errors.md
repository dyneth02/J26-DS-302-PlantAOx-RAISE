# found_errors.md — AOP-ProCon (Component 01), consolidated register (rebuilt 2026-10-18)

**Project:** J26-DS-302 · PlantAOx-RAISE · Component 01 **Owner:** Fernando W A A T (IT23144408)
**What this file is:** one line per defect found since 2026-09-01, with its **current** status against the corrected pipeline (S2 v3, fingerprint `47d9c2a2fff63eb1`, Steps 1–8). The long S1-era write-ups (evidence, code, viva answers for E-001 … N-15) are in the old `C1/found_errors.md`; this file does not repeat them, it says what became of each item.

**Severity:** 🔴 high · 🟡 medium · 🟢 low  **Status:** `FIXED` (in a notebook / verified) · `SUPERSEDED` (belonged to the S1 pipeline) · `ACCEPTED` (kept, reported) · `OPEN` · `WITHDRAWN`

---

## A. Summary table

### A1. First audit (S1 era, 2026-09-01)
| ID | Issue | Sev | Status | Resolved by |
|---|---|---|---|---|
| E-001 | 25 sequences in both folds (cross-fold leakage) | 🔴 | **FIXED** | S2 = one row per sequence; union-find homology groups; Step 1 asserts no sequence / `cluster_40` / `homology_group` spans folds; Step 5 re-asserts |
| E-002 | Tier-2 prototype dominated by dual peptides | 🔴 | **SUPERSEDED** | A dual peptide is a legitimate member of both classes in S2 (design, not a bug) |
| E-003 | Cross-tier overlap (66 sequences) | 🟡 | **FIXED** | explicit multi-label `FRS;MC` (86 in S2) |
| E-004 | Single-label relevance penalised dual peptides | 🟡 | **FIXED** | Step 5 uses MC-active as the target; FRS retrieval shown to be saturated |
| E-005 | `descriptors.csv` duplicate rows | 🟢 | **FIXED** | Step 2 asserts unique sequences and equality with S2 |
| E-006 | Labels are two binary attributes, not two classes | 🔴 | **FIXED** | the whole S2 design (`FRS`, `MC`, `FRS;MC`, `GEN`) |
| E-007 | λ 0.1 (TAF/deck) vs 5.0 (code); τ 0.07 vs 0.2 | 🔴 | **ACCEPTED, OPEN in documents** | Step 4 §2a documents the deviation and the sweep that shows the TAF recipe collapses; TAF / proposal text must be updated |
| E-008 | FRS/MC separation under-measured | 🔴 | **FIXED** | probe = MC-active vs FRS-only |
| E-009 | No chance floor for Recall@K | 🔴 | **FIXED** | exact chance Recall@K and permutation AP in Step 5 |
| E-010 | Trained models worse than raw ESM-2 | 🔴 | **CONFIRMED** | Step 5: 10/10 worse; Step 6: 0/25 above |
| E-011 | Conclusion cell contradicted its own table | 🔴 | **FIXED** | Step 5 conclusions are generated from the tables |
| E-012 | HP5 (150M vs 650M) driven by a leak | 🟡 | **FIXED** | HP5 re-tested on grouped probe + Step 6 scale sweep: not supported |
| E-013 | ARI-checkpoint mode not reproducible | 🟡 | **ACCEPTED** | kept as a documented ablation (fixed seeds in v3) |
| E-014 | Step 4 overwrote Step 3's pair file | 🟢 | **FIXED** | Step 4 reads Step 3 files and checks their SHA-256 |

### A2. Documents (deck / proposal)
| ID | Issue | Sev | Status |
|---|---|---|---|
| D-001 | Deck / TAF references and typos | 🟢 | OPEN (documents, not notebooks) |
| D-002 | Final deck: slide numbers in speech wrong + 6 errors | 🔴 | OPEN |
| D-003 | 4 proposal references with fabricated bibliographic details | 🔴 | **FIXED** (proposal v8) |
| D-004 | "Leave-source-out" name vs the real split (homology-grouped 2-fold) + 3 TAF/code mismatches | 🟡 | OPEN in TAF text; Step 1 manifest already states `split_type` honestly. Use the name "homology-grouped 2-fold split" |

### A3. Second audit (S2 era, 2026-10-08 → 2026-10-16)
| ID | Issue | Sev | Status | Resolved by |
|---|---|---|---|---|
| N-1 | S2 relevance rule made 91.7 % of queries uninformative | 🔴 | **FIXED** | Step 5 v3 evaluates MC retrieval only, with exact chance |
| N-2 | Pairing/backbone decomposition cell undefined (−150 % / 250 %) | 🔴 | **SUPERSEDED** | cell removed in the Step 5 rewrite; pairing and backbone compared as paired ΔAP |
| N-3 | HP2 "not significant" was actually harmful | 🟠 | **RE-MEASURED** | Step 5 v3: fusion vs ESM-only ΔAP +0.013, but both below untrained ESM-2; reported as "not supported in any useful sense" |
| N-4 | "flat plateau" claim false for 1 of 8 models | 🟠 | **FIXED** | Step 4 v3 reports 0 of 15 models hold a plateau; claim removed |
| N-5 | FRS ≈ GEN prototypes identical after the anti-collapse fix | 🟡 | **ACCEPTED** | reported as descriptive (GEN is a mixed pool the loss never separates) |
| N-6 | Two `help_thesis` versions, §§1–11 superseded but still current-looking | 🟡 | **FIXED** | new `help_thesis.md` (this folder) |
| N-7 | `sample_weight` sensitivity changes queries, not the gallery | 🟢 | **SUPERSEDED** | analysis not part of Step 5 v3 |
| N-8 | "V2 Step 3 still S1" | ⚪ | **WITHDRAWN** | rejected by the Drive data |
| N-9 | Primary-150M trained on k-NN pairs (HP5 confounded) | 🔴 | **FIXED** | Step 4 v3 has Primary-150M (percentile pairs) **and** k-NN-150M |
| N-10 | `min_proto_dist` guard evaluated before GEN was recomputed | 🔴 | **FIXED** | Step 4 §2b: distance measured on the tensors that are saved (`min_proto_dist_saved`) |
| N-11 | "STEP02 cannot build V2 embeddings" | ⚪ | **WITHDRAWN** | artifacts were right; notebook was stale (N-12) |
| N-12 | `C1_10.06` STEP02/03 stale copies | 🟠 | **FIXED** | the `FIXED_V2` notebooks are the ones that produced the Drive data |
| N-13 | Step 1 downloads DFBP from the live web archive → not deterministic | 🟠 | **OPEN (mitigated)** | S2 data frozen and fingerprint-checked; **never re-run Step 1 end to end** |
| N-14 | `BASE_RAW` undefined in Step 1 | 🟠 | **FIXED** | single `BASE` in Step 1 FINAL |
| N-15 | HP1 random control shares 9.5 % of pairs with the treatment; re-running Step 3 invalidates HP1-Random | 🟢 | **ACCEPTED** | documented; fixed-seed, count-matched control; **do not re-run Step 3** |
| N-16 | `_real/results` were 12-epoch local runs | 🟡 | **FIXED** | full Colab runs of Steps 4–6 |
| N-17 | Two AUROC values (0.806 / 0.784) for the "same" probe; Step 2 descriptor cell empty in one Colab run | 🟡 | **FIXED (a)** one probe definition in Step 5 v4; **(b)** `descriptors.csv` SHA-256 verified in every notebook, re-check the cell output at the next Step 2 run |

### A4. Third audit (assessment 2026-10-18) and STEP 08
| ID | Issue | Sev | Status | Resolved by |
|---|---|---|---|---|
| N-18 | "Positive-only / no negatives" claim vs loss with uniformity + prototype push-away | 🔴 | **OPEN (wording)** | write: *"no confirmed-negative peptides are used; collapse is controlled by label-free uniformity and prototype repulsion"* |
| N-19 | Source confound: `source_group` alone ≥ ESM-2 probe | 🟡 | **ADDRESSED** | Step 5 v4 baselines + STEP 08; the length numbers in N-19 were wrong (see N-21) |
| N-20 | Collapse guard measures prototypes, not embeddings (held-out mean cos ≈ 0.99) | 🟡 | **ACCEPTED, reported** | Step 5 geometry table; claim "collapse prevented" only at prototype level |
| N-21 | "MC 9.4 aa vs FRS 5.8 aa" wrong in the strict pool | 🟡 | **FIXED** | true means 5.86 vs 5.75; the confound is the **tripeptide share** 16.3 % vs 42.8 % |
| N-22 | Step 5's 0.593 = one `GroupKFold` split, pooled OOF AUROC (biased; 0.59–0.66 across scikit-learn releases) | 🟡 | **FIXED** | Step 5 v4 / Step 7 v4: repeated grouped CV, fold-mean AUROC, own fold code (Colab and local replay identical) |
| N-23 | `RANDOM noise` row 0.376–0.384 is one low draw, not chance; bootstrap CIs hold the model fixed | 🟢 | **FIXED** | 20-seed null band 0.511 [0.430, 0.567]; CI limitation stated |

### A5. New items from this session (2026-10-18, late)
| ID | Issue | Sev | Status |
|---|---|---|---|
| N-24 | The new-approach exploratory results (domain-feature probe, SupCon, tripeptide task) were **not** source-controlled; absolute AUROCs partly reflect source | 🟡 | **OPEN** — shown with a warning in the frontend; only paired comparisons are informative; re-run with SOURCE as baseline if used in the paper |
| N-25 | `extended` mode is the most source-confounded: SOURCE alone 0.747 vs ESM-2 650M 0.671 (54 of 63 MC peptides are external literature) | 🟡 | **OPEN (documented)** — do not quote extended-mode probe numbers as mechanism evidence |
| N-26 | An explanation that "ESM-2 learned length" for the AnOxPePred-only gain is **not tested** (size-matched control only partly agrees) | 🟢 | **OPEN** — wording rule: say "the gain disappears under length matching", not "ESM-2 learns length" |
| N-27 | Stale numbers outside the notebooks: PP1 slides, `progress_log` HTML, prototype `C1Page.tsx` + `artifacts/c1/*.json`, `C1_Assessment_2026-10-18.md` (9.4 vs 5.8 aa), old `README` headline (0.593) | 🔴 | **OPEN** (README / CONTRACT / frontend already corrected) |
| N-28 | Step 8 uses scikit-learn's `StratifiedGroupKFold`; Step 5 v4 uses its own fold code → same feature set differs by ≤ 0.02 between them (ESM-2 650M 0.601 vs 0.606) | 🟢 | **ACCEPTED** — noted in the frontend; conclusions identical |

---

## B. Items that still need action (checklist)
- [ ] **N-18** change the "positive-only" wording in TAF / slides / thesis.
- [ ] **E-007 / D-004** update TAF text: τ 0.2, λ 5.0, "homology-grouped 2-fold split".
- [ ] **N-27** update PP1 slides, progress HTML, prototype JSON, assessment text.
- [ ] **N-24 / N-25 / N-26** wording discipline in the thesis (see `help_thesis.md` §6).
- [ ] **N-13 / N-15** never re-run Step 1 / Step 3 in full.

## C. How to use this register in the viva
For any defect: (1) what was wrong, (2) how it was measured, (3) which notebook fixed it, (4) what the corrected number is. The strongest examples: **N-22** (a single split moved AUROC by 0.06 → repeated CV), **N-19 / N-21** (source and tripeptide share explain the signal → confound controls), **N-23** (a "chance" row that was not chance → null band).
