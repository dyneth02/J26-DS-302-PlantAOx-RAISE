# c1_procon — processed data and results (Component 1, AOP-ProCon)

Benchmark **S2 build v3** (fingerprint `47d9c2a2fff63eb1`): 1,389 unique peptides (FRS 565, FRS;MC 86, MC 63, GEN 675), 573 homology groups, strict-evidence pool 669 (104 MC-active / 565 FRS-only).

| Path | Content |
|---|---|
| `AOP-BenchPos_S2.csv` | the benchmark (one row per unique sequence, multi-label) |
| `AOP-Provenance.csv`, `AOP-Conflicts.csv`, `AOP-Inactive.csv`, `excluded_by_primary_evidence.csv`, `s2_change_log.csv` | provenance, label conflicts, inactive set, exclusions, change log |
| `descriptors.csv` | 14 physicochemical descriptors per peptide |
| `pairs/<strict|extended|strict_ge4>/` | positive-pair files used for training (Step 3) |
| `step1_manifest.json`, `step2_manifest.json`, `pairs_manifest.json` | SHA-256 manifests of the steps |
| `results/` | Step 4-6 tables, Step 5 v4 supervised probe (repeated grouped CV), Step 7 OOF probe scores, `step8/` confound controls |
| `results/checkpoint_sha256.csv` | SHA-256 of the 15 trained checkpoints (the `.pt` files are not committed) |

Not committed: ESM-2 embedding arrays (`.npy`), model checkpoints (`.pt`), the release zip, raw third-party repositories. They can be regenerated with `notebooks/c1_procon/STEP02` and `STEP04` (see `src/plantaox/c1_procon/docs/PIPELINE_README.md`).

Data files are byte-exact copies (the repository sets `data/** -text`).
