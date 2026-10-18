# Component 4 (PlantAOP-Screen) Deployment Progress

**Status snapshot:** 19 October 2026  
**Scope:** Repository evidence available at this snapshot; status is not supervisor approval.

## Summary

| Workstream | Status | Evidence / gap |
|---|---|---|
| Documentation architecture | Done | Component README, architecture, methodology, data/output contracts, and validation criteria are present in `src/plantaox/c4_screen/docs/`. They explicitly distinguish planned methodology from current implementation. |
| Repository scaffold | In Progress | `src/plantaox/c4_screen/__init__.py` exists. Gate 1 scaffold work has started; digestion, filtering, deduplication, descriptors, configuration, and CLI are not yet verified. |
| Proteome inputs | In Progress | Downloaded the four exact UniProt taxonomy + `reviewed:true` FASTA queries into `data/raw/c4_screen/`; API headers confirm release `2026_03` (02 September 2026). Record counts: soybean 439, rice 4,197, rapeseed 159, olive 110. Sizes and SHA-256 values are recorded in `SCREEN_PP1_DATA_AND_OUTPUTS.md`; each download byte-matches its prior `.txt` counterpart. The protein counts do not directly establish peptide candidate scope. Length/alphabet filters and exclusion logs remain pending. |
| Dependencies and environment | In Progress | The requested fair-esm, biopython, pyteomics, pandas, pyarrow, scikit-learn, and pytest packages are installed in `.venv`, and `requirements.txt` now records the environment via `pip freeze`. CUDA is unavailable (`False`); the ESM-2 download remains incomplete and model loading is not verified. `tests/c4_screen/check_gpu.py` is a probe, not a pipeline acceptance test. |
| Candidate generation (FR1 / Gate 1) | In Progress | This work session is scoped to candidate generation (digest, filter, exact dedup, descriptors, exports, and tests). No implementation or acceptance evidence is present yet; no counts are inferred. |
| Embeddings and AD tiers (FR2) | Pending | No ESM-2 embedding pipeline, reference cloud, fitted parameters, tier table, diagnostics, or validation evidence is present. |
| PDSS (FR3) | Pending | No implementation or results. Planned stretch/later analysis. |
| Signal integration and combined score (FR4) | Pending | No C1/C2 signal contract, scoring, abstention, or dummy signal artifacts are present. |
| Cross-predictor audit (FR5) | Pending | No implementation or predictor outputs are present. Later milestone. |
| Retrieval evaluation (FR6) | Pending | No held-out evaluation set, metric implementation, or results are present. Later milestone. |
| Evidence cards (FR7) | Pending | No card schema, generator, BCS integration, or example cards are present. |
| Dashboard, PP1 freeze, report, and presentation | Pending | No C4 dashboard integration, freeze manifest, report, slides, or acceptance evidence is present. |

## Verified repository facts

- The C4 Python package is at `src/plantaox/c4_screen/`, and tests are at `tests/c4_screen/`.
- The only file under the package is currently `__init__.py`; the only C4 test-directory file is `check_gpu.py`.
- Four reviewed-only UniProt query results are present, with release/query, protein counts, sizes, and hashes recorded in `SCREEN_PP1_DATA_AND_OUTPUTS.md`. The separate input filters and biological suitability have not yet been checked.
- The newly downloaded UniProt reviewed-only query results and their exact query/release provenance are now recorded in `SCREEN_PP1_DATA_AND_OUTPUTS.md`; all four downloaded FASTAs match the corresponding prior raw `.txt` files byte-for-byte.
- Reviewed input protein counts are 439 soybean, 4,197 rice, 159 rapeseed, and 110 olive. These are not peptide candidate counts; do not equate them with the proposal's post-digestion candidate estimate.
- The local project environment reports no CUDA device. A first-call ESM-2 weight retrieval was initiated; a successful download/model load is not yet verified.
- The top-level project `README.md` is empty. This snapshot does not infer that C4's technical acceptance criteria have passed.

## Source-document alignment and unresolved decisions

- The PP1 task inventory narrows the near-term target to FR1, FR2, and FR4/FR7 using explicitly labelled dummy C1/C2/C3 signals. FR3 is stretch; FR5/FR6 are later milestones.
- The supplied plain-language overview and Full Analysis V2 describe the proposed end-state, not implemented behavior. Their assumptions must not be presented as results.
- The inventory's safeguards take precedence for the PP1 execution plan where source drafts differ: rule-based pepsin pH 1.3 as a documented BIOPEP-UWM substitute if no batch interface is available; exact-sequence deduplication with provenance; provisional reference cloud explicitly labelled; dummy signals never represented as evaluation results.
- Open scientific decisions include the cloud-distance calibration and `d_norm` definition, the potentially unstable PDSS denominator, BCS warning/strata thresholds, C1 embedding recipe confirmation, and disjointness of reference and held-out sets. Resolve and record before treating resulting numbers as validated.
- The proposal and analysis include target metrics (PARRS, PDSS, ARR, Recall@K, MRR, EF@1%) and novelty statements. They are planned outcomes and claims to validate, not current results.

## Current work session

- **Done:** Re-read this progress report and the task inventory before starting the requested Gate 1 work. Existing repository evidence still shows the four reviewed input downloads and environment/GPU probe recorded above.
- **In Progress:** Inspect repository conventions and the planner, interface specification, and supplied mock signal generator; implement only candidate generation and Gate 1 validation.
- **Pending:** Gate 1 acceptance, including verified digestion-rule names, actual filtered protein/funnel counts, deterministic output comparison, and passing tests. No embedding, AD, scoring, or frontend work is in scope.

## Next actions

1. Complete Gate 1 candidate generation, registry, exclusions, deterministic exports, and acceptance tests; record actual observed counts.
2. Confirm the project scope and inter-component contracts with C1/C2/C3 owners; record decisions and label the reference cloud source.
3. Implement and test FR1 candidate generation and provenance before marking any FR1 task complete.
4. Confirm the ESM-2 model/layer/pooling contract, then implement the reproducible embedding and AD pipeline with diagnostics before marking FR2 complete.
5. Keep all PP1 dummy-signal outputs visibly labelled and defer evaluation claims until real signals and a leakage-checked held-out set exist.

## Status rule

Use **Done** only when the inventory's defined output and acceptance evidence are present and verified. **In Progress** means a partial artifact exists but acceptance is incomplete. **Pending** means there is no implementation/output evidence or the work is explicitly later scope. Update this file and the task inventory together when status changes.
