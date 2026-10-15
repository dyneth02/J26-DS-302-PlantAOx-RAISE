# PU-AOP Research Context (Component 02 — PlantAOx-RAISE)

**Last updated:** 14 October 2026
**Audience:** Any AI coding agent (Claude Code, Codex) or human picking up this component cold.
**Purpose:** Explain *what this component is, why decisions were made the way they were, and what has actually been done so far* — so work doesn't need to be re-derived or accidentally redone differently each session.

This file is background/knowledge. For live task status see `IMPLEMENTATION_STATUS.md`. For standing rules an agent must follow, see `AGENTS.md`.

---

## 1. What this component is

**Component 02 — PU-AOP**: Evidence-Tiered Positive-Unlabeled Curriculum Classifier with a Random-Negative Inflation Audit, part of the larger **PlantAOx-RAISE** system (4 components total; this doc only covers Component 02).

The core research problem: predicting whether a peptide has antioxidant activity, under **Positive-Unlabeled (PU) learning** — we have confirmed positives, but no confirmed negatives. "Negative-looking" pools (C1/C2/C3, see below) are *assumed* non-antioxidant, not *proven* non-antioxidant. This distinction is the single most important modeling constraint in this component — see `AGENTS.md` for the hard rule around it.

## 2. Functional requirements map

| Req | What it means | Status |
|---|---|---|
| **FR1** | Evidence-tiered (E1/E2/E3) positive pool: merge Multi-AOP + AnOxPePred, CD-HIT 90% dedup, GraphPart 40% homology-safe split, target 500–800 final positives (SO1 stretch ≥800) | **Not started** |
| **FR2** | Three unlabeled "challenge" pools: C1 (5,000 random decoys), C2 (~2,000 non-AOP bioactive), C3 (2,000 ESM-2-nearest hard negatives) | **C1 in progress (pipeline built, full-file validation pending)**; C2/C3 not started |
| **FR3** | Baselines: PN, nnPU, Two-Step PU, PU-Bagging on fused ESM-2 + 15-descriptor features | Not started |
| **FR4** | Curriculum nnPU: C1 → C2 → C3 staged training, plateau transition (patience 5), label weights E1=1.0 / E2=0.5 | Not started (optional stretch) |
| **FR5** | Hypothesis testing, ablations, sensitivity analysis | Later milestone (PP2+) |
| **FR6** | RNIS = MCC(C1 test) − MCC(C3 test), plus audits | Later milestone (PP2+) |
| **FR7** | Calibration report + frozen model / PROB_C2 handoff to Components 3/4 | Later milestone (PP2+) |

**PP1 mandatory scope: FR1 + FR2 only.** FR3 is stretch. Do not let an agent "helpfully" start FR3/FR4/FR5 work before FR1/FR2 are frozen and accepted — see the decision gate in `IMPLEMENTATION_STATUS.md`.

## 3. Source datasets (what, where, why)

| Dataset | Used for | Source | Notes |
|---|---|---|---|
| **Multi-AOP** | Positive pool (FR1) | `github.com/CaiJianxiu/Multi-AOP` | Unified AOP benchmark. Use its positives only — ignore its own negative labels; we build our own C1/C2/C3 instead. |
| **AnOxPePred** | Positive pool (FR1) + external inactive control | `github.com/dtu-pas/AnOxPePred` | Also contains a small set of **experimentally tested inactive** peptides — rare gold-standard data. Keep this set completely separate from C1/C2/C3; it's an independent negative-control evaluation set, not training data. |
| **UniProtKB (reviewed)** | C1 random decoys (FR2) | `rest.uniprot.org/uniprotkb/stream` | See §4 — this is a deliberate, documented deviation from the proposal's looser wording. |
| **Peptipedia** | C2 bioactive-unlabeled pool (FR2) | — | Source of non-antioxidant-annotated bioactive peptides (antimicrobial, antihypertensive, etc.). Not yet acquired. |
| **AODB, DFBP, BIOPEP-UWM** | Contamination/exclusion checks for C2/C3 | — | Used to screen OUT any known-AOP entries from the unlabeled pools. Not yet integrated. |
| **ESM-2 (`esm2_t12_35M_UR50D`)** | Feature pipeline + C3 construction | — | Needed for embeddings before C3 (hard-challenge) selection and before the fused feature cache can be built. Not yet set up. |

## 4. Decision already made: C1 source = UniProtKB `reviewed:true`, not raw UniRef50

The proposal document is internally inconsistent: FR2/SO2 say C1 should be **"random SwissProt decoys,"** while methodology section 3.2.2 says **"sampled from UniRef50."** These are different databases (SwissProt = reviewed UniProtKB only; UniRef50 = all reviewed + unreviewed, clustered at 50% identity).

