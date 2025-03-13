import unittest
import os
import json
import tempfile
from src.library.ucf_customizer import UCFCustomizer
from src.library.library_manager import LibraryManager

class TestUCFCustomization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Load base UCF and create temp directory"""
        # Use the library manager to find a suitable library
        cls.library_manager = LibraryManager()
        
        # Try to select an E. coli library
        success = cls.library_manager.select_library("ecoli")
        if not success:
            # If no E. coli library, try any available library
            available_libraries = cls.library_manager.get_available_libraries()
            success = cls.library_manager.select_library(available_libraries[0])
            
        # Get the UCF path from the library manager
        library_info = cls.library_manager.get_current_library_info()
        cls.base_ucf_path = library_info["ucf_path"]
        
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_dir = cls.temp_dir.name
        
        # Load sample data from base UCF
        with open(cls.base_ucf_path) as f:
            cls.base_data = json.load(f)
        
        # Create a customizer to help extract parts
        cls.customizer = UCFCustomizer(cls.base_ucf_path)
        
        # Find some sample gates and parts for testing
        cls.sample_gate_ids = []
        cls.sample_part_ids = []
        
        # Extract gates
        for item in cls.base_data:
            if isinstance(item, dict) and item.get("collection") == "gates":
                gate_id = item.get("gate_name")
                if gate_id:
                    cls.sample_gate_ids.append(gate_id)
                    if len(cls.sample_gate_ids) >= 2:
                        break
        
        # Extract parts
        for item in cls.base_data:
            if isinstance(item, dict) and item.get("collection") == "parts":
                if "parts" in item and isinstance(item["parts"], list):
                    for part in item["parts"]:
                        part_id = part.get("name")
                        if part_id:
                            cls.sample_part_ids.append(part_id)
                            if len(cls.sample_part_ids) >= 4:
                                break
        
        print(f"Using gate IDs: {cls.sample_gate_ids}")
        print(f"Using part IDs: {cls.sample_part_ids}")


    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_minimal_ucf(self):
        """Test creating UCF with selected gates only"""
        customizer = UCFCustomizer(self.base_ucf_path)
        
        # Create custom UCF with first 2 gates
        ucf_path = customizer.create_custom_ucf(
            selected_gates=self.sample_gate_ids,
            ucf_name="minimal.ucf.json",
            output_dir=self.test_dir
        )
        
        # Verify file creation
        self.assertTrue(os.path.exists(ucf_path))
        
        # Verify gate selection
        with open(ucf_path) as f:
            custom_data = json.load(f)
            
        # In this UCF format, gates are individual collection items
        gate_ids = []
        for item in custom_data:
            if isinstance(item, dict) and item.get("collection") == "gates":
                gate_id = item.get("gate_name")
                if gate_id:
                    gate_ids.append(gate_id)
        
        # Check if our selected gates are included
        for gate_id in self.sample_gate_ids:
            self.assertIn(gate_id, gate_ids, f"Gate {gate_id} should be in the custom UCF")

    def test_part_filtering(self):
        """Test filtering of parts collections"""
        customizer = UCFCustomizer(self.base_ucf_path)
            
        print(f"\nTest part filtering with parts: {self.sample_part_ids}")
        
        # Create UCF with specific parts
        ucf_path = customizer.create_custom_ucf(
            selected_parts=self.sample_part_ids,
            output_dir=self.test_dir
        )
        
        with open(ucf_path) as f:
            custom_data = json.load(f)
            
        # Verify parts filtering
        parts_found = False
        
        # In this UCF format, parts may be individual collection items
        for item in custom_data:
            if isinstance(item, dict) and item.get("collection") == "parts":
                part_id = item.get("name")
                if part_id in self.sample_part_ids:
                    parts_found = True
                    print(f"Found matching part: {part_id}")
                    break
                
                # Also check if there's a parts array
                if "parts" in item and isinstance(item["parts"], list):
                    parts = item["parts"]
                    part_ids = [p.get("name") or p.get("id") for p in parts]
                    print(f"Found {len(part_ids)} parts in parts collection: {part_ids}")
                    
                    # Check if any of our sample parts are in this collection
                    for part_id in part_ids:
                        if part_id in self.sample_part_ids:
                            parts_found = True
                            print(f"Found matching part: {part_id}")
                            break
        
        self.assertTrue(parts_found, "No selected parts found in custom UCF")

    def test_part_modification(self):
        """Test modifying part parameters"""
        customizer = UCFCustomizer(self.base_ucf_path)
        
        # Use the first sample part if available
        if len(self.sample_part_ids) > 0:
            modified_part = self.sample_part_ids[0]
        
        modifications = {
            "parameters": {"strength": 2.5},
            "type": "modified_promoter"
        }
        
        ucf_path = customizer.create_custom_ucf(
            modified_parts={modified_part: modifications},
            output_dir=self.test_dir
        )
        
        with open(ucf_path) as f:
            custom_data = json.load(f)
            
        # Find the modified part in the UCF
        modified = None
        
        # In this UCF format, parts may be individual collection items
        for item in custom_data:
            if isinstance(item, dict) and item.get("collection") == "parts":
                # Check if this is the part itself
                part_id = item.get("name") or item.get("id")
                if part_id == modified_part:
                    modified = item
                    break
                
                # Also check if there's a parts array
                if "parts" in item and isinstance(item["parts"], list):
                    for part in item["parts"]:
                        part_id = part.get("name") or part.get("id")
                        if part_id == modified_part:
                            modified = part
                            break
                    
                    if modified:
                        break
        
        self.assertIsNotNone(modified, f"Modified part {modified_part} not found in UCF")
        self.assertEqual(modified["type"], "modified_promoter")
        self.assertEqual(modified["parameters"]["strength"], 2.5)

    def test_new_part_addition(self):
        """Test adding new synthetic parts"""
        customizer = UCFCustomizer(self.base_ucf_path)
        new_promoter = {
            "name": "syn_pTEST",
            "type": "promoter",
            "dnasequence": "ATGC",
            "parameters": {"strength": 1.2}
        }
        
        ucf_path = customizer.create_custom_ucf(
            new_parts=[new_promoter],
            output_dir=self.test_dir
        )
        
        with open(ucf_path) as f:
            custom_data = json.load(f)
            
        # Find the parts collection
        parts_collection = None
        for item in custom_data:
            if isinstance(item, dict) and item.get("collection") == "parts":
                parts_collection = item
                break
                
        self.assertIsNotNone(parts_collection, "Parts collection should exist")
        
        # Find our new part
        added = None
        for part in parts_collection.get("parts", []):
            if part.get("name") == "syn_pTEST":
                added = part
                break
                
        self.assertIsNotNone(added, "New part should be in the UCF")
        self.assertEqual(added["dnasequence"], "ATGC")

    def test_invalid_part_handling(self):
        """Test handling of invalid part IDs"""
        customizer = UCFCustomizer(self.base_ucf_path)
        
        # Shouldn't raise errors for invalid IDs
        ucf_path = customizer.create_custom_ucf(
            selected_gates=["invalid_gate"],
            selected_parts=["invalid_part"],
            output_dir=self.test_dir
        )
        
        # Load the generated UCF
        with open(ucf_path) as f:
            custom_data = json.load(f)
            
        # Check for empty gate collection
        gates_found = False
        for item in custom_data:
            if isinstance(item, dict) and item.get("collection") == "gates":
                gates = item.get("gates", [])
                if len(gates) > 0:
                    for gate in gates:
                        gate_id = gate.get("name") or gate.get("id")
                        self.assertNotEqual(gate_id, "invalid_gate", "Invalid gate should not be in UCF")
                        gates_found = True
        
        # Check for empty parts collection
        parts_found = False
        for item in custom_data:
            if isinstance(item, dict) and item.get("collection") == "parts":
                parts = item.get("parts", [])
                if len(parts) > 0:
                    for part in parts:
                        part_id = part.get("name") or part.get("id")
                        self.assertNotEqual(part_id, "invalid_part", "Invalid part should not be in UCF")
                        parts_found = True

    def test_ucf_validation(self):
        """Test generated UCF structure validation"""
        customizer = UCFCustomizer(self.base_ucf_path)
        
        # Create a regular UCF
        ucf_path = customizer.create_custom_ucf(output_dir=self.test_dir)
        
        # Test validation method directly
        validation_result = customizer.validate_ucf()
        self.assertTrue(validation_result['valid'], 
                       f"Base UCF should be valid: {validation_result['errors']}")
        
        # Validate the generated file
        with open(ucf_path) as f:
            custom_data = json.load(f)
            
        validation_result = customizer.validate_ucf(custom_data)
        self.assertTrue(validation_result['valid'], 
                       f"Generated UCF should be valid: {validation_result['errors']}")
            
        # Basic structure checks
        self.assertTrue(isinstance(custom_data, list), "UCF should be an array")
        
        # Check for required collections
        collection_types = [item.get("collection") for item in custom_data if isinstance(item, dict)]
        self.assertIn("header", collection_types, "UCF should contain a header collection")
        self.assertIn("parts", collection_types, "UCF should contain a parts collection")

    def test_part_field_alignment(self):
        """Test automatic alignment of part fields to match schema requirements"""
        customizer = UCFCustomizer(self.base_ucf_path)
        
        # Test with "id" instead of "name" and "sequence" instead of "dnasequence"
        new_part_wrong_fields = {
            "id": "syn_pFIELD_TEST",  # should be converted to "name"
            "type": "promoter",
            "sequence": "ATGCATGC",   # should be converted to "dnasequence"
            "parameters": {"strength": 1.5}
        }
        
        ucf_path = customizer.create_custom_ucf(
            new_parts=[new_part_wrong_fields],
            output_dir=self.test_dir
        )
        
        with open(ucf_path) as f:
            custom_data = json.load(f)
            
        # Find the part collection
        parts_collection = next(item for item in custom_data if isinstance(item, dict) 
                               and item.get("collection") == "parts")
        
        # Find our specific part
        added_part = next(p for p in parts_collection.get("parts", []) 
                        if p.get("name") == "syn_pFIELD_TEST")
        
        # Verify field conversion
        self.assertIn("name", added_part, "Field 'id' should be converted to 'name'")
        self.assertIn("dnasequence", added_part, "Field 'sequence' should be converted to 'dnasequence'")
        self.assertEqual(added_part["dnasequence"], "ATGCATGC")
        
        # Validate the UCF is valid after these transformations
        validation_result = customizer.validate_ucf(custom_data)
        self.assertTrue(validation_result['valid'], 
                      f"UCF with transformed fields should be valid: {validation_result['errors']}")

    def test_library_manager_integration(self):
        """Test that the library manager can create custom UCFs"""
        # Create a custom UCF using the library manager
        ucf_path = self.library_manager.create_custom_ucf(
            ucf_name="library_manager_test.UCF.json",
            output_dir=self.test_dir
        )
        
        # Verify the UCF was created
        self.assertIsNotNone(ucf_path, "Library manager should be able to create a custom UCF")
        self.assertTrue(os.path.exists(ucf_path), "Custom UCF file should exist")
        
        # Verify the UCF is valid JSON
        with open(ucf_path) as f:
            try:
                ucf_data = json.load(f)
                self.assertTrue(isinstance(ucf_data, list), "UCF data should be a list")
            except json.JSONDecodeError:
                self.fail("Custom UCF should be valid JSON")
        
        # Validate the UCF
        validation_result = self.customizer.validate_ucf(ucf_data)
        self.assertTrue(validation_result['valid'], 
                      f"UCF created by library manager should be valid: {validation_result['errors']}")

if __name__ == '__main__':
    unittest.main(verbosity=2) 