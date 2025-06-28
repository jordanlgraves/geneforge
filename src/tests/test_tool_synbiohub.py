import os
import sys
import unittest

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.session_state import SessionState
from src.functions import (
    SynBioHubSearchTool,
    SynBioHubDownloadPartTool,
)


class TestSynBioHubTools(unittest.TestCase):
    """Tests for SynBioHub tool wrappers (search & download)."""

    @classmethod
    def setUpClass(cls):
        cls.session_state = SessionState()  # auto-instantiates SynBioHub client (public access)
        # well-known public part URI (iGEM promoter BBa_J23100 v1)
        cls.part_uri = "https://synbiohub.org/public/igem/BBa_J23100/1"

    # ------------------------------------------------------------------
    #  Search tool
    # ------------------------------------------------------------------
    def test_search_tool(self):
        tool = SynBioHubSearchTool(self.session_state)
        result = tool.execute(query="pLac", offset=0, limit=5)

        # Basic structure
        self.assertTrue(result.get("success"), result.get("error", "Search failed"))
        self.assertIn("raw", result)
        self.assertGreater(len(result["raw"]), 0, "Raw search output should not be empty")

    # ------------------------------------------------------------------
    #  Download tool (SBOL & FASTA)
    # ------------------------------------------------------------------
    def test_download_part_sbol_tool(self):
        tool = SynBioHubDownloadPartTool(self.session_state)
        out = tool.execute(uri=self.part_uri, format="sbol")
        self.assertTrue(out.get("success"), out.get("error", "Download failed"))
        self.assertEqual(out["format"], "sbol")
        self.assertGreater(out["bytes"], 100)

    def test_download_part_fasta_tool(self):
        tool = SynBioHubDownloadPartTool(self.session_state)
        out = tool.execute(uri=self.part_uri, format="fasta")
        self.assertTrue(out.get("success"), out.get("error", "Download failed"))
        self.assertEqual(out["format"], "fasta")
        self.assertGreater(out["bytes"], 10)
        # first char should be '>' in base64 truncated representation decoded earlier; we skip strict check


if __name__ == "__main__":
    unittest.main(verbosity=2)
