#!/usr/bin/env python3
"""
Promoter Optimization Workflow Example

This script demonstrates a complete workflow for optimizing a promoter in a genetic circuit:
1. Generate a custom UCF with a specific promoter using LLM
2. Extract the promoter from the generated UCF
3. Design a circuit using Cello
4. Evaluate the circuit performance
5. Optimize the promoter using the Promoter Calculator
6. Update the UCF with the optimized promoter
7. Re-run Cello to compare results
"""

import os
import sys
import json
import logging
import shutil
import uuid
from pathlib import Path
import time
import matplotlib.pyplot as plt

# Ensure the project root is in the Python path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

# Make sure the current working directory is the project root
os.chdir(project_root)

# Import required modules
from src.tools.cello_integration import CelloIntegration
from src.tools.promoter_calculator_integration import PromoterCalculatorIntegration
from src.library.library_manager import LibraryManager
from src.library.ucf_customizer import UCFCustomizer
from src.library.ucf_retrieval import get_dna_part_by_name, list_promoters
from src.llm_module import chat_with_tool

# For OpenAI client
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("promoter_optimization_workflow")

def print_section(title):
    """Print a formatted section title."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def print_json(data):
    """Print JSON data with nice formatting."""
    print(json.dumps(data, indent=2))

def create_output_dir(base_dir="outputs/promoter_optimization_example"):
    """Create a unique output directory for this run."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    run_id = str(uuid.uuid4())[:8]
    output_dir = os.path.join(project_root, base_dir, f"run_{timestamp}_{run_id}")
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")
    return output_dir

def generate_custom_ucf(client, promoter_name, output_dir):
    """
    Generate a custom UCF with a specific promoter.
    
    Args:
        client: OpenAI client
        promoter_name: Name of the promoter to find (e.g., 'pTet')
        output_dir: Directory to save the generated UCF
        
    Returns:
        Tuple of (path to the generated UCF file, promoter information)
    """
    print_section(f"Generating Custom UCF with Promoter: {promoter_name}")
    
    # Initialize the library manager and select the correct library
    library_manager = LibraryManager()
    library_manager.select_library("Eco1C1G1T1")
    
    # Get the raw UCF data
    ucf_data = library_manager.get_ucf_data()
    
    # Get the promoter data from the library
    all_promoters = []
    for item in ucf_data:
        if item.get("collection") == "parts" and item.get("type") == "promoter":
            all_promoters.append(item)
    
    # Find the requested promoter
    promoter_data = None
    for promoter in all_promoters:
        if promoter.get("name", "").lower() == promoter_name.lower():
            promoter_data = promoter
            break
    
    if not promoter_data:
        logger.warning(f"Promoter {promoter_name} not found in library, using first available promoter")
        if all_promoters:
            promoter_data = all_promoters[0]
        else:
            raise Exception("No promoters found in library")
    
    logger.info(f"Found promoter: {promoter_data.get('name', 'unknown')}")
    
    # Create a custom UCF with only this promoter
    custom_ucf_name = f"custom_Eco1C1G1T1_{promoter_name}.UCF.json"
    
    # Create the UCF customizer to extract parameters and create the custom UCF
    ucf_customizer = UCFCustomizer()
    
    # Get the promoter's parameters from its associated models
    promoter_params = ucf_customizer.get_promoter_parameters(ucf_data, promoter_data.get("name"))
    
    # Create the custom UCF - we pass only the selected promoter part
    ucf_path = library_manager.create_custom_ucf(
        selected_parts=[promoter_data],
        ucf_name=custom_ucf_name,
        output_dir=output_dir
    )
    
    if not ucf_path:
        logger.error("Failed to create custom UCF")
        raise Exception("Failed to create custom UCF")
    
    logger.info(f"Created custom UCF at: {ucf_path}")
    print(f"Custom UCF generated with promoter {promoter_name}")
    
    # Extract the promoter information using the parameters from the models
    promoter_info = {
        "name": promoter_data.get("name", "unknown"),
        "sequence": promoter_data.get("dnasequence", ""),
        "type": "promoter",
        "y_min": promoter_params.get("ymin", 0.01),
        "y_max": promoter_params.get("ymax", 2.8),
        "k": promoter_params.get("K", 0.0005),
        "raw_data": promoter_data
    }
    
    return ucf_path, promoter_info

