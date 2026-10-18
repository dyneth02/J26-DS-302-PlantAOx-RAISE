# Component 3 (AOP-BCS) Status

## Current task

- **Task 3.3 — Create the C3 research configuration:** Completed on 2026-10-18.
- **Task 3.4 — Acquire the perturbation subject sequences:** Not started.

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

## Environment note

- The project `.venv` does not currently have `pytest` installed even though it is listed in `requirements.txt`; Task 3.3 tests use standard-library `unittest` and remain compatible with later pytest discovery.

## Scope guard

- Changes for this task are restricted to files under the `c3_aop_bcs` path/pattern.
