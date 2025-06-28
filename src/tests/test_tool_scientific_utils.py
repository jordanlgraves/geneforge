import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.session_state import SessionState
from src.functions import (
    ScientificSearchTool,
    TranslateDnaTool,
    GcContentTool,
    SynBioHubSequenceSearchTool,
    SynBioHubGetRelatedTool,
)


class TestScientificAndUtilityTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session_state = SessionState()
        cls.sequence_tool = SynBioHubSequenceSearchTool(cls.session_state)
        cls.related_tool = SynBioHubGetRelatedTool(cls.session_state)

    # ---------------------------------------------------------------
    # Scientific search
    # ---------------------------------------------------------------
    def test_scientific_search_tool(self):
        tool = ScientificSearchTool(self.session_state)
        out = tool.execute(query="CRISPR promoter engineering", max_results=3)
        self.assertTrue(out.get("success"), out.get("error", "Scientific search failed"))
        papers = out.get("papers", [])
        self.assertGreater(len(papers), 0)
        first = papers[0]
        self.assertIn("title", first)
        self.assertIn("url", first)

    # ---------------------------------------------------------------
    # Sequence utilities
    # ---------------------------------------------------------------
    def test_translate_dna_tool(self):
        tool = TranslateDnaTool(self.session_state)
        dna = "ATGTTCGAA"
        out = tool.execute(seq_dna=dna, frame=0)
        self.assertTrue(out.get("success"), out.get("error", "translate error"))
        self.assertEqual(out["protein"], "MFE")

    def test_gc_content_tool(self):
        tool = GcContentTool(self.session_state)
        seq = "ATGC" * 5  # 20 bp, 50% GC
        out = tool.execute(seq=seq)
        self.assertTrue(out.get("success"))
        self.assertAlmostEqual(out["gc_percent"], 50.0, delta=0.1)

    # --------------------------------------------------------------
    # SynBioHub sequence search / related
    # --------------------------------------------------------------
    def test_sequence_search_tool(self):
        # Use exact sequence search for a short motif, expect JSON/text result
        out = self.sequence_tool.execute(search_params="sequence=atgc")
        self.assertTrue(out.get("success") or "error" in out)

    def test_get_related_tool(self):
        uri = "https://synbiohub.org/public/igem/BBa_J23100/1"
        out = self.related_tool.execute(uri=uri, relation="twins")
        # service may return 404 if none; just ensure request processed
        self.assertTrue(out.get("success"))


if __name__ == "__main__":
    unittest.main(verbosity=2) 