def extract_promoter_from_ucf(ucf_path, promoter_name):
    """
    Extract the promoter from the UCF file.
    
    Args:
        ucf_path: Path to the UCF file
        promoter_name: Name of the promoter to extract
        
    Returns:
        Promoter information dictionary
    """
    print_section("Extracting Promoter from UCF")
    
    # Use the UCF customizer to load the UCF and access its data
    ucf_customizer = UCFCustomizer(ucf_path)
    
    # Get promoter data from the UCF
    promoter_data = None
    for collection in ucf_customizer.collections.values():
        for item in collection:
            if item.get("name") == promoter_name and item.get("type", "").lower() == "promoter":
                promoter_data = item
            break
    
    if not promoter_data:
        logger.warning(f"Promoter {promoter_name} not found in UCF, searching for any promoter")
        # Use the ucf_retrieval module to find promoters
        with open(ucf_path, 'r') as f:
            ucf_data = json.load(f)
        
        # First try to use library data structure if possible
        try:
            library_data = {"parts": []}
            for item in ucf_data:
                if item.get("collection") == "parts":
                    library_data["parts"].append({
                        "id": item.get("name", ""),
                        "type": item.get("type", ""),
                        "raw_data": item
                    })
            
            all_promoters = list_promoters(library_data)
            if all_promoters:
                promoter_data = all_promoters[0]["raw_data"]
                promoter_name = promoter_data.get("name", "unknown_promoter")
                logger.info(f"Using alternative promoter: {promoter_name}")
            else:
                raise Exception("No promoters found in UCF")
                
        except Exception as e:
            logger.error(f"Failed to extract promoters: {e}")
            raise Exception("Failed to extract promoter from UCF")
    
    # Extract the promoter information
    sequence = promoter_data.get("dnasequence", "")
    
    # Extract parameters (these may vary based on UCF structure)
    parameters = {}
    for param in promoter_data.get("parameters", []):
        param_name = param.get("name", "").lower()
        param_value = param.get("value", 0)
        parameters[param_name] = param_value
    
    # Construct promoter info dictionary
    promoter_info = {
        "name": promoter_name,
        "sequence": sequence,
        "type": "promoter",
        "y_min": parameters.get("ymin", 0.01),
        "y_max": parameters.get("ymax", 2.8),
        "k": parameters.get("k", 0.0005),
        "raw_data": promoter_data
    }
    
    logger.info(f"Extracted promoter {promoter_name}")
    logger.info(f"Sequence: {sequence[:50]}...")
    logger.info(f"Parameters: y_min={promoter_info['y_min']}, y_max={promoter_info['y_max']}, k={promoter_info['k']}")
    
    return promoter_info

