import sys
import os
# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import random
import unittest
import json
import tempfile
from typing import List, Dict, Optional

from jsonschema import ValidationError
from src.library.part_library_customizer import *
from src.library.library_manager import LibraryManager

def get_by_name(data: List[Dict], name: str) -> Optional[Dict]:
    for item in data:
        if item.get("name") == name:
            return item
    return None

class TestUCFCustomization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Load base UCF and create temp directory"""
        # Use the library manager to find a suitable library
        cls.library_manager = LibraryManager()
        
        # Try to select an E. coli library
        success = cls.library_manager.select_library("Eco1C1G1T1")
        if not success:
            # If no E. coli library, try any available library
            available_libraries = cls.library_manager.get_available_libraries()
            success = cls.library_manager.select_library('Eco1C1G1T1')
            
        # Get the UCF path from the library manager
        library_info = cls.library_manager.get_current_library_info()
        cls.base_ucf_path = library_info["ucf_path"]
        
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_dir = cls.temp_dir.name
        
        # Load sample data from base UCF
        with open(cls.base_ucf_path) as f:
            cls.base_data = json.load(f)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_related_collections_are_removed_when_parts_are_removed(self):
        """Test that structures are removed when parts are removed.
        
        This test checks that when a promoter is selected, all the other promoters are removed.
        It also checks that the structures and gates that reference the removed parts are also removed.
        """
        library_manager = LibraryManager()
        library_manager.select_library("Eco1C1G1T1")
        ucf_path = library_manager.create_custom_ucf(
            selected_parts=["pBM3R1"],
            ucf_name="test_related_components_removed.UCF.json",
            output_dir=self.test_dir
        )

        with open(ucf_path) as f:
            custom_data = json.load(f)

        # Check that parts os same type that are not specified are removed
        parts = [item for item in custom_data if item.get("collection") == "parts"]
        part_names = [item.get("name") for item in parts]
        self.assertNotIn("pAmtR", part_names)

        # Check that the structure is removed
        structures = [item for item in custom_data if item.get("collection") == "structures"]
        structure_names = [item.get("name") for item in structures]
        self.assertNotIn("A1_AmtR_structure", structure_names)

        # Check that the gate is removed
        gates = [item for item in custom_data if item.get("collection") == "gates"]
        gate_names = [item.get("name") for item in gates]
        self.assertNotIn("A1_AmtR_gate", gate_names)

        # Check that the model is removed
        models = [item for item in custom_data if item.get("collection") == "models"]
        model_names = [item.get("name") for item in models]
        self.assertNotIn("A1_AmtR_model", model_names)

    def test_part_modification(self):
        """Test modifying part parameters"""
        
        # Grab a random promoter from the base UCF
        promoters = [item for item in self.base_data if item.get("collection") == "parts" and item.get("type") == "promoter"]
        modified_part = random.choice(promoters)
        
        # change the promoters
        assert modified_part.get("name").startswith("p")
        # get the protein which is the name without the p
        regulator_name = modified_part.get("name")[1:]

        # Get the gate which is regulated by the protein
        gate = [item for item in self.base_data if item.get('collection') == 'gates' and item.get('regulator') == regulator_name][0]
        # Get the model which is regulated by the protein
        model_name = gate.get("model")
        model = [item for item in self.base_data if item.get('collection') == 'models' and item.get('name') == model_name][0]

        # change the model parameters
        model_parameters = model['parameters']
        # change the ymax parameter
        for parameter in model_parameters:
            if parameter.get('name') == 'ymax':
                parameter['value'] = 0.0 # just for testing
                break
        # change the ymin parameter
        for parameter in model_parameters:
            if parameter.get('name') == 'ymin':
                parameter['value'] = 1.0 # just for testing
                break
        
        # change the K parameter
        for parameter in model_parameters:
            if parameter.get('name') == 'K':
                parameter['value'] = 2.0 # just for testing
                break
        
        # change the n parameter
        for parameter in model_parameters:
            if parameter.get('name') == 'n':
                parameter['value'] = 3.0 # just for testing
                break
        
        # change the alpha parameter
        for parameter in model_parameters:
            if parameter.get('name') == 'alpha':
                parameter['value'] = 4.0 # just for testing
                break
        
        # change the beta parameter
        for parameter in model_parameters:
            if parameter.get('name') == 'beta':
                parameter['value'] = 5.0 # just for testing
                break
        

        # Grab a random ribozyme from the base UCF and change the ribozyme parameters and sequence
        ribozymes = [item for item in self.base_data if item.get("collection") == "parts" and item.get("type") == "ribozyme"]
        modified_ribozyme = random.choice(ribozymes)
        """
            {
        "collection": "parts",
        "type": "ribozyme",
        "name": "BydvJ",
        "dnasequence": "CTGAagGGTGTCTCAAGGTGCGTACCTTGACTGATGAGTCCGAAAGGACGAAACACCcctctacaaataattttgtttaa",
        "parameters": [
            {
                "name": "ribozyme_efficiency",
                "value": 0.95
            }
        ]
        }"""
        ribozyme_parameters = modified_ribozyme.get("parameters")
        for parameter in ribozyme_parameters:
            if parameter.get("name") == "ribozyme_efficiency":
                parameter["value"] = 0.0
                break
        modified_ribozyme["dnasequence"] = "A"
        
        
        # Create the customized UCF
        library_manager = LibraryManager()
        library_manager.select_library("Eco1C1G1T1")
        ucf_path = library_manager.create_custom_ucf(
            modified_parts=[model, modified_ribozyme],
            ucf_name="test_part_modification.UCF.json",
            output_dir=self.test_dir
        )
        
        with open(ucf_path) as f:
            custom_data = json.load(f)
            
        # Find the modified part in the UCF
        modified = [item for item in custom_data if item.get("collection") == "models" and item.get("name") == model_name][0]
        # check ymax
        modified_parameters = modified.get("parameters")
        ymax = [item for item in modified_parameters if item.get("name") == "ymax"][0]
        self.assertEqual(ymax.get("value"), 0.0)
        # check ymin
        ymin = [item for item in modified_parameters if item.get("name") == "ymin"][0]
        self.assertEqual(ymin.get("value"), 1.0)
        # check K
        K = [item for item in modified_parameters if item.get("name") == "K"][0]
        self.assertEqual(K.get("value"), 2.0)
        # check n
        n = [item for item in modified_parameters if item.get("name") == "n"][0]
        self.assertEqual(n.get("value"), 3.0)
        # check alpha
        alpha = [item for item in modified_parameters if item.get("name") == "alpha"][0]
        self.assertEqual(alpha.get("value"), 4.0)
        # check beta
        beta = [item for item in modified_parameters if item.get("name") == "beta"][0]
        self.assertEqual(beta.get("value"), 5.0)

        # check ribozyme efficiency and check ribozyme sequence
        ribozyme_efficiency = [item for item in modified_ribozyme.get("parameters") if item.get("name") == "ribozyme_efficiency"][0]
        self.assertEqual(ribozyme_efficiency.get("value"), 0.0)
        self.assertEqual(modified_ribozyme.get("dnasequence"), "A")


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
        validation_result = validate_ucf(ucf_data)
        self.assertTrue(validation_result['valid'], 
                      f"UCF created by library manager should be valid: {validation_result['errors']}")

    def test_validation_error_handling(self):
        """Test validation error handling with invalid UCF data"""
        
        # Create a deliberately invalid UCF - missing required collections
        invalid_ucf = [
            {"collection": "test", "value": "This is not a valid UCF structure"}
        ]

        # Test that validation raises an exception for missing header
        with self.assertRaises(ValidationError):
            validate_ucf(invalid_ucf)
        
        # Test that create_custom_ucf with invalid part raises an exception
        with self.assertRaises(Exception):
            # Using an invalid part should fail
            create_custom_ucf(invalid_ucf,
                new_parts=[{"type": "invalid_type"}]  # Missing required fields
            )

    def test_duplicate_promoter_dependencies(self):
        """Test that duplicate promoter dependencies are handled correctly"""
        ucf_data = self.library_manager.get_ucf_data()
        new_items, gate_map = duplicate_promoter_dependencies(ucf_data, 
                                                            "pPhlF", 
                                                            "pPhlFvar1", 
                                                            "A" * 90, 
                                                            1.0)
        result = validate_ucf(new_items)
        assert result['valid']

    def test_remove_part_and_dependencies(self):
        """Test that the remove_part_and_dependencies function works correctly"""
        ucf_data = self.library_manager.get_ucf_data()
        new_ucf, summary = remove_part_and_dependencies(ucf_data, "pPhlF")
        print('summary:   ')
        print(summary)
        assert new_ucf is not None
        assert(get_by_name(new_ucf, "pPhlF") is None)
        assert(get_by_name(new_ucf, "P1_PhlF_model") is None)
        assert(get_by_name(new_ucf, "P2_PhlF_model") is None)
        assert(get_by_name(new_ucf, "P3_PhlF_model") is None)
        assert(get_by_name(new_ucf, "P1_PhlF") is None)
        assert(get_by_name(new_ucf, "P2_PhlF") is None)
        assert(get_by_name(new_ucf, "P3_PhlF") is None)
        assert(get_by_name(new_ucf, "P1_PhlF_structure") is None)
        assert(get_by_name(new_ucf, "P2_PhlF_structure") is None)
        assert(get_by_name(new_ucf, "P3_PhlF_structure") is None)

    def test_add_promoter_variant_and_remove_original(self):
        """Test that the adding a promoter, then removing the original functionality works correctly"""
        ucf_data = self.library_manager.get_ucf_data()
        # duplicate the promoter
        new_items, summary = duplicate_promoter_dependencies(ucf_data, "pPhlF", "pPhlFvar1", "A" * 90, 1.0)
        
        # Add the new items to the original UCF
        new_ucf = ucf_data + new_items
    
        # remove the original promoter
        filtered_ucf, summary = remove_part_and_dependencies(new_ucf, "pPhlF")
    
        assert filtered_ucf is not None
        assert(get_by_name(filtered_ucf, "pPhlF") is None)
        assert(get_by_name(filtered_ucf, "P1_PhlF_model") is None)
        assert(get_by_name(filtered_ucf, "P2_PhlF_model") is None)
        assert(get_by_name(filtered_ucf, "P3_PhlF_model") is None)
        assert(get_by_name(filtered_ucf, "P1_PhlF") is None)
        assert(get_by_name(filtered_ucf, "P2_PhlF") is None)
        assert(get_by_name(filtered_ucf, "P3_PhlF") is None)
        assert(get_by_name(filtered_ucf, "P1_PhlF_structure") is None)
        assert(get_by_name(filtered_ucf, "P2_PhlF_structure") is None)
        assert(get_by_name(filtered_ucf, "P3_PhlF_structure") is None)
    
        assert(get_by_name(filtered_ucf, "pPhlFvar1") is not None)
        assert(get_by_name(filtered_ucf, "P1_PhlFvar1_model") is not None)
        assert(get_by_name(filtered_ucf, "P2_PhlFvar1_model") is not None)
        assert(get_by_name(filtered_ucf, "P3_PhlFvar1_model") is not None)
        assert(get_by_name(filtered_ucf, "P1_PhlFvar1") is not None)
        assert(get_by_name(filtered_ucf, "P2_PhlFvar1") is not None)
        assert(get_by_name(filtered_ucf, "P3_PhlFvar1") is not None)
        assert(get_by_name(filtered_ucf, "P1_PhlFvar1_structure") is not None)
        assert(get_by_name(filtered_ucf, "P2_PhlFvar1_structure") is not None)
        assert(get_by_name(filtered_ucf, "P3_PhlFvar1_structure") is not None)


if __name__ == '__main__':
    unittest.main(verbosity=2) 
    