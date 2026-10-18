# PlantAOP-Screen (Component 4)

PlantAOP-Screen is the planned Component 4 of PlantAOx-RAISE. Its research objective is to generate plant digestome peptide candidates, characterize whether they fall within an antioxidant-peptide (AOP) applicability domain, and produce traceable, evidence-backed rankings that can abstain on out-of-domain candidates.

> **Implementation status (19 October 2026):** Gate 1 candidate generation is implemented and was run across the four reviewed UniProt proteomes. The package provides download/registry, sequential digestion, input exclusions, peptide filters, exact-sequence deduplication, provenance, descriptors, deterministic exports, and funnel reporting. The focused suite has five passing tests. ESM-2 embedding, applicability-domain tiers, scoring, evaluation, and cards remain unimplemented. See [PP1 deployment progress](SCREEN_PP1_Deployment_Progress.md) for observed counts and limitations.

## Scope

The four target plants are soybean (*Glycine max*), rice (*Oryza sativa* subsp. *japonica*), rapeseed (*Brassica napus*), and olive (*Olea europaea*). The proposed candidate-generation protocol simulates sequential pepsin then trypsin digestion, retains 3–20 residue peptides with at least two distinct standard amino-acid types, and preserves parent-protein provenance.

The PP1 delivery plan prioritizes:

1. **FR1 — Candidate generation:** reviewed-proteome inputs, digestion, filtering, deduplication, descriptors, and a traceable candidate FASTA/table.
2. **FR2 — Applicability-domain tiering:** ESM-2 embeddings, a labelled reference cloud, cosine-distance diagnostics, and Tier 1/2/3 assignments.
3. **FR4 and FR7 — Dummy-signal integration and evidence cards:** exercise contracts, combined scoring, forced Tier 3 abstention, and cards with conspicuous dummy-signal labels.

PDSS (FR3) is a stretch analysis. ARR (FR5) and held-out retrieval metrics including PARRS (FR6) are later milestones requiring validated predictor inputs and a leakage-controlled evaluation set. Dummy-signal rankings are integration demonstrations, not model performance results.

## Current repository layout

```text
src/plantaox/c4_screen/
  config.yaml                  # Gate 1 defaults and C4-provisional signal thresholds
  digest.py                    # UniProt input handling and pepsin -> trypsin digestion
  filters.py                   # peptide length, alphabet, and composition criteria
  dedup.py                     # exact sequence deduplication and provenance aggregation
  descriptors.py               # Biopython physicochemical descriptors
  run.py                       # download, digest, and all CLI stages
  docs/
    README.md                 # this entry point
    SCREEN_PP1_ARCHITECTURE.md      # component boundaries and planned data flow
    SCREEN_PP1_METHODOLOGY.md       # proposed algorithms, definitions, and caveats
    SCREEN_PP1_DATA_AND_OUTPUTS.md  # input provenance and artifact contracts
    SCREEN_PP1_VALIDATION.md        # acceptance evidence required before claims
    SCREEN_PP1_Task_Inventory.md
    SCREEN_PP1_Deployment_Progress.md
tests/c4_screen/
  test_candidate_generation.py # Gate 1 unit and mock contract tests
  check_gpu.py                 # CUDA availability probe; not an acceptance test
data/raw/<plant>.fasta         # unchanged local source FASTA files
data/raw/c4_data_registry.csv  # query, retrieval, size, hash, and record counts
data/raw/c4_protein_exclusions.csv
data/interim/c4/               # regeneratable candidate outputs (Git-ignored)
```

## Documentation map

