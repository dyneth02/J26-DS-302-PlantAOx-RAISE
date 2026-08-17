"""Component 2 (PU-AOP) prototype artifact generator.

Trains a real (small, descriptor-only) classifier on the real Component 1 AOP-BenchPos
positives against three challenge pools of increasing difficulty, then reports the
Random-Negative Inflation Score (RNIS = MCC on easy negatives - MCC on hard negatives).

Real:      AOP positives (from C1), non-AOP bioactive peptides sampled from Peptipedia,
           descriptor computation, the trained classifier, and all reported metrics.
Synthetic: only the "easy" random-composition decoy pool (Challenge Pool C1), which is
           supposed to be structurally naive by design -- that is the whole point of the
           inflation comparison.
"""
import json
import random
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, matthews_corrcoef
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from common_descriptors import compute_descriptors, is_valid_sequence

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ARTIFACT_DIR = ROOT / "artifacts" / "c2"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

DESCRIPTOR_COLS = [
    "mw", "gravy", "aromaticity", "instability", "charge_ph7", "aliphatic_index",
    "ctd_hydro_C_hydrophobic", "ctd_hydro_C_neutral", "ctd_hydro_C_polar",
    "ctd_hydro_T_hydrophobic_neutral", "ctd_hydro_T_neutral_polar", "ctd_hydro_T_hydrophobic_polar",
    "ctd_charge_C_positive", "ctd_charge_C_negative",
]
AA = list("ACDEFGHIKLMNPQRSTVWY")
N_PEPTIPEDIA_SAMPLE = 3000
DELTA_THRESHOLD = 0.5  # decision-probability threshold for classification


def load_positives() -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "data" / "processed" / "aop_sequences.parquet")
    df = df[["sequence"] + DESCRIPTOR_COLS].copy()
    df["label"] = 1
    return df


def build_random_easy_negatives(n: int, length_pool: list[int]) -> pd.DataFrame:
    rows = []
    for i in range(n):
        length = random.choice(length_pool)
        seq = "".join(random.choices(AA, k=length))
        d = compute_descriptors(seq)
        d["label"] = 0
        rows.append(d)
    return pd.DataFrame(rows)[["sequence"] + DESCRIPTOR_COLS + ["label"]]


def sample_peptipedia_negatives(exclude: set[str], n: int) -> pd.DataFrame:
    cache_path = RAW / "peptipedia_sample.csv"
    if cache_path.exists():
        cached = pd.read_csv(cache_path)
        if len(cached) >= n:
            return cached.head(n)

    # Peptipedia's full export is 27MB and lives outside the repo; read it directly from
    # the Downloads folder it was generated in, then cache only a small sample here.
    import os
    external_path = os.environ.get("PEPTIPEDIA_CSV", r"D:\Download\peptipedia_search.csv")
    src = pd.read_csv(external_path)
    src = src.rename(columns={"Sequence": "sequence"})
    src["sequence"] = src["sequence"].astype(str).str.strip().str.upper()
    src = src[src["sequence"].apply(is_valid_sequence)]
    src = src[~src["sequence"].isin(exclude)]
    src = src[src["sequence"].str.len().between(3, 50)]
    src = src.drop_duplicates(subset="sequence")

    sample = src.sample(n=min(n * 2, len(src)), random_state=RANDOM_SEED)

    rows = []
    for seq in sample["sequence"]:
        d = compute_descriptors(seq)
        rows.append(d)
    out = pd.DataFrame(rows).drop_duplicates(subset="sequence").head(n)
    out["label"] = 0
    out.to_csv(cache_path, index=False)
    return out[["sequence"] + DESCRIPTOR_COLS + ["label"]]


def compute_mcc_at_threshold(y_true, y_prob, threshold=DELTA_THRESHOLD) -> float:
    y_pred = (y_prob >= threshold).astype(int)
    return float(matthews_corrcoef(y_true, y_pred))


def compute_ece(y_true, y_prob, n_bins=10) -> float:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < n_bins - 1 else y_prob <= hi)
        if mask.sum() == 0:
            continue
        conf = y_prob[mask].mean()
        acc = y_true[mask].mean()
        ece += (mask.sum() / n) * abs(acc - conf)
    return float(ece)


