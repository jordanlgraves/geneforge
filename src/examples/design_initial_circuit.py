#!/usr/bin/env python3
"""
Design a genetic circuit in E. coli that implements a 2-input AND logic function.

This script implements the first step in the optimization workflow:
1. Design an initial circuit with Cello
2. Get the results and performance metrics

Inputs:
- Input A (induced by arabinose)
- Input B (induced by IPTG)
Output:
- GFP expression (controlled by pLac promoter)
"""

import os
import sys
import logging
import json
from pathlib import Path

from src.tools.cello_integration import CelloIntegration
from src.library.ucf_customizer import UCFCustomizer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("InitialCircuitDesign")

def design_initial_circuit():
    """
    Design an initial 2-input AND gate circuit in E. coli using Cello.
    
    Returns:
        Dictionary with design results
    """
    logger.info("Setting up Cello integration...")
    cello = CelloIntegration()
    
    # Create output directory
    output_dir = "outputs/initial_circuit"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create the Verilog code for a 2-input AND gate
    verilog_code = """
module main(input a, input b, output out);
  and(out, a, b);
endmodule
    """
    
    logger.info("Generated Verilog code for 2-input AND gate")
    
    # Get available libraries
    available_libraries = cello.get_available_libraries()
    logger.info(f"Available libraries: {available_libraries}")
    
    # Select the Eco1C1G1T1 library which should have E. coli parts
    library_id = "Eco1C1G1T1"
    logger.info(f"Selecting library: {library_id}")
    
    success = cello.select_library(library_id)
    if not success:
        logger.error(f"Failed to select library: {library_id}")
        return {'success': False, 'error': f"Failed to select library: {library_id}"}
    
    # Get the UCF path
    ucf_path = os.path.join(
        cello.cello_args.get('constraints_path', ''),
        cello.cello_args.get('ucf_name', '')
    )
    
    if not os.path.exists(ucf_path):
        logger.error(f"UCF file not found at: {ucf_path}")
        return {'success': False, 'error': f"UCF file not found at: {ucf_path}"}
    
    logger.info(f"Using UCF file: {ucf_path}")
    
    # Save the Verilog code to a file for debugging
    verilog_file_path = os.path.join(output_dir, "and_gate.v")
    with open(verilog_file_path, "w") as f:
        f.write(verilog_code)
    logger.info(f"Saved Verilog code to: {verilog_file_path}")
    
    # Run Cello
    logger.info("Running Cello to design the circuit...")
    results = cello.run_cello(verilog_code)
    
    if not results['success']:
        logger.error(f"Error running Cello: {results.get('error', 'Unknown error')}")
        return results
    
    output_path = results['results']['output_path']
    logger.info(f"Cello ran successfully. Output saved to: {output_path}")
    
    # Evaluate performance
    logger.info("Evaluating circuit performance...")
    metrics = cello.evaluate_circuit_performance(output_path)
    
    if not metrics['success']:
        logger.error(f"Error evaluating circuit performance: {metrics.get('error', 'Unknown error')}")
        return {'success': False, 'error': metrics.get('error', 'Unknown error')}
    
    # Log the key metrics
    logger.info(f"Performance metrics:")
    logger.info(f"  Overall score: {metrics.get('overall_score', 'N/A')}")
    
    for output, ratio in metrics.get('on_off_ratios', {}).items():
        logger.info(f"  ON/OFF ratio for {output}: {ratio}")
        logger.info(f"  Leakage for {output}: {metrics['leakage'].get(output, 'N/A')}%")
    
    logger.info(f"  Average ON/OFF ratio: {metrics.get('average_on_off_ratio', 'N/A')}")
    logger.info(f"  Average leakage: {metrics.get('average_leakage', 'N/A')}%")
    
    # Save the initial design details
    design_details = {
        'verilog_code': verilog_code,
        'library_id': library_id,
        'ucf_path': ucf_path,
        'output_path': output_path,
        'metrics': metrics
    }
    
    # Save results to a file
    results_path = os.path.join(output_dir, "initial_design_results.json")
    with open(results_path, 'w') as f:
        json.dump(design_details, f, indent=2)
    
    logger.info(f"Initial design results saved to: {results_path}")
    
    return {
        'success': True,
        'design_details': design_details,
        'message': "Initial circuit design completed successfully"
    }

def main():
    """Main entry point for the script."""
    result = design_initial_circuit()
    
    if result['success']:
        logger.info("Initial circuit design completed successfully!")
        
        # Print summary of key metrics
        metrics = result['design_details']['metrics']
        
        logger.info("\nCircuit Performance Summary:")
        logger.info(f"  Overall score: {metrics.get('overall_score', 'N/A')}")
        logger.info(f"  Average ON/OFF ratio: {metrics.get('average_on_off_ratio', 'N/A')}")
        logger.info(f"  Average leakage: {metrics.get('average_leakage', 'N/A')}%")
        
        # Print the path to the results
        output_path = result['design_details']['output_path']
        logger.info(f"\nCello output available at: {output_path}")
        logger.info("You can now examine the output files to see the circuit design details.")
        
        # Next steps suggestion
        logger.info("\nNext steps:")
        logger.info("1. Analyze the circuit diagram and response functions")
        logger.info("2. Identify promoters that need optimization")
        logger.info("3. Use the GPro tool to optimize selected promoters")
        logger.info("4. Create a modified UCF with optimized promoters")
        logger.info("5. Re-run Cello with the modified UCF")
    else:
        logger.error(f"Initial circuit design failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 