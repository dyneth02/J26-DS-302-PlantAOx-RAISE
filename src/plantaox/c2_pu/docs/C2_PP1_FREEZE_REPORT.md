# Component 02 PP1 research implementation freeze report

**Freeze ID:** `c2_pp1_freeze_v1`
**Frozen:** 2026-10-16
**Verified implementation revision:** `31d95224dd07dea7f9908c83f7cb1ba65edaa404`
**Release tag:** `c2-pp1-v1` (annotated tag on the dedicated freeze commit)
**Decision:** **FROZEN — READY WITH LIMITATIONS**

The accepted implementation, research artifacts, and owner-supplied external data copy passed the release checks. The dedicated source commit and annotated tag establish the Git reference; the verified external copy preserves the essential ignored bytes that Git does not contain. The methodological status remains **READY WITH LIMITATIONS**.

The initial worktree had one unrelated staged file, `.idea/modules.xml`. It predates this freeze, does not affect Component 02 science, and was unstaged without changing its working-tree bytes. It is excluded from the release commit.

## What the freeze covers

- FR1 `pp1_baseline_v1`: evidence-tiered positive pool, conflicts, CD-HIT output, and GraphPart folds.
- FR2 `pp2_baseline_v1`: C1/C2 pools, fold-specific C3 ranking/union, external controls, and integrity/distribution audits.
- FR3: descriptor and fusion schemas, descriptor table, fixed scalers, embedding manifest, five cache manifests, and the local arrays needed by the offline fold-0 demonstration.
- FR4: PN, direct-clamped nnPU, corrective nnPU, Two-Step PU, PU-Bagging, Task 4.5 evaluation, external-control diagnostic, corrective-nnPU curriculum, and the matched pre-freeze comparison.
- The accepted reports and the pre-freeze methodological audit. Historical results and checkpoint bytes were read only.

The machine-readable release record is `data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json`. Its companion `C2_PP1_ARTIFACT_INVENTORY.csv` gives a repository-relative path, byte size, SHA-256, Git disposition, retention class, local availability, and recovery route for every in-scope file. The manifest intentionally records the verified implementation **parent** revision. Resolving `c2-pp1-v1` identifies the later commit containing the freeze files without requiring a commit to embed its own hash.

## Integrity verification

The inventory contains **170 files** and no missing files:

| Disposition | Files | Bytes | Preservation state |
|---|---:|---:|---|
| Git-tracked | 106 | 11,850,209 | Preserved by the dedicated freeze commit and annotated tag |
| Git-ignored | 64 | 452,510,034 | Present and checksum-verified locally; the 56 essential files are also verified in the external data copy |

Of the ignored files, 56 files (39,103,768 bytes) are essential accepted cache/checkpoint/run bytes. All 56 exist under the owner-supplied backup root `C:\Users\metal\Documents\SLIIT Research\Data\C2-PP1-baseline-data` and independently match the inventory size and SHA-256 values. Eight larger inputs/caches (413,406,266 bytes, including the versioned Peptipedia dump and regenerable FR3/C3 arrays) have documented recovery pipelines and were not part of the required 56-file preservation set.

The release verifier confirmed:

- all 10 files in `pp1_baseline_v1` match its manifest;
- all 28 files in `pp2_baseline_v1` match its manifest;
- all 170 inventory entries match size and SHA-256;
- all five fold caches pass their accepted checksum/schema/shape/dtype/scaler-identity checks; fold 0 is `9356 × 495`, `float32`;
- the 9,356 × 480 embedding cache matches its accepted embedding manifest;
- fold-0 C3 contains 2,000 selected rows from the 2,325-row union;
- external-control IDs have zero overlap with the positive training or held-out partitions;
- the accepted PN best checkpoint and curriculum Stage-C1/Stage-C3 best checkpoints reload through the compatibility-checked loader and produce finite, bounded `8 × 1` scores.

The five baseline best and last files and all six curriculum best/last files are present and hash-verified through the inventory. Stage C1 remains the `weighted_c1_only_curriculum_reference`. Stage C3's zero-based epoch-0 checkpoint remains a post-update checkpoint after 63 C3 optimizer steps.

Focused release tests passed **4/4** through the repaired project `.venv`. A broader relevant regression covering the release verifier, frozen-manifest checks, feature cache, models, checkpoint recorder, experiment data, baseline evaluation, and curriculum passed **106/106**. Pytest emitted a cache-write permission warning; collection and tests completed normally. One existing FR3 acceptance test appended its standard rerun record to `fr3_feature_cache_provenance.jsonl`; because the freeze treats that log as historical output, it was restored to its verified pre-test Git bytes before the final 170-file inventory and smoke verification. No accepted scientific artifact remains modified.

The broader command was:

```powershell
& $py -m pytest tests/c2_pu/test_pp1_freeze.py tests/c2_pu/test_freeze.py tests/c2_pu/test_fr1_freeze_acceptance.py tests/c2_pu/test_fr2_freeze_acceptance.py tests/c2_pu/test_feature_cache.py tests/c2_pu/test_fr3_feature_cache_acceptance.py tests/c2_pu/test_models.py tests/c2_pu/test_run_recorder.py tests/c2_pu/test_experiment_data.py tests/c2_pu/test_baseline_evaluation.py tests/c2_pu/test_curriculum_training.py -q
```

## Offline demonstration readiness

The verified environment is Python 3.11.14 with NumPy 2.4.6, pandas 3.0.5, PyArrow 25.0.1, PyTorch 2.14.0+cpu, scikit-learn 1.9.0, pulearn 0.2.0, joblib 1.6.0, and pytest 9.1.1. The broken `.venv` base-runtime pointer was repaired to the existing repository-local Python 3.11.14 runtime; `.venv/Scripts/python.exe` now loads the installed environment successfully. `requirements.txt` is the project dependency declaration but is not a complete lockfile.

From the repository root in PowerShell:

```powershell
$py=(Resolve-Path '.venv\Scripts\python.exe').Path
$env:PYTHONPATH=(Resolve-Path 'src').Path
& $py -m plantaox.c2_pu.pp1_freeze verify --manifest data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json
& $py -m pytest tests/c2_pu/test_pp1_freeze.py -q
```

The verifier is the read-only PP1 smoke path. It exercises the same strict feature-cache loader, fold-safe C3 accessor, checkpoint loader, and inference method as the accepted implementation. It avoids `fr3-demo`'s canonical output/provenance writes while verifying the cached pipeline needed by that demonstration. The original feature demo remains available as `python -m plantaox.c2_pu.run fr3-demo`, but it writes the committed demo output and provenance log and was therefore not used during the freeze check.

Required local ignored inputs for this smoke path are `fr3_fold0_scaled_features.npz`, the accepted PN checkpoint, and the Stage-C1/Stage-C3 checkpoints. The original `fr3-demo` additionally needs `fr3_embeddings.npz`. Their exact hashes and sizes are in the inventory.

## Accepted research findings

Task 4.5's assay-supported comparison is unchanged:

| Model | MCC | AP | AUROC | Recall |
|---|---:|---:|---:|---:|
| PN | -0.1833 | 0.6392 | 0.2541 | 0.8710 |
| Direct-clamped nnPU | -0.0436 | 0.6915 | 0.3235 | 0.9919 |
| Corrective nnPU | -0.2498 | 0.6827 | 0.3224 | 0.5565 |
| Two-Step PU | -0.1694 | 0.6466 | 0.2818 | 0.7984 |
| PU-Bagging | -0.2495 | 0.6567 | 0.3005 | 0.7339 |

The matched curriculum sequence is also unchanged:

| Condition | Positive recovery | C1 >0.5 | C2 >0.5 | C3 >0.5 | External MCC / AUROC |
|---|---:|---:|---:|---:|---:|
| Weighted C1-only reference | 59.68% | 2.22% | 13.05% | 0.50% | -0.2929 / 0.2334 |
| After C2 | 38.71% | 2.35% | 3.30% | 0.60% | -0.1641 / 0.3171 |
| After C3 | 67.74% | 4.65% | 12.20% | 0.60% | -0.2338 / 0.2381 |

These results demonstrate technically reproducible data, feature, model, checkpoint, and evaluation paths. They do not demonstrate reliable antioxidant classification. C1/C2/C3 remain unlabeled, the 38 controls are small and assay-specific, two controls have cross-database conflicts, E2 is provisional, π=0.10 is assumed, source/descriptor shift may create shortcuts, curriculum selection remains C1-based, evaluation is fold-0 only, and model outputs are not calibrated biological probabilities.

## Outstanding scientific approvals and technical limitations

The following remain outside technical acceptance:

- supervisor confirmation of the UniProtKB-reviewed/SwissProt C1 interpretation;
- supervisor review of the 179 positive/inactive conflicts and provisional E2 policy;
- project-owner confirmation of retaining and flagging the two BIOPEP-UWM/external-control conflicts;

The external backup is a filesystem copy rather than a managed artifact service. Its absolute path is machine-specific, so handover still requires preserving that directory or migrating it with a fresh checksum verification. The Git tag alone does not contain ignored checkpoint/cache bytes.

## Post-PP1 continuation

Future work should branch from `c2-pp1-v1` and write new versions or experiment directories; it must not mutate the frozen datasets, accepted runs, summaries, or reports. The commit and tag remain local until the owner separately authorizes a remote destination and push.

The next research track should start with the existing shortcut-learning/source-bias diagnostic plan: descriptor/source matching, stronger assay-matched inactive controls, revised validation criteria, and later multi-fold experiments. RNIS/FR6, calibration, and biological validation remain future work.

**Final decision: FROZEN — READY WITH LIMITATIONS.** The implementation and required artifact bytes are verified and release-referenced; biological discrimination and the recorded scientific approvals remain unresolved.
