#!/usr/bin/env python3
"""
Demo script for the LLM-based Cello designer.
This script demonstrates how to use the LLMCelloDesigner class to select files and parts
for Cello based on user requests.
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any

# Add the parent directory to the path so we can import the library
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library.llm_cello_designer import LLMCelloDesigner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_argparse() -> argparse.ArgumentParser:
    """
    Set up command-line argument parsing.
    
    Returns:
        ArgumentParser object
    """
    parser = argparse.ArgumentParser(description='Demo for LLM-based Cello designer')
    
    parser.add_argument(
        '--ucf-dir',
        type=str,
        default='data/ucf',
        help='Directory containing UCF files'
    )
    
    parser.add_argument(
        '--input-dir',
        type=str,
        default='data/input',
        help='Directory containing input files'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/output',
        help='Directory containing output files'
    )
    
    parser.add_argument(
        '--request',
        type=str,
        default='Design a circuit that senses arabinose and produces GFP using NOT and AND gates.',
        help='User request for circuit design'
    )
    
    parser.add_argument(
        '--llm-reasoning',
        type=str,
        default=None,
        help='Optional LLM reasoning about file and part selection'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        default='demo_results.json',
        help='File to save the results to'
    )
    
    parser.add_argument(
        '--generate-verilog',
        action='store_true',
        help='Generate Verilog code for the selected parts'
    )
    
    return parser

def print_section_header(title: str):
    """
    Print a section header with the given title.
    
    Args:
        title: Title of the section
    """
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def print_available_files(designer: LLMCelloDesigner):
    """
    Print information about available files.
    
    Args:
        designer: LLMCelloDesigner instance
    """
    print_section_header("Available Files")
    
    available_files = designer.get_available_files()
    
    # Print UCF files
    print("UCF Files:")
    for organism, files in available_files.get("ucf", {}).items():
        print(f"  Organism: {organism}")
        for file_info in files:
            print(f"    - {file_info['path']} ({file_info['size']} bytes)")
    
    # Print input files
    print("\nInput Files:")
    for organism, files in available_files.get("input", {}).items():
        print(f"  Organism: {organism}")
        for file_info in files:
            print(f"    - {file_info['path']} ({file_info['size']} bytes)")
    
    # Print output files
    print("\nOutput Files:")
    for organism, files in available_files.get("output", {}).items():
        print(f"  Organism: {organism}")
        for file_info in files:
            print(f"    - {file_info['path']} ({file_info['size']} bytes)")

def print_selected_files(designer: LLMCelloDesigner):
    """
    Print information about selected files.
    
    Args:
        designer: LLMCelloDesigner instance
    """
    print_section_header("Selected Files")
    
    if not designer.selected_files:
        print("No files were selected.")
        return
    
    # Print selected UCF file
    if "ucf" in designer.selected_files:
        print(f"UCF File: {designer.selected_files['ucf']}")
    else:
        print("UCF File: None")
    
    # Print selected input file
    if "input" in designer.selected_files:
        print(f"Input File: {designer.selected_files['input']}")
    else:
        print("Input File: None")
    
    # Print selected output file
    if "output" in designer.selected_files:
        print(f"Output File: {designer.selected_files['output']}")
    else:
        print("Output File: None")

def print_available_parts(designer: LLMCelloDesigner):
    """
    Print information about available parts.
    
    Args:
        designer: LLMCelloDesigner instance
    """
    print_section_header("Available Parts")
    
    available_parts = designer.get_available_parts()
    
    # Print gates
    print("Gates:")
    for gate in available_parts.get("gates", []):
        print(f"  - {gate['name']}: {gate['description']}")
        print(f"    Properties: {json.dumps(gate['properties'], indent=2)}")
    
    # Print sensors
    print("\nSensors:")
    for sensor in available_parts.get("sensors", []):
        print(f"  - {sensor['name']}: {sensor['description']}")
        print(f"    Properties: {json.dumps(sensor['properties'], indent=2)}")
    
    # Print reporters
    print("\nReporters:")
    for reporter in available_parts.get("reporters", []):
        print(f"  - {reporter['name']}: {reporter['description']}")
        print(f"    Properties: {json.dumps(reporter['properties'], indent=2)}")

def print_selected_parts(designer: LLMCelloDesigner):
    """
    Print information about selected parts.
    
    Args:
        designer: LLMCelloDesigner instance
    """
    print_section_header("Selected Parts")
    
    if not designer.selected_parts:
        print("No parts were selected.")
        return
    
    # Print selected gates
    print("Gates:")
    for gate in designer.selected_parts.get("gates", []):
        print(f"  - {gate.get('name', 'Unknown')}")
        if "gate_type" in gate:
            print(f"    Type: {gate['gate_type']}")
    
    # Print selected sensors
    print("\nSensors:")
    for sensor in designer.selected_parts.get("sensors", []):
        print(f"  - {sensor.get('name', 'Unknown')}")
        if "sensing" in sensor:
            print(f"    Senses: {sensor['sensing']}")
    
    # Print selected reporters
    print("\nReporters:")
    for reporter in designer.selected_parts.get("reporters", []):
        print(f"  - {reporter.get('name', 'Unknown')}")
        if "output" in reporter:
            print(f"    Output: {reporter['output']}")

def print_explanations(designer: LLMCelloDesigner, user_request: str):
    """
    Print explanations for file and part selection.
    
    Args:
        designer: LLMCelloDesigner instance
        user_request: User's request
    """
    print_section_header("Explanations")
    
    explanations = designer.explain_selection(user_request)
    
    # Print file selection explanation
    if "file_selection" in explanations:
        print(explanations["file_selection"])
    
    # Print part selection explanation
    if "part_selection" in explanations:
        print("\n" + explanations["part_selection"])

def print_verilog_code(designer: LLMCelloDesigner, user_request: str):
    """
    Print generated Verilog code.
    
    Args:
        designer: LLMCelloDesigner instance
        user_request: User's request
    """
    print_section_header("Generated Verilog Code")
    
    verilog_code = designer.generate_verilog(user_request)
    print(verilog_code)

def save_results(designer: LLMCelloDesigner, user_request: str, output_file: str, generate_verilog: bool):
    """
    Save the results to a JSON file.
    
    Args:
        designer: LLMCelloDesigner instance
        user_request: User's request
        output_file: Path to the output file
        generate_verilog: Whether to generate Verilog code
    """
    results = {
        "user_request": user_request,
        "selected_files": designer.selected_files,
        "selected_parts": {},
        "explanations": designer.explain_selection(user_request)
    }
    
    # Convert selected parts to a serializable format
    if designer.selected_parts:
        for category, parts in designer.selected_parts.items():
            results["selected_parts"][category] = []
            for part in parts:
                # Extract relevant information
                part_info = {
                    "name": part.get("name", "Unknown"),
                    "type": part.get("type", "Unknown")
                }
                
                # Add gate-specific information
                if category == "gates" and "gate_type" in part:
                    part_info["gate_type"] = part["gate_type"]
                
                # Add sensor-specific information
                if category == "sensors" and "sensing" in part:
                    part_info["sensing"] = part["sensing"]
                
                # Add reporter-specific information
                if category == "reporters" and "output" in part:
                    part_info["output"] = part["output"]
                
                results["selected_parts"][category].append(part_info)
    
    # Add Verilog code if requested
    if generate_verilog:
        results["verilog_code"] = designer.generate_verilog(user_request)
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {output_file}")

def main():
    """
    Main function for the demo script.
    """
    # Parse command-line arguments
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Create directories if they don't exist
    os.makedirs(args.ucf_dir, exist_ok=True)
    os.makedirs(args.input_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create the designer
    designer = LLMCelloDesigner(
        ucf_dir=args.ucf_dir,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        organism_prefixes={
            "Escherichia coli": "Eco",
            "Bacillus subtilis": "Bsu",
            "Saccharomyces cerevisiae": "Sce"
        }
    )
    
    # Print information about available files
    print_available_files(designer)
    
    # Process the user request
    print_section_header(f"Processing Request: {args.request}")
    result = designer.process_user_request(args.request, args.llm_reasoning)
    
    # Print selected files
    print_selected_files(designer)
    
    # Print available parts
    print_available_parts(designer)
    
    # Print selected parts
    print_selected_parts(designer)
    
    # Print explanations
    print_explanations(designer, args.request)
    
    # Print Verilog code if requested
    if args.generate_verilog:
        print_verilog_code(designer, args.request)
    
    # Save results to file
    save_results(designer, args.request, args.output_file, args.generate_verilog)

if __name__ == "__main__":
    main() 