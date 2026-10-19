"""Mock signal generation via the existing utility and strict sequence-key joins."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def mock_utility_path() -> Path:
    """Resolve the existing project fixture utility without copying/duplicating it."""
    return Path(__file__).resolve().parents[3] / "tests" / "c4_screen" / "fixtures" / "mock_signals.py"


def generate_and_validate_mock_signals(tier_table: str | Path, output_dir: str | Path,
                                       seed: int = 42, inject: int = 10) -> None:
    utility = mock_utility_path()
    if not utility.is_file():
        raise FileNotFoundError(f"Existing mock signal utility is missing: {utility}")
    out = Path(output_dir)
    commands = [
        [sys.executable, str(utility), "generate", "--candidates", str(tier_table), "--out", str(out),
         "--seed", str(seed), "--inject", str(inject)],
        [sys.executable, str(utility), "validate", "--candidates", str(tier_table), "--dir", str(out)],
    ]
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError(f"mock_signals.py {' '.join(command[2:3])} failed:\n{result.stdout}\n{result.stderr}")


def validate_and_join_signals(tiers: pd.DataFrame, signals_dir: str | Path) -> tuple[pd.DataFrame, dict]:
    """Join C1/C2/BCS stand-ins to tier rows by sequence and preserve source labels."""
    if "sequence" not in tiers:
        raise ValueError("tier table missing sequence join key")
    if tiers.sequence.duplicated().any():
        raise ValueError("tier table sequence join key is not unique")
    root = Path(signals_dir)
    c1 = pd.read_parquet(root / "c1_sim.parquet")
    c2 = pd.read_parquet(root / "c2_prob.parquet")
    for frame, score in ((c1, "SIM_C1"), (c2, "PROB_C2")):
        missing_cols = {"sequence", score, "source"} - set(frame.columns)
        if missing_cols:
            raise ValueError(f"signal table missing required columns: {sorted(missing_cols)}")
        if frame.sequence.duplicated().any():
            raise ValueError(f"duplicate sequence keys in {score} signal table")
        if not frame["source"].isin(["mock", "real"]).all():
            raise ValueError(f"invalid source label in {score} signal table")
        values = frame[score].to_numpy(dtype=np.float64)
        if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
            raise ValueError(f"{score} contains NaN/Inf or values outside [0,1]")
        missing = set(tiers.sequence) - set(frame.sequence)
        if missing:
            raise ValueError(f"{score} has no row for {len(missing)} tier candidate(s)")
    joined = tiers.merge(c1[["sequence", "SIM_C1", "source"]].rename(columns={"source": "SIM_C1_source"}),
                         on="sequence", how="left", validate="one_to_one")
    joined = joined.merge(c2[["sequence", "PROB_C2", "evidence_tier", "source"]].rename(
        columns={"source": "PROB_C2_source"}), on="sequence", how="left", validate="one_to_one")
    import json
    bcs = json.loads((root / "c3_bcs.json").read_text(encoding="utf-8"))
    if bcs.get("source") not in {"mock", "real"}:
        raise ValueError("c3_bcs.json has invalid source label")
    if bcs.get("source") == "mock" and not c1.source.eq("mock").all() or bcs.get("source") == "mock" and not c2.source.eq("mock").all():
        raise ValueError("Mock signal batch must carry source=mock on every C1/C2 row")
    if joined[["SIM_C1", "PROB_C2"]].isna().any().any():
        raise ValueError("signal join produced missing values")
    return joined, bcs
