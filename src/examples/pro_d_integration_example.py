#!/usr/bin/env python3
"""
Example script demonstrating the use of the ProD integration.

This script shows how to:
1. Evaluate existing spacer sequences
2. Generate promoter libraries with specific strengths
3. Extract spacers from full promoter sequences
4. Compose full promoters from spacers
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the ProD integration
from src.tools.pro_d_integration import ProDIntegration, DEFAULT_MODEL_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("pro_d_example")

def print_section(title):
    """Print a section title with separators."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_json(data):
    """Print a dictionary as formatted JSON."""
    print(json.dumps(data, indent=2))

def main():
    """Main example function."""
    print_section("Initializing ProD Integration")
    
    # Check if model exists
    if not os.path.exists(DEFAULT_MODEL_PATH):
        print(f"WARNING: ProD model file not found at {DEFAULT_MODEL_PATH}")
        print("Make sure to place the model file at this location to run this example.")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(DEFAULT_MODEL_PATH), exist_ok=True)
        print(f"Created directory: {os.path.dirname(DEFAULT_MODEL_PATH)}")
        
        # Inform about required steps
        print("\nPlease acquire the ProD model file and place it at the path shown above.")
        print("The example will continue, but operations calling the ProD model will fail.")
    
    # Initialize the ProD integration
    prod = ProDIntegration(use_cuda=False, model_path=DEFAULT_MODEL_PATH)
    
    # Example 1: Evaluate specific spacer sequences
    print_section("Example 1: Evaluating Spacer Sequences")
    
    # Define some example spacer sequences (17bp each)
    spacers = [
        "ACTGACTAGCTAGCTAG",  # Example 1
        "TGCATGCAGTCAGTCAG",  # Example 2
        "ATATATATATATATAT",   # Example 3
    ]
    
    print(f"Evaluating {len(spacers)} spacer sequences:")
    for i, spacer in enumerate(spacers):
        print(f"  Spacer {i+1}: {spacer}")
    
    if os.path.exists(DEFAULT_MODEL_PATH):
        # Evaluate the spacers
        spacer_strengths = prod.evaluate_spacers(spacers)
        
        print("\nEvaluation results:")
        if spacer_strengths:
            for spacer, strength in spacer_strengths.items():
                print(f"  Spacer: {spacer} -> Strength: {strength:.2f}")
        else:
            print("  No valid results returned from ProD tool.")
    else:
        print("\nSkipping evaluation - model file not found.")
    
    # Example 2: Generate a promoter library with specific strengths
    print_section("Example 2: Generating Promoter Library")
    
    # Define a degenerate blueprint for library generation
    blueprint = "NNNCGGGNCCNGGGNNN"  # Degenerate spacer pattern
    desired_strengths = [7, 8, 9]     # Medium to high expression
    library_size = 3                  # Number of promoters per strength class
    
    print(f"Generating library from blueprint: {blueprint}")
    print(f"Desired strengths: {desired_strengths}")
    print(f"Library size per strength: {library_size}")
    
    if os.path.exists(DEFAULT_MODEL_PATH):
        # Generate the library
        library = prod.generate_library(
            blueprint=blueprint,
            desired_strengths=desired_strengths,
            library_size=library_size
        )
        
        print(f"\nGenerated {len(library)} promoter variants:")
        if library:
            # Display first 3 entries (or all if less than 3)
            for i, (spacer, data) in enumerate(list(library.items())[:3]):
                print(f"\nPromoter {i+1}:")
                print(f"  Spacer: {spacer}")
                print(f"  Strength: {data['strength']:.2f} (Class: {data['class']})")
                print(f"  Strength band: {data['strength_band']}")
                print(f"  Probability: {data['probability']:.2f}")
                print(f"  Full promoter length: {len(data['full_promoter'])} bp")
        else:
            print("  No valid results returned from ProD tool.")
    else:
        print("\nSkipping library generation - model file not found.")
    
    # Example 3: Extract spacer from existing promoter sequence
    print_section("Example 3: Extracting Spacer from Promoter")
    
    # Define an example full promoter sequence
    full_promoter = "GGTCTATGAGTGGTTGCTGGATAACTTGACAACTGGCTAGCTAGCTAGTATAATAGAGAGCACAACGGTTTCCCTCTACAAATAATTTTGTTTAACTTT"
    
    print(f"Full promoter sequence ({len(full_promoter)} bp):")
    print(f"  {full_promoter}")
    
    # Extract the spacer
    extracted_spacer = prod.extract_spacer(full_promoter)
    
    print("\nExtracted spacer:")
    if extracted_spacer:
        print(f"  {extracted_spacer} ({len(extracted_spacer)} bp)")
    else:
        print("  Could not identify a valid spacer in the promoter sequence.")
    
    # Example 4: Compose a full promoter from a spacer
    print_section("Example 4: Composing Full Promoter from Spacer")
    
    # Define an example spacer
    custom_spacer = "GCTGACTAGCTAGCTAG"
    
    print(f"Custom spacer: {custom_spacer}")
    
    # Compose the full promoter
    full_promoter = prod.get_full_promoter(custom_spacer)
    
    print(f"\nFull promoter ({len(full_promoter)} bp):")
    print(f"  {full_promoter}")
    
    # Extract regions to verify
    upstream_end = 30
    spacer_start = 31
    spacer_end = spacer_start + len(custom_spacer) - 1
    downstream_start = spacer_end + 1
    
    print("\nVerifying components:")
    print(f"  Upstream region: {full_promoter[:upstream_end]}")
    print(f"  Spacer region:   {full_promoter[spacer_start:spacer_end+1]}")
    print(f"  Downstream:      {full_promoter[downstream_start:]}")

if __name__ == "__main__":
    main() 