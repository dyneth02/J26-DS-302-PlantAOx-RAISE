# C4 FR4 Function B Scoring Acceptance

**Status:** PASS for deterministic mock integration behavior; no biological scoring claim.

- Join key: sequence; missing/duplicate/out-of-range rows are rejected. Signal source labels propagate to scores.
- Default CS: 0.5·SIM_C1 + 0.5·PROB_C2·(1−d_norm); Tier 3 forced to zero.
- Tested CS bounds, Tier 3 zeroing, monotonic decrease with increasing d_AD, mock source validation, synthetic real-source swap fixture, and planted-positive ranking on a seeded 2,000-row synthetic embedding sandbox.
- Weight sweep accepts w1={0.25,0.5,0.75}; configured default remains 0.5.
- Cached rice scoring/ranking timing: 1.644521 s; combined tiering + scoring/ranking: 20.207124 s.
- Tests: `pytest tests/c4_screen` — 15 passed.
