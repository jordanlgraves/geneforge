# cello_integration.py
import subprocess
import os
import time
import atexit
import logging
import shutil
from typing import Dict, Optional, List, Any, Union

# Set up the Python path for Cello
from src.tools.cello_setup import is_setup_successful

# Import CELLO3 after setting up the path
if is_setup_successful:
    from core_algorithm.celloAlgo import CELLO3
else:
    raise ImportError("Failed to set up Cello path. Cannot import CELLO3.")

from src.library.ucf_customizer import UCFCustomizer  # Import UCFCustomizer for validation
from src.library.library_manager import LibraryManager

class CelloIntegration:
    def __init__(self, 
                cello_args: Optional[Dict] = None, 
                cello_config: Optional[Dict] = None,
                library_id: Optional[str] = None):
        # Default configuration that can be overridden
        self.cello_args = {
            'v_name': '0x17.v',
            'ucf_name': 'Eco1C1G1T1.UCF.json',
            'in_name': 'Eco1C1G1T1.input.json',
            'out_name': 'Eco1C1G1T1.output.json',
            'verilogs_path': 'ext_repos/Cello-v2-1-Core/library/verilogs',
            'constraints_path': 'ext_repos/Cello-v2-1-Core/library/constraints',
            'out_path': 'outputs/cello_outputs'
        } if cello_args is None else cello_args

        self.cello_config = {
            'verbose': True,  # Enable detailed logging
            'print_iters': True,  
            'exhaustive': False,
            'test_configs': False,
            'log_overwrite': True,
            'total_iters': 1_000
        } if cello_config is None else cello_config

        self.java_process = None
        self.log_buffer = []
        self._setup_logging()
        
        # Initialize library manager
        self.library_manager = LibraryManager()
        
        # Select library if specified
        if library_id:
            self.select_library(library_id)
            
        self._start_minieugene_server()

    def _setup_logging(self):
        """Configure logging to capture Cello output"""
        self.logger = logging.getLogger('cello_integration')
        self.logger.setLevel(logging.INFO)
        
        # Handler to capture logs in memory
        class LogCaptureHandler(logging.Handler):
            def __init__(self, log_buffer):
                super().__init__()
                self.log_buffer = log_buffer

            def emit(self, record):
                self.log_buffer.append(self.format(record))

        # Add handlers for both file and memory capture
        os.makedirs('outputs/cello_outputs', exist_ok=True)
        file_handler = logging.FileHandler('outputs/cello_outputs/cello_run.log')
        capture_handler = LogCaptureHandler(self.log_buffer)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        capture_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(capture_handler)

    def _start_minieugene_server(self):
        """Start the MiniEugene Java server if not already running"""
        try:
            # Check if server is already running
            gateway_dir = os.path.join("ext_repos", "Cello-v2-1-Core", 
                                     "core_algorithm", "utils", "py4j_gateway")
            
            # Start the Java server as a subprocess
            self.java_process = subprocess.Popen(
                ["java", "-cp", 
                 ".:jars/py4j.jar:./jars/miniEugene-core-1.0.0-jar-with-dependencies.jar:./src", 
                 "miniEugenePermuter"],
                cwd=gateway_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait briefly for server initialization
            time.sleep(2)
            atexit.register(self._stop_minieugene_server)  # Cleanup on exit
            
        except Exception as e:
            print(f"Failed to start MiniEugene server: {e}")
            raise

    def _stop_minieugene_server(self):
        """Stop the Java server process"""
        if self.java_process:
            self.java_process.terminate()
            try:
                self.java_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.java_process.kill()
            self.java_process = None
            
    def select_library(self, library_id: str) -> bool:
        """
        Select a library to use for Cello.
        
        Args:
            library_id: Library identifier (e.g., "Eco1C1G1T1" or "ecoli")
            
        Returns:
            True if library was successfully selected, False otherwise
        """
        success = self.library_manager.select_library(library_id)
        
        if success:
            # Update Cello arguments with the selected library
            library_info = self.library_manager.get_current_library_info()
            
            # Process the UCF file
            if library_info["ucf_path"]:
                # Extract just the filename for the UCF
                ucf_filename = os.path.basename(library_info["ucf_path"])
                
                # Update the UCF name in Cello args
                self.cello_args["ucf_name"] = ucf_filename
                
                # Copy the UCF file to the Cello constraints directory if needed
                constraints_dir = self.cello_args["constraints_path"]
                os.makedirs(constraints_dir, exist_ok=True)
                
                target_path = os.path.join(constraints_dir, ucf_filename)
                if not os.path.exists(target_path):
                    import shutil
                    shutil.copy2(library_info["ucf_path"], target_path)
                    self.logger.info(f"Copied UCF file to {target_path}")
            else:
                self.logger.warning(f"Selected library {library_id} has no UCF file")
                return False
                
            # Process the input file if available
            if library_info["input_path"]:
                # Extract just the filename for the input file
                input_filename = os.path.basename(library_info["input_path"])
                
                # Update the input name in Cello args
                self.cello_args["in_name"] = input_filename
                
                # Copy the input file to the Cello constraints directory if needed
                if not os.path.exists(os.path.join(constraints_dir, input_filename)):
                    import shutil
                    shutil.copy2(library_info["input_path"], os.path.join(constraints_dir, input_filename))
                    self.logger.info(f"Copied input file to {os.path.join(constraints_dir, input_filename)}")
            
            # Process the output file if available
            if library_info["output_path"]:
                # Extract just the filename for the output file
                output_filename = os.path.basename(library_info["output_path"])
                
                # Update the output name in Cello args
                self.cello_args["out_name"] = output_filename
                
                # Copy the output file to the Cello constraints directory if needed
                if not os.path.exists(os.path.join(constraints_dir, output_filename)):
                    import shutil
                    shutil.copy2(library_info["output_path"], os.path.join(constraints_dir, output_filename))
                    self.logger.info(f"Copied output file to {os.path.join(constraints_dir, output_filename)}")
            
            self.logger.info(f"Selected library: {library_id}")
            self.logger.info(f"  UCF: {self.cello_args.get('ucf_name', 'None')}")
            self.logger.info(f"  Input: {self.cello_args.get('in_name', 'None')}")
            self.logger.info(f"  Output: {self.cello_args.get('out_name', 'None')}")
            return True
        else:
            self.logger.error(f"Failed to select library: {library_id}")
            return False
            
    def get_available_libraries(self) -> List[str]:
        """
        Get a list of available libraries.
        
        Returns:
            List of library IDs
        """
        return self.library_manager.get_available_libraries()
        
    def create_custom_ucf(self, 
                         selected_gates: List[str] = None,
                         selected_parts: List[str] = None,
                         modified_parts: Dict[str, Dict] = None,
                         new_parts: List[Dict] = None,
                         ucf_name: str = None,
                         output_dir: str = None) -> Optional[str]:
        """
        Create a custom UCF file with selected parts and modifications.
        
        Args:
            selected_gates: List of gate IDs to include
            selected_parts: List of part IDs to include
            modified_parts: Dict of part_id -> modified properties
            new_parts: List of new part definitions to add
            ucf_name: Optional name for the UCF file
            output_dir: Optional directory to save the UCF file
            
        Returns:
            Path to the created UCF file or None if creation failed
        """
        # Create the custom UCF
        custom_ucf_path = self.library_manager.create_custom_ucf(
            selected_gates=selected_gates,
            selected_parts=selected_parts,
            modified_parts=modified_parts,
            new_parts=new_parts,
            ucf_name=ucf_name,
            output_dir=output_dir or self.cello_args["constraints_path"]
        )
        
        if custom_ucf_path:
            # Update Cello args to use the new UCF
            self.cello_args["ucf_name"] = os.path.basename(custom_ucf_path)
            self.logger.info(f"Created custom UCF: {custom_ucf_path}")
            return custom_ucf_path
        else:
            self.logger.error("Failed to create custom UCF")
            return None

    def _check_yosys_dependency(self) -> bool:
        """
        Check if Yosys is installed and available in the system PATH.
        
        Returns:
            bool: True if Yosys is available, False otherwise
        """
        yosys_available = shutil.which("yosys") is not None
        if not yosys_available:
            self.logger.warning("Yosys is not installed or not in the system PATH.")
            self.logger.warning("Yosys is required for Cello's logic synthesis.")
            self.logger.warning("Installation instructions:")
            self.logger.warning("  - macOS: brew install yosys")
            self.logger.warning("  - Ubuntu/Debian: sudo apt-get install yosys")
            self.logger.warning("  - Windows: Follow instructions at https://github.com/YosysHQ/yosys")
            self.logger.warning("Please install Yosys and ensure it's in your system PATH.")
        return yosys_available

    def run_cello(self, verilog_code: str = None, custom_ucf: Dict[str, Any] = None) -> Dict:
        """
        Run Cello with configured parameters and return results
        
        Args:
            verilog_code: Optional Verilog code to process. If provided, saves to temp file.
            custom_ucf: Optional dictionary with custom UCF parameters:
                - selected_gates: List of gate IDs to include
                - selected_parts: List of part IDs to include
                - modified_parts: Dict of part_id -> modified properties
                - new_parts: List of new part definitions to add
            
        Returns:
            Dict containing:
            - success: bool
            - log: str (captured log output)
            - results: Dict (Cello results including DNA design)
        """
        try:
            # Check for Yosys dependency
            yosys_available = self._check_yosys_dependency()
            if not yosys_available:
                return {
                    'success': False,
                    'log': '\n'.join(self.log_buffer),
                    'error': "Yosys is not installed or not in the system PATH. Yosys is required for Cello's logic synthesis."
                }
            
            # Process Verilog code if provided
            if verilog_code:
                # Save verilog code to temporary file
                verilog_path = os.path.join(self.cello_args['verilogs_path'], 
                                          self.cello_args['v_name'])
                os.makedirs(os.path.dirname(verilog_path), exist_ok=True)
                with open(verilog_path, 'w') as f:
                    f.write(verilog_code)
            
            # Create custom UCF if requested
            if custom_ucf:
                custom_ucf_path = self.create_custom_ucf(
                    selected_gates=custom_ucf.get("selected_gates"),
                    selected_parts=custom_ucf.get("selected_parts"),
                    modified_parts=custom_ucf.get("modified_parts"),
                    new_parts=custom_ucf.get("new_parts"),
                    ucf_name=custom_ucf.get("ucf_name")
                )
                
                if not custom_ucf_path:
                    return {
                        'success': False,
                        'log': '\n'.join(self.log_buffer),
                        'error': "Failed to create custom UCF"
                    }
            
            # Validate UCF file before running Cello
            ucf_path = os.path.join(
                self.cello_args.get('constraints_path', ''), 
                self.cello_args.get('ucf_name', '')
            )
            
            if os.path.exists(ucf_path):
                self.logger.info(f"Validating UCF file: {ucf_path}")
                try:
                    ucf_validator = UCFCustomizer(ucf_path)
                    validation_result = ucf_validator.validate_ucf()
                    
                    if not validation_result['valid']:
                        self.logger.error(f"UCF validation failed: {validation_result['errors']}")
                        return {
                            'success': False,
                            'log': '\n'.join(self.log_buffer),
                            'error': f"UCF validation failed: {validation_result['errors']}"
                        }
                except Exception as e:
                    self.logger.error(f"UCF validation error: {e}")
                    return {
                        'success': False,
                        'log': '\n'.join(self.log_buffer),
                        'error': f"UCF validation error: {e}"
                    }
            else:
                self.logger.error(f"UCF file not found at: {ucf_path}")
                return {
                    'success': False,
                    'log': '\n'.join(self.log_buffer),
                    'error': f"UCF file not found at: {ucf_path}"
                }

            self.logger.info("Starting Cello run with configuration: %s", self.cello_config)
            
            # Run Cello
            cello = CELLO3(**self.cello_args, options=self.cello_config)
            
            # Get output path
            output_path = os.path.join(self.cello_args['out_path'], 
                                     self.cello_args['v_name'])

            return {
                'success': True,
                'log': '\n'.join(self.log_buffer),
                'results': {
                    'output_path': output_path,
                    'dna_design': self._parse_cello_output(output_path)
                }
            }

        except Exception as e:
            self.logger.error(f"Cello run failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'log': '\n'.join(self.log_buffer),
                'error': str(e)
            }
        finally:
            self._stop_minieugene_server()

    def _parse_cello_output(self, output_path: str) -> Dict:
        """Parse Cello output files to extract design information"""
        results = {
            'sbol_file': None,
            'eugene_script': None,
            'dna_sequences': None,
            'activity_table': None,
            'circuit_score': None,
            'visualizations': [],
            'all_files_zip': None
        }

        # Check for expected files
        base_name = os.path.basename(output_path).replace('.v', '')
        search_patterns = {
            'sbol_file': f'{base_name}._pySBOL3.nt',
            'eugene_script': f'{base_name}._eugene.eug',
            'dna_sequences': f'{base_name}._dna-sequences.csv',
            'activity_table': f'{base_name}._activity-table.csv',
            'circuit_score': f'{base_name}._circuit-score.csv',
            'all_files_zip': f'{base_name}._all-files.zip'
        }

        # Find matching files
        for file_type, pattern in search_patterns.items():
            full_path = os.path.join(output_path, pattern)
            if os.path.exists(full_path):
                results[file_type] = full_path

        # Find visualizations
        vis_files = [
            f'{base_name}._response-plots.pdf',
            f'{base_name}._tech-mapping.pdf',
            f'{base_name}._dpl-sbol.pdf'
        ]
        results['visualizations'] = [
            os.path.join(output_path, f) for f in vis_files
            if os.path.exists(os.path.join(output_path, f))
        ]

        return results

if __name__ == "__main__":
    # Example usage
    cello = CelloIntegration(library_id="Eco1C1G1T1")
    
    # Print available libraries
    print("Available libraries:", cello.get_available_libraries())
    
    # Create a custom UCF with specific gates and parts
    custom_ucf = {
        "selected_gates": ["A1_AmtR", "P3_PhlF"],
        "selected_parts": ["pTac", "YFP", "L3S2P21"],
        "ucf_name": "custom_test.UCF.json"
    }
    
    # Run Cello with the custom UCF
    result = cello.run_cello(
        verilog_code="module main(input a, input b, output y); assign y = a & b; endmodule",
        custom_ucf=custom_ucf
    )
    
    print("Cello run success:", result["success"])
    if result["success"]:
        print("Output path:", result["results"]["output_path"])
