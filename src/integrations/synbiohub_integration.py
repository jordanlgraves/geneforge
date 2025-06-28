"""Light-weight SynBioHub REST client (MVP).

Only the most common operations are implemented:
  • automatic login using env vars → token cached per session
  • search metadata
  • download part in SBOL / FASTA / GenBank / …
  • submit a design file

This module is intentionally minimal; extend as needed.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

import requests

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

DEFAULT_SBH_URL = os.getenv("SYNBIOHUB_URL", "https://synbiohub.org")
ENV_USER = os.getenv("SYNBIOHUB_USERNAME_OR_EMAIL")
ENV_PASS = os.getenv("SYNBIOHUB_PASSWORD")

# ---------------------------------------------------------------------------
#  Client
# ---------------------------------------------------------------------------


class SynBioHubClient:
    """Small wrapper around the SynBioHub REST API (token-based auth)."""

    def __init__(
        self,
        base_url: str = DEFAULT_SBH_URL,
        email: Optional[str] = ENV_USER,
        password: Optional[str] = ENV_PASS,
        auto_login: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self._token: Optional[str] = None

        if auto_login and self.email and self.password:
            self.login()  # may raise

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    @property
    def token(self) -> Optional[str]:
        return self._token

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        hdr: Dict[str, str] = {"Accept": "text/plain"}
        if self._token:
            hdr["X-authorization"] = self._token
        if extra:
            hdr.update(extra)
        return hdr

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            resp = requests.request(method, url, **kwargs, timeout=30)
            resp.raise_for_status()
            return resp
        except requests.HTTPError as exc:
            logger.error("SynBioHub HTTP error: %s", exc)
            raise

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    # Login happens automatically in __init__, but method is public for re-login.
    def login(self) -> str:
        """Authenticate and cache token. Returns token string."""
        if not self.email or not self.password:
            raise RuntimeError("SynBioHub credentials not set in env or params.")

        url = f"{self.base_url}/login"
        resp = self._request(
            "POST",
            url,
            headers={"Accept": "text/plain"},
            data={"email": self.email, "password": self.password},
        )
        self._token = resp.text.strip()
        logger.info("Logged in to SynBioHub – token length %d", len(self._token))
        return self._token

    # --------------------------- SEARCH ---------------------------------
    def search(self, query: str, offset: int | None = None, limit: int | None = None) -> str:
        """Return raw search metadata (text/JSON) for *query* string.

        `query` is the portion that usually follows `/search/` in the API.
        """
        url = f"{self.base_url}/search/{query}"
        if offset is not None or limit is not None:
            url += f"?offset={offset or 0}&limit={limit or 20}"
        resp = self._request("GET", url, headers=self._headers())
        return resp.text

    # --------------------------- SEQUENCE SEARCH ----------------------
    def sequence_search(self, search_params: str) -> str:
        """Run a sequence-based search (search/... endpoint) and return raw JSON/text."""
        # Endpoint identical to generic search; expose for clarity
        return self.search(search_params)

    # --------------------------- DOWNLOAD ------------------------------
    def download_part(self, uri: str, fmt: str = "sbol") -> bytes:
        """Download a part/collection in the specified *fmt* (sbol, fasta, gb, gff, metadata)."""
        fmt = fmt.lower()
        if fmt not in {"sbol", "fasta", "gb", "gff", "sbolnr", "metadata"}:
            raise ValueError(f"Unsupported format: {fmt}")

        endpoint = uri.rstrip("/") + ("" if fmt == "sbol" else f"/{fmt}")
        if fmt == "sbol":
            endpoint += "/sbol"

        resp = self._request("GET", endpoint, headers=self._headers())
        return resp.content

    # --------------------------- SUBMIT --------------------------------
    def submit(
        self,
        file_path: str,
        submission_id: str,
        version: str,
        name: str,
        description: str,
        citations: str = "",
        overwrite_merge: int = 0,
    ) -> str:
        """Submit a file (SBOL / GenBank / FASTA / zip) to a new collection."""

        if not self._token:
            self.login()  # ensure we have token

        url = f"{self.base_url}/submit"
        with open(file_path, "rb") as fh:
            files = {"files": fh}
            data = {
                "id": submission_id,
                "version": version,
                "name": name,
                "description": description,
                "citations": citations,
                "overwrite_merge": str(overwrite_merge),
            }
            resp = self._request(
                "POST",
                url,
                headers=self._headers(),
                files=files,
                data=data,
            )
        return resp.text

    # --------------------------- RELATED QUERIES ----------------------
    def get_related(self, uri: str, relation: str) -> str:
        """Fetch 'uses', 'twins', or 'similar' for a given SBH object URI."""
        relation = relation.lower()
        if relation not in {"uses", "twins", "similar"}:
            raise ValueError("relation must be one of 'uses', 'twins', 'similar'")
        resp = self._request("GET", f"{uri.rstrip('/')}/{relation}", headers=self._headers())
        return resp.text

    # ------------------------------------------------------------------
    #  String representation
    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover
        return f"<SynBioHubClient url={self.base_url} token={'yes' if self._token else 'no'}>"