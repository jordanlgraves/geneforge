from __future__ import annotations

import logging
import time
import urllib.parse
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Base URL for the BioNumbers website
_BIONUMBERS_BASE_URL = "https://bionumbers.hms.harvard.edu/"

# Search endpoint (regular website search page)
_BIONUMBERS_SEARCH_URL = urllib.parse.urljoin(_BIONUMBERS_BASE_URL, "search.aspx")


def search_bionumbers(
    query: str,
    max_results: int = 10,
    retries: int = 3,
    backoff_factor: float = 1.0,
) -> List[Dict[str, Any]]:
    """Search the BioNumbers database and return parsed results.

    This function performs a web‐scraping request to the BioNumbers website because a
    public API is not (currently) available. It **only** fetches the search results
    page – it does *not* crawl individual record pages. For many workflows this is
    sufficient and avoids generating excessive traffic to the BioNumbers servers.

    Args:
        query: Free‐text search term (e.g. "protein half life").
        max_results: Maximum number of records to return. Defaults to ``10``.
        retries: Number of retry attempts when the HTTP request fails.
        backoff_factor: Base delay (in seconds) for exponential back-off between
            retries (``delay = backoff_factor * 2 ** (attempt-1)``).

    Returns:
        A list of dictionaries, each containing the keys
        ``bnid``, ``name``, ``value``, ``organism``, ``source`` and ``url``. If a
        column cannot be found the corresponding entry is an empty string.

    Raises:
        ValueError: If *query* is empty.
        requests.HTTPError: On non-successful response after exhausting retries.
    """

    if not query:
        raise ValueError("query must not be empty")

    # BioNumbers uses the query-string parameter ``trm=<search-term>``. A form submit
    # also includes ``task=search`` but that appears optional. We include only the
    # essential ``trm`` to keep the request minimal.
    params = {"trm": query}

    attempt = 0
    while True:
        attempt += 1
        try:
            response = requests.get(_BIONUMBERS_SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            break  # Successful request
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
            if attempt >= retries:
                logger.error("BioNumbers search failed after %d attempt(s): %s", attempt, exc)
                raise

            delay = backoff_factor * (2 ** (attempt - 1))
            logger.info(
                "BioNumbers search attempt %d/%d failed: %s. Retrying in %.1f s…",
                attempt,
                retries,
                exc,
                delay,
            )
            time.sleep(delay)

    soup = BeautifulSoup(response.text, "html.parser")

    # The results page is rendered as an HTML <table>. On 2025-06 it looks roughly
    # like this (header row followed by data):
    #
    # | BNID | Description | Value | Organism | Source | … |
    #
    # We attempt to be robust to potential future layout tweaks by focusing on rows
    # that contain an <a> tag whose "href" links to the record detail page.

    table = soup.find("table")
    if table is None:
        logger.warning("No <table> element found on BioNumbers results page – layout may have changed.")
        return []

    results: List[Dict[str, Any]] = []

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            # Header or empty row
            continue

        link_tag = cells[0].find("a", href=True)
        if link_tag is None:
            # Unexpected layout. Skip.
            continue

        text = link_tag.get_text(strip=True)
        href = link_tag["href"]
        record_url = urllib.parse.urljoin(_BIONUMBERS_BASE_URL, href)

        # Defensive: Ensure we always create the dict with expected keys.
        col_text = [c.get_text(strip=True) for c in cells]
        # Pad to at least 5 elements.
        while len(col_text) < 5:
            col_text.append("")

        results.append(
            {
                "description": text,
                "organism": col_text[1],
                "value": col_text[2],
                "units": col_text[3],
                "bnid": col_text[4],
                "url": record_url,
            }
        )

        if len(results) >= max_results:
            break

    return results


# __all__ = ["search_bionumbers"] 
if __name__ == "__main__":
    results = search_bionumbers("protein degradation rate of GFP")
    print(results)