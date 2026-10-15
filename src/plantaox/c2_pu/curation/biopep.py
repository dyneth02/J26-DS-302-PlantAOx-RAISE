"""Bucket 2.4 -- BIOPEP-UWM antioxidative-peptide reference set, for the
external known-AOP screen of C1/C2/C3 (Planner Bucket 2.3/2.4; see
IMPLEMENTATION_STATUS.md Known Issue #11).

BIOPEP-UWM (https://biochemia.uwm.edu.pl/biopep/) is open-access, no
registration required (confirmed via its own "open access" framing and
absence of a login wall on every page touched here). Its own citation
request (not a redistribution license, since no formal license terms were
published site-wide): Minkiewicz P, Iwaniak A, Darewicz M. "BIOPEP-UWM
database of bioactive peptides: current opportunities." Int J Mol Sci.
2019;20(23):5978. doi:10.3390/ijms20235978.

The site's own "search by activity" page (``peptide_data_search.php``)
returns every matching peptide as one server-rendered HTML table -- for
the "antioxidative" activity code, 1,039 rows on a single page, no
pagination needed (confirmed by matching the page's own reported "Number
of peptides" count against the number of distinct peptide ids parsed).
Scraped directly via stdlib ``urllib`` (no API exists), same "filtered
query over anything resembling a bulk dump" preference as C1/C3's UniProt
queries -- there is no bulk-download alternative to scrape here, only
this HTML page.

AODB and DFBP are NOT covered by this module: AODB's server returned a
hard 502 (confirmed via direct ``curl``, both with and without TLS
verification) at the time of this audit -- genuinely inaccessible, not
skipped. DFBP has no discoverable hosting URL (the 2022 paper, PubMed
35552640, was found, but neither the paper's page nor web search surfaced
an access link) -- see IMPLEMENTATION_STATUS.md for the full account of
what was tried.
"""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

BIOPEP_SEARCH_URL = "https://biochemia.uwm.edu.pl/biopep/peptide_data_search.php"
BIOPEP_CITATION = (
    "Minkiewicz P, Iwaniak A, Darewicz M. BIOPEP-UWM database of bioactive "
    "peptides: current opportunities. Int J Mol Sci. 2019;20(23):5978. "
    "doi:10.3390/ijms20235978"
)

_ROW_RE = re.compile(r'<tr class="info">(.*?)</tr>', re.S)
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_cell(cell_html: str) -> str:
    text = _TAG_RE.sub("", cell_html)
    return text.replace("&nbsp;", "").strip()


def _get_with_retries(url: str, timeout: float, max_retries: int, retry_backoff: float) -> str:
    """Same retry/backoff discipline as curation/uniref.py -- this
    connection has repeatedly dropped mid-transfer on other large fetches
    this session."""
    request = urllib.request.Request(url, headers={"Accept": "text/html"})
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(retry_backoff * (2**attempt))
    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts") from last_error


def fetch_biopep_by_activity(
    activity_code: str, timeout: float = 60.0, max_retries: int = 5, retry_backoff: float = 2.0
) -> list[dict]:
    """Scrape every peptide tagged ``activity_code`` (BIOPEP-UWM's own
    short activity codes, e.g. "antioxidative" -- see
    ``activity_dic_list.php``) from its single-page HTML search result.

    Returns a list of dicts: id, name, sequence, chem_mass, monois_mass,
    activity, inchikey -- straight from the table, unfiltered (callers
    apply their own alphabet/length/screening logic, same separation of
    concerns as curation/uniref.py and curation/peptipedia.py).
    """
    url = f"{BIOPEP_SEARCH_URL}?{urlencode({'txt_search': activity_code, 'menu_search': 'activity'})}"
    html = _get_with_retries(url, timeout, max_retries, retry_backoff)

    records = []
    for row_html in _ROW_RE.findall(html):
        cells = [_clean_cell(c) for c in _CELL_RE.findall(row_html)]
        if len(cells) < 7:
            continue
        _link, id_, name, sequence, chem_mass, monois_mass, activity, *rest = cells
        records.append(
            {
                "id": id_,
                "name": name,
                "sequence": sequence,
                "chem_mass": chem_mass,
                "monois_mass": monois_mass,
                "activity": activity,
                "inchikey": rest[0] if rest else None,
            }
        )
    return records
