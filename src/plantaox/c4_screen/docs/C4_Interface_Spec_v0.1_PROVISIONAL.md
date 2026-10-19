# C4 (PlantAOP-Screen) Interface Spec v0.1 — PROVISIONAL

**Owner:** Cooray Y H (C4) · **Status:** proposed by C4 so work can proceed; C1/C2/C3 owners may correct it.  
**Rule:** nothing below is presented as already defined by C1, C2, or C3 unless it is in the "Frozen" column.

## 1. What is frozen vs. proposed

| Item | Status | Source / note |
|---|---|---|
| Sequence range 3–50 AA, standard 20-residue alphabet | **Frozen** | C3 proposal; C2 pipeline uses the same range. C4 candidates are 3–20 AA, so they fit. |
| `BCS = IR × (1 − FSR)` | **Frozen** | C3 proposal |
| Primary δ = 0.05 (sensitivity δ ∈ {0.02, 0.05, 0.10}) | **Frozen** | C3 proposal |
| Length bins 3–10 / 11–20 / 21–50 AA | Working assumption | Appears in the C3 analysis document, **not** in the proposal. C4 candidates only use the first two. |
| Mechanism strata (FRS / CHEL) | Working assumption | C3 analysis document; C4 candidates carry no mechanism label, so C4 reads the `ALL` stratum. |
| `c3_bcs.json` schema | **C4-proposed** | Section 3 |
| BCS reliability-flag cutoffs | **C4-proposed** | C3 sets thresholds empirically in Phase 2. C4 keeps provisional cutoffs in its own config, never in C3's file. |
| `c2_prob.parquet` / `c1_sim.parquet` schemas, join key | **C4-proposed** | Sections 2 and 4 |

## 2. Join key and C2 / C1 files

Join key is the **sequence string**, because C1 and C2 will score C4's candidate FASTA with their own pipelines and may not share C4's IDs.

`c2_prob.parquet`

| Column | Type | Rule |
|---|---|---|
| `sequence` | str | unique, 3–50 AA, standard alphabet |
| `PROB_C2` | float | in [0, 1], no NaN |
| `evidence_tier` | str | `U` for novel candidates |
| `model_id` | str | e.g. `MOCK_PU_v0.1` or the real checkpoint name |
| `source` | str | `mock` or `real` |

`c1_sim.parquet` has the same shape with `SIM_C1` in [0, 1] and a `model_id`.

## 3. `c3_bcs.json`

```json
{
  "schema_version": "c4-interface-0.1-provisional",
  "source": "mock",
  "predictor": "PU-AOP",
  "delta": 0.05,
  "formula": "BCS = IR * (1 - FSR)",
  "length_bins": ["3-10", "11-20", "21-50"],
  "overall": {"IR": 0.0, "FSR": 0.0, "BCS": 0.0},
  "strata": [
    {"mechanism": "ALL", "length_bin": "3-10", "n_sequences": 0, "IR": 0.0, "FSR": 0.0, "BCS": 0.0}
  ]
}
```

C4 reads `mechanism == "ALL"` rows. Validation fails if a stratum's BCS differs from `IR × (1 − FSR)`, if δ ≠ 0.05, or if any candidate's length bin has no `ALL` row.

## 4. Flags are computed by C4, not delivered by C3

`LOW` if BCS < 0.5, `HIGH` if BCS ≥ 0.7, otherwise `MEDIUM`. These cutoffs are C4-provisional (`config.yaml`), and every card shows the raw BCS next to the flag. When C3 fixes its thresholds, only the C4 config changes.

## 5. Mock generation rules (`mock_signals.py`)

- Fixed seed (42), independent sub-seeds per signal, SHA-256 manifest, `source = mock` on every file.
- `PROB_C2`: rule-based AOP-likeness (redox residues W/Y/H/M/C, hydrophobic fraction, short-length bonus) → logistic, low base rate, with noise that grows with AD distance. Up to 10 Tier 3 candidates are overridden to PROB_C2 ≥ 0.9 and listed in `MOCK_MANIFEST.json` as injected demo cases.
- `BCS`: IR and FSR are sampled per stratum; BCS is always computed from the frozen formula.
- Mock values are never results. Do not compute PARRS, Recall@K, MRR, or EF@1% on them.

## 6. Swap-out and change process

1. Owner delivers a real file in the same schema → replace the mock file.
2. Set `signals.source: real` in the C4 config and run `python mock_signals.py validate ...`.
3. Tiers must be unchanged; CS changes only through the signals.
4. Any schema change is made by editing this spec and bumping the version (v0.2, ...), with the change logged in the decision log.

## 7. One-line confirm-or-correct message for C1, C2, C3 owners

> "C4 is proceeding on mock data using Interface Spec v0.1 (attached). Please reply only if something conflicts with what your component will produce; otherwise I'll treat the schema as agreed and swap in your real files when ready."