- [Architecture](SCREEN_PP1_ARCHITECTURE.md) describes the planned stages, component handoffs, and lifecycle boundaries.
- [Methodology](SCREEN_PP1_METHODOLOGY.md) defines the proposed digestion, embedding, AD, score, and metric contracts, including unresolved choices.
- [Data and outputs](SCREEN_PP1_DATA_AND_OUTPUTS.md) describes required provenance, artifact properties, and file-level guarantees.
- [Validation](SCREEN_PP1_VALIDATION.md) states what evidence is needed before marking a task Done or reporting a scientific result.
- [PP1 task inventory](SCREEN_PP1_Task_Inventory.md) is the execution plan and functional-requirement map.
- [PP1 deployment progress](SCREEN_PP1_Deployment_Progress.md) is the current evidence-based status snapshot.

## Interfaces and execution

Install the project in editable mode once, then use the Gate 1 CLI:

```powershell
python -m pip install --no-deps --no-build-isolation -e .
python -m plantaox.c4_screen.run download
python -m plantaox.c4_screen.run digest
python -m plantaox.c4_screen.run all
```

`all` fetches reviewed FASTA inputs when they are absent (or reuses the already recorded exact-query files), validates and excludes short/non-standard proteins, digests, filters, deduplicates, computes descriptors, writes artifacts under `data/interim/c4/`, and prints the per-plant funnel. Dependencies are listed in the repository's `requirements.txt`; their presence there does not prove successful model loading, GPU availability, or runtime feasibility.

With the project virtual environment active, install the C4 package set with:

```powershell
pip install fair-esm biopython pyteomics pandas pyarrow scikit-learn pytest
```

On 19 October 2026, all requested packages were already present in `.venv`. `requirements.txt` is now generated from that environment with `pip freeze`, including installed scikit-learn 1.9.1 and transitive packages.

### ESM-2 environment probe and weight retrieval

Run these commands with the project environment active:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
python -c "import esm; esm.pretrained.esm2_t33_650M_UR50D()"
```

The first command reports CUDA availability. The second invokes fair-esm's model loader; on first use it automatically fetches the weights into PyTorch's model cache, then loads the model. A successful process exit is required to consider the model available. GPU availability is independent of whether the model can be downloaded or loaded on CPU.

**Environment check on 19 October 2026:** the project virtual environment returned `False` for CUDA availability. The model loader reached the automatic download step, but no completed checkpoint or successful model load has been verified yet. See [deployment progress](SCREEN_PP1_Deployment_Progress.md) before relying on this environment.

Planned inter-component signals are `SIM_C1` (C1 similarity), `PROB_C2` (C2 probability), and `BCS_C3` (C3 predictor behavioral consistency). Their schemas, row-key uniqueness, missing-value policy, provenance, and version compatibility must be agreed with the owning components and validated before scoring. PP1 dummy values must be identified in every machine-readable output and human-facing view.

## Scientific and operational safeguards

- Unlabeled plant fragments are not confirmed negatives; the component is a retrieval and prioritization aid, not an experimental activity classifier.
- Tier 3 is abstention. Its combined score must be exactly zero once the scoring stage exists.
- AOP reference-cloud sequences and held-out evaluation sequences must be disjoint under the agreed homology rule. Do not use evaluation labels to fit the reference cloud or thresholds.
- The target ESM-2 model is `esm2_t33_650M_UR50D` (1280 dimensions), but layer, token handling, pooling, dtype, and exact C1 compatibility require a recorded contract.
- A provisional or Stage 0 reference cloud is not equivalent to the final C1 cloud. Label its source and all dependent outputs.
- The proposed PDSS denominator may be close to zero; do not calculate or interpret PDSS until its baseline definition and stability checks are approved.
- No PARRS, ARR, Recall@K, MRR, EF@1%, significance, or biological discovery claim is supported by the current repository state.

## Source basis

This documentation reconciles the repository's PP1 task inventory with the Component 4 proposal (especially Sections 2–5.3), the supplied C4 Full Analysis V2, and the plain-language C4 explainer. These materials specify research intent and proposed methods; they are not implementation evidence. Where they conflict, the PP1 inventory's explicit safeguards are followed and unresolved scientific choices are labelled rather than silently fixed.
