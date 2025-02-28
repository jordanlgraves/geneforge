import unittest
import os
import tempfile
import json
from src.library.library_manager import LibraryManager
from src.tools.cello_integration import CelloIntegration

class TestLibrarySelection(unittest.TestCase):
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
        
        # Get available libraries for testing
        cls.available_libraries = cls.library_manager.get_available_libraries()
        
        if not cls.available_libraries:
            raise unittest.SkipTest("No libraries available for testing")
            
        print(f"Available libraries for testing: {cls.available_libraries}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cls.temp_dir.cleanup()
    
    def test_library_scanning(self):
        """Test that the library manager can scan and find libraries"""
        # Verify that we found at least one library
        self.assertTrue(len(self.available_libraries) > 0, 
                       "Library manager should find at least one library")
        
        # Check that each library has a valid path
        for library_id in self.available_libraries:
            library_info = self.library_manager.available_libraries[library_id]
            
            # Should have either a UCF path or a parsed path
            self.assertTrue("ucf" in library_info or "parsed" in library_info,
                          f"Library {library_id} should have either a UCF or parsed path")
            
            # If it has a UCF path, it should exist
            if "ucf" in library_info:
                self.assertTrue(os.path.exists(library_info["ucf"]),
                              f"UCF path for library {library_id} should exist")
            
            # If it has a parsed path, it should exist
            if "parsed" in library_info:
                self.assertTrue(os.path.exists(library_info["parsed"]),
                              f"Parsed path for library {library_id} should exist")
    
    def test_direct_library_selection(self):
        """Test selecting a library directly by ID"""
        # Skip if no libraries available
        if not self.available_libraries:
            self.skipTest("No libraries available for testing")
        
        # Select the first available library
        library_id = self.available_libraries[0]
        success = self.library_manager.select_library(library_id)
        
        # Verify selection was successful
        self.assertTrue(success, f"Should be able to select library {library_id}")
        
        # Verify library info
        library_info = self.library_manager.get_current_library_info()
        self.assertEqual(library_info["library_id"], library_id,
                        f"Current library ID should be {library_id}")
        
        # Verify we have either library data or a customizer
        self.assertTrue(library_info["has_library_data"] or library_info["has_customizer"],
                       "Should have either library data or a customizer")
    
    def test_organism_prefix_selection(self):
        """Test selecting a library by organism prefix"""
        # Try to select an E. coli library
        success = self.library_manager.select_library("ecoli")
        
        # If we have any E. coli libraries, this should succeed
        eco_libraries = [lib for lib in self.available_libraries if lib.startswith("Eco")]
        
        if eco_libraries:
            self.assertTrue(success, "Should be able to select an E. coli library")
            
            # Verify the selected library is an E. coli library
            library_info = self.library_manager.get_current_library_info()
            self.assertTrue(library_info["library_id"].startswith("Eco"),
                          "Selected library should be an E. coli library")
        else:
            self.assertFalse(success, "Should not be able to select an E. coli library if none exist")
    
    def test_invalid_library_selection(self):
        """Test selecting an invalid library"""
        # Try to select a non-existent library
        success = self.library_manager.select_library("NonExistentLibrary")
        
        # This should fail
        self.assertFalse(success, "Should not be able to select a non-existent library")
    
    def test_cello_integration_library_selection(self):
        """Test that the Cello integration can select libraries"""
        # Skip if no libraries available
        if not self.available_libraries:
            self.skipTest("No libraries available for testing")
        
        try:
            # Create a Cello integration with a specific library
            library_id = self.available_libraries[0]
            cello = CelloIntegration(library_id=library_id)
            
            # Verify that the library was selected
            self.assertEqual(cello.library_manager.current_library_id, library_id,
                            f"Cello integration should select library {library_id}")
            
            # Try selecting a different library
            if len(self.available_libraries) > 1:
                library_id = self.available_libraries[1]
                success = cello.select_library(library_id)
                
                self.assertTrue(success, f"Should be able to select library {library_id}")
                self.assertEqual(cello.library_manager.current_library_id, library_id,
                               f"Cello integration should select library {library_id}")
        except ImportError as e:
            self.skipTest(f"Skipping Cello integration test due to import error: {e}")
    
    def test_custom_ucf_creation(self):
        """Test creating a custom UCF with the library manager"""
        # Skip if no libraries available
        if not self.available_libraries:
            self.skipTest("No libraries available for testing")
        
        # Select a library
        library_id = self.available_libraries[0]
        success = self.library_manager.select_library(library_id)
        
        if not success or not self.library_manager.current_customizer:
            self.skipTest(f"Could not select library {library_id} or no customizer available")
        
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
        # Skip if no libraries available
        if not self.available_libraries:
            self.skipTest("No libraries available for testing")
        
        try:
            # Create a Cello integration with a specific library
            library_id = self.available_libraries[0]
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
        except ImportError as e:
            self.skipTest(f"Skipping Cello integration test due to import error: {e}")

if __name__ == "__main__":
    unittest.main() 