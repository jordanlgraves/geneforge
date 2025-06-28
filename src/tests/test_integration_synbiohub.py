import os
import sys
import unittest

# Ensure project root on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.tools.synbiohub_integration import SynBioHubClient


class TestSynBioHubIntegration(unittest.TestCase):
    """Basic integration tests against the public synbiohub.org instance.

    These tests use only *public* endpoints, so no credentials are required.
    If environment variables `SYNBIOHUB_USERNAME_OR_EMAIL` and `SYNBIOHUB_PASSWORD`
    are provided the client will auto-login, otherwise we disable auto_login.
    """

    @classmethod
    def setUpClass(cls):
        # Create client without auto login to avoid credential requirement
        cls.client = SynBioHubClient(auto_login=False)
        # Use a well-known public part URI (iGEM registry promoter BBa_J23100)
        cls.test_part_uri = "https://synbiohub.org/public/igem/BBa_J23100/1"

    # ------------------------------------------------------------------
    #  Search endpoint
    # ------------------------------------------------------------------
    def test_search_public_database(self):
        """Search for a common keyword and ensure we get non-empty result."""
        query = "pLac"
        result = self.client.search(query, limit=10)
        self.assertIsInstance(result, str)
        # The result should contain at least one line / object
        self.assertGreater(len(result), 0, "Search result should not be empty")

    # ------------------------------------------------------------------
    #  Download SBOL
    # ------------------------------------------------------------------
    def test_download_part_sbol(self):
        """Download SBOL for a public part and verify basic structure."""
        content = self.client.download_part(self.test_part_uri, fmt="sbol")
        self.assertIsInstance(content, (bytes, bytearray))
        self.assertGreater(len(content), 100, "SBOL file should be >100 bytes")
        text_start = content[:50].decode("utf-8", errors="ignore").lower()
        self.assertTrue("rdf" in text_start or "sbol" in text_start,
                        "SBOL content should contain RDF/SBOL markers")

    # ------------------------------------------------------------------
    #  Download FASTA
    # ------------------------------------------------------------------
    def test_download_part_fasta(self):
        """Download FASTA for the same part and verify it starts with '>'."""
        content = self.client.download_part(self.test_part_uri, fmt="fasta")
        self.assertGreater(len(content), 10, "FASTA content too small")
        self.assertTrue(content.startswith(b">"), "FASTA should start with '>' character")


if __name__ == "__main__":
    unittest.main(verbosity=2)
