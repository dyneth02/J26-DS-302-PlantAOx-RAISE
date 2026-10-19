"""Traceable top-candidate cards and abstention lists."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _bcs_by_bin(bcs: dict) -> dict[str, float]:
    return {row["length_bin"]: float(row["BCS"])
            for row in bcs.get("strata", []) if row.get("mechanism") == "ALL"}


def _reliability_flag(value: float, low: float, high: float) -> str:
    return "LOW" if value < low else ("HIGH" if value >= high else "MEDIUM")


def make_cards(ranked: pd.DataFrame, config: dict, mock_manifest: dict, bcs: dict,
               output_path: str | Path | None = None) -> dict:
    flags = config.get("bcs_flag", {})
    low, high = float(flags.get("low_below", .5)), float(flags.get("high_at_or_above", .7))
    bcs_values = _bcs_by_bin(bcs)
    injected = set(mock_manifest.get("injected_demo_cases", []))
    plant_names = {key: value["scientific_name"] for key, value in config["plants"].items()}
    output = {"mock_notice": "DUMMY SIGNALS / MOCK CLOUD", "cloud_source": "mock_cloud",
              "signals_source": "mock", "plants": {}}
    for plant, group in ranked.groupby("plant", sort=True):
        visible = group[group.tier.astype(int).isin([1, 2])].sort_values(["CS", "sequence"], ascending=[False, True])
        cards = []
        for row in visible.head(50).itertuples(index=False):
            length = int(getattr(row, "length", len(row.sequence)))
            length_bin = "3-10" if length <= 10 else "11-20"
            bcs_value = bcs_values.get(length_bin)
            provenance = json.loads(row.provenance) if isinstance(row.provenance, str) else []
            cards.append({"sequence": row.sequence, "peptide_id": row.peptide_id, "species": plant_names.get(plant, plant),
                "plant": plant, "provenance": provenance,
                "physicochemical": {"molecular_weight": getattr(row, "molecular_weight", None),
                    "pI": getattr(row, "isoelectric_point", None), "GRAVY": getattr(row, "gravy", None),
                    "net_charge_ph7": getattr(row, "net_charge_ph7", None)},
                "SIM_C1": float(row.SIM_C1), "PROB_C2": float(row.PROB_C2),
                "evidence_tier": row.evidence_tier, "tier": int(row.tier), "d_AD": float(row.d_AD),
                "flag": "GREEN" if int(row.tier) == 1 else "AMBER", "CS": float(row.CS), "rank": int(row.rank),
                "BCS": bcs_value, "BCS_flag": None if bcs_value is None else _reliability_flag(bcs_value, low, high),
                "BCS_threshold_status": "C4-provisional", "BCS_warning": bool(bcs_value is not None and bcs_value < low),
                "signal_sources": {"SIM_C1": row.SIM_C1_source, "PROB_C2": row.PROB_C2_source,
                                   "BCS": bcs.get("source", "mock")},
                "cloud_source": "mock_cloud", "injected_demo_case": row.sequence in injected,
                "notice": "DUMMY SIGNALS / MOCK CLOUD"})
        abstained = []
        for row in group[group.tier.astype(int) == 3].sort_values("sequence").itertuples(index=False):
            abstained.append({"sequence": row.sequence, "peptide_id": row.peptide_id, "plant": plant,
                              "tier": 3, "flag": "RED", "CS": 0.0,
                              "injected_demo_case": row.sequence in injected,
                              "notice": "DUMMY SIGNALS / MOCK CLOUD"})
        output["plants"][plant] = {"top_50": cards, "abstained": abstained}
    if output_path is not None:
        path = Path(output_path); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return output
