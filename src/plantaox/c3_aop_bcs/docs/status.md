# Component 3 (AOP-BCS) Status

## Current task

- **Task 3.3 — Create the C3 research configuration:** Completed on 2026-10-18.
- **Task 3.4 — Acquire the perturbation subject sequences:** Completed on 2026-10-18.
- **Task 3.5 — Standardize sequence records:** Not started.
- The acquired source records remain byte-for-byte unchanged; no Task 3.5 standardization has been performed.

## Completed

- Added the versioned `research_config.toml` source of truth with:
  - random seed `42`;
  - sequence length range `3–50`;
  - redox residues `W`, `Y`, `H`, `M`, and `C`;
  - CD-HIT identity threshold `0.90`;
  - primary delta `0.05`;
  - sensitivity deltas `0.02`, `0.05`, and `0.10`;
  - PP1 pilot dataset size `20`.
- Added a dependency-free, typed TOML loader with validation for missing, unknown, malformed, and out-of-range values.
- Exported the configuration API from the Component 3 package.
- Added focused configuration tests; all 5 tests pass with the project Python interpreter.
- Acquired and preserved four original C3 source files under `data/raw/c3_aop_bcs/`:
  - AnOxPePred supplementary assay table: 917 records, including 699 direct assay-positive candidates and 218 assay-inactive records;
  - Multi-AOP AnOxPePred benchmark: 1,404 records (676 positive, 728 negative);
  - Multi-AOP AnOxPP benchmark: 2,120 records (1,060 positive, 1,060 negative);
  - Multi-AOP AOPP benchmark: 3,022 records (1,511 positive, 1,511 negative).
- Added `PROVENANCE.json` as the machine-readable `c3_aop_bcs_raw_v1` manifest, recording acquisition date, authoritative repository/path, schema, row counts, byte counts, evidence notes, and SHA-256 version pins.
- Documented the later-selection policy: prefer AnOxPePred direct assay-positive records, retain Multi-AOP positive records as candidates, and defer standardization/filtering/conflict resolution to Tasks 3.5–3.8.
- Added four acquisition-integrity tests covering source traceability, raw byte hashes, CSV schemas, row counts, and label/assay counts; the complete C3 suite now passes 9 tests.

## Environment note

- The project `.venv` does not currently have `pytest` installed even though it is listed in `requirements.txt`; Task 3.3 tests use standard-library `unittest` and remain compatible with later pytest discovery.

## Scope guard

- Changes for this task are restricted to files under the `c3_aop_bcs` path/pattern.
