from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def c4_client(tmp_path, monkeypatch) -> TestClient:
    root = tmp_path / "c4_fixture"
    diagnostics = root / "diagnostics"
    embeddings = root / "embeddings"
    signals = root / "signals"
    for directory in (diagnostics, embeddings, signals):
        directory.mkdir(parents=True)
    monkeypatch.setenv("C4_DATA_DIR", str(root))

    provenance = json.dumps([
        {"parent_accession": "PARENT1", "plant": "rice", "start": 3, "end": 5,
         "enzyme_path": "pepsin_ph1.3>trypsin"}
    ])
    pd.DataFrame([
        {"sequence": "ACD", "peptide_id": "p1", "length": 3, "n_parents": 1,
         "provenance": provenance, "molecular_weight": 307.3, "isoelectric_point": 5.2,
         "gravy": 0.1, "net_charge_ph7": -0.2},
        {"sequence": "WYKF", "peptide_id": "p2", "length": 4, "n_parents": 1,
         "provenance": provenance, "molecular_weight": 600.4, "isoelectric_point": 8.1,
         "gravy": -0.3, "net_charge_ph7": 0.8},
    ]).to_parquet(root / "candidates.parquet", index=False)
    pd.DataFrame([
        {"peptide_id": "p1", "sequence": "ACD", "plant": "rice"},
        {"peptide_id": "p1", "sequence": "ACD", "plant": "soybean"},
        {"peptide_id": "p2", "sequence": "WYKF", "plant": "rice"},
    ]).to_parquet(root / "plant_membership.parquet", index=False)
    pd.DataFrame([
        {"peptide_id": "p1", "sequence": "ACD", "d_AD": 0.1, "d_norm": 0.3,
         "tier": 1, "embedded": True, "cloud_source": "mock_cloud"},
        {"peptide_id": "p2", "sequence": "WYKF", "d_AD": 0.9, "d_norm": 1.0,
         "tier": 3, "embedded": True, "cloud_source": "mock_cloud"},
    ]).to_parquet(root / "c4_ad_tiers.parquet", index=False)

    ranked = []
    for plant, tier, peptide_id, sequence, d_ad, d_norm, cs, rank in [
        ("rice", 1, "p1", "ACD", 0.1, 0.3, 0.7, 1),
        ("soybean", 1, "p1", "ACD", 0.1, 0.3, 0.7, 1),
        ("rice", 3, "p2", "WYKF", 0.9, 1.0, 0.0, 2),
    ]:
        ranked.append({
            "peptide_id": peptide_id, "sequence": sequence, "d_AD": d_ad,
            "d_norm": d_norm, "tier": tier, "embedded": True, "cloud_source": "mock_cloud",
            "SIM_C1": 0.8, "SIM_C1_source": "mock", "PROB_C2": 0.7,
            "evidence_tier": "U", "PROB_C2_source": "mock", "plant": plant,
            "molecular_weight": 307.3 if peptide_id == "p1" else 600.4,
            "isoelectric_point": 5.2 if peptide_id == "p1" else 8.1,
            "gravy": 0.1 if peptide_id == "p1" else -0.3,
            "net_charge_ph7": -0.2 if peptide_id == "p1" else 0.8,
            "length": len(sequence), "provenance": provenance, "CS": cs, "rank": rank,
        })
    pd.DataFrame(ranked).to_parquet(root / "c4_ranked_candidates.parquet", index=False)
    pd.DataFrame([
        {"plant": "rice", "proteins": 1, "protein_exclusions": 0, "raw_fragments": 5,
         "length_filtered": 2, "composition_filtered": 2, "deduplicated": 2},
        {"plant": "soybean", "proteins": 1, "protein_exclusions": 0, "raw_fragments": 2,
         "length_filtered": 1, "composition_filtered": 1, "deduplicated": 1},
    ]).to_csv(root / "funnel_summary.csv", index=False)
    pd.DataFrame([
        {"plant": plant, "tier": tier, "fraction": fraction, "n": n}
        for plant, vals in {"rice": [(1, .5, 1), (3, .5, 1)], "soybean": [(1, 1., 1)]}.items()
        for tier, fraction, n in vals
    ]).to_csv(diagnostics / "tier_fractions_by_plant.csv", index=False)
    pd.DataFrame([
        {"plant": "rice", "length_bin": "3-10", "tier": 1, "fraction": .5, "n": 1},
        {"plant": "rice", "length_bin": "3-10", "tier": 3, "fraction": .5, "n": 1},
        {"plant": "soybean", "length_bin": "3-10", "tier": 1, "fraction": 1., "n": 1},
    ]).to_csv(diagnostics / "tier_fractions_by_length_bin.csv", index=False)
    pd.DataFrame([
        {"analysis": "MEAN_CENTERING_SENSITIVITY_ONLY", "group": "all_candidates",
         "length_bin": "all", "n": 2, "tier": 1, "baseline_fraction": .5,
         "mean_centered_fraction": .5, "fraction_delta": 0., "thresholds_tuned": False,
         "reference_source": "mock_cloud"}
    ]).to_csv(diagnostics / "mean_centering_tier_fraction_sensitivity.csv", index=False)
    pd.DataFrame([
        {"id": "MOCK0000", "sequence": "AA", "evidence_tier": "MOCK",
         "source": "mock_cloud", "is_plant": False},
        {"id": "MOCK0001", "sequence": "AAA", "evidence_tier": "MOCK",
         "source": "mock_cloud", "is_plant": False},
    ]).to_csv(root / "ref_cloud_meta.csv", index=False)
    np.save(embeddings / "ref_cloud.npy", np.asarray([[1., 0.], [0., 1.]], dtype=np.float16))
    (root / "ad_params.json").write_text(json.dumps({
        "cloud_source": "mock_cloud", "cloud_is_mock": True, "n_cloud": 2,
        "mu_cloud": .2, "sigma_cloud": .1, "t1": .3, "t2": .4,
    }), encoding="utf-8")
    (root / "summary.json").write_text(json.dumps({
        "cloud": {"source": "mock_cloud", "n_sequences": 2, "mock": True},
        "signal_sources": {"SIM_C1": "mock", "PROB_C2": "mock", "BCS": "mock", "cloud": "mock_cloud"},
    }), encoding="utf-8")
    (root / "c4_output_manifest.json").write_text(json.dumps({"cloud_source": "mock_cloud", "files": []}), encoding="utf-8")
    (root / "c4_embedding_manifest.json").write_text(json.dumps({"model": "esm2_t33_650M_UR50D", "dim": 1280, "n": 2}), encoding="utf-8")
    (signals / "MOCK_MANIFEST.json").write_text(json.dumps({"source": "mock", "injected_demo_cases": ["ACD"]}), encoding="utf-8")
    (signals / "c3_bcs.json").write_text(json.dumps({"source": "mock", "schema_version": "c4-interface-0.1-provisional",
        "strata": [{"mechanism": "ALL", "length_bin": "3-10", "BCS": .4}]}), encoding="utf-8")

    with TestClient(app) as client:
        yield client
