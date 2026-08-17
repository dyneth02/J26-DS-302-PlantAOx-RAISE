"""Component 4 (PlantAOP-Screen) prototype artifact generator.

Input proteome: 25 real, reviewed UniProt Arabidopsis thaliana proteins annotated with the
antioxidant/defense keyword (KW-0929), fetched via the UniProt REST API and cached at
data/raw/plant_proteome.fasta. This stands in for the "small plant proteome subset" the
architecture doc calls for; the full project will process complete plant proteomes across
multiple species.

Everything downstream is real: rule-based in-silico digestion, descriptor computation,
scoring against the real Component 1 positive centroid, the real Component 2 predictor
probability, and the real Component 3 reliability flag. The applicability-domain (AD)
distance uses descriptor-space standardized-Euclidean distance (the documented Level-3
fallback) rather than ESM-2 embedding distance, because no embeddings were computed for
plant fragments in this prototype.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from Bio import SeqIO
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from common_descriptors import compute_descriptors, is_valid_sequence

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ARTIFACT_DIR = ROOT / "artifacts" / "c4"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

DESCRIPTOR_COLS = [
    "mw", "gravy", "aromaticity", "instability", "charge_ph7", "aliphatic_index",
    "ctd_hydro_C_hydrophobic", "ctd_hydro_C_neutral", "ctd_hydro_C_polar",
    "ctd_hydro_T_hydrophobic_neutral", "ctd_hydro_T_neutral_polar", "ctd_hydro_T_hydrophobic_polar",
    "ctd_charge_C_positive", "ctd_charge_C_negative",
]
MIN_LEN, MAX_LEN = 3, 50
TOP_N_CANDIDATES = 200
TOP_K_EVIDENCE = 5


def tryptic_pepsin_digest(protein_seq: str) -> list[str]:
    """Rule-based dual digestion: trypsin (cleave after K/R, not before P) followed by
    pepsin (cleave after F/L/W/Y, low-pH simplification)."""
    def cleave_after(seq: str, cut_residues: set, block_before: set) -> list[str]:
        frags, start = [], 0
        for i, c in enumerate(seq):
            if c in cut_residues and (i + 1 >= len(seq) or seq[i + 1] not in block_before):
                frags.append(seq[start:i + 1])
                start = i + 1
        if start < len(seq):
            frags.append(seq[start:])
        return frags

    tryptic = cleave_after(protein_seq, set("KR"), set("P"))
    fragments = []
    for frag in tryptic:
        fragments.extend(cleave_after(frag, set("FLWY"), set()))
    return fragments


def load_plant_fragments() -> pd.DataFrame:
    records = list(SeqIO.parse(RAW / "plant_proteome.fasta", "fasta"))
    rows = []
    seen = set()
    for rec in records:
        protein_seq = str(rec.seq)
        fragments = tryptic_pepsin_digest(protein_seq)
        for frag in fragments:
            frag = frag.strip().upper()
            if not (MIN_LEN <= len(frag) <= MAX_LEN) or not is_valid_sequence(frag) or frag in seen:
                continue
            seen.add(frag)
            rows.append({
                "sequence": frag,
                "source_protein": rec.id,
                "plant_species": "Arabidopsis thaliana",
                "enzyme": "trypsin+pepsin",
                "length": len(frag),
            })
    return pd.DataFrame(rows)


def main():
    model_bundle = joblib.load(ROOT / "artifacts" / "c2" / "pu_model.joblib")
    model, scaler, feature_cols = model_bundle["model"], model_bundle["scaler"], model_bundle["features"]

    # C3 now audits two predictors (this prototype's C2 model, and the real external
    # Multi-AOP checkpoint). C4 scores candidates with the C2 model specifically (see
    # `model_bundle` below), so it must pick that same predictor's reliability flag, not
    # rely on whichever key happens to come first in the file.
    c3_flags = json.loads((ROOT / "artifacts" / "c3" / "predictor_reliability_flags.json").read_text())
    predictor_name = "c2_logreg"
    predictor_flag = c3_flags[predictor_name]["flag"]

    positives = pd.read_parquet(ROOT / "data" / "processed" / "aop_sequences.parquet")
    train_eligible = positives[positives["training_eligible"]]

    fragments = load_plant_fragments()
    print(f"Digested {fragments['source_protein'].nunique()} real UniProt plant proteins into "
          f"{len(fragments)} unique candidate fragments (length {MIN_LEN}-{MAX_LEN})")

    desc_rows = [compute_descriptors(s) for s in fragments["sequence"]]
    desc_df = pd.DataFrame(desc_rows)
    fragments = fragments.merge(desc_df, on="sequence")

    # Descriptor-space AD reference cloud, fit on real training-eligible AOP positives
    # (Level-3 fallback per the architecture doc: descriptor distance in place of an ESM-2
    # embedding cloud, since no embeddings were computed for plant fragments).
    # Distance is Euclidean after z-scoring, not cosine similarity: z-scoring pulls the
    # positive centroid to ~the origin, which makes cosine similarity to it degenerate.
    ad_scaler = StandardScaler().fit(train_eligible[DESCRIPTOR_COLS].values)
    pos_scaled = ad_scaler.transform(train_eligible[DESCRIPTOR_COLS].values)
    pos_centroid = pos_scaled.mean(axis=0).reshape(1, -1)

    pos_self_distance = np.linalg.norm(pos_scaled - pos_centroid, axis=1)
    mu, sigma = float(pos_self_distance.mean()), float(pos_self_distance.std())

    frag_scaled = ad_scaler.transform(fragments[DESCRIPTOR_COLS].values)
    frag_distance = np.linalg.norm(frag_scaled - pos_centroid, axis=1)
    fragments["ad_distance"] = np.round(frag_distance, 4)
    # Similarity is a decaying function of standardized distance, bounded in (0, 1].
    fragments["sim_c1"] = np.round(1.0 / (1.0 + frag_distance), 4)

    def tier_of(d):
        if d < mu + sigma:
            return "Tier1"
        elif d < mu + 2 * sigma:
            return "Tier2"
        return "Tier3_abstain"

    fragments["ad_tier"] = fragments["ad_distance"].apply(tier_of)

    # Real Component 2 predictor probability.
    X = scaler.transform(fragments[DESCRIPTOR_COLS].values)
    fragments["prob_c2"] = np.round(model.predict_proba(X)[:, 1], 4)

    # AD proximity: 1 at the positive centroid, decaying to 0 at the Tier2/Tier3 abstention
    # boundary (mu + 2*sigma), clipped so far-outlier fragments don't go negative.
    ad_boundary = mu + 2 * sigma
    ad_proximity = np.clip(1.0 - fragments["ad_distance"] / ad_boundary, 0.0, 1.0)
    fragments["combined_score"] = np.round(
        0.5 * fragments["sim_c1"] + 0.5 * fragments["prob_c2"] * ad_proximity, 4
    )
    fragments["abstention_flag"] = fragments["ad_tier"].map(
        {"Tier1": "GREEN", "Tier2": "AMBER", "Tier3_abstain": "RED_ABSTAIN"}
    )
    fragments["predictor_reliability"] = predictor_flag

    fragments = fragments.sort_values("combined_score", ascending=False).reset_index(drop=True)
    fragments.insert(0, "candidate_id", ["PLANT_" + str(i).zfill(4) for i in range(1, len(fragments) + 1)])

    ranked = fragments.head(TOP_N_CANDIDATES).copy()
    ranked.to_parquet(ARTIFACT_DIR / "plant_candidates.parquet", index=False)
    ranked.drop(columns=DESCRIPTOR_COLS).to_json(ARTIFACT_DIR / "plant_candidates.json", orient="records", indent=2)
    print(f"Saved plant_candidates (top {len(ranked)} of {len(fragments)} by combined score)")

    # --- AD summary ---
    tier_counts = fragments["ad_tier"].value_counts().to_dict()
    ad_summary = {
        "reference_cloud": "descriptor-space centroid of real training-eligible AOP-BenchPos positives",
        "n_reference_sequences": int(len(train_eligible)),
        "mu": round(mu, 4),
        "sigma": round(sigma, 4),
        "n_candidates": int(len(fragments)),
        "tier_counts": {t: int(tier_counts.get(t, 0)) for t in ["Tier1", "Tier2", "Tier3_abstain"]},
    }
    (ARTIFACT_DIR / "ad_summary.json").write_text(json.dumps(ad_summary, indent=2))

    # --- PARRS: applicability-domain enrichment of the top-ranked candidates ---
    top_n = ranked.head(50)
    ef_top = float((top_n["ad_tier"] == "Tier1").mean())
    ef_full = float((fragments["ad_tier"] == "Tier1").mean())
    parrs = round(ef_top / ef_full, 4) if ef_full > 0 else None
    parrs_report = {
        "definition": "PARRS = enrichment_factor(Tier1 among top-50 ranked) / enrichment_factor(Tier1 among all candidates)",
        "ef_top50": round(ef_top, 4),
        "ef_full_pool": round(ef_full, 4),
        "parrs": parrs,
        "interpretation": "PARRS > 1 means the ranking preferentially surfaces in-domain (Tier1) candidates rather than ranking by chance.",
    }
    (ARTIFACT_DIR / "parrs_report.json").write_text(json.dumps(parrs_report, indent=2))

    # --- PDSS: plant distributional shift score ---
    mean_plant_ad = float(fragments["ad_distance"].mean())
    mean_benchpos_ad = float(pos_self_distance.mean())
    pdss = round(mean_plant_ad / mean_benchpos_ad, 4) if mean_benchpos_ad > 0 else None
    pdss_report = {
        "definition": "PDSS = mean(AD distance of plant fragments) / mean(AD self-distance of AOP-BenchPos positives)",
        "mean_plant_ad_distance": round(mean_plant_ad, 4),
        "mean_benchpos_ad_distance": round(mean_benchpos_ad, 4),
        "pdss": pdss,
        "interpretation": "PDSS close to 1 means the plant digestome sits inside the same descriptor distribution as the training positives; PDSS >> 1 flags distributional shift.",
    }
    (ARTIFACT_DIR / "pdss_report.json").write_text(json.dumps(pdss_report, indent=2))

    # --- ARR: abstention-adjusted retrieval rate among top nominations ---
    top_nominations = ranked.head(20)
    arr = round(float((top_nominations["ad_tier"] != "Tier3_abstain").mean()), 4)
    arr_report = {
        "definition": "ARR = fraction of the top-20 ranked candidates that are NOT abstained (AD tier != Tier3)",
        "n_top_nominations": int(len(top_nominations)),
        "arr": arr,
        "interpretation": "ARR close to 1 means the framework can make a confident, non-abstained call on nearly all of its own top picks.",
    }
    (ARTIFACT_DIR / "arr_report.json").write_text(json.dumps(arr_report, indent=2))

    # --- Evidence cards for the top candidates ---
    evidence_cards = []
    for _, row in ranked.head(TOP_K_EVIDENCE).iterrows():
        evidence_cards.append({
            "candidate_id": row["candidate_id"],
            "sequence": row["sequence"],
            "plant_species": row["plant_species"],
            "source_protein": row["source_protein"],
            "enzyme": row["enzyme"],
            "length": int(row["length"]),
            "physicochemical_summary": {
                "molecular_weight": round(float(row["mw"]), 2),
                "gravy": round(float(row["gravy"]), 3),
                "net_charge": round(float(row["charge_ph7"]), 3),
                "aromaticity": round(float(row["aromaticity"]), 3),
            },
            "sim_c1": float(row["sim_c1"]),
            "prob_c2": float(row["prob_c2"]),
            "ad_distance": float(row["ad_distance"]),
            "ad_tier": row["ad_tier"],
            "combined_score": float(row["combined_score"]),
            "abstention_flag": row["abstention_flag"],
            "predictor_reliability": {predictor_name: predictor_flag},
            "interpretation": "Computationally prioritized candidate. Not experimentally validated.",
        })
    (ARTIFACT_DIR / "evidence_cards.json").write_text(json.dumps(evidence_cards, indent=2))
    print(f"Saved {len(evidence_cards)} evidence cards")

    summary = {
        "component": "C4_PlantAOP_Screen",
        "prototype_mode": True,
        "data_mode": "real_uniprot_proteome_real_digestion_real_c1c2c3_integration",
        "source": "25 reviewed UniProt Arabidopsis thaliana antioxidant/defense-keyword proteins (KW-0929)",
        "n_source_proteins": int(fragments["source_protein"].nunique()),
        "n_candidate_fragments": int(len(fragments)),
        "ad_tier_counts": ad_summary["tier_counts"],
        "parrs": parrs,
        "pdss": pdss,
        "arr": arr,
        "notes": [
            "Digestion (trypsin+pepsin cleavage rules), descriptor computation, C2 predictor "
            "probabilities, and the C3 reliability flag are all real and computed live from "
            "upstream component artifacts.",
            "AD distance uses descriptor-space standardized-Euclidean distance (documented Level-3 fallback), "
            "not ESM-2 embedding distance, since no embeddings were computed for plant fragments.",
            "Input proteome is a real but small (25-protein) UniProt subset, standing in for "
            "the full multi-species plant digestome planned for the full project.",
        ],
    }
    (ARTIFACT_DIR / "c4_summary.json").write_text(json.dumps(summary, indent=2))
    print("Component 4 prototype artifacts generated successfully.")


if __name__ == "__main__":
    main()
