"""Live C2 RNIS: user picks which negative pool(s) to train on, a fresh LogisticRegression
is fit on demand, and MCC/RNIS is recomputed for real -- the "build your own negative
pool" feature from the enhancement plan.

Pool-generation logic (easy/peptipedia/hard) is imported directly from
generate_c2_artifacts.py -- the same functions that produced challenge_pools.json and
rnis_report.json -- rather than reimplemented, so the pools here are identical to what's
already documented on the page.

Leakage-safe design: each pool (positives + the 3 negative pools) is split into a fixed
75/25 train/test partition ONCE at load time (seeded, so this matches, in the pools=
["easy"]-only case, the exact train/test split the static artifact generator used). A
live request concatenates the TRAIN partitions of positives + whichever negative pool(s)
were selected to fit a fresh model, then evaluates it two ways: against the TEST
partitions of that same selection ("mcc_selected", mirrors the original script's
mcc_c1_easy when pools=["easy"]), and separately, always, against the hard pool's TEST
partition ("mcc_hard") -- which the model never trains on unless "hard" itself was
selected, and even then only ever sees the hard TRAIN partition, never the held-out
hard TEST rows. This keeps "mcc_hard" a genuine held-out generalization number in every
combination, not just the default one.
"""
from __future__ import annotations

import sys
import threading

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from . import paths

_lock = threading.Lock()
_state: dict = {}

RANDOM_SEED = 42
VALID_POOLS = ("easy", "peptipedia", "hard")


def _import_generator():
    sys.path.insert(0, str(paths.SCRIPTS_DIR))
    import generate_c2_artifacts as c2gen  # noqa: E402
    return c2gen


def load_c2_state() -> None:
    with _lock:
        if _state:
            return
        c2gen = _import_generator()
        cols = c2gen.DESCRIPTOR_COLS

        positives = c2gen.load_positives()

        # Re-seed immediately before generation so this reproduces the same pools the
        # static artifacts were built from, regardless of any other random calls made
        # elsewhere in this process beforehand.
        import random
        random.seed(RANDOM_SEED)
        np.random.seed(RANDOM_SEED)
        length_pool = positives["sequence"].str.len().tolist()
        easy = c2gen.build_random_easy_negatives(len(positives), length_pool)
        peptipedia = c2gen.sample_peptipedia_negatives(set(positives["sequence"]), len(positives))

        hard_scaler = StandardScaler().fit(positives[cols].values)
        pos_centroid = hard_scaler.transform(positives[cols].values).mean(axis=0).reshape(1, -1)
        mod_feats = hard_scaler.transform(peptipedia[cols].values)
        distances = np.linalg.norm(mod_feats - pos_centroid, axis=1)
        hard_idx = np.argsort(distances)[: len(positives)]
        hard = peptipedia.iloc[hard_idx].reset_index(drop=True)

        pools = {"easy": easy, "peptipedia": peptipedia, "hard": hard}

        splits: dict[str, dict[str, pd.DataFrame]] = {}
        pos_train, pos_test = train_test_split(positives, test_size=0.25, random_state=RANDOM_SEED)
        splits["positives"] = {"train": pos_train, "test": pos_test}
        for name, df in pools.items():
            train, test = train_test_split(df, test_size=0.25, random_state=RANDOM_SEED)
            splits[name] = {"train": train, "test": test}

        _state["cols"] = cols
        _state["splits"] = splits
        print(f"[live/c2] loaded positives ({len(positives)}) + pools: "
              + ", ".join(f"{k}={len(v)}" for k, v in pools.items()))


def live_rnis(pools: list[str]) -> dict:
    pools = [p for p in dict.fromkeys(pools) if p in VALID_POOLS]  # dedupe, validate, keep order
    if not pools:
        raise ValueError(f"pools must be a non-empty subset of {VALID_POOLS}")

    splits = _state["splits"]
    cols = _state["cols"]

    train_df = pd.concat(
        [splits["positives"]["train"].assign(label=1)]
        + [splits[p]["train"].assign(label=0) for p in pools],
        ignore_index=True,
    )
    selected_test_df = pd.concat(
        [splits["positives"]["test"].assign(label=1)]
        + [splits[p]["test"].assign(label=0) for p in pools],
        ignore_index=True,
    )
    hard_test_df = pd.concat(
        [splits["positives"]["test"].assign(label=1), splits["hard"]["test"].assign(label=0)],
        ignore_index=True,
    )

    scaler = StandardScaler().fit(train_df[cols].values)
    clf = LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)
    clf.fit(scaler.transform(train_df[cols].values), train_df["label"].values)

    def mcc_on(df: pd.DataFrame) -> float:
        prob = clf.predict_proba(scaler.transform(df[cols].values))[:, 1]
        pred = (prob >= 0.5).astype(int)
        from sklearn.metrics import matthews_corrcoef
        return float(matthews_corrcoef(df["label"].values, pred))

    mcc_selected = round(mcc_on(selected_test_df), 4)
    mcc_hard = round(mcc_on(hard_test_df), 4)
    rnis = round(mcc_selected - mcc_hard, 4)

    return {
        "pools_selected": pools,
        "n_train": int(len(train_df)),
        "mcc_easy": mcc_selected,  # named to match the existing rnis_report.json field, see docstring
        "mcc_hard": mcc_hard,
        "rnis": rnis,
        "interpretation": (
            "Performance is inflated when evaluated against the selected pool(s) vs. the hard pool."
            if rnis > 0.05
            else "No strong evidence of inflation between the selected pool(s) and the hard pool."
        ),
        "live": True,
    }


def _reliability_bins(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> list[dict]:
    """Same binning as generate_c2_artifacts.compute_ece, but returns the per-bin rows
    instead of collapsing them into a single ECE scalar -- this is what a calibration
    plot actually needs."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    rows = []
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < n_bins - 1 else y_prob <= hi)
        count = int(mask.sum())
        rows.append(
            {
                "bin_center": round(float((lo + hi) / 2), 3),
                "confidence": round(float(y_prob[mask].mean()), 4) if count else None,
                "accuracy": round(float(y_true[mask].mean()), 4) if count else None,
                "count": count,
                "weight": round(count / n, 4) if n else 0.0,
            }
        )
    return rows


def live_calibration(pools: list[str]) -> dict:
    pools = [p for p in dict.fromkeys(pools) if p in VALID_POOLS]
    if not pools:
        raise ValueError(f"pools must be a non-empty subset of {VALID_POOLS}")

    splits = _state["splits"]
    cols = _state["cols"]

    train_df = pd.concat(
        [splits["positives"]["train"].assign(label=1)]
        + [splits[p]["train"].assign(label=0) for p in pools],
        ignore_index=True,
    )
    selected_test_df = pd.concat(
        [splits["positives"]["test"].assign(label=1)]
        + [splits[p]["test"].assign(label=0) for p in pools],
        ignore_index=True,
    )
    hard_test_df = pd.concat(
        [splits["positives"]["test"].assign(label=1), splits["hard"]["test"].assign(label=0)],
        ignore_index=True,
    )

    scaler = StandardScaler().fit(train_df[cols].values)
    clf = LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)
    clf.fit(scaler.transform(train_df[cols].values), train_df["label"].values)

    def bins_for(df: pd.DataFrame) -> list[dict]:
        prob = clf.predict_proba(scaler.transform(df[cols].values))[:, 1]
        return _reliability_bins(df["label"].values, prob)

    return {
        "pools_selected": pools,
        "selected_bins": bins_for(selected_test_df),
        "hard_bins": bins_for(hard_test_df),
        "live": True,
    }