**Resolution adopted:** use UniProtKB directly with `reviewed:true` (= SwissProt), not UniRef50 clusters. Rationale:
- Matches the more specific FR2/SO2 wording.
- UniRef50's bulk FASTA is ~13GB compressed — unnecessary when we only need a few thousand short, reviewed, non-bioactive fragments.
- UniProtKB's REST API supports direct keyword-based exclusion (`NOT keyword:Toxin` etc.), which UniRef's endpoint does **not** support (its `reviewed` field doesn't exist there — confirmed by a live 400 error during implementation).

**This should be flagged to supervisors for formal sign-off** (see `IMPLEMENTATION_STATUS.md` open risks) but is the working assumption for all current and future C1-related code.

## 5. C1 pipeline — what's actually been built so far

A working Colab/Python pipeline exists with this shape:

1. **Query-level filter** (UniProtKB REST, `format=fasta`):
   ```
   reviewed:true AND length:[3 TO 50]
   NOT keyword:Toxin NOT keyword:Hormone NOT keyword:Neuropeptide
   NOT keyword:Antimicrobial NOT keyword:Antibiotic NOT keyword:Antioxidant
   NOT keyword:"Amphibian defense peptide"
   ```
2. **Secondary Python keyword blocklist** (string-match on `record.description.lower()`), because UniProt's own keyword tagging has real coverage gaps across species records (see §6). Current list (keep this as the canonical version — do not regenerate from scratch, extend it):
   ```python
   BIOACTIVITY_KEYWORDS = [kw.lower() for kw in [
       "antioxidant", "antimicrobial", "antihypertensive", "antifungal",
       "anticancer", "anti-inflammatory", "bioactive", "antibacterial",
       "antiviral", "chelat", "toxin", "venom", "neurotoxin", "hormone",
       "neuropeptide", "inhibitor", "lectin", "defensin", "cecropin",
       "magainin", "temporin", "contryphan", "conotoxin", "kinin",
       "tachykinin", "allatotropin", "allatostatin", "tropin",
       "cyclotide", "cupiennin", "signiferin", "tryptophyllin",
       "formaecin", "corazonin", "ampulexin", "myosuppressin",
       "fmrfamide", "antimicrobial peptide", "amp",
       "superoxide dismutase", "peroxidase", "catalase",
       "glutathione", "thioredoxin", "ferredoxin reductase",
       "metallothionein"
   ]]
   ```
   **Important:** the list must be lowercased (either by typing lowercase or via the comprehension above). A real bug was hit mid-development where an item was added with a capital letter and silently never matched — `desc.lower()` lowercases the description but not the keyword, so case mismatches fail silently with no error. Any future addition to this list must go through the same lowercasing path.
3. **Deterministic sampling**: `random.seed(42)`, then `random.sample(candidates, 5000)`.
4. **Provenance logging**: a `stage_c1_provenance.txt` file records the query, candidate counts at each filter stage, final sampled count, and seed.

As of last run: query-level filter → 8,830 candidates; after secondary Python filter → 8,233; final sample → 5,000 (seed 42).

## 6. Confirmed contamination categories (why the blocklist looks the way it does)

Six rounds of manual spot-checking (25-record random previews from the sampled set) caught real contamination that automated filtering alone missed. Each category below is now in the blocklist, but **the underlying lesson matters more than the specific words**: UniProt's keyword annotation coverage is incomplete per-species, so name-based and keyword-based filtering will never be 100% complete.

- **Toxins/venoms** named by family, not the word "toxin" (contryphan, lycotoxin, stichotoxin)
- **Neuropeptide hormones** named by family (periviscerokinin, allatotropin, corazonin, myosuppressin, FMRFamide)
- **Antimicrobial peptides** named by family, not "antimicrobial" (temporin, cupiennin, cyclotide, signiferin, tryptophyllin, formaecin) — frog/toad skin peptides are a recurring offender class
- **Antioxidant enzymes** that don't contain the word "antioxidant" (Superoxide dismutase, Peroxidase, Metallothionein — the last one is debated in the literature but documented enough to exclude)
- **Fungal/yeast mating pheromones** (Rhodotorucin-A, Schizophyllum BAP1) — genuinely bioactive signaling molecules, lower-severity but worth excluding

**Lower-priority borderline cases intentionally left in** (judgment call, not a defect): Fibrinogen chains, alpha-amylase, omega-gliadin, Ovostatin, auxin-responsive plant peptides. These have *some* biological function but don't compete with the antioxidant/toxin/hormone/AMP categories this experiment is specifically distinguishing.

## 7. Known, accepted limitation (put this in the FR2 report, don't hide it)

No keyword-based filter (API-level or string-level) can achieve 100% purity against a database this large, because UniProt's own curator annotation coverage varies by species and record age. The agreed approach: document this explicitly in the FR2 acceptance report, e.g.:

> "Automated keyword-based filtering was applied at both the UniProtKB query level and a secondary Python string-match level to exclude known bioactive protein families (toxins, hormones, neuropeptides, antimicrobial peptides, antioxidant enzymes) from the Stage C1 pool. Six rounds of manual spot-checking against random 25-record samples were used to iteratively expand filter coverage. Residual annotation gaps in UniProt's species-level curation mean a small number of functionally active sequences may remain unflagged in the final 5,000-record pool. This is a known and accepted limitation, not an unaddressed defect."

This is the expected, academically normal thing to say — do not let an agent try to "achieve perfect filtering" as an open-ended task. See `AGENTS.md` for the explicit stopping rule.

## 8. Outstanding validation gap — do not skip this

**Every spot-check performed so far has been on a 25-record reduced sample, never the full 5,000-record file.** Before FR2/C1 can be marked complete, someone (human or agent) must:
- Run the blocklist check against the **full** `stage_c1_decoys.fasta` (not a preview), and report the count of any remaining flagged terms.
- Confirm the file actually contains exactly 5,000 unique records, all length 3–50 AA, all `reviewed:true` sourced.
- Re-run the pipeline end-to-end from the raw UniProtKB query to confirm reproducibility (same seed → same 5,000 records).

## 9. Not yet started (full list)

- Positive pool acquisition/merge/tiering (Multi-AOP + AnOxPePred) — Bucket 1 (FR1), all of it
- CD-HIT clustering, GraphPart splitting
- C2 (Peptipedia bioactive-unlabeled pool)
- C3 (ESM-2 hard-challenge pool) — blocked on ESM-2 setup
- Pool contamination/leakage audit across C1/C2/C3 and the positive pool (Bucket 2.4)
- Feature pipeline (descriptors + ESM-2 + fusion + cache) — Bucket 3
- All model baselines — Bucket 4
