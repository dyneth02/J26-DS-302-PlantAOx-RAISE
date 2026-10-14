"""Bucket 2.3 (FR2/C3) -- UniRef50 candidate-fragment-universe acquisition
via UniProt's REST API, paginated with its cursor-based ``Link`` header.

Mirrors C1's "filtered query, not a bulk database dump" approach (AGENTS.md
rule 6): UniRef50's full bulk FASTA is ~13GB (already rejected for C1 for
exactly this reason, see PU_AOP_RESEARCH_CONTEXT.md section 4) and is not
needed here either -- a length-windowed, identity-0.5-clustered REST query
returns a bounded, versioned candidate set directly.

Unlike C1's UniProtKB query, UniRef50's search index has no ``keyword:``
field (confirmed empirically -- UniProt returns "'keyword' is not a valid
search field" for the uniref endpoint), so the query-level bioactivity
exclusion C1 used isn't available here. The secondary free-text blocklist
(``pools.py::apply_secondary_blocklist``) is applied downstream instead, the
same defense-in-depth pattern already used for C1 -- expected to catch
fewer matches here since most UniRef50 representatives are unreviewed
TrEMBL entries named generically ("Uncharacterized protein"), not an error.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

UNIREF50_BASE_URL = "https://rest.uniprot.org/uniref/search"
UNIREF50_QUERY = "identity:0.5 AND length:[3 TO 50]"
UNIREF50_FIELDS = "id,name,length,sequence"
UNIREF50_SORT = "id asc"  # explicit, not the implicit default -- deterministic pagination

_LINK_CURSOR_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def fetch_uniref50_page(
    url: str, timeout: float = 60.0, max_retries: int = 5, retry_backoff: float = 2.0
) -> tuple[list[dict], str | None]:
    """One paginated request, with retry/backoff on transient network errors
    (this connection has already been observed to drop/timeout mid-transfer
    on other large acquisitions in this project -- see IMPLEMENTATION_STATUS.md).
    Raises the last error if every retry is exhausted, rather than silently
    returning an empty page that would truncate the candidate universe
    without anyone noticing.
    """
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                link_header = response.headers.get("Link")
            next_url = None
            if link_header:
                match = _LINK_CURSOR_RE.search(link_header)
                if match:
                    next_url = match.group(1)
            return payload.get("results", []), next_url
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(retry_backoff * (2**attempt))
    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts") from last_error


def fetch_uniref50_candidates(
    target_size: int,
    page_size: int = 500,
    query: str = UNIREF50_QUERY,
    sort: str = UNIREF50_SORT,
    request_delay: float = 0.34,
) -> list[tuple[str, str]]:
    """Paginate the UniRef50 REST query until ``target_size`` cluster
    representatives are collected (or the query is exhausted first).

    Returns a list of (header, sequence) tuples in the exact order UniProt
    returned them -- ``header`` is ``"<UniRef50_id> <cluster name>"``, kept
    FASTA-like so the existing blocklist/parsing helpers built for C1's
    UniProtKB headers can scan it for free-text bioactivity terms.
    """
    params = {"query": query, "format": "json", "fields": UNIREF50_FIELDS, "sort": sort, "size": page_size}
    url = f"{UNIREF50_BASE_URL}?{urlencode(params)}"

    records: list[tuple[str, str]] = []
    while url and len(records) < target_size:
        results, url = fetch_uniref50_page(url)
        if not results:
            break
        for entry in results:
            member = entry.get("representativeMember", {})
            sequence = member.get("sequence", {}).get("value")
            if not sequence:
                continue
            header = f"{entry['id']} {entry.get('name', '')}".strip()
            records.append((header, sequence))
        if url:
            time.sleep(request_delay)
    return records[:target_size]
