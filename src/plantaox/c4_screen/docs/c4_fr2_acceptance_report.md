# C4 FR2 Embedding and AD Acceptance

**Status:** PASS against MOCK cloud; real cloud sequence handoff is pending Colab embeddings.

- Candidate handoff: 152,259 × 1,280, finite; row order and newline-joined sequence SHA-256 validated against manifest.
- Cloud: 500 sequences, `source=mock_cloud`; not biological evidence.
- Parameters: mu=0.0185099002, sigma=0.0097886926, t1=0.0282985928, t2=0.0380872854; population SD, leave-one-out centroid calibration.
- Tier coverage: 152,259/152,259. Tier fractions/length bins and sensitivity: `PP1_NUMBERS.md`.
- Rice cached tiering timing: 18.562604 s. Thresholds were not tuned.
- Real-cloud staging: `data/interim/c4_screen/embeddings_staging/ref_cloud_sequences_real.csv`, N=912; embed in Colab before any production replacement.