def run_cello_design(verilog_code, ucf_path, output_dir):
    """Run Cello to design a circuit with the given UCF."""
    print_section("Running Cello Design")
    
    # Initialize CelloIntegration
    cello = CelloIntegration()
    
    # Set up Cello arguments
    cello_args = {
        'v_name': 'NOT_gate.v',
        'out_path': output_dir,
        'input_ucf': ucf_path
    }
    
    # Update Cello arguments
    cello.cello_args.update(cello_args)
    
    # Write the Verilog code to a temporary file
    verilog_path = os.path.join(output_dir, cello_args['v_name'])
    with open(verilog_path, 'w') as f:
        f.write(verilog_code)
    
    logger.info(f"Running Cello with UCF: {os.path.basename(ucf_path)}")
    logger.info(f"Verilog: {verilog_code}")
    
    # Run Cello
    try:
        result = cello.run_cello(verilog_code=verilog_code)
        
        if result["success"]:
            logger.info("Cello design successful")
            
            # Extract DNA design and metrics
            dna_design = result["results"]["dna_design"]
            output_path = result["results"]["output_path"]
            
            # Extract performance metrics
            metrics = cello.extract_circuit_metrics(output_path)
            
            design_result = {
                "success": True,
                "output_path": output_path,
                "dna_design": dna_design,
                "metrics": metrics
            }
            
            # Log key metrics
            logger.info(f"Circuit score: {metrics['overall_score']:.2f}")
            logger.info(f"ON/OFF ratios: {metrics['on_off_ratios']}")
            
            return design_result
        else:
            logger.error(f"Cello design failed: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "log": result.get("log", "")
            }
    except Exception as e:
        logger.exception(f"Error running Cello: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def optimize_promoter(promoter_info):
    """Optimize the promoter using the Promoter Calculator."""
    print_section("Optimizing Promoter")
    
    # Initialize the promoter calculator
    calculator = PromoterCalculatorIntegration()
    
    # Extract the promoter sequence and operator regions
    sequence = promoter_info["sequence"]
    operator_regions = promoter_info.get("operator_regions")
    
    logger.info(f"Optimizing promoter: {promoter_info['name']}")
    logger.info(f"Original sequence: {sequence}")
    logger.info(f"Operator regions: {operator_regions}")
    
    # First, run promoter calculator on the original sequence to get a baseline
    # and identify the promoter regions automatically
    initial_analysis = calculator.predict_promoter_strength(sequence)
    
    # Optimize the promoter sequence
    # We'll use the region-specific optimization if available, otherwise fall back to standard
    if hasattr(calculator, "optimize_promoter_regions"):
        # Use the more advanced region-specific optimization
        optimization_result = calculator.optimize_promoter_regions(
            sequence=sequence,
            target_strength=None,  # Maximize strength
            iterations=50,
            preserve_operators=True
        )
    else:
        # Fall back to the standard optimization
        optimization_result = calculator.optimize_promoter(
            sequence=sequence,
            target_strength=None,  # Maximize strength
            iterations=50,
            preserve_operators=True,
            operator_regions=operator_regions
        )
    
    # Extract the optimized sequence and strength
    optimized_sequence = optimization_result["optimized_sequence"]
    optimized_strength = optimization_result["optimized_strength"]
    
    # Convert the optimized strength to RPU
    # For this example, we'll use a simple linear mapping
    # In a real application, a more sophisticated mapping would be used
    reference_strength = optimization_result["original_strength"]
    reference_rpu = promoter_info["y_max"]
    optimized_rpu = calculator.calculator_to_rpu(
        calculator_value=optimized_strength,
        reference_value=reference_strength,
        reference_rpu=reference_rpu
    )
    
    logger.info(f"Optimization complete:")
    logger.info(f"  Original sequence: {sequence}")
    logger.info(f"  Optimized sequence: {optimized_sequence}")
    logger.info(f"  Original strength: {reference_strength:.2f}")
    logger.info(f"  Optimized strength: {optimized_strength:.2f}")
    logger.info(f"  Original RPU: {reference_rpu:.2f}")
    logger.info(f"  Optimized RPU: {optimized_rpu:.2f}")
    
    # Package the results
    optimized_promoter = promoter_info.copy()
    optimized_promoter["sequence"] = optimized_sequence
    optimized_promoter["y_max"] = optimized_rpu
    
    # Record the optimization result for visualization
    result = {
        "optimized_promoter": optimized_promoter,
        "optimization_result": optimization_result,
        "improvement_factor": optimized_strength / reference_strength,
        "improvement_percentage": ((optimized_strength / reference_strength) - 1) * 100
    }
    
    return result

def visualize_optimization_history(optimization_result, output_dir):
    """Visualize the optimization history."""
    print_section("Visualizing Optimization")
    
    history = optimization_result.get("history", [])
    if not history:
        logger.warning("No optimization history available")
        return
    
    # Extract iteration and strength data
    iterations = list(range(len(history)))
    strengths = [entry.get("strength", 0) for entry in history]
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(iterations, strengths, 'b-', linewidth=2)
    plt.scatter(iterations, strengths, color='blue', s=50)
    
    # Add title and labels
    plt.title('Promoter Optimization History', fontsize=16)
    plt.xlabel('Iteration', fontsize=14)
    plt.ylabel('Promoter Strength', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Highlight the best result
    best_iteration = strengths.index(max(strengths))
    plt.scatter([best_iteration], [strengths[best_iteration]], color='red', s=150, zorder=5, label='Optimal Strength')
    
    # Add legend
    plt.legend(fontsize=12)
    
    # Improve layout
    plt.tight_layout()
    
    # Save the plot
    plot_path = os.path.join(output_dir, 'optimization_history.png')
    plt.savefig(plot_path)
    logger.info(f"Saved optimization history plot to: {plot_path}")
    
    # Close the plot to free memory
    plt.close()

def update_ucf_with_optimized_promoter(original_ucf_path, promoter_info, output_dir):
    """Create an updated UCF with the optimized promoter."""
    print_section("Updating UCF with Optimized Promoter")
    
    # Load the original UCF
    ucf_customizer = UCFCustomizer(original_ucf_path)
    
    # Find and update the promoter
    promoter_name = promoter_info["name"]
    logger.info(f"Updating promoter {promoter_name} in UCF")
    
    # Update the promoter parameters
    ucf_customizer.update_part(
        part_name=promoter_name,
        sequence=promoter_info["sequence"],
        parameters={
            "ymin": promoter_info["y_min"],
            "ymax": promoter_info["y_max"],
            "K": promoter_info["k"]
        }
    )
    
    # Save the updated UCF
    updated_ucf_filename = f"updated_{os.path.basename(original_ucf_path)}"
    updated_ucf_path = os.path.join(output_dir, updated_ucf_filename)
    
    ucf_customizer.save_ucf(updated_ucf_path)
    logger.info(f"Saved updated UCF to: {updated_ucf_path}")
    
    return updated_ucf_path

def compare_results(original_metrics, updated_metrics):
    """Compare the performance of the original and updated designs."""
    print_section("Comparing Results")
    
    comparison = {
        "original": original_metrics,
        "updated": updated_metrics
    }
    
    # Calculate improvements
    if "overall_score" in original_metrics and "overall_score" in updated_metrics:
        score_improvement = updated_metrics["overall_score"] - original_metrics["overall_score"]
        score_improvement_percent = (score_improvement / original_metrics["overall_score"]) * 100
        
        comparison["score_improvement"] = score_improvement
        comparison["score_improvement_percent"] = score_improvement_percent
        
        logger.info(f"Score improvement: {score_improvement:.2f} ({score_improvement_percent:.2f}%)")
    
    # Compare ON/OFF ratios
    if "on_off_ratios" in original_metrics and "on_off_ratios" in updated_metrics:
        original_ratios = original_metrics["on_off_ratios"]
        updated_ratios = updated_metrics["on_off_ratios"]
        
        ratio_improvements = {}
        for output in original_ratios:
            if output in updated_ratios:
                ratio_improvement = updated_ratios[output] - original_ratios[output]
                ratio_improvement_percent = (ratio_improvement / original_ratios[output]) * 100
                
                ratio_improvements[output] = {
                    "original": original_ratios[output],
                    "updated": updated_ratios[output],
                    "improvement": ratio_improvement,
                    "improvement_percent": ratio_improvement_percent
                }
                
                logger.info(f"ON/OFF ratio improvement for {output}: {ratio_improvement:.2f} ({ratio_improvement_percent:.2f}%)")
        
        comparison["ratio_improvements"] = ratio_improvements
    
    return comparison

def generate_summary_report(results, output_dir):
    """Generate a summary report of the workflow results."""
    print_section("Summary Report")
    
    # Extract key results
    original_design = results.get("original_design", {})
    updated_design = results.get("updated_design", {})
    promoter_optimization = results.get("promoter_optimization", {})
    comparison = results.get("comparison", {})
    
    # Create a summary report
    summary = {
        "workflow_summary": {
        "promoter_optimization": {
                "original_promoter": promoter_optimization.get("optimized_promoter", {}).get("name"),
                "original_sequence": promoter_optimization.get("optimized_promoter", {}).get("sequence"),
                "original_strength": promoter_optimization.get("optimization_result", {}).get("original_strength"),
                "optimized_sequence": promoter_optimization.get("optimized_promoter", {}).get("sequence"),
                "optimized_strength": promoter_optimization.get("optimization_result", {}).get("optimized_strength"),
                "improvement_factor": promoter_optimization.get("improvement_factor"),
                "improvement_percentage": promoter_optimization.get("improvement_percentage")
            },
            "circuit_performance": {
                "original_score": original_design.get("metrics", {}).get("overall_score"),
                "updated_score": updated_design.get("metrics", {}).get("overall_score"),
                "score_improvement": comparison.get("score_improvement"),
                "score_improvement_percent": comparison.get("score_improvement_percent")
            }
        }
    }
    
    # Print the summary
    print("Workflow Summary:")
    print(f"  Original Promoter: {summary['workflow_summary']['promoter_optimization']['original_promoter']}")
    print(f"  Optimization Improvement: {summary['workflow_summary']['promoter_optimization']['improvement_percentage']:.2f}%")
    print(f"  Circuit Score Improvement: {summary['workflow_summary']['circuit_performance']['score_improvement_percent']:.2f}%")
    
    # Save the summary to a file
    summary_path = os.path.join(output_dir, "summary_report.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Saved summary report to: {summary_path}")
    
    return summary

def main():
    """Run the complete promoter optimization workflow."""
    print_section("PROMOTER OPTIMIZATION WORKFLOW")
    
    # Create output directory for this run
    output_dir = create_output_dir()
    
    # Define a simple NOT gate circuit in Verilog
    verilog_code = """
    module NOT_gate (
        input a,
        output out
    );
        assign out = ~a;
    endmodule
    """
    
    # Store results for each step
    workflow_results = {}
    
    # Initialize OpenAI client (if environment variable is not set, use a fallback)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.warning("OPENAI_API_KEY not found in environment. Using DEEPSEEK if available.")
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"), 
            base_url=os.getenv("DEEPSEEK_BASE_URL")
        )
    else:
        client = OpenAI(api_key=openai_api_key)
    

    # Step 1: Define the promoter we want to optimize
    promoter_name = "pBM3R1"
    
    # Step 2: Generate a custom UCF with our specified promoter using LLM
    # The LLM will find the promoter in the library and return both the UCF path and promoter info
    ucf_path, promoter_info = generate_custom_ucf(client, promoter_name, output_dir)
    
    # No need for a separate "extract promoter" step since we already have the info
    
    # Step 3: Run Cello to design the circuit with the original promoter
    original_design = run_cello_design(verilog_code, ucf_path, output_dir)
    workflow_results["original_design"] = original_design
    
    # Step 4: Optimize the promoter
    promoter_optimization = optimize_promoter(promoter_info)
    workflow_results["promoter_optimization"] = promoter_optimization
    
    # Visualize the optimization history
    visualize_optimization_history(
        promoter_optimization["optimization_result"], 
        output_dir
    )
    
    # Step 5: Update the UCF with the optimized promoter
    updated_ucf_path = update_ucf_with_optimized_promoter(
        ucf_path, 
        promoter_optimization["optimized_promoter"],
        output_dir
    )
    
    # Step 6: Run Cello again with the updated UCF
    updated_design = run_cello_design(
        verilog_code, 
        updated_ucf_path, 
        os.path.join(output_dir, "optimized_design")
    )
    workflow_results["updated_design"] = updated_design
    
    # Step 7: Compare the results
    comparison = compare_results(
        original_design["metrics"], 
        updated_design["metrics"]
    )
    workflow_results["comparison"] = comparison
    
    # Step 8: Generate a summary report
    summary = generate_summary_report(workflow_results, output_dir)
    
    print(f"\nWorkflow completed successfully. All outputs saved to: {output_dir}")
    print(f"To visualize the circuit designs, check the output directories within {output_dir}")


if __name__ == "__main__":
        main()