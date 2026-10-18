# Component 4 Validation and Acceptance

This checklist defines evidence required before marking work complete. Passing a test demonstrates only the property tested; it does not establish biological activity or research hypotheses.

## FR1 — Candidate generation

- [ ] Four inputs have verified UniProt provenance, release/query, reviewed status, checksums, record counts, and exclusion logs.
- [ ] Protein minimum length and standard-residue filters are implemented and counts are recorded per plant.
- [ ] Sequential pepsin → trypsin behavior, cleavage rules, pH interpretation, and missed-cleavage setting are documented; toy-sequence unit cases have hand-checkable expected fragments.
- [ ] Rule-based digestion deviation from BIOPEP-UWM is explicit; comparison spot-check is attached if performed.
- [ ] Candidate length is 3–20 AA, alphabet is standard, and at least two residue types are present.
- [ ] Every candidate is traceable to parent accession, coordinates, plant, and enzyme path; exact deduplication loses no source provenance.
- [ ] Descriptor calculations are finite and validated for representative sequences.
- [ ] Per-plant and combined outputs, candidate FASTA, funnel, and full-output checks are present; fixed-seed rerun reproduces IDs/counts/content.
- [ ] Candidate FASTA handoff to C1/C2 is recorded.

## FR2 — Embedding and applicability domain

- [ ] C1 confirms the ESM-2 model/layer/pooling recipe; model weights and software environment are identified.
- [ ] Embedding manifest and ID map prove row alignment, N×1280 shape, finite values, declared dtype, and stable rerun behavior.
- [ ] Reference-cloud source, evidence tier, version, and sequence IDs are documented and labelled provisional if applicable.
- [ ] Reference/calibration set is disjoint from the held-out set; fitting uses only the permitted reference/training data.
- [ ] Exact centroid, distance, calibration mean/std, and tier formulas are frozen in a versioned parameter artifact.
- [ ] Full candidate table is tiered, with per-plant histograms and diagnostics reviewed; nondegeneracy is investigated rather than cosmetically tuned.
- [ ] Threshold sensitivity outputs are retained if reported.

## FR3 — PDSS (stretch)

- [ ] The denominator, near-zero guard, baseline set, aggregation, and sensitivity analysis are pre-specified.
- [ ] PDSS is computed from frozen AD outputs, with per-plant counts and uncertainty/limitations.
- [ ] Kruskal-Wallis/Spearman analyses include assumptions, sample size, effect size, and the low-power limitation of four proteome-level observations.
- [ ] Values from a provisional cloud are labelled preliminary and are not presented as validated domain-shift findings.

## FR4 — Signal integration and combined score

- [ ] C1/C2 schema versions, score semantics/ranges, candidate coverage, model provenance, and missingness are validated.
- [ ] Joins are checked for duplicate/missing candidate IDs; no positional joins.
- [ ] The exact `d_norm` equation, weight defaults, tie behavior, and score range are recorded.
- [ ] Unit cases prove Tier 3 receives exactly zero regardless of upstream signals and Tier 1/2 use the declared equation.
- [ ] Dummy values are marked in every record, report, and view and are never used for retrieval claims.

## FR5/FR6 — Later evaluation milestones

- [ ] External predictor versions and top-50/tie/failure handling are recorded before reporting ARR.
- [ ] Held-out known plant AOPs have source and evidence records and are homology-filtered against C1/C2 training data and the reference cloud.
- [ ] Positive matching, candidate universe, Recall@K denominator, MRR query unit, EF@1% cutoff, and PARRS undefined/zero-denominator behavior are fixed before computing results.
- [ ] Metrics are computed on full final outputs, with numerator/denominator, per-plant counts, and uncertainty where appropriate.
- [ ] Statistical tests, directional hypotheses, multiplicity handling, effect sizes, and limitations are stated; no significance claim rests on dummy data.

## FR7 — Evidence cards

- [ ] Schema includes stable candidate ID, sequence, complete provenance, descriptors, signal values and sources, AD distance/tier, score/rank, BCS context, and run/config IDs.
- [ ] GREEN/AMBER/RED mapping matches frozen tier rules; RED communicates abstention.
- [ ] BCS is presented as predictor-level reliability context; threshold policy is confirmed with C3.
- [ ] Provisional-cloud and dummy-signal states are visible in machine-readable and human-readable outputs.
- [ ] Representative cards are checked for internal consistency against their source tables.

## Reproducibility and release

- [ ] Seeds, configs, input hashes, code revision, environment lock, model weights, and output hashes are recorded.
- [ ] Re-run from frozen inputs reproduces deterministic artifacts or documents the source of permitted numeric variation.
- [ ] PP1 freeze manifest and report distinguish verified results, provisional results, and planned work.
- [ ] Status inventory and deployment-progress page are updated together; a task is Done only when its acceptance evidence is linked.

## Current acceptance state

No FR1–FR7 acceptance checklist above is evidenced as passed in the current repository snapshot. The existing `tests/c4_screen/check_gpu.py` only prints PyTorch and CUDA availability and is not itself evidence that C4 dependencies, model weights, or pipeline stages work.
