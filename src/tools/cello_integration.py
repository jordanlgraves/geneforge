# cello_integration.py
import subprocess
import os
import time
import atexit
import logging
import shutil
import math
from typing import Dict, Optional, List, Any, Union
import json
import tempfile
from pathlib import Path
import sys

# Import UCFCustomizer for validation
from src.library.ucf_customizer import UCFCustomizer
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
        """
        Start the MiniEugene server if needed for Cello
        
        Note: This is now a placeholder since MiniEugene server is managed by 
        the wrapper script in its own subprocess environment
        """
        self.logger.info("MiniEugene server will be managed by the wrapper script")
        self.java_process = None

    def _stop_minieugene_server(self):
        """
        Stop the MiniEugene server if it's running
        
        Note: This is now a placeholder since MiniEugene server is managed by 
        the wrapper script in its own subprocess environment
        """
        self.logger.info("MiniEugene server is managed by the wrapper script")
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
            
            # Make sure output directory exists
            os.makedirs(self.cello_args.get('out_path', 'outputs/cello_outputs'), exist_ok=True)
            
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
            
            # Prepare input for wrapper script
            wrapper_input = {
                'cello_args': self.cello_args,
                'cello_config': self.cello_config,
                'verilog_code': verilog_code,
                'custom_ucf': custom_ucf
            }
            
            # Write input to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
                json.dump(wrapper_input, input_file)
                input_path = input_file.name
            
            self.logger.info(f"Saved wrapper input to {input_path}")
            
            # Get the absolute path to the wrapper script
            wrapper_script = os.path.join(os.getcwd(), "src", "tools", "cello_wrapper.py")
            if not os.path.exists(wrapper_script):
                self.logger.error(f"Wrapper script not found at {wrapper_script}")
                return {
                    'success': False,
                    'log': '\n'.join(self.log_buffer),
                    'error': f"Wrapper script not found at {wrapper_script}"
                }
            
            # Make wrapper script executable
            os.chmod(wrapper_script, 0o755)
            
            # Run the wrapper script in a separate process
            self.logger.info(f"Running wrapper script: {wrapper_script}")
            
            # Build the command to run the wrapper script
            cmd = [
                "python3",  # Use Python 3
                wrapper_script,
                "--input-file", input_path
            ]
            
            self.logger.info(f"Running command: {' '.join(cmd)}")
            
            # Run the command and capture output
            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=os.getcwd(),  # Run from the project root
                    timeout=600  # 10-minute timeout for Cello run
                )
            except subprocess.TimeoutExpired:
                self.logger.error("Cello process timed out after 10 minutes")
                return {
                    'success': False,
                    'log': '\n'.join(self.log_buffer),
                    'error': "Cello process timed out after 10 minutes"
                }
            
            # Clean up the input file
            try:
                os.unlink(input_path)
            except Exception as e:
                self.logger.warning(f"Failed to delete input file {input_path}: {e}")
            
            # Process the output
            if process.returncode != 0:
                self.logger.error(f"Wrapper script failed with exit code {process.returncode}")
                self.logger.error(f"Stdout: {process.stdout}")
                self.logger.error(f"Stderr: {process.stderr}")
                return {
                    'success': False,
                    'log': '\n'.join(self.log_buffer) + '\n' + process.stderr,
                    'error': f"Wrapper script failed with exit code {process.returncode}"
                }
            
            # Parse the output JSON
            try:
                result = json.loads(process.stdout)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse wrapper output as JSON: {e}")
                self.logger.error(f"Wrapper output: {process.stdout}")
                return {
                    'success': False,
                    'log': '\n'.join(self.log_buffer) + '\n' + process.stdout,
                    'error': f"Failed to parse wrapper output as JSON: {e}"
                }
            
            # Add the log buffer to the result
            if 'log' in result:
                result['log'] = '\n'.join(self.log_buffer) + '\n' + result['log']
            else:
                result['log'] = '\n'.join(self.log_buffer)
            
            # If successful, add more detailed information about the output directory
            if result.get('success', False) and 'results' in result:
                output_path = result['results'].get('output_path')
                if output_path and os.path.exists(output_path):
                    self.logger.info(f"Cello output directory: {output_path}")
                    # List all files in the output directory
                    all_files = []
                    for root, dirs, files in os.walk(output_path):
                        for file in files:
                            rel_path = os.path.relpath(os.path.join(root, file), output_path)
                            all_files.append(rel_path)
                    
                    if all_files:
                        self.logger.info(f"Generated {len(all_files)} output files")
                        result['results']['all_files'] = all_files
            
            return result

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

        # Check if directory exists
        if not os.path.exists(output_path):
            self.logger.warning(f"Output path does not exist: {output_path}")
            return results

        # List all files in the output directory
        output_files = os.listdir(output_path)
        
        # Map file types to patterns
        file_type_patterns = {
            'sbol_file': '_pySBOL3.nt',
            'eugene_script': '_eugene.eug',
            'dna_sequences': '_dna-sequences.csv',
            'activity_table': '_activity-table.csv',
            'circuit_score': '_circuit-score.csv',
            'all_files_zip': '_all-files.zip'
        }
        
        # Find matching files for each file type
        for file_type, pattern in file_type_patterns.items():
            for filename in output_files:
                if pattern in filename:
                    results[file_type] = os.path.join(output_path, filename)
                    break
        
        # Find visualizations
        visualization_patterns = [
            '_response-plots.pdf',
            '_tech-mapping.pdf',
            '_dpl-sbol.pdf',
            '_response-plots.png',
            '_tech-mapping.png',
            '_dpl-sbol.png'
        ]
        
        for pattern in visualization_patterns:
            for filename in output_files:
                if pattern in filename:
                    results['visualizations'].append(os.path.join(output_path, filename))
        
        # Log what we found
        self.logger.info(f"Found Cello output files:")
        for file_type, file_path in results.items():
            if file_type == 'visualizations':
                self.logger.info(f"  Visualizations: {len(results['visualizations'])} files")
            elif file_path:
                self.logger.info(f"  {file_type}: {os.path.basename(file_path)}")
            else:
                self.logger.info(f"  {file_type}: Not found")
        
        return results

    def evaluate_circuit_performance(self, output_path: str) -> Dict:
        """
        Evaluates circuit performance by extracting and analyzing metrics from Cello output files.
        
        Args:
            output_path: Path to Cello output directory
            
        Returns:
            Dictionary containing performance metrics including:
            - Overall circuit score
            - ON/OFF ratios for each output
            - Leakage percentages
            - Dynamic range
            - Derived KPIs
        """
        metrics = {
            'overall_score': None,
            'input_output_states': [],
            'on_off_ratios': {},
            'leakage': {},
            'dynamic_range': {},
            'part_usage': {},
            'success': False,
            'error': None
        }
        
        try:
            # Get files to analyze
            parsed_output = self._parse_cello_output(output_path)
            circuit_score_file = parsed_output.get('circuit_score')
            activity_table_file = parsed_output.get('activity_table')
            part_info_file = None
            
            # Look for part information file
            for filename in os.listdir(output_path):
                if '_dpl-part-information.csv' in filename:
                    part_info_file = os.path.join(output_path, filename)
                    break
            
            # Extract overall circuit score
            if circuit_score_file and os.path.exists(circuit_score_file):
                metrics['overall_score'] = self._extract_circuit_score(circuit_score_file)
            
            # Extract activity table data
            if activity_table_file and os.path.exists(activity_table_file):
                io_data = self._extract_activity_table_data(activity_table_file)
                metrics.update(io_data)
            
            # Extract part usage information
            if part_info_file and os.path.exists(part_info_file):
                metrics['part_usage'] = self._extract_part_usage(part_info_file)
            
            # Calculate derived metrics
            self._calculate_derived_metrics(metrics)
            
            metrics['success'] = True
            
        except Exception as e:
            metrics['success'] = False
            metrics['error'] = str(e)
            self.logger.error(f"Error evaluating circuit performance: {str(e)}")
        
        return metrics
    
    def _extract_circuit_score(self, circuit_score_file: str) -> float:
        """Extract the overall circuit score from circuit_score.csv"""
        self.logger.info(f"Extracting circuit score from: {circuit_score_file}")
        try:
            with open(circuit_score_file, 'r') as f:
                lines = f.readlines()
                self.logger.info(f"Read {len(lines)} lines from circuit score file: {lines}")
                if len(lines) >= 1:  # Changed from 2 to 1 as we only need one line
                    # Expected format: "circuit_score,SCORE_VALUE"
                    score_line = lines[0].strip()  # Always use the first line
                    self.logger.info(f"Score line: {score_line}")
                    parts = score_line.split(',')
                    self.logger.info(f"Split parts: {parts}")
                    if len(parts) >= 2:
                        return float(parts[1])
                    elif len(parts) == 1 and parts[0].replace('.', '', 1).isdigit():
                        return float(parts[0])
                    else:
                        self.logger.warning(f"Unexpected circuit score format: {score_line}")
                        return 0.0
                self.logger.warning(f"Not enough lines in circuit score file")
                return 0.0
        except Exception as e:
            self.logger.error(f"Error extracting circuit score: {str(e)}")
            return 0.0
    
    def _extract_activity_table_data(self, activity_table_file: str) -> Dict:
        """Extract data from the activity table CSV file"""
        result = {
            'input_output_states': [],
            'on_off_ratios': {},
            'leakage': {},
            'on_values': {},
            'off_values': {}
        }
        
        try:
            with open(activity_table_file, 'r') as f:
                lines = f.readlines()
                
                # Parse the file based on sections
                section = None
                headers = []
                numeric_values = []
                binary_values = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.lower() == "scores...":
                        section = "scores"
                        continue
                    elif line.lower() == "binary...":
                        section = "binary"
                        continue
                    
                    if section == "scores":
                        if "," in line and not any(keyword in line.lower() for keyword in ["scores", "binary"]):
                            parts = line.split(',')
                            if all(part.replace('.', '', 1).replace('e', '', 1).replace('-', '', 1).replace('+', '', 1).isdigit() for part in parts[1:]):
                                numeric_values.append([float(p) if p else 0.0 for p in parts])
                            else:
                                headers = parts
                    elif section == "binary":
                        if "," in line and not any(keyword in line.lower() for keyword in ["scores", "binary"]):
                            parts = line.split(',')
                            if "_I/O" in parts[0]:
                                headers = parts
                            elif all(part in ("0", "1", "") for part in parts):
                                binary_values.append([int(p) if p else 0 for p in parts])
                
                # Process the extracted data
                if headers and binary_values:
                    # Extract input/output states
                    io_states = []
                    for binary_row in binary_values:
                        if len(binary_row) == len(headers):
                            state = {}
                            for i, header in enumerate(headers):
                                component_name = header.replace("_I/O", "")
                                state[component_name] = binary_row[i]
                            io_states.append(state)
                    result['input_output_states'] = io_states
                
                # Process numeric scores for ON/OFF ratio and leakage calculation
                if headers and numeric_values and len(numeric_values) >= 2:
                    # Identify outputs (typically the last component)
                    if len(headers) > 1:
                        output_components = [header for header in headers if 'reporter' in header.lower()]
                        if not output_components and len(headers) > 1:
                            # If no reporter found, assume the last component is the output
                            output_components = [headers[-1]]
                            
                        # For each output component, calculate ON/OFF ratio
                        for output in output_components:
                            output_idx = headers.index(output)
                            on_values = []
                            off_values = []
                            
                            # Determine which states are ON and OFF for this output
                            for i, binary_row in enumerate(binary_values):
                                if i < len(numeric_values):  # Make sure we have corresponding numeric values
                                    if output_idx < len(binary_row) and output_idx < len(numeric_values[i]):
                                        if binary_row[output_idx] == 1:
                                            on_values.append(numeric_values[i][output_idx])
                                        else:
                                            off_values.append(numeric_values[i][output_idx])
                            
                            # Calculate metrics if we have both ON and OFF values
                            if on_values and off_values:
                                avg_on = sum(on_values) / len(on_values)
                                avg_off = sum(off_values) / len(off_values)
                                
                                # Store values for later use
                                result['on_values'][output] = on_values
                                result['off_values'][output] = off_values
                                
                                # Calculate ON/OFF ratio
                                if avg_off > 0:
                                    ratio = avg_on / avg_off
                                    result['on_off_ratios'][output] = ratio
                                else:
                                    result['on_off_ratios'][output] = float('inf')  # Avoid division by zero
                                
                                # Calculate leakage (OFF value as percentage of ON value)
                                if avg_on > 0:
                                    leakage_pct = (avg_off / avg_on) * 100
                                    result['leakage'][output] = leakage_pct
                                else:
                                    result['leakage'][output] = 0.0
            
        except Exception as e:
            self.logger.error(f"Error extracting activity table data: {str(e)}")
        
        return result
    
    def _extract_part_usage(self, part_info_file: str) -> Dict:
        """Extract information about parts used in the circuit"""
        part_usage = {
            'promoters': [],
            'rbs': [],
            'cds': [],
            'terminators': [],
            'other': []
        }
        
        try:
            with open(part_info_file, 'r') as f:
                # Skip header line
                next(f)
                
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        part_name = parts[0]
                        part_type = parts[1].lower()
                        
                        if 'promoter' in part_type:
                            part_usage['promoters'].append(part_name)
                        elif 'rbs' in part_type:
                            part_usage['rbs'].append(part_name)
                        elif 'cds' in part_type:
                            part_usage['cds'].append(part_name)
                        elif 'terminator' in part_type:
                            part_usage['terminators'].append(part_name)
                        else:
                            part_usage['other'].append(part_name)
        except Exception as e:
            self.logger.error(f"Error extracting part usage information: {str(e)}")
        
        return part_usage
    
    def _calculate_derived_metrics(self, metrics: Dict) -> None:
        """Calculate additional performance metrics derived from basic metrics"""
        # Calculate dynamic range for each output
        for output, ratio in metrics.get('on_off_ratios', {}).items():
            # Dynamic range in decibels (dB)
            if ratio > 0:
                metrics['dynamic_range'][output] = 20 * math.log10(ratio)
            else:
                metrics['dynamic_range'][output] = 0.0
        
        # Add any other derived metrics here
        metrics['average_on_off_ratio'] = sum(metrics.get('on_off_ratios', {}).values()) / len(metrics.get('on_off_ratios', {})) if metrics.get('on_off_ratios') else 0.0
        metrics['average_leakage'] = sum(metrics.get('leakage', {}).values()) / len(metrics.get('leakage', {})) if metrics.get('leakage') else 0.0
        
        # Determine if the circuit meets common performance standards
        metrics['meets_performance_standards'] = {}
        
        for output, ratio in metrics.get('on_off_ratios', {}).items():
            metrics['meets_performance_standards'][output] = {
                'on_off_ratio': ratio >= 500,  # Much stricter threshold: ON/OFF ratio should be at least 500 (was 10)
                'leakage': metrics.get('leakage', {}).get(output, 100) <= 0.1  # Much stricter threshold: leakage should be less than 0.1% (was 10%)
            }

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
