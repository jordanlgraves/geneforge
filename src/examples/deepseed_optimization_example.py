#!/usr/bin/env python3
"""
Example script demonstrating the use of DeepSEED for promoter optimization.

This script demonstrates how to integrate DeepSEED into the genetic circuit design
workflow, including:
1. Setting up the DeepSEED integration
2. Optimizing individual promoters to target strengths
3. Optimizing all promoters in a UCF file based on circuit performance

Prerequisites:
- DeepSEED must be installed in ext_repos/deepseed
- DeepSEED models must be trained and available in outputs/deepseed_models

Usage:
    python deepseed_optimization_example.py --input-dir INPUT_DIR --output-dir OUTPUT_DIR --circuit CIRCUIT_NAME

Example:
    python deepseed_optimization_example.py --input-dir designs/not_gate --output-dir outputs --circuit not_gate
"""

import os
import sys
import argparse
import logging
import time
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(project_root)

# Import DeepSEED integration classes
from src.tools.deepseed_integration import DeepSeedIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("deepseed_example")

def setup_argparse():
    """Set up command-line arguments."""
    parser = argparse.ArgumentParser(description='DeepSEED Promoter Optimization Example')
    parser.add_argument('--input-dir', type=str, 
                        help='Input directory containing UCF files',
                        default="ext_repos/Cello-UCF/files/v2/ucf/Eco/Eco1C1G1T1.UCF.json")
    parser.add_argument('--output-dir', type=str, 
                        help='Output directory for results',
                        default="outputs/deepseed_optimization_example")
    parser.add_argument('--circuit', type=str, 
                        help='Name of the circuit to optimize',
                        default="Eco1C1G1T1")
    parser.add_argument('--model-dir', type=str, default='outputs/deepseed_models',
                        help='Directory containing DeepSEED models')
    return parser.parse_args()

def example_1_optimize_single_promoter():
    """
    Demonstrate optimizing a single promoter sequence using DeepSEED.
    """
    logger.info("Example 1: Optimizing a single promoter")
    
    # Initialize DeepSEED integration
    deepseed = DeepSeedIntegration(
        cache_dir="outputs/deepseed_cache"
    )
    
    # Example promoter sequence (E. coli-like)
    seed_sequence = "TTGACATTTTATGCTTCCGGCTCGTATAATGTGTGGAATTGTGAGCGGATAACAATTTCACACAGGAAACAGCT"
    target_strength = 0.75  # Target strength (0-1 scale)
    
    # Fixed regions to preserve (approximate -35 and -10 boxes)
    fixed_regions = [(6, 12), (30, 36)]
    
    logger.info(f"Original sequence: {seed_sequence}")
    logger.info(f"Target strength: {target_strength}")
    
    # Predict original strength
    original_strength = deepseed.predict_promoter_strength(seed_sequence)
    logger.info(f"Original predicted strength: {original_strength:.4f}")
    
    # Optimize the promoter
    start_time = time.time()
    result = deepseed.optimize_promoter(
        seed_sequence=seed_sequence,
        target_strength=target_strength,
        iterations=30,  # Reduced for demonstration
        fixed_regions=fixed_regions
    )
    elapsed_time = time.time() - start_time
    
    # Display results
    logger.info(f"Optimization completed in {elapsed_time:.2f} seconds")
    logger.info(f"Optimized sequence: {result['optimized_sequence']}")
    logger.info(f"Achieved strength: {result['predicted_strength']:.4f}")
    
    # Show differences
    logger.info("Sequence differences:")
    for i, (orig, optim) in enumerate(zip(seed_sequence, result['optimized_sequence'])):
        if orig != optim:
            logger.info(f"Position {i}: {orig} -> {optim}")
    
    return result

def example_2_circuit_optimization(args):
    """
    Demonstrate optimizing all promoters in a circuit UCF file.
    
    Args:
        args: Command-line arguments
    """
    logger.info("Example 2: Circuit-level promoter optimization")
    
    # Ensure input and output directories exist
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Find UCF file
    ucf_files = list(input_dir.glob("*.UCF.json"))
    if not ucf_files:
        logger.error(f"No UCF files found in {input_dir}")
        return
    
    ucf_path = ucf_files[0]
    logger.info(f"Using UCF file: {ucf_path}")
    
    # Initialize the circuit optimizer
    circuit_optimizer = DeepSeedCircuitOptimizer(
        input_directory=str(input_dir),
        output_directory=str(output_dir),
        circuit_name=args.circuit,
    )
    
    # Run the optimization
    start_time = time.time()
    optimized_ucf_path, optimization_results = circuit_optimizer.optimize_promoters(
        ucf_path=str(ucf_path),
        iterations=2  # Small number for demonstration
    )
    elapsed_time = time.time() - start_time
    
    # Display results
    logger.info(f"Circuit optimization completed in {elapsed_time:.2f} seconds")
    logger.info(f"Optimized UCF saved to: {optimized_ucf_path}")
    logger.info(f"Number of promoters optimized: {len(optimization_results)}")
    
    # Display some optimization details
    for promoter_name, result in optimization_results.items():
        logger.info(f"Promoter: {promoter_name}")
        logger.info(f"  Original strength: {result['original_strength']:.4f}")
        logger.info(f"  Target strength: {result['target_strength']:.4f}")
        logger.info(f"  Achieved strength: {result['achieved_strength']:.4f}")
        logger.info(f"  Sequence length: {len(result['optimized_sequence'])}")
    
    return optimization_results

def main():
    """Main function to run examples."""
    args = setup_argparse()
    
    try:
        # Run example 1 - single promoter optimization
        example_1_result = example_1_optimize_single_promoter()
        
        # Run example 2 - circuit optimization
        example_2_result = example_2_circuit_optimization(args)
        
        logger.info("All examples completed successfully!")
        
    except FileNotFoundError as e:
        logger.error(f"DeepSEED models not found: {e}")
        logger.error("Please ensure DeepSEED is installed and models are trained.")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Error during optimization: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 