"""Scientific literature search integration using Semantic Scholar API.

Returns simplified metadata useful for the agent (title, abstract, url, year).
"""

from __future__ import annotations

import logging
import os
import time
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def scientific_search(
    query: str,
    max_results: int = 5,
    fields: Optional[str] = None,
    retries: int = 3,
    backoff_factor: float = 1.0,
) -> List[Dict[str, Any]]:
    """Query Semantic Scholar and return list of paper metadata dicts.

    Args:
        query: Free-text search string.
        max_results: Number of hits to return.
        fields: Comma-separated Semantic Scholar fields (defaults to a sensible subset).
        retries: Maximum number of attempts before giving up. Defaults to ``3``.
        backoff_factor: Base delay in seconds for exponential back-off between retries. Delay is
            calculated as ``backoff_factor * 2 ** (attempt - 1)`` where *attempt* starts at 1.
    """

    if not query:
        raise ValueError("query must not be empty")

    fields = fields or "title,abstract,year,url,authors"

    params = {
        "query": query,
        "limit": max_results,
        "fields": fields,
    }

    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.get(SEMANTIC_SCHOLAR_URL, params=params, timeout=30)
            resp.raise_for_status()
            break  # Successful request – exit retry loop
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
            if attempt >= retries:
                logger.error("ScientificSearch failed after %d attempt(s): %s", attempt, exc)
                raise

            sleep_seconds = backoff_factor * (2 ** (attempt - 1))
            logger.info(
                "ScientificSearch attempt %d/%d failed: %s. Retrying in %.1f s…",
                attempt,
                retries,
                exc,
                sleep_seconds,
            )
            time.sleep(sleep_seconds)

    data = resp.json()
    papers = data.get("data", [])

    results: List[Dict[str, Any]] = []
    for p in papers:
        results.append({
            "title": p.get("title"),
            "abstract": p.get("abstract"),
            "url": p.get("url"),
            "year": p.get("year"),
            "authors": ", ".join(a.get("name", "") for a in p.get("authors", [])[:5]),
        })
    return results 