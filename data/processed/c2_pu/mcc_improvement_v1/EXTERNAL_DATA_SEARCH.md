# Independent external-data search

Search date: 19 October 2026 (Asia/Colombo). Search queries included:

- antioxidant peptide prediction experimentally validated inactive peptides dataset independent AnOxPePred 2024 2025
- antioxidant peptides synthetic inactive DPPH ABTS assay supplementary dataset 2024 peptides
- RLAnOxPeptide DPPH IC50; Bangia fuscopurpurea Table 2

This is a candidate search, not a newly validated dataset. No observations were
added to training, validation, controls or metrics. No restricted data were obtained.

## Sources and disposition

1. [Original AnOxPePred study](https://www.nature.com/articles/s41598-020-78319-w)
   describes different FRS and chelation endpoints. This is the historical control
   source and cannot supply a pristine independent test by resampling its records.
2. [Multi-AOP](https://pmc.ncbi.nlm.nih.gov/articles/PMC12864603/) describes reused
   AnOxPePred controls and synthetic/random sequences in benchmark populations.
   These do not provide new assay-confirmed inactive observations for this project.
3. [AOP-DRL](https://pmc.ncbi.nlm.nih.gov/articles/PMC12800373/) attributes benchmark
   construction to AnOxPePred. Independence from project inputs is not established;
   counts and negative provenance require source-level verification before reuse.
4. [RLAnOxPeptide, Bioinformatics 2026](https://academic.oup.com/bioinformatics/article/42/7/btag504/8728787)
   is a promising **new experimental** lead (17 synthesized peptides, chemical and
   cellular assays). Its training set's UniProt filtering does not create confirmed
   negatives. Published activity summaries do not establish a defensible binary
   inactive panel; source supplementary measurements and assay definitions need
   review. No arbitrary activity cutoff is introduced here.
5. [Bangia fuscopurpurea synthetic peptides, Foods 2025](https://www.mdpi.com/2304-8158/14/24/4220)
   reports sequence-specific DPPH/ABTS/OH measurements at stated concentrations.
   This is an assay-data lead, not automatically an inactive classification set.
   Full table retrieval was rate-limited; PMC retrieval presented a browser check.
6. [Goat-milk short-peptide activity modeling](https://www.sciencedirect.com/science/article/pii/S0022030224009706)
   describes ABTS collections and removal of inactive observations before modeling.
   The omitted measurements in supplementary data may merit audit; full text was
   blocked by HTTP403. Their assay support, identities and independence remain unverified.

Search-index excerpts were accessible for these leads, while several full pages
or supplementary tables were inaccessible. Search results are insufficient for
label assignment or dataset acceptance. No authenticated access or bypass was used.

## Acquisition gate for future research

Obtain complete sequence-specific raw measurements, assay controls/LOD, dose,
mechanism, confidence/replicates and publication provenance. Define an assay-matched
endpoint before scoring; distinguish inactivity from absent measurement. Check exact
and homologous overlap against all positive and unlabeled sources, including the
179 disputed historical records. Freeze the independent panel and model/thresholds
before a single evaluation. Until then independent MCC improvement is unverified.

## PU-method reference

[Kiryo et al., NeurIPS 2017](https://proceedings.neurips.cc/paper_files/paper/2017/hash/7cce53cf90577442771720a370c3c723-Abstract.html)
motivates nonnegative empirical risk to reduce PU overfitting. Its assumptions do
not establish that project C1 sampling is a representative biological mixture or
that the provisional prior is correct. Retaining corrective gradients cannot by
itself fix dataset/assay mismatch.