def main():
    positives = load_positives()
    print(f"Loaded {len(positives)} real AOP positives (all tiers)")

    length_pool = positives["sequence"].str.len().tolist()
    easy_negatives = build_random_easy_negatives(len(positives), length_pool)
    print(f"Built {len(easy_negatives)} synthetic random-composition easy negatives (Pool C1)")

    moderate_negatives = sample_peptipedia_negatives(set(positives["sequence"]), len(positives))
    print(f"Sampled {len(moderate_negatives)} real non-AOP bioactive peptides from Peptipedia (Pool C2)")

    # Hard negatives (Pool C3): the moderate pool's peptides closest, in *standardized*
    # descriptor space, to the real AOP positive centroid -- i.e. the peptides that most
    # resemble AOP peptides physicochemically without being annotated as antioxidant.
    # Distance is Euclidean *after* z-scoring, not cosine similarity: z-scoring pulls the
    # positive centroid to ~the origin, which makes cosine similarity to it degenerate
    # (nearly every point looks equally "similar"). Euclidean distance to that same centroid
    # remains meaningful because it is just the standardized vector's norm.
    hard_scaler = StandardScaler().fit(positives[DESCRIPTOR_COLS].values)
    pos_centroid = hard_scaler.transform(positives[DESCRIPTOR_COLS].values).mean(axis=0).reshape(1, -1)
    mod_feats = hard_scaler.transform(moderate_negatives[DESCRIPTOR_COLS].values)
    distances = np.linalg.norm(mod_feats - pos_centroid, axis=1)
    hard_idx = np.argsort(distances)[: len(positives)]
    hard_negatives = moderate_negatives.iloc[hard_idx].reset_index(drop=True)
    print(f"Selected {len(hard_negatives)} descriptor-nearest hard negatives from Pool C2 (Pool C3)")

    pools_meta = {
        "pool_c1_random_easy": {
            "size": len(easy_negatives),
            "source": "synthetic random-composition decoys",
            "purpose": "baseline easy-negative evaluation, matches how most published AOP predictors are benchmarked",
        },
        "pool_c2_non_aop_bioactive": {
            "size": len(moderate_negatives),
            "source": "Peptipedia (real, non-AOP-labelled bioactive peptides)",
            "purpose": "moderate-difficulty negative pool",
        },
        "pool_c3_hard_descriptor_nearest": {
            "size": len(hard_negatives),
            "source": "Peptipedia subset closest to AOP positive centroid in descriptor space",
            "purpose": "hard-negative evaluation used to compute RNIS",
        },
    }
    (ARTIFACT_DIR / "challenge_pools.json").write_text(json.dumps(pools_meta, indent=2))

    # Train on positives vs easy negatives (the "typical published paper" setup).
    train_df = pd.concat([positives, easy_negatives], ignore_index=True)
    X = train_df[DESCRIPTOR_COLS].values
    y = train_df["label"].values
    X_train, X_test_easy, y_train, y_test_easy = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_SEED, stratify=y
    )

    scaler = StandardScaler().fit(X_train)
    clf = LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)
    clf.fit(scaler.transform(X_train), y_train)

    prob_easy = clf.predict_proba(scaler.transform(X_test_easy))[:, 1]
    mcc_c1 = compute_mcc_at_threshold(y_test_easy, prob_easy)

    # Evaluate the *same* trained model against the untouched hard-negative pool.
    hard_eval_pos = positives.sample(n=min(len(hard_negatives), len(positives)), random_state=RANDOM_SEED)
    hard_eval = pd.concat([hard_eval_pos, hard_negatives], ignore_index=True)
    X_hard = scaler.transform(hard_eval[DESCRIPTOR_COLS].values)
    y_hard = hard_eval["label"].values
    prob_hard = clf.predict_proba(X_hard)[:, 1]
    mcc_c3 = compute_mcc_at_threshold(y_hard, prob_hard)

    rnis = round(mcc_c1 - mcc_c3, 4)

    ece_easy = compute_ece(y_test_easy, prob_easy)
    brier_easy = float(brier_score_loss(y_test_easy, prob_easy))
    ece_hard = compute_ece(y_hard, prob_hard)
    brier_hard = float(brier_score_loss(y_hard, prob_hard))

    rnis_report = {
        "classifier": "logistic_regression (descriptor-only, 14 physicochemical features)",
        "mcc_c1_easy": round(mcc_c1, 4),
        "mcc_c3_hard": round(mcc_c3, 4),
        "rnis": rnis,
        "interpretation": (
            "Performance is inflated when evaluated against easy random negatives."
            if rnis > 0.05
            else "No strong evidence of inflation between easy and hard negative pools for this classifier."
        ),
    }
    (ARTIFACT_DIR / "rnis_report.json").write_text(json.dumps(rnis_report, indent=2))

    classification_metrics = {
        "easy_pool": {"n_test": int(len(y_test_easy)), "mcc": round(mcc_c1, 4)},
        "hard_pool": {"n_test": int(len(y_hard)), "mcc": round(mcc_c3, 4)},
    }
    (ARTIFACT_DIR / "classification_metrics.json").write_text(json.dumps(classification_metrics, indent=2))

    calibration_metrics = {
        "easy_pool": {"ece": round(ece_easy, 4), "brier": round(brier_easy, 4)},
        "hard_pool": {"ece": round(ece_hard, 4), "brier": round(brier_hard, 4)},
    }
    (ARTIFACT_DIR / "calibration_metrics.json").write_text(json.dumps(calibration_metrics, indent=2))

    stage_comparison = {
        "chart_type": "bar",
        "series": [
            {"stage": "Easy negatives (Pool C1)", "mcc": round(mcc_c1, 4)},
            {"stage": "Hard negatives (Pool C3)", "mcc": round(mcc_c3, 4)},
        ],
        "rnis": rnis,
    }
    (ARTIFACT_DIR / "stage_comparison.json").write_text(json.dumps(stage_comparison, indent=2))

    joblib.dump({"model": clf, "scaler": scaler, "features": DESCRIPTOR_COLS}, ARTIFACT_DIR / "pu_model.joblib")

    summary = {
        "component": "C2_PU_AOP",
        "prototype_mode": True,
        "data_mode": "real_positives_real_hard_negatives_synthetic_easy_negatives",
        "n_positives": int(len(positives)),
        "pools": pools_meta,
        "rnis": rnis,
        "notes": [
            "Positives are the real, curated Component 1 AOP-BenchPos peptides (all tiers).",
            "Hard negatives (Pool C3) are real Peptipedia peptides selected for descriptor-space "
            "similarity to AOP positives, not embedding-nearest (no ESM-2 embeddings computed "
            "for the negative pool in this prototype).",
            "Only the easy-negative pool (Pool C1) is synthetic, by design: it represents naive "
            "random-composition decoys, the standard (and misleading) baseline in the literature.",
            "Classifier is descriptor-only logistic regression; the full project adds ESM-2 "
            "embedding features and PU/curriculum learning.",
        ],
    }
    (ARTIFACT_DIR / "c2_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"\nRNIS = {rnis} (MCC_easy={mcc_c1:.4f}, MCC_hard={mcc_c3:.4f})")
    print("Component 2 prototype artifacts generated successfully.")


if __name__ == "__main__":
    main()
