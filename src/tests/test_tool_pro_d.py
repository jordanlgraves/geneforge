import os
import sys
import unittest

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.session_state import SessionState
from src.functions import (
    EstimatePromoterStrengthWithProDTool,
    GetSpacerFromPromoterTool,
    GeneratePromoterLibraryFromSpacerTool,
    GeneratePromoterLibraryFromPromoterTool
)

class TestProDTools(unittest.TestCase):
    """Tests for ProD integration tools."""

    @classmethod
    def setUpClass(cls):
        cls.session_state = SessionState()
        # Select a library known to have pAmtR for ID-based tests
        if not cls.session_state.select_library("Eco1C1G1T1"):
            # If library not found, we can't run ID-based tests.
            # We can skip them later if session_state.current_library_id is None.
            print("Warning: Could not select library 'Eco1C1G1T1'. ID-based tests may be skipped.")

        cls.estimate_tool = EstimatePromoterStrengthWithProDTool(cls.session_state)
        cls.spacer_tool = GetSpacerFromPromoterTool(cls.session_state)
        cls.lib_from_spacer_tool = GeneratePromoterLibraryFromSpacerTool(cls.session_state)
        cls.lib_from_promoter_tool = GeneratePromoterLibraryFromPromoterTool(cls.session_state)

    def test_estimate_promoter_strength_by_id(self):
        """Test estimating promoter strength for a promoter ID from the selected UCF."""

        args = {'promoter': 'pAmtR', 'file_type': 'ucf'}
        result = self.estimate_tool.execute(**args)

        self.assertTrue(result.get("success"), result.get("error", "Tool execution failed"))
        self.assertIn("promoter_sequence", result)
        self.assertIn("spacer", result)
        self.assertIn("class", result)
        self.assertIn("ymax", result)
        self.assertIsInstance(result["class"], int)

    def test_estimate_promoter_strength_by_sequence(self):
        """Test estimating promoter strength for a raw DNA sequence."""
        # pAmtR sequence from Eco1C1G1T1
        pAmtR_seq = "TTGACAGCTAGCTCAGTCCTAGGGATTGTGCTAGC"
        result = self.estimate_tool.execute(promoter=pAmtR_seq)

        self.assertTrue(result.get("success"), result.get("error", "Tool execution failed"))
        self.assertIn("class", result)
        self.assertEqual(result["promoter_sequence"], pAmtR_seq)
        self.assertEqual(result["spacer"], "GCTAGCTCAGTCCTAGG")

    def test_get_spacer_from_promoter(self):
        """Test extracting a spacer from a full promoter sequence."""
        pAmtR_seq = "TTGACAGCTAGCTCAGTCCTAGGGATTGTGCTAGC"
        expected_spacer = "GCTAGCTCAGTCCTAGG"
        
        result = self.spacer_tool.execute(promoter=pAmtR_seq)
        
        self.assertTrue(result.get("success"), result.get("error", "Tool execution failed"))
        self.assertEqual(result.get("spacer"), expected_spacer)

    def test_get_spacer_from_promoter_by_id(self):
        """Test extracting a spacer from a part id/name."""
        result = self.spacer_tool.execute(promoter="pAmtR")
        self.assertTrue(result.get("success"), result.get("error", "Tool execution failed"))
        self.assertEqual(result.get("spacer"), "GTTTCTATCGATCTATA")

    def test_generate_library_from_spacer(self):
        """Test generating a promoter library from a degenerate spacer blueprint."""
        # Using a degenerate spacer from ProD documentation examples
        blueprint = "NNNNNNNNNTATNNNNN"
        result = self.lib_from_spacer_tool.execute(
            blueprint=blueprint,
            desired_strengths=[3, 7],
            sequences_per_class=2
        )
        self.assertTrue(result.get("success"), result.get("error", "Tool execution failed"))
        self.assertIn("variants", result)
        self.assertEqual(len(result["variants"]), 4) # 2 classes * 2 seqs
        first_variant = result["variants"][0]
        self.assertIn("spacer", first_variant)
        self.assertIn("class", first_variant)
        self.assertEqual(len(first_variant["spacer"]), 17)

    def test_generate_library_from_spacer_2(self):
        """
        generate_library_from_spacer with args: {'blueprint': 'GTNNCTATCGATCTATA', 'desired_strengths': [7], 'sequences_per_class': 1, 'parent_promoter': 'pAmtR'}
        """
        result = self.lib_from_spacer_tool.execute(
            blueprint="GTNNCTATCGATCTATA",
            desired_strengths=[1,2,3,4,7, 8, 9, 10],
            sequences_per_class=1,
            parent_promoter="pAmtR"
        )
        self.assertTrue(result.get("success"))
        self.assertIn("variants", result)
        self.assertTrue(len(result["variants"]) > 1)
        for variant in result["variants"]:
            self.assertIn("spacer", variant)
            self.assertEqual(len(variant["spacer"]), 17)

    def test_generate_library_from_promoter(self):
        """Test generating variants by mutating an existing promoter."""

        mutable_positions = {"10": "N", "11": "W", "12": "S"}
        result = self.lib_from_promoter_tool.execute(
            promoter="pAmtR",
            mutable_positions=mutable_positions,
            desired_strengths=[5],
            sequences_per_class=3,
            file_type="ucf"
        )
        self.assertTrue(result.get("success"), result.get("error", "Tool execution failed"))
        self.assertIn("variants", result)
        self.assertEqual(len(result["variants"]), 3)
        first_variant = result["variants"][0]
        self.assertIn("promoter_sequence", first_variant) # flanks should be added
        self.assertIn("pAmtR", result.get("parent_promoter", ""))

    
    def test_generate_library_from_promoter_with_mutations_3(self):
        """
        {
            "blueprint":"GTTTCTATCGATCTATN"
            "desired_strengths":[
            0:6
            ]
            "sequences_per_class":3
            "parent_promoter":"pAmtR"
        }
        """
        result = self.lib_from_promoter_tool.execute(
            promoter="pAmtR",
            desired_strengths=[0,1,2,3,4,5,6],
            sequences_per_class=3,
        )
        self.assertIsNotNone(result.get("error"))
        

if __name__ == "__main__":
    unittest.main(verbosity=2)