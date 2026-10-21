# Source-bias and assay-mismatch analysis

This analysis is exploratory. Dataset membership can be predicted from sequence
features; this does not prove that any single feature causes biological failure.

## Source contrast

A diagnostic logistic classifier predicts FR1-vs-C1 dataset membership, with
class-balanced loss, on fold0 optimization positives and C1 training rows. It fits
no assay-inactive controls and uses training-positive-only feature scaling. Inner
GraphPart positives and disjoint C1 validation rows assess the source contrast.
These membership labels are observed dataset origins, **not antioxidant labels**.

Validation source-membership AUROC is 0.9699 using length alone, 0.9691 using 15
descriptors and 0.9694 using ESM embeddings. The length-only classifier assigns
median FR1 support 0.9266 to held-out positives and 0.9686 to controls; ESM yields
0.9448 and 0.9962. Source discrimination is therefore easy, and controls look
positive-source-like to these contrasts. This supports a shortcut interpretation
but does not isolate model mechanisms or show causation.

Raw descriptor comparison uses 576 optimization positives, 134 inner-validation
positives, 124 held-out positives and 38 controls. Training/control means differ:
length 7.90/4.79 residues (KS=.352), molecular weight 912.69/587.55 (KS=.354),
hydrophobic moment .341/.481 (KS=.283). Exploratory tests, rank effects and BH
adjustments for all 15 descriptors are in descriptor_shift_statistics.csv.
All amino-acid fractions are compared in amino_acid_composition.csv.

Training-positive-fitted ESM PCA and nearest-neighbor distances show overlapping
positive/control feature regions, while C1 is farther from positives. Median
nearest-training distance is 14.48 for held-out positives, 15.64 for controls,
22.80 for C1 and 18.28 for C2 in standardized ESM space. These distances depend
on the representation/scaling and are not biological uncertainty or OOD guarantees.
PCA is descriptive, not a proof of separability or activity.

## Matching and families

Length and 15-descriptor matching use unique minimum-cost assignments of 38 held-out
positives to all 38 controls; no difficult control is removed. The full 124/38 set
remains primary. Membership and distances are saved; no causal balance claim is
made. matched_and_conflict_sensitivity.json retains both matched analyses plus the
36-control conflict-exclusion sensitivity alongside full results.

control_publication_errors.csv reports errors for each recorded control DOI and
method across repeated folds/seeds. selected_consistent_errors.csv identifies
peptides consistently misclassified. DOI repetition and sequence families create
dependence: per-peptide bootstrap intervals do not account for all of it. There is
no harmonized family/source registry for all positive records, so a causal
family-effect decomposition or source-held-out biological validation is not
identifiable here. Existing GraphPart outer and inner folds mitigate sequence
homology leakage; accepted C1/C2 near-duplicate limitations remain documented.

## Assay labels and applicability

The 38 controls have recorded inactive status under their source assays, not
universal inactivity. FCM and YPQLLPNE retain cross-database conflicts. E1 assay
support and E2 provisional benchmark annotations are analyzed separately in
evidence_tier_evaluations.json. Control DOI provenance is retained, but matched
concentration, mechanism, substrate and assay conditions are not available for
every positive/control pair. We cannot separate assay mismatch from dataset/source
effects using these observations alone.

Training-only source reweighting cannot create missing short assay-inactive
observations or verify C1 specificity. No controls were reweighted during training.
The prospectively described C1+C2 unlabeled follow-up tests a broader source
mixture while preserving PU semantics; its unmeasured mixture prior remains an
assumption. No C3 training was attempted because the accepted centroid selection
uses all non-outer-fold positives, including the stricter inner validation fold.
Using those challenges for optimization would violate this study's inner boundary.
Its accepted fold-specific 2,000-row selection is used only descriptively.

New independent assay-matched controls remain the key missing evidence. Candidate
literature leads and access limitations are recorded in ../EXTERNAL_DATA_SEARCH.md.
