import unittest
import os
import json
from src.library.ucf_retrieval import *
from src.library.parse_ucf import parse_ecoli_ucf
import uuid

class TestUCFRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Load the UCF library once for all tests"""
        ucf_path = "libs/cello-ucf/Eco1C1G1T0.UCF.json"
        if not os.path.exists(ucf_path):
            raise FileNotFoundError(f"Test UCF file not found: {ucf_path}")
            
        # Load raw JSON first to inspect contents
        with open(ucf_path, 'r') as f:
            cls.raw_ucf = json.load(f)
            
        cls.library_data = parse_ecoli_ucf(ucf_path)["structured_data"]
        
        # Debug: Print all parts and their IDs
        print("\n=== Available Parts ===")
        for part in cls.library_data.get("parts", []):
            print(f"Part ID: {part.get('id')}")
            print(f"Part type: {part.get('type')}")
            print(f"Raw data type: {part.get('raw_data', {}).get('type')}")
            print("---")

        # Debug: Print all gates
        print("\n=== Available Gates ===")
        for gate in cls.library_data.get("gates", []):
            print(f"Gate ID: {gate.get('id')}")
            print(f"Gate type: {gate.get('gate_type')}")
            print("---")

    def test_load_ecoli_library(self):
        """Test loading the library file"""
        import tempfile
        import shutil

        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        try:
            # Source UCF file
            ucf_path = "libs/cello-ucf/Eco1C1G1T0.UCF.json"
            
            # Create processed file path in temp directory
            processed_path = os.path.join(temp_dir, "Eco1C1G1T0.processed.json")
            
            # Process the UCF file and save it
            processed_data = parse_ecoli_ucf(ucf_path)
            with open(processed_path, 'w') as f:
                json.dump(processed_data, f)

            # Verify the processed file was created
            self.assertTrue(os.path.exists(processed_path), 
                           "Failed to create processed file")

            # Test loading raw UCF file (should fail)
            with self.assertRaises(ValueError):
                load_ecoli_library(ucf_path)

            # Test nonexistent file - this should raise FileNotFoundError
            non_existent_path = os.path.join(temp_dir, "definitely_does_not_exist.json")
            self.assertFalse(os.path.exists(non_existent_path), 
                            "Test file should not exist")
            try:
                load_ecoli_library(non_existent_path)
                self.fail("Expected FileNotFoundError was not raised")
            except FileNotFoundError as e:
                # Test passes - the expected error was raised
                pass

            # Test loading the processed file (should succeed)
            data = load_ecoli_library(processed_path)
            self.assertIn("parts", data)
            self.assertIn("gates", data)
            self.assertIn("experimental_data", data)

        finally:
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)

    def test_get_all_gates(self):
        """Test retrieving all gates"""
        gates = get_all_gates(self.library_data)
        self.assertIsInstance(gates, list)
        self.assertTrue(len(gates) > 0)
        
        # Check gate structure
        first_gate = gates[0]
        self.assertIn("id", first_gate)
        self.assertIn("raw_data", first_gate)

    def test_get_gate_by_id(self):
        """Test retrieving specific gates by ID"""
        # Test with known gate IDs
        amtr_gate = get_gate_by_id(self.library_data, "AmtR")
        self.assertIsNotNone(amtr_gate)
        self.assertEqual(amtr_gate["id"].lower(), "amtr")

        # Test case insensitivity
        amtr_gate_lower = get_gate_by_id(self.library_data, "amtr")
        self.assertEqual(amtr_gate, amtr_gate_lower)

        # Test nonexistent gate
        nonexistent = get_gate_by_id(self.library_data, "NonexistentGate")
        self.assertIsNone(nonexistent)

    def test_get_gates_by_type(self):
        """Test retrieving gates by type"""
        nor_gates = get_gates_by_type(self.library_data, "NOR")
        self.assertTrue(len(nor_gates) > 0)
        for gate in nor_gates:
            self.assertEqual(gate["gate_type"].lower(), "nor")

        # Test case insensitivity
        nor_gates_lower = get_gates_by_type(self.library_data, "nor")
        self.assertEqual(nor_gates, nor_gates_lower)

    def test_get_all_parts(self):
        """Test retrieving all parts"""
        parts = get_all_parts(self.library_data)
        self.assertIsInstance(parts, list)
        self.assertTrue(len(parts) > 0)
        
        # Check part structure
        first_part = parts[0]
        self.assertIn("id", first_part)
        self.assertIn("sequence", first_part)
        self.assertIn("raw_data", first_part)

    def test_get_part_by_id(self):
        """Test retrieving specific parts by ID"""
        # Test with known part (AmtR exists in the library)
        amtr = get_part_by_id(self.library_data, "AmtR")
        self.assertIsNotNone(amtr)
        self.assertEqual(amtr["id"], "AmtR")
        self.assertIn("sequence", amtr)
        self.assertEqual(amtr["raw_data"]["type"], "cds")

        # Test with a known promoter
        pamtr = get_part_by_id(self.library_data, "pAmtR")
        self.assertIsNotNone(pamtr)
        self.assertEqual(pamtr["id"], "pAmtR")
        self.assertEqual(pamtr["raw_data"]["type"], "promoter")

        # Test nonexistent part
        nonexistent = get_part_by_id(self.library_data, "NonexistentPart")
        self.assertIsNone(nonexistent)

    def test_get_parts_by_type(self):
        """Test retrieving parts by type"""
        dna_parts = get_parts_by_type(self.library_data, "dna_part")
        self.assertTrue(len(dna_parts) > 0)
        for part in dna_parts:
            self.assertEqual(part["type"], "dna_part")

    def test_list_dna_parts_by_keyword(self):
        """Test searching parts by keyword"""
        # Test with parts we know exist
        amtr_parts = list_dna_parts_by_keyword(self.library_data, "AmtR")
        self.assertTrue(len(amtr_parts) > 0)
        self.assertTrue(all("amtr" in p["id"].lower() for p in amtr_parts))

        # Test case insensitivity
        amtr_parts_upper = list_dna_parts_by_keyword(self.library_data, "AMTR")
        self.assertEqual(amtr_parts, amtr_parts_upper)

        # Test with a known promoter
        phlf_parts = list_dna_parts_by_keyword(self.library_data, "PhlF")
        self.assertTrue(len(phlf_parts) > 0)
        self.assertTrue(any("pphlf" in p["id"].lower() for p in phlf_parts))

    def test_get_dna_part_by_name(self):
        """Test retrieving DNA parts by name"""
        # Test with a part we know exists from the debug output
        amtr = get_dna_part_by_name(self.library_data, "AmtR")
        self.assertIsNotNone(amtr)
        self.assertEqual(amtr["id"], "AmtR")
        self.assertEqual(amtr["raw_data"]["type"], "cds")

        # Test case insensitivity
        amtr_lower = get_dna_part_by_name(self.library_data, "amtr")
        self.assertEqual(amtr, amtr_lower)

        # Test with a promoter
        pamtr = get_dna_part_by_name(self.library_data, "pAmtR")
        self.assertIsNotNone(pamtr)
        self.assertEqual(pamtr["raw_data"]["type"], "promoter")

        # Test nonexistent part
        nonexistent = get_dna_part_by_name(self.library_data, "NonexistentPart")
        self.assertIsNone(nonexistent)

    def test_list_promoters(self):
        """Test retrieving promoter parts"""
        promoters = list_promoters(self.library_data)
        self.assertTrue(len(promoters) > 0)
        
        # Check for promoters we know exist from the debug output
        promoter_ids = [p["id"].lower() for p in promoters]
        self.assertTrue(
            any(pid in promoter_ids for pid in ["pamtr", "pbm3r1", "pphlf", "psrpr"]),
            "No expected promoters found"
        )

    def test_list_terminators(self):
        """Test retrieving terminator parts"""
        terminators = list_terminators(self.library_data)
        self.assertTrue(len(terminators) > 0)
        
        # Check for terminators we know exist from the debug output
        terminator_ids = [t["id"].lower() for t in terminators]
        self.assertTrue(
            any(tid in terminator_ids for tid in ["l3s2p55", "l3s2p11", "eck120033736", "eck120033737"]),
            "No expected terminators found"
        )
        
        # Verify they're actually terminators
        for term in terminators:
            self.assertTrue(
                "terminator" in term["id"].lower() or 
                term["raw_data"].get("type", "").lower() == "terminator"
            )

    def test_choose_repressor(self):
        """Test retrieving repressor parts"""
        # Test without family specification first
        repressors = choose_repressor(self.library_data)
        self.assertTrue(len(repressors) > 0)
        print("\nFound repressors:", [r["id"] for r in repressors])

        # Test with specific families that exist in the data
        for family in ["SrpR", "BetI", "PhlF", "AmtR"]:  # Update based on actual data
            family_repressors = choose_repressor(self.library_data, family)
            print(f"\nTesting {family} family:", [r["id"] for r in family_repressors])
            self.assertTrue(len(family_repressors) > 0, 
                          f"No repressors found for family {family}")
            self.assertTrue(all(family.lower() in r["id"].lower() 
                              for r in family_repressors))

    def test_get_experimental_data_for_gate(self):
        """Test retrieving experimental data for gates"""
        # First get all gates to find one that exists
        gates = get_all_gates(self.library_data)
        if not gates:
            self.skipTest("No gates found in library")
        
        # Use the first gate as a test case
        test_gate = gates[0]
        gate_data = get_experimental_data_for_gate(self.library_data, test_gate["id"])
        
        # Note: If there's no experimental data in the UCF, we should modify the test
        # to check the structure rather than requiring data
        self.assertIsInstance(gate_data, list)
        
        # Test nonexistent gate
        nonexistent = get_experimental_data_for_gate(self.library_data, "NonexistentGate")
        self.assertEqual(len(nonexistent), 0)

    def test_list_misc_items(self):
        """Test retrieving miscellaneous items"""
        misc_items = list_misc_items(self.library_data)
        self.assertIsInstance(misc_items, list)

    def test_list_unrecognized_items(self):
        """Test retrieving unrecognized items"""
        unrec_items = list_unrecognized_items(self.library_data)
        self.assertIsInstance(unrec_items, list)

if __name__ == '__main__':
    unittest.main(verbosity=2) 