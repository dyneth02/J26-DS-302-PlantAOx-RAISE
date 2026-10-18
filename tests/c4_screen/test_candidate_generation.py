from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from plantaox.c4_screen.dedup import deduplicate
from plantaox.c4_screen.descriptors import describe
from plantaox.c4_screen.digest import RULE_NAMES, digest_protein
from plantaox.c4_screen.filters import filter_fragments
from plantaox.c4_screen.run import run_digest


def toy_protein():
    # Deliberately contains both trypsin and pepsin recognition contexts.
    return {"plant": "toy", "accession": "P00001", "sequence": "MKWVTFISLLFLFSSAYS" * 4}


def test_pyteomics_rules_and_parent_coordinates():
    from pyteomics import parser

    assert RULE_NAMES["pepsin"] in parser.expasy_rules
    assert RULE_NAMES["trypsin"] in parser.expasy_rules
    protein = toy_protein()
    fragments = digest_protein(protein)
    assert fragments
    for item in fragments:
        assert protein["sequence"][item["start"] - 1:item["end"]] == item["sequence"]
        assert item["enzyme_path"] == "pepsin_ph1.3>trypsin"


def test_filter_constraints_and_exact_dedup_provenance():
    rows = [
        {"plant": "soybean", "sequence": "ACD", "parent_accession": "P1", "start": 1, "end": 3,
         "enzyme_path": "pepsin_ph1.3>trypsin"},
        {"plant": "rice", "sequence": "ACD", "parent_accession": "P2", "start": 4, "end": 6,
         "enzyme_path": "pepsin_ph1.3>trypsin"},
        {"plant": "soybean", "sequence": "AAA", "parent_accession": "P1", "start": 7, "end": 9,
         "enzyme_path": "pepsin_ph1.3>trypsin"},
        {"plant": "soybean", "sequence": "AC", "parent_accession": "P1", "start": 1, "end": 2,
         "enzyme_path": "pepsin_ph1.3>trypsin"},
    ]
    kept, _ = filter_fragments(rows)
    assert [x["sequence"] for x in kept] == ["ACD", "ACD"]
    candidates, membership = deduplicate(kept)
    assert [x["sequence"] for x in candidates] == ["ACD"]
    assert candidates[0]["n_parents"] == 2
    assert {x["plant"] for x in membership} == {"soybean", "rice"}
    assert all(3 <= len(x["sequence"]) <= 20 and len(set(x["sequence"])) >= 2 for x in candidates)


def test_descriptors_are_finite():
    assert all(pd.notna(value) for value in describe("ACDEFG" ).values())


def test_two_digest_runs_are_byte_identical(tmp_path):
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio import SeqIO

    raw = tmp_path / "raw"
    raw.mkdir()
    plant = "toy"
    records = [SeqRecord(Seq(toy_protein()["sequence"]), id="sp|P00001|TOY", description="")]
    with (raw / "toy.fasta").open("w") as handle:
        SeqIO.write(records, handle, "fasta")
    config = {"plants": {plant: {}}, "missed_cleavages": 0,
              "length": {"min": 3, "max": 20}, "min_unique_amino_acids": 2}
    first, second = tmp_path / "one", tmp_path / "two"
    run_digest(config, raw, first)
    run_digest(config, raw, second)
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes(), path.name


def test_attached_mock_signals_generate_and_validate(tmp_path):
    utility = Path(__file__).parent / "fixtures" / "mock_signals.py"
    candidates = tmp_path / "candidates.parquet"
    pd.DataFrame({"sequence": ["ACD", "KLMN", "WQERTY"]}).to_parquet(candidates, index=False)
    out = tmp_path / "signals"
    for args in (("generate", "--candidates", str(candidates), "--out", str(out), "--seed", "42"),
                 ("validate", "--candidates", str(candidates), "--dir", str(out))):
        result = subprocess.run([sys.executable, str(utility), *args], capture_output=True,
                                text=True, check=False, env={**os.environ, "PYTHONHASHSEED": "0"})
        assert result.returncode == 0, result.stdout + result.stderr
    for name in ("c1_sim.parquet", "c2_prob.parquet"):
        assert set(pd.read_parquet(out / name)["source"]) == {"mock"}
    manifest = json.loads((out / "MOCK_MANIFEST.json").read_text())
    assert "MOCK DATA" in manifest["note"]
