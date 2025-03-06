#!/usr/bin/env python3
"""
Cello Wrapper Script

This script is designed to be run as a separate process to isolate Cello
dependencies from the main application. It accepts arguments via a JSON
string, runs Cello, and returns the results as JSON.
"""

import argparse
import json
import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
import traceback
import subprocess
import time

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Try to set up the gateway
try:
    from gateway_setup import setup_gateway
    setup_gateway()
except ImportError:
    print("Warning: gateway_setup module not found")

def setup_logging():
    """Configure logging for the wrapper script"""
    logger = logging.getLogger('cello_wrapper')
    logger.setLevel(logging.INFO)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'cello_wrapper.log')
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

def setup_cello_path():
    """Add the Cello-v2-1-Core directory to the Python path"""
    cwd = os.getcwd()
    cello_core_path = os.path.join(cwd, "ext_repos", "Cello-v2-1-Core")
    
    if not os.path.exists(cello_core_path):
        raise ImportError(f"Cello-v2-1-Core directory not found at {cello_core_path}")
    
    sys.path.insert(0, cello_core_path)
    return cello_core_path

def start_minieugene_server():
    """Start the MiniEugene server in the background"""
    logger = logging.getLogger('cello_wrapper')
    logger.info("Starting MiniEugene server...")
    
    try:
        # Import the gateway module directly
        cwd = os.getcwd()
        py4j_path = os.path.join(cwd, "ext_repos", "Cello-v2-1-Core", "core_algorithm", "utils", "py4j_gateway")
        
        # Add py4j_gateway to path if not already there
        if py4j_path not in sys.path:
            sys.path.insert(0, py4j_path)
            logger.info(f"Added {py4j_path} to Python path")
        
        # Import the gateway module
        try:
            from gateway import start_gateway
            logger.info("Successfully imported gateway module")
        except ImportError as e:
            logger.error(f"Failed to import gateway module: {e}")
            
            # Create a temporary module to define BASE_DIR
            import types
            config_module = types.ModuleType('config')
            config_module.BASE_DIR = cwd
            sys.modules['config'] = config_module
            logger.info(f"Created temporary config module with BASE_DIR={cwd}")
            
            # Try again
            try:
                from gateway import start_gateway
                logger.info("Successfully imported gateway module after creating config")
            except ImportError as e2:
                logger.error(f"Still failed to import gateway module: {e2}")
                return None
        
        # Start the gateway
        logger.info("Starting MiniEugene gateway...")
        process = start_gateway()
        logger.info("MiniEugene gateway started")
        
        # Wait for the server to start
        time.sleep(5)
        
        # Check if the process is still running
        if process.poll() is not None:
            logger.error(f"MiniEugene server failed to start. Exit code: {process.poll()}")
            return None
        
        logger.info("MiniEugene server started successfully")
        return process
    
    except Exception as e:
        logger.error(f"Error starting MiniEugene server: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def stop_minieugene_server(process):
    """Stop the MiniEugene server process"""
    logger = logging.getLogger('cello_wrapper')
    
    if process is None:
        logger.warning("No MiniEugene server process to stop")
        return
    
    try:
        logger.info("Stopping MiniEugene server...")
        
        # Try to import gateway module to use terminate_gateway
        try:
            from gateway import terminate_gateway
            terminate_gateway(process)
            logger.info("MiniEugene gateway terminated")
        except ImportError:
            # Fall back to manual termination
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("MiniEugene server did not terminate gracefully, forcing kill")
                process.kill()
        
        logger.info("MiniEugene server stopped")
    
    except Exception as e:
        logger.error(f"Error stopping MiniEugene server: {str(e)}")
        logger.error(traceback.format_exc())

def create_custom_ucf(cello_args, selected_gates=None, selected_parts=None, 
                   modified_parts=None, new_parts=None, ucf_name=None, output_dir=None):
    """
    Create a custom UCF file based on selections or modifications
    
    Args:
        cello_args: Dictionary with Cello arguments
        selected_gates: List of gate IDs to include
        selected_parts: List of part IDs to include
        modified_parts: Dict of part_id -> modified properties
        new_parts: List of new part definitions to add
        ucf_name: Optional name for the custom UCF file
        output_dir: Optional directory to save the UCF file
        
    Returns:
        Path to the custom UCF file if successful, None otherwise
    """
    logger = logging.getLogger('cello_wrapper')
    
    try:
        # Get the path to the source UCF file
        ucf_path = os.path.join(
            cello_args.get('constraints_path', ''), 
            cello_args.get('ucf_name', '')
        )
        
        if not os.path.exists(ucf_path):
            logger.error(f"Source UCF file not found at {ucf_path}")
            return None
        
        # Load UCF file
        with open(ucf_path, 'r') as f:
            ucf_data = json.load(f)
        
        logger.info(f"Loaded source UCF file: {ucf_path}")
        
        if not isinstance(ucf_data, list):
            logger.error(f"UCF file is not in the expected list format")
            return None
        
        # Create a modified copy of the UCF
        modified_ucf = []
        
        # Process each item based on its collection
        for item in ucf_data:
            if not isinstance(item, dict) or 'collection' not in item:
                # Include non-standard items as-is
                modified_ucf.append(item)
                continue
            
            collection = item.get('collection')
            
            # Process gates
            if collection == 'gate':
                gate_name = item.get('gate_name')
                if selected_gates and gate_name not in selected_gates:
                    # Skip gates not in the selected list
                    continue
                
                # Include the gate
                modified_ucf.append(item)
            
            # Process parts
            elif collection == 'part':
                part_name = item.get('name')
                
                if selected_parts and part_name not in selected_parts:
                    # Skip parts not in the selected list
                    continue
                
                if modified_parts and part_name in modified_parts:
                    # Create a copy of the part and apply modifications
                    modified_part = item.copy()
                    for prop, value in modified_parts[part_name].items():
                        modified_part[prop] = value
                    
                    # Add the modified part
                    modified_ucf.append(modified_part)
                else:
                    # Include the part as-is
                    modified_ucf.append(item)
            
            else:
                # Include other collections as-is
                modified_ucf.append(item)
        
        # Add new parts if provided
        if new_parts:
            logger.info(f"Adding new parts: {len(new_parts)}")
            
            for new_part in new_parts:
                # Ensure the new part has the correct structure
                if not isinstance(new_part, dict):
                    logger.warning(f"Skipping invalid new part: not a dictionary")
                    continue
                
                # Ensure the part has a collection field set to 'part'
                if 'collection' not in new_part:
                    new_part['collection'] = 'part'
                
                # Add the new part
                modified_ucf.append(new_part)
        
        # Determine output path
        if not ucf_name:
            # Generate a name based on the source UCF
            base_name = os.path.basename(ucf_path)
            name_parts = os.path.splitext(base_name)
            ucf_name = f"{name_parts[0]}_custom{name_parts[1]}"
        
        if not output_dir:
            # Use constraints_path as default output directory
            output_dir = cello_args.get('constraints_path', '')
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the modified UCF file
        custom_ucf_path = os.path.join(output_dir, ucf_name)
        with open(custom_ucf_path, 'w') as f:
            json.dump(modified_ucf, f, indent=2)
        
        logger.info(f"Created custom UCF file at {custom_ucf_path}")
        
        # Update the UCF file name in cello_args
        cello_args['ucf_name'] = ucf_name
        
        return custom_ucf_path
    
    except Exception as e:
        logger.error(f"Error creating custom UCF: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def run_cello(args_dict):
    """
    Run Cello with the provided arguments
    
    Args:
        args_dict: Dictionary with cello_args, cello_config, verilog_code, and custom_ucf
    
    Returns:
        Dictionary with results
    """
    logger = logging.getLogger('cello_wrapper')
    minieugene_process = None
    
    try:
        # Extract arguments
        cello_args = args_dict.get('cello_args', {})
        cello_config = args_dict.get('cello_config', {})
        verilog_code = args_dict.get('verilog_code')
        custom_ucf_dict = args_dict.get('custom_ucf')
        
        # Setup Cello path
        setup_cello_path()
        
        # Process Verilog code if provided
        if verilog_code:
            verilog_path = os.path.join(cello_args['verilogs_path'], cello_args['v_name'])
            os.makedirs(os.path.dirname(verilog_path), exist_ok=True)
            with open(verilog_path, 'w') as f:
                f.write(verilog_code)
            logger.info(f"Saved Verilog code to {verilog_path}")
        
        # Handle custom UCF if provided
        if custom_ucf_dict:
            logger.info("Processing custom UCF")
            custom_ucf_path = create_custom_ucf(
                cello_args,
                selected_gates=custom_ucf_dict.get("selected_gates"),
                selected_parts=custom_ucf_dict.get("selected_parts"),
                modified_parts=custom_ucf_dict.get("modified_parts"),
                new_parts=custom_ucf_dict.get("new_parts"),
                ucf_name=custom_ucf_dict.get("ucf_name")
            )
            
            if not custom_ucf_path:
                return {
                    'success': False,
                    'error': "Failed to create custom UCF"
                }
            
            # Update the UCF name in cello_args
            cello_args['ucf_name'] = os.path.basename(custom_ucf_path)
        
        # Validate UCF file
        ucf_path = os.path.join(
            cello_args.get('constraints_path', ''), 
            cello_args.get('ucf_name', '')
        )
        
        logger.info(f"Validating UCF file: {ucf_path}")
        validation_result = validate_ucf(ucf_path)
        
        if not validation_result['valid']:
            return {
                'success': False,
                'error': f"UCF validation failed: {validation_result['errors']}"
            }
        
        # Check for Yosys dependency
        yosys_check = subprocess.run(
            ['which', 'yosys'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        if yosys_check.returncode != 0:
            return {
                'success': False,
                'error': "Yosys is not installed or not in the system PATH."
            }
        
        # Import Cello after setting up the path
        from core_algorithm.celloAlgo import CELLO3

        # Start MiniEugene server
        logger.info("Starting MiniEugene server before running Cello")
        minieugene_process = start_minieugene_server()
        
        if minieugene_process is None:
            return {
                'success': False,
                'error': "Failed to start MiniEugene server"
            }
        
        # Wait a bit more for the server to be fully ready
        time.sleep(3)
        
        # Configure Python path for py4j
        cwd = os.getcwd()
        py4j_path = os.path.join(cwd, "ext_repos", "Cello-v2-1-Core", "core_algorithm", "utils", "py4j_gateway")
        if py4j_path not in sys.path:
            sys.path.insert(0, py4j_path)
            logger.info(f"Added {py4j_path} to Python path")
        
        logger.info("Starting Cello run with configuration: %s", cello_config)
        
        # Create output directory if it doesn't exist
        os.makedirs(cello_args.get('out_path', 'outputs/cello_outputs'), exist_ok=True)
        
        # Run Cello
        try:
            cello = CELLO3(**cello_args, options=cello_config)
            
            # Get output path
            output_path = os.path.join(cello_args['out_path'], cello_args['v_name'])
            
            # Parse output files
            results = parse_cello_output(output_path)
            
            return {
                'success': True,
                'results': {
                    'output_path': output_path,
                    'dna_design': results
                }
            }
        except Exception as cello_error:
            logger.error(f"Error running CELLO3: {str(cello_error)}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': f"Error running CELLO3: {str(cello_error)}"
            }
    
    except Exception as e:
        logger.error(f"Cello run failed: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }
    finally:
        # Stop MiniEugene server
        if minieugene_process is not None:
            stop_minieugene_server(minieugene_process)

def parse_cello_output(output_path):
    """
    Parse Cello output files to extract design information
    
    Args:
        output_path: Path to the output directory
        
    Returns:
        Dictionary with parsed data
    """
    logger = logging.getLogger('cello_wrapper')
    logger.info(f"Parsing Cello output from: {output_path}")
    
    results = {
        'sbol_file': None,
        'eugene_script': None,
        'dna_sequences': None,
        'activity_table': None,
        'circuit_score': None,
        'visualizations': [],
        'all_files_zip': None,
        'part_usage': None
    }
    
    try:
        # Check if output directory exists
        if not os.path.exists(output_path):
            logger.error(f"Output directory not found: {output_path}")
            return results
        
        # Find all files recursively in the output directory
        all_files = []
        for root, dirs, files in os.walk(output_path):
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)
        
        # Log all found files for debugging
        logger.info(f"Found {len(all_files)} files in output directory:")
        for file in all_files:
            logger.info(f"  - {file}")
        
        # Find specific file types by extension or directory
        for file_path in all_files:
            # Get relative path for logging
            rel_path = os.path.relpath(file_path, output_path)
            file_name = os.path.basename(file_path)
            
            # SBOL file
            if file_name.endswith(".sbol") or file_name.endswith(".nt"):
                results['sbol_file'] = file_path
                logger.info(f"Found SBOL file: {rel_path}")
            
            # Eugene script
            elif file_name.endswith(".eug"):
                results['eugene_script'] = file_path
                logger.info(f"Found Eugene script: {rel_path}")
            
            # DNA sequences
            elif "dnafiles" in file_path and (file_name.endswith(".prom") or file_name.endswith(".csv")):
                results['dna_sequences'] = file_path
                logger.info(f"Found DNA sequences: {rel_path}")
            
            # Activity table
            elif "logic" in file_path and file_name == "activity.txt" or file_name.endswith("activity-table.csv"):
                results['activity_table'] = file_path
                logger.info(f"Found activity table: {rel_path}")
                
                # Parse activity table data
                activity_data = extract_activity_table_data(file_path)
                results['activity_data'] = activity_data
            
            # Circuit score
            elif "results" in file_path and file_name == "circuit_score.txt" or file_name.endswith("circuit-score.csv"):
                results['circuit_score'] = file_path
                
                # Extract score value
                score = extract_circuit_score(file_path)
                results['score_value'] = score
                logger.info(f"Found circuit score: {score}")
            
            # Visualizations
            elif file_name.endswith((".png", ".svg", ".jpg", ".jpeg", ".pdf")):
                results['visualizations'].append(file_path)
                logger.info(f"Found visualization: {rel_path}")
            
            # ZIP file with all output
            elif file_name.endswith(".zip") and "all-files" in file_name:
                results['all_files_zip'] = file_path
                logger.info(f"Found ZIP archive: {rel_path}")
            
            # Part usage info
            elif "parts" in file_path and file_name == "parts.txt" or file_name.endswith("part-information.csv"):
                part_usage = extract_part_usage(file_path)
                results['part_usage'] = part_usage
                logger.info(f"Found part usage info: {rel_path}")
        
        logger.info("Completed parsing Cello output")
        return results
    
    except Exception as e:
        logger.error(f"Error parsing Cello output: {str(e)}")
        logger.error(traceback.format_exc())
        return results

def extract_activity_table_data(activity_file):
    """Extract data from the activity table file"""
    logger = logging.getLogger('cello_wrapper')
    
    try:
        with open(activity_file, 'r') as f:
            lines = f.readlines()
        
        data = {
            'inputs': [],
            'outputs': [],
            'rows': []
        }
        
        # Parse header for inputs and outputs
        if len(lines) > 0:
            header = lines[0].strip().split()
            # Assuming first columns are inputs, last column is output
            if len(header) > 1:
                data['inputs'] = header[:-1]
                data['outputs'] = [header[-1]]
        
        # Parse data rows
        for line in lines[1:]:
            values = line.strip().split()
            if len(values) == len(header):
                row = {
                    'input_states': values[:-1],
                    'output_states': [values[-1]]
                }
                data['rows'].append(row)
        
        return data
    
    except Exception as e:
        logger.error(f"Error extracting activity table data: {str(e)}")
        return {}

def extract_circuit_score(score_file):
    """Extract the circuit score from the score file"""
    logger = logging.getLogger('cello_wrapper')
    
    try:
        with open(score_file, 'r') as f:
            content = f.read().strip()
        
        try:
            score = float(content)
            return score
        except ValueError:
            logger.error(f"Could not convert score to float: {content}")
            return None
    
    except Exception as e:
        logger.error(f"Error extracting circuit score: {str(e)}")
        return None

def extract_part_usage(part_info_file):
    """Extract part usage information from parts file"""
    logger = logging.getLogger('cello_wrapper')
    
    try:
        with open(part_info_file, 'r') as f:
            lines = f.readlines()
        
        part_usage = {
            'promoters': [],
            'ribozymes': [],
            'rbs': [],
            'cds': [],
            'terminators': []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Check for section headers
            if line.startswith("Promoters:"):
                current_section = 'promoters'
            elif line.startswith("Ribozymes:"):
                current_section = 'ribozymes'
            elif line.startswith("RBS:"):
                current_section = 'rbs'
            elif line.startswith("CDS:"):
                current_section = 'cds'
            elif line.startswith("Terminators:"):
                current_section = 'terminators'
            # Skip empty lines or section headers
            elif line and current_section and not line.endswith(":"):
                part_usage[current_section].append(line)
        
        return part_usage
    
    except Exception as e:
        logger.error(f"Error extracting part usage: {str(e)}")
        return {}

def validate_ucf(ucf_path):
    """
    Validate a UCF file
    
    Args:
        ucf_path: Path to the UCF file
        
    Returns:
        Dict with validation results
    """
    logger = logging.getLogger('cello_wrapper')
    
    try:
        # Check if file exists
        if not os.path.exists(ucf_path):
            return {
                'valid': False,
                'errors': [f"UCF file not found at {ucf_path}"]
            }
        
        # Read the UCF file
        with open(ucf_path, 'r') as f:
            ucf_data = json.load(f)
        
        # Validate basic structure
        errors = []
        
        # Check that UCF data is a list
        if not isinstance(ucf_data, list):
            errors.append("UCF data must be a list")
            return {
                'valid': False,
                'errors': errors
            }
        
        # Check for required collections
        required_collections = ['header', 'measurement_std']
        found_collections = set()
        
        # Count gates and parts
        gate_count = 0
        part_count = 0
        
        for item in ucf_data:
            if not isinstance(item, dict):
                errors.append("UCF item must be an object")
                continue
                
            if 'collection' not in item:
                errors.append("UCF item must have a 'collection' property")
                continue
                
            collection = item.get('collection')
            found_collections.add(collection)
            
            # Count gates
            if collection == 'gate':
                gate_count += 1
                # Validate gate
                if 'gate_name' not in item:
                    errors.append(f"Gate at index {ucf_data.index(item)} is missing 'gate_name'")
                if 'gate_type' not in item:
                    errors.append(f"Gate at index {ucf_data.index(item)} is missing 'gate_type'")
            
            # Count parts
            elif collection == 'part':
                part_count += 1
                # Validate part
                if 'name' not in item:
                    errors.append(f"Part at index {ucf_data.index(item)} is missing 'name'")
                if 'type' not in item:
                    errors.append(f"Part at index {ucf_data.index(item)} is missing 'type'")
        
        # Check that required collections are present
        for collection in required_collections:
            if collection not in found_collections:
                errors.append(f"UCF is missing required collection: {collection}")
        
        # Check that there are gates and parts
        # Note: Some UCFs might not have gates or parts directly, they could be in other collections
        # So this is more of a warning than an error
        if gate_count == 0:
            logger.warning("UCF does not contain any gates (collection: 'gate')")
        
        if part_count == 0:
            logger.warning("UCF does not contain any parts (collection: 'part')")
        
        # Return validation result
        if errors:
            logger.error(f"UCF validation failed with {len(errors)} errors")
            for error in errors:
                logger.error(f"  - {error}")
            return {
                'valid': False,
                'errors': errors
            }
        else:
            logger.info(f"UCF validation successful")
            return {
                'valid': True,
                'errors': []
            }
    
    except json.JSONDecodeError as e:
        error = f"UCF file is not valid JSON: {str(e)}"
        logger.error(error)
        return {
            'valid': False,
            'errors': [error]
        }
    except Exception as e:
        error = f"Error validating UCF: {str(e)}"
        logger.error(error)
        logger.error(traceback.format_exc())
        return {
            'valid': False,
            'errors': [error]
        }

def main():
    """Main function to run the wrapper script"""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description='Cello Wrapper Script')
    parser.add_argument('--input', help='JSON-encoded input arguments')
    parser.add_argument('--input-file', help='Path to file containing JSON input arguments')
    args = parser.parse_args()
    
    try:
        # Get input arguments from either command-line or file
        input_json = None
        if args.input:
            input_json = args.input
        elif args.input_file:
            with open(args.input_file, 'r') as f:
                input_json = f.read()
        else:
            # If no arguments provided, try reading from stdin
            input_json = sys.stdin.read()
        
        if not input_json:
            logger.error("No input arguments provided")
            sys.exit(1)
        
        # Parse JSON input
        args_dict = json.loads(input_json)
        
        # Run Cello
        result = run_cello(args_dict)
        
        # Output results as JSON
        print(json.dumps(result))
    
    except Exception as e:
        logger.error(f"Error running wrapper script: {str(e)}")
        logger.error(traceback.format_exc())
        error_result = {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == '__main__':
    main() 