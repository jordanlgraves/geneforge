import unittest
import os
import tempfile
import json
from src.library.library_manager import LibraryManager
from src.tools.cello_integration import CelloIntegration

class TestLibraryManager(unittest.TestCase):
    """
    Tests for the library selection functionality.
    These tests verify that the system can correctly select libraries based on user input.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_dir = cls.temp_dir.name
        
        # Create a library manager for testing
        cls.library_manager = LibraryManager()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cls.temp_dir.cleanup()
    
    def test_library_scanning(self):
        """Test that the library manager can scan and find libraries"""
        # Verify that we found at least one library
        self.assertTrue(len(self.library_manager.get_available_libraries()) > 0, 
                       "Library manager should find at least one library")
        
        # Check that each library has a valid path
        available_libraries = self.library_manager.get_available_libraries()
        for library_id in available_libraries:
            library_info = available_libraries[library_id]
            
            # Should have either a UCF path or a parsed path
            self.assertTrue("ucf" in library_info,f"Library {library_id} should have a UCF path")
            
            self.assertTrue(os.path.exists(library_info["ucf"]), f"UCF path for library {library_id}")
            
    
    def test_direct_library_selection(self):
        """Test selecting a library directly by ID"""
        
        # Select the first available library
        library_id = list(self.library_manager.get_available_libraries().keys())[0]
        success = self.library_manager.select_library(library_id)
        
        # Verify selection was successful
        self.assertTrue(success, f"Should be able to select library {library_id}")
        
        # Verify library info
        library_info = self.library_manager.get_current_library_info()
        self.assertEqual(library_info["library_id"], library_id,
                        f"Current library ID should be {library_id}")
        
        # Verify we have either library data or a customizer
        self.assertTrue(library_info["ucf_path"] is not None, "Should have a UCF path")
        self.assertTrue(library_info["input_path"] is not None, "Should have an input path")
        self.assertTrue(library_info["output_path"] is not None, "Should have an output path")
    
    
    def test_library_metadata_retrieval(self):
        """Test retrieving library metadata"""
        
        library_metadata = self.library_manager.describe_available_libraries()
        self.assertIsNotNone(library_metadata, "Should be able to retrieve library metadata")

        # Verify the metadata is a list
        self.assertTrue(isinstance(library_metadata, dict), "Library metadata should be a list")
        
        self.assertIn("Eco1C1G1T1", library_metadata, "Library metadata should contain Eco1C1G1T1")
        self.assertIn("Eco1C2G2T2", library_metadata, "Library metadata should contain Eco1C2G2T2")
        
        metadata = library_metadata["Eco1C1G1T1"]
        self.assertIsNotNone(metadata, "Library metadata should contain Eco1C1G1T1")
        self.assertIsNotNone(metadata['description'], "metadata should contain description")
    

    def test_invalid_library_selection(self):
        """Test selecting an invalid library"""
        # Try to select a non-existent library
        success = self.library_manager.select_library("NonExistentLibrary")
        
        # This should fail
        self.assertFalse(success, "Should not be able to select a non-existent library")
    

    def test_cello_integration_library_selection(self):
        """Test that the Cello integration can select libraries"""
        
        
        # Create a Cello integration with a specific library
        library_id = list(self.library_manager.get_available_libraries().keys())[0]
        cello = CelloIntegration(library_id=library_id)
        
        # Verify that the library was selected
        self.assertEqual(cello.library_manager.current_library_id, library_id,
                        f"Cello integration should select library {library_id}")
        
        # Try selecting a different library
        if len(self.library_manager.get_available_libraries()) > 1:
            library_id = list(self.library_manager.get_available_libraries().keys())[1]
            success = cello.select_library(library_id)
            
            self.assertTrue(success, f"Should be able to select library {library_id}")
            self.assertEqual(cello.library_manager.current_library_id, library_id,
                            f"Cello integration should select library {library_id}")
    
    
    def test_custom_ucf_creation(self):
        """Test creating a custom UCF with the library manager"""
        
        # Select a library
        library_id = list(self.library_manager.get_available_libraries().keys())[0]
        success = self.library_manager.select_library(library_id)
        
        # Create a simple custom UCF
        ucf_path = self.library_manager.create_custom_ucf(
            ucf_name="test_custom.UCF.json",
            output_dir=self.test_dir
        )
        
        # Verify the UCF was created
        self.assertIsNotNone(ucf_path, "Should be able to create a custom UCF")
        self.assertTrue(os.path.exists(ucf_path), "Custom UCF file should exist")
        
        # Verify the UCF is valid JSON
        with open(ucf_path) as f:
            try:
                ucf_data = json.load(f)
                self.assertTrue(isinstance(ucf_data, list), "UCF data should be a list")
            except json.JSONDecodeError:
                self.fail("Custom UCF should be valid JSON")
    
    def test_cello_with_custom_ucf(self):
        """Test creating a custom UCF with Cello integration"""
        
        # Create a Cello integration with a specific library
        library_id = list(self.library_manager.get_available_libraries().keys())[0]
        cello = CelloIntegration(library_id=library_id)
        
        # Create a custom UCF
        custom_ucf_path = cello.create_custom_ucf(
            ucf_name="test_custom_cello.UCF.json",
            output_dir=self.test_dir
        )
        
        # Verify the UCF was created
        self.assertIsNotNone(custom_ucf_path, "Should be able to create a custom UCF")
        self.assertTrue(os.path.exists(custom_ucf_path), "Custom UCF file should exist")
        
        # Verify the UCF is valid JSON
        with open(custom_ucf_path) as f:
            try:
                ucf_data = json.load(f)
                self.assertTrue(isinstance(ucf_data, list), "UCF data should be a list")
            except json.JSONDecodeError:
                self.fail("Custom UCF should be valid JSON")


if __name__ == "__main__":
    unittest.main() 