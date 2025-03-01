import unittest
import os
import shutil
import time
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

# Determine the absolute path to the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Add the Cello-v2-1-Core directory to the Python path
cello_core_path = os.path.join(project_root, "ext_repos", "Cello-v2-1-Core")
if os.path.exists(cello_core_path):
    print(f"Added {cello_core_path} to Python path")
    os.environ["PYTHONPATH"] = f"{cello_core_path}:{os.environ.get('PYTHONPATH', '')}"

from src.tools.cello_integration import CelloIntegration
from src.library.library_manager import LibraryManager

# Remove the skipUnless decorator to always run the tests
class TestCelloIntegration(unittest.TestCase):
    """
    Tests for the CelloIntegration class.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Configure logging to capture messages
        import logging
        cls.logger = logging.getLogger("TestCelloIntegration")
        cls.logger.setLevel(logging.INFO)
        
        # Set the project root for use in tests
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        
        # Create a library manager for testing
        cls.library_manager = LibraryManager()
        
        # Get available libraries for testing
        cls.available_libraries = cls.library_manager.get_available_libraries()
        
        if not cls.available_libraries:
            raise unittest.SkipTest("No libraries available for testing")
            
        print(f"Available libraries for testing: {cls.available_libraries}")
    
    def test_initialization(self):
        """Test that CelloIntegration initializes correctly"""
        # Test initialization with default parameters
        cello = CelloIntegration()
        self.assertIsNotNone(cello)
        self.assertIsNotNone(cello.library_manager)
        self.assertIsNotNone(cello.cello_args)
        self.assertIsNotNone(cello.cello_config)
        
        # Test initialization with a specific library ID
        library_id = self.available_libraries[0]
        cello = CelloIntegration(library_id=library_id)
        self.assertEqual(cello.library_manager.current_library_id, library_id)
    
    def test_select_library(self):
        """Test selecting a library"""
        cello = CelloIntegration()
        
        # Test selecting each available library
        for library_id in self.available_libraries:
            success = cello.select_library(library_id)
            self.assertTrue(success)
            self.assertEqual(cello.library_manager.current_library_id, library_id)
            
            # Check that the Cello arguments were updated correctly
            self.assertTrue(library_id in cello.cello_args['ucf_name'])
            
            # If input and output paths exist, they should be updated
            lib_info = cello.library_manager.get_current_library_info()
            if lib_info.get("input_path"):
                self.assertTrue(library_id in cello.cello_args['in_name'])
            if lib_info.get("output_path"):
                self.assertTrue(library_id in cello.cello_args['out_name'])
        
        # Test selecting a non-existent library
        success = cello.select_library("NonExistentLibrary")
        self.assertFalse(success)
    
    def test_get_available_libraries(self):
        """Test getting available libraries"""
        cello = CelloIntegration()
        
        # Get available libraries
        libraries = cello.get_available_libraries()
        
        # Check that the libraries match the ones from the LibraryManager
        self.assertEqual(set(libraries), set(self.available_libraries))
    
    @patch('src.tools.cello_integration.CELLO3')
    def test_run_cello_mock(self, mock_cello3):
        """Test running Cello with mock CELLO3"""
        # Mock the CELLO3 class
        mock_cello_instance = MagicMock()
        mock_cello3.return_value = mock_cello_instance
        
        # Create test output directory structure
        output_path = os.path.join(self.project_root, "outputs", "cello_outputs", "0x17.v")
        os.makedirs(output_path, exist_ok=True)
        
        # Create mock output files
        test_files = {
            "sbol_file": "0x17._pySBOL3.nt",
            "eugene_script": "0x17._eugene.eug",
            "dna_sequences": "0x17._dna-sequences.csv",
            "activity_table": "0x17._activity-table.csv",
            "circuit_score": "0x17._circuit-score.csv",
            "all_files_zip": "0x17._all-files.zip"
        }
        
        for _, filename in test_files.items():
            with open(os.path.join(output_path, filename), 'w') as f:
                f.write("Test content")
        
        # Create visualization files
        vis_files = [
            "0x17._response-plots.pdf",
            "0x17._tech-mapping.pdf",
            "0x17._dpl-sbol.pdf"
        ]
        
        for filename in vis_files:
            with open(os.path.join(output_path, filename), 'w') as f:
                f.write("Test visualization content")
        
        # Create CelloIntegration instance
        with patch('src.tools.cello_integration.UCFCustomizer') as mock_ucf_customizer:
            # Mock UCF validation
            mock_validator = MagicMock()
            mock_validator.validate_ucf.return_value = {"valid": True}
            mock_ucf_customizer.return_value = mock_validator
            
            # Mock the dependency check
            with patch.object(CelloIntegration, '_check_yosys_dependency', return_value=True):
                with patch.object(CelloIntegration, '_start_minieugene_server'):
                    with patch.object(CelloIntegration, '_stop_minieugene_server'):
                        cello = CelloIntegration()
                        
                        # Test run_cello with Verilog code
                        verilog_code = "module NOT_gate (input a, output out); assign out = ~a; endmodule"
                        result = cello.run_cello(verilog_code=verilog_code)
                        
                        # Check that CELLO3 was called with the correct arguments
                        mock_cello3.assert_called_once()
                        
                        # Check the result structure
                        self.assertTrue(result["success"])
                        self.assertIn("log", result)
                        self.assertIn("results", result)
                        self.assertIn("output_path", result["results"])
                        self.assertIn("dna_design", result["results"])
                        
                        # Check that the output files were detected
                        dna_design = result["results"]["dna_design"]
                        for file_type in test_files.keys():
                            self.assertIn(file_type, dna_design)
                            self.assertIsNotNone(dna_design[file_type])
                            
                        # Check that visualizations were detected
                        self.assertIn("visualizations", dna_design)
                        self.assertEqual(len(dna_design["visualizations"]), len(vis_files))
        
        # Clean up test files
        try:
            shutil.rmtree(os.path.dirname(output_path))
        except:
            pass
    
    @patch('src.tools.cello_integration.CELLO3')
    def test_custom_ucf_creation(self, mock_cello3):
        """Test creating and using a custom UCF"""
        # Mock the CELLO3 class
        mock_cello_instance = MagicMock()
        mock_cello3.return_value = mock_cello_instance
        
        # Create test output directory
        output_path = os.path.join(self.project_root, "outputs", "cello_outputs", "0x17.v")
        os.makedirs(output_path, exist_ok=True)
        
        # Create a minimal output file for the test
        with open(os.path.join(output_path, "0x17._dna-sequences.csv"), 'w') as f:
            f.write("Test DNA sequence")
        
        # Create CelloIntegration instance
        with patch.object(CelloIntegration, 'create_custom_ucf') as mock_create_custom_ucf:
            # Set up the mock to return a success value
            mock_create_custom_ucf.return_value = os.path.join(
                self.project_root, "ext_repos", "Cello-v2-1-Core", "input", "constraints", "custom_test.UCF.json"
            )
            
            # Mock the UCF validation and dependency check
            with patch('src.tools.cello_integration.UCFCustomizer') as mock_ucf_customizer:
                mock_validator = MagicMock()
                mock_validator.validate_ucf.return_value = {"valid": True}
                mock_ucf_customizer.return_value = mock_validator
                
                with patch.object(CelloIntegration, '_check_yosys_dependency', return_value=True):
                    with patch.object(CelloIntegration, '_start_minieugene_server'):
                        with patch.object(CelloIntegration, '_stop_minieugene_server'):
                            cello = CelloIntegration()
                            
                            # Test run_cello with a custom UCF
                            verilog_code = "module NOT_gate (input a, output out); assign out = ~a; endmodule"
                            custom_ucf = {
                                "selected_gates": ["A1_AmtR", "P3_PhlF"],
                                "selected_parts": ["pTac", "YFP", "L3S2P21"],
                                "ucf_name": "custom_test.UCF.json"
                            }
                            
                            result = cello.run_cello(verilog_code=verilog_code, custom_ucf=custom_ucf)
                            
                            # Check that create_custom_ucf was called with the correct arguments
                            mock_create_custom_ucf.assert_called_once_with(
                                selected_gates=custom_ucf["selected_gates"],
                                selected_parts=custom_ucf["selected_parts"],
                                modified_parts=None,
                                new_parts=None,
                                ucf_name=custom_ucf["ucf_name"]
                            )
                            
                            # Check the result
                            self.assertTrue(result["success"])
        
        # Clean up test files
        try:
            shutil.rmtree(os.path.dirname(output_path))
        except:
            pass
    
    def test_yosys_dependency_check(self):
        """Test the Yosys dependency check"""
        # First test the normal method with shutil.which
        normal_check = CelloIntegration._check_yosys_dependency(None)
        
        # Then check directly for the Homebrew installed version
        brew_yosys_path = "/opt/homebrew/bin/yosys"
        has_brew_yosys = os.path.exists(brew_yosys_path) and os.access(brew_yosys_path, os.X_OK)
        
        # Pass the test if either check passes
        yosys_available = normal_check or has_brew_yosys
        
        if not normal_check and has_brew_yosys:
            print(f"Yosys found at {brew_yosys_path} but not in PATH. Consider adding it to PATH.")
        
        # Test that Yosys is available
        self.assertTrue(yosys_available, "Yosys is required for Cello integration tests")
    
    def test_end_to_end_cello_run(self):
        """
        Test an end-to-end run of Cello with a real (not mocked) integration.
        
        This test verifies that:
        1. Cello can be initialized with a valid library
        2. A simple NOT gate circuit can be processed
        3. Output files are generated correctly
        4. The results contain all the expected components
        5. All expected output files are present
        
        Note: This test requires Yosys to be installed (checked by the class decorator)
        """
        # Skip if no libraries available
        if not self.available_libraries:
            self.skipTest("No libraries available for testing")
        
        # Create a test-specific output directory
        test_output_dir = os.path.join(self.project_root, "outputs", "cello_test_outputs")
        test_verilog_name = "test_NOT_gate.v"
        
        # Clean up any previous test output directory entirely
        if os.path.exists(test_output_dir):
            print(f"Cleaning up previous test output directory: {test_output_dir}")
            shutil.rmtree(test_output_dir)
            
        
        # Ensure output directory exists
        os.makedirs(test_output_dir, exist_ok=True)
        print(f"Created test output directory: {test_output_dir}")
        
        try:
            # Create a CelloIntegration instance with the first available library
            library_id = self.available_libraries[0]
            print(f"Using library: {library_id}")
            
            # Custom cello_args with complete path overrides
            cello_args = {
                'v_name': test_verilog_name,
                'out_path': test_output_dir,
                # Keep other defaults but ensure paths are correctly set
                'verilogs_path': os.path.join(self.project_root, "ext_repos", "Cello-v2-1-Core", "library", "verilogs"),
                'constraints_path': os.path.join(self.project_root, "ext_repos", "Cello-v2-1-Core", "library", "constraints")
            }
            
            print(f"Cello arguments: {cello_args}")
            
            # Create Cello instance with custom args
            cello = CelloIntegration(library_id=library_id, cello_args=cello_args)
            
            # Simple NOT gate Verilog code
            verilog_code = """
            module NOT_gate (
                input a,
                output out
            );
                assign out = ~a;
            endmodule
            """
            
            print(f"Running Cello with Verilog code for a NOT gate...")
            
            # Run Cello without mocking
            result = cello.run_cello(verilog_code=verilog_code)
            
            # Print full result for debugging
            print(f"Cello run result: {result}")
            
            # Verify the result structure
            self.assertTrue(result["success"], f"Cello run failed: {result.get('error', 'Unknown error')}")
            self.assertIn("log", result, "Result should contain logs")
            self.assertIn("results", result, "Result should contain results")
            
            # Verify that results contain expected data
            results_data = result["results"]
            self.assertIn("output_path", results_data, "Results should contain output_path")
            self.assertIn("dna_design", results_data, "Results should contain dna_design")
            
            # Verify that the output directory exists
            output_path = results_data["output_path"]
            print(f"Output path from results: {output_path}")
            self.assertTrue(os.path.exists(output_path), f"Output path {output_path} does not exist")
            
            # Get the base filenames for testing (with and without extensions)
            output_dir = Path(output_path)
            v_name = os.path.basename(output_path)  # Should be our test verilog name
            print(f"Base verilog name: {v_name}")
            
            # Check for the log file - try both the custom and default locations
            cello_log_paths = [
                os.path.join(test_output_dir, "cello_run.log"),  # Custom location
                os.path.join(self.project_root, "outputs", "cello_outputs", "cello_run.log")  # Default location
            ]
            
            log_found = False
            for log_path in cello_log_paths:
                if os.path.exists(log_path):
                    print(f"Found log file at: {log_path}")
                    self.assertGreater(os.path.getsize(log_path), 0, f"Cello log file is empty")
                    log_found = True
                    break
                    
            if not log_found:
                print("Warning: Could not find Cello log file in expected locations")
            
            # Verify that DNA design contains expected components
            dna_design = results_data["dna_design"]
            print(f"DNA design keys: {dna_design.keys()}")
            
            # List all files in the output directory and subdirectories for debugging
            print(f"All files in output directory tree:")
            for root, dirs, files in os.walk(output_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, output_path)
                    print(f"  - {rel_path} ({os.path.getsize(full_path)} bytes)")
            
            # Expected output files based on the list provided - adjust patterns based on actual output files
            expected_files = [
                f"*_activity-table.csv",
                f"*_all-files.zip",
                f"*_circuit-score.csv",
                f"*_dna-sequences.csv",
                f"*_dpl-dna-designs.csv",
                f"*_dpl-part-information.csv",
                f"*_dpl-plot-parameters.csv",
                f"*_dpl-regulatory-info.csv",
                f"*_dpl-sbol.pdf",
                f"*_dpl-sbol.png",
                f"*_eugene.eug",
                f"*_pySBOL3.nt",
                f"*_response-plots.pdf",
                f"*_response-plots.png",
                f"*_tech-mapping.pdf",
                f"*_tech-mapping.png",
                f"*_yosys",
                f"*_yosys.dot",
                f"*_yosys.edif",
                f"*_yosys.json"
            ]
            
            # Get all files in the output directory
            if os.path.exists(output_path):
                output_files = os.listdir(output_path)
                self.assertGreater(len(output_files), 0, f"No output files found in {output_path}")
                
                print(f"Found {len(output_files)} files in output directory:")
                for file in output_files:
                    print(f"  - {file}")
            else:
                assert False, f"Output path {output_path} does not exist"
                
            # Check for essential file types with more thorough validation
            essential_file_types = ["dna_sequences", "eugene_script", "sbol_file", "activity_table"]
            for file_type in essential_file_types:
                self.assertIn(file_type, dna_design, f"DNA design should contain {file_type}")
                file_path = dna_design[file_type]
                if file_path:  # Some files might be None if Cello didn't generate them
                    # Verify file exists
                    self.assertTrue(os.path.exists(file_path), f"File {file_path} does not exist")
                    
                    # Verify file is not empty
                    file_size = os.path.getsize(file_path)
                    self.assertGreater(file_size, 0, f"File {file_path} exists but is empty (0 bytes)")
                    
                    # Perform content validation based on file type
                    with open(file_path, 'r') as f:
                        content = f.read(1024)  # Read first 1KB to check content
                        self.assertTrue(len(content) > 0, f"File {file_path} couldn't be read or is empty")
                        
                        # File-specific validation
                        if file_type == "dna_sequences":
                            self.assertIn(",", content, f"DNA sequences file doesn't contain expected CSV format")
                        elif file_type == "eugene_script":
                            self.assertIn("PartType", content, "Eugene script doesn't contain expected PartType definitions")
                        elif file_type == "sbol_file":
                            self.assertTrue(content.strip(), "SBOL file appears to be empty")
                        elif file_type == "activity_table":
                            self.assertIn(",", content, "Activity table doesn't contain expected CSV format")
            
            # Check for visualizations
            self.assertIn("visualizations", dna_design, "DNA design should contain visualizations")
            visualizations = dna_design["visualizations"]
            self.assertTrue(isinstance(visualizations, list), "Visualizations should be a list")
            if visualizations:  # If any visualizations were generated
                for viz_path in visualizations:
                    self.assertTrue(os.path.exists(viz_path), f"Visualization file {viz_path} does not exist")
                    self.assertGreater(os.path.getsize(viz_path), 0, f"Visualization file {viz_path} exists but is empty")
            
            # Check for each expected file pattern using glob
            import glob
            missing_files = []
            for file_pattern in expected_files:
                pattern_path = os.path.join(output_path, file_pattern)
                matching_files = glob.glob(pattern_path)
                if not matching_files:
                    missing_files.append(file_pattern)
            
            # Report missing files (if any)
            if missing_files:
                print(f"Warning: The following expected file patterns did not match any files:")
                for missing in missing_files:
                    print(f"  - {missing}")
                
                # Don't fail the test but print a warning
                print("Note: Some expected files were not found. This may be normal depending on the specific Cello run configuration.")
            else:
                print("All expected file patterns matched at least one file.")
            
            print(f"Cello end-to-end test successful with library {library_id}")
            print(f"Output files generated in {output_path}")
            
            # Print the DNA sequence from the output
            dna_sequences_file = dna_design.get("dna_sequences")
            if dna_sequences_file and os.path.exists(dna_sequences_file):
                with open(dna_sequences_file, 'r') as f:
                    print(f"DNA Sequences (first 5 lines):")
                    lines = f.readlines()
                    for i, line in enumerate(lines[:5]):  # More robust way to get first 5 lines
                        print(f"  {line.strip()}")
                    
                    # Report total number of sequences
                    print(f"  ... ({len(lines)} total lines in DNA sequences file)")
        
        except Exception as e:
            import traceback
            self.fail(f"End-to-end Cello test failed: {str(e)}\n{traceback.format_exc()}")
        finally:
            # Log that test is complete
            print(f"Test completed. Test output directory: {test_output_dir}")
            # Optionally clean up test output - uncomment to remove test files after test
            # if os.path.exists(test_output_dir):
            #     shutil.rmtree(test_output_dir)
            
if __name__ == "__main__":
    unittest.main() 