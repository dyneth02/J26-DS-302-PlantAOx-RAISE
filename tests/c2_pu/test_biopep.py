"""Tests for curation/biopep.py (Bucket 2.4 -- BIOPEP-UWM antioxidative
reference set), against a small synthetic HTML fixture mirroring the
site's real table structure (no live network calls in CI).
"""

from __future__ import annotations

from unittest.mock import patch

from plantaox.c2_pu.curation.biopep import fetch_biopep_by_activity

_FIXTURE_HTML = """
<html><body>
<table>
<tr><td bgcolor="#eeeeff">ID</td></tr>
<tr class="info">
    <td nowrap><a href="peptide_data_page1.php?zm_ID=9916">Peptide
      Data</a>&nbsp;</td>
    <td nowrap>9916&nbsp;</td>
    <td nowrap>Antioxidative peptide&nbsp;</td>
    <td nowrap>AGPSIVH&nbsp;</td>
    <td nowrap>679.7630&nbsp;</td>
    <td nowrap>679.3642&nbsp;</td>
    <td nowrap>antioxidative&nbsp;</td>
    <td nowrap>AEFJWHJXCUHKLX-UDMYPXPJSA-N&nbsp;</td>
</tr>
<tr class="info">
    <td nowrap><a href="peptide_data_page1.php?zm_ID=3301">Peptide
      Data</a>&nbsp;</td>
    <td nowrap>3301&nbsp;</td>
    <td nowrap>&nbsp;</td>
    <td nowrap>HLH&nbsp;</td>
    <td nowrap>405.4504&nbsp;</td>
    <td nowrap>405.2119&nbsp;</td>
    <td nowrap>antioxidative&nbsp;</td>
    <td nowrap>BPOHQCZZSFBSON-KKUMJFAQSA-N&nbsp;</td>
</tr>
</table>
</body></html>
"""


def test_fetch_biopep_by_activity_parses_rows():
    with patch("plantaox.c2_pu.curation.biopep._get_with_retries", return_value=_FIXTURE_HTML):
        records = fetch_biopep_by_activity("antioxidative")
    assert len(records) == 2
    assert records[0] == {
        "id": "9916",
        "name": "Antioxidative peptide",
        "sequence": "AGPSIVH",
        "chem_mass": "679.7630",
        "monois_mass": "679.3642",
        "activity": "antioxidative",
        "inchikey": "AEFJWHJXCUHKLX-UDMYPXPJSA-N",
    }
    assert records[1]["name"] == ""  # some rows have no name, must not crash
    assert records[1]["sequence"] == "HLH"


def test_fetch_biopep_by_activity_strips_nbsp_and_whitespace():
    with patch("plantaox.c2_pu.curation.biopep._get_with_retries", return_value=_FIXTURE_HTML):
        records = fetch_biopep_by_activity("antioxidative")
    assert all("\xa0" not in v for r in records for v in r.values() if isinstance(v, str))
    assert all(v == v.strip() for r in records for v in r.values() if isinstance(v, str))
