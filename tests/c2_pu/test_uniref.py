"""Tests for curation/uniref.py (Bucket 2.3 -- C3 candidate universe),
against a mocked UniProt REST API (no live network calls in CI).
"""

from __future__ import annotations

import json
from unittest.mock import patch

from plantaox.c2_pu.curation.uniref import fetch_uniref50_candidates, fetch_uniref50_page


class _FakeResponse:
    def __init__(self, body: dict, link_header: str | None):
        self._body = json.dumps(body).encode("utf-8")
        self.headers = {"Link": link_header} if link_header else {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _page(ids_and_seqs, next_url=None):
    body = {
        "results": [
            {
                "id": pid,
                "name": "Cluster: Uncharacterized protein",
                "representativeMember": {"sequence": {"value": seq, "length": len(seq)}},
            }
            for pid, seq in ids_and_seqs
        ]
    }
    link = f'<{next_url}>; rel="next"' if next_url else None
    return _FakeResponse(body, link)


def test_fetch_uniref50_page_parses_results_and_next_cursor():
    fake = _page([("UniRef50_A", "ACDEFG")], next_url="https://rest.uniprot.org/uniref/search?cursor=abc")
    with patch("plantaox.c2_pu.curation.uniref.urllib.request.urlopen", return_value=fake):
        results, next_url = fetch_uniref50_page("https://rest.uniprot.org/uniref/search")
    assert len(results) == 1
    assert results[0]["id"] == "UniRef50_A"
    assert next_url == "https://rest.uniprot.org/uniref/search?cursor=abc"


def test_fetch_uniref50_page_returns_none_next_url_on_last_page():
    fake = _page([("UniRef50_A", "ACDEFG")], next_url=None)
    with patch("plantaox.c2_pu.curation.uniref.urllib.request.urlopen", return_value=fake):
        _, next_url = fetch_uniref50_page("https://rest.uniprot.org/uniref/search")
    assert next_url is None


def test_fetch_uniref50_candidates_paginates_until_target_size(monkeypatch):
    pages = [
        _page(
            [("UniRef50_A", "ACDEFG"), ("UniRef50_B", "GHIKLM")],
            next_url="https://rest.uniprot.org/uniref/search?cursor=page2",
        ),
        _page(
            [("UniRef50_C", "MNPQRS"), ("UniRef50_D", "STVWYA")],
            next_url="https://rest.uniprot.org/uniref/search?cursor=page3",
        ),
        _page([("UniRef50_E", "CDEFGH")], next_url=None),
    ]
    call_count = {"n": 0}

    def fake_urlopen(request, timeout=30.0):
        page = pages[call_count["n"]]
        call_count["n"] += 1
        return page

    monkeypatch.setattr("plantaox.c2_pu.curation.uniref.urllib.request.urlopen", fake_urlopen)
    records = fetch_uniref50_candidates(target_size=4, page_size=2, request_delay=0)
    assert len(records) == 4
    assert records[0] == ("UniRef50_A Cluster: Uncharacterized protein", "ACDEFG")
    assert call_count["n"] == 2  # stopped as soon as target_size was reached


def test_fetch_uniref50_candidates_stops_when_query_exhausted(monkeypatch):
    pages = [_page([("UniRef50_A", "ACDEFG")], next_url=None)]
    call_count = {"n": 0}

    def fake_urlopen(request, timeout=30.0):
        page = pages[call_count["n"]]
        call_count["n"] += 1
        return page

    monkeypatch.setattr("plantaox.c2_pu.curation.uniref.urllib.request.urlopen", fake_urlopen)
    records = fetch_uniref50_candidates(target_size=100, page_size=2, request_delay=0)
    assert len(records) == 1  # query exhausted long before target_size
