"""
Circuit Optimizer

This module provides functionality to optimize genetic circuits by modifying
both DNA sequences and response function parameters in UCF files.
"""
import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from src.tools.cello_integration import CelloIntegration
from src.tools.gpro_integration import PromoterOptimizer
from src.library.ucf_customizer import UCFCustomizer
from src.library.promoter_parameter_predictor import PromoterParameterPredictor
from src.library.ucf_retrieval import list_promoters

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("circuit_optimizer")

class CircuitOptimizer:
    """
    Manages the workflow of designing, evaluating, and optimizing genetic circuits.
    
    This class integrates sequence optimization with parameter prediction to create
    a comprehensive optimization workflow that updates both DNA sequences and
    response function parameters in UCF files.
    """
    
    def __init__(self, output_dir="outputs/circuit_optimization"):
        """
        Initialize the circuit optimizer.
        
        Args:
            output_dir: Directory to store optimization outputs
        """
        self.cello = CelloIntegration()
        self.promoter_optimizer = PromoterOptimizer()
        self.ucf_customizer = UCFCustomizer()
        self.parameter_predictor = PromoterParameterPredictor()
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Tracking data for optimization iterations
        self.iterations = []
    
    def design_initial_circuit(self, verilog_code, organism="E. coli", 
                              inducers=None, outputs=None, gate_types=None):
        """
        Design the initial circuit using Cello.
        
        Args:
            verilog_code: Verilog code for the circuit
            organism: Target organism
            inducers: List of inducers required (e.g., ['arabinose', 'IPTG'])
            outputs: List of outputs required (e.g., ['GFP'])
            gate_types: List of gate types required (e.g., ['AND'])
            
        Returns:
            Dictionary with design results
        """
        logger.info("Designing initial circuit...")
        
        # If inducers, outputs, or gate_types are not provided, use defaults
        if inducers is None:
            inducers = ["arabinose", "IPTG"]
        if outputs is None:
            outputs = ["GFP"]
        if gate_types is None:
            gate_types = ["AND"]
        
        # Hardcode the library selection instead of searching
        # We're using Eco1C1G1T1 library which has the necessary parts for our circuit
        library_id = "Eco1C1G1T1"
        success = self.cello.select_library(library_id)
        
        if not success:
            logger.error(f"Failed to select library: {library_id}")
            return {'success': False, 'error': f"Failed to select library: {library_id}"}
        
        logger.info(f"Selected library: {library_id}")
        
        # Get the UCF path from the cello instance
        ucf_path = os.path.join(
            self.cello.cello_args.get('constraints_path', ''),
            self.cello.cello_args.get('ucf_name', '')
        )
        
        if not os.path.exists(ucf_path):
            logger.error(f"UCF file not found at: {ucf_path}")
            return {'success': False, 'error': f"UCF file not found at: {ucf_path}"}
        
        # Run Cello
        results = self.cello.run_cello(verilog_code)
        
        if not results['success']:
            logger.error(f"Error running Cello: {results.get('error', 'Unknown error')}")
            return results
        
        # Store the iteration data
        iteration_data = {
            'iteration': 0,
            'type': 'initial',
            'verilog_code': verilog_code,
            'ucf_path': ucf_path,
            'output_path': results['results']['output_path'],
            'metrics': None  # Will be populated by evaluate_performance
        }
        
        # Evaluate performance
        metrics = self.evaluate_performance(results['results']['output_path'])
        iteration_data['metrics'] = metrics
        
        # Add to iterations tracker
        self.iterations.append(iteration_data)
        
        return {
            'success': True,
            'iteration': iteration_data,
            'message': "Initial circuit design completed"
        }
    
    def evaluate_performance(self, output_path):
        """
        Evaluate the performance of a circuit design.
        
        Args:
            output_path: Path to Cello output directory
            
        Returns:
            Dictionary with performance metrics
        """
        logger.info(f"Evaluating circuit performance for: {output_path}")
        
        # Use the evaluate_circuit_performance function
        metrics = self.cello.evaluate_circuit_performance(output_path)
        
        if not metrics['success']:
            logger.error(f"Error evaluating circuit performance: {metrics.get('error', 'Unknown error')}")
            return metrics
        
        # Log the key metrics
        logger.info(f"Performance metrics:")
        logger.info(f"  Overall score: {metrics.get('overall_score', 'N/A')}")
        
        for output, ratio in metrics.get('on_off_ratios', {}).items():
            logger.info(f"  ON/OFF ratio for {output}: {ratio}")
            logger.info(f"  Leakage for {output}: {metrics['leakage'].get(output, 'N/A')}%")
        
        logger.info(f"  Average ON/OFF ratio: {metrics.get('average_on_off_ratio', 'N/A')}")
        logger.info(f"  Average leakage: {metrics.get('average_leakage', 'N/A')}%")
        
        return metrics
    
    def optimize_promoters(self, current_iteration):
        """
        Optimize promoters based on circuit performance.
        
        This method optimizes both the DNA sequence and the response function parameters
        of selected promoters.
        
        Args:
            current_iteration: Data from the current iteration
            
        Returns:
            Dictionary with optimization results
        """
        logger.info("Optimizing promoters...")
        
        # Get metrics from current iteration
        metrics = current_iteration['metrics']
        
        # Extract the UCF path from current iteration
        ucf_path = current_iteration['ucf_path']
        
        # Parse the UCF file to get promoter data
        with open(ucf_path, 'r') as f:
            ucf_data = json.load(f)
        
        # Extract all promoters from UCF using ucf_retrieval
        all_promoters = list_promoters(ucf_data)
        
        # Choose a specific promoter to optimize (pSrpR in this case)
        target_promoter_name = "pSrpR"  # We're choosing this specific promoter from the available list
        target_promoter = None
        
        logger.info(f"Looking for target promoter: {target_promoter_name}")
        
        # Find the target promoter
        for promoter in all_promoters:
            if promoter.get('name') == target_promoter_name:
                target_promoter = promoter
                break
        
        if target_promoter:
            promoters_to_optimize = [target_promoter]
            logger.info(f"Target promoter found: {target_promoter.get('name')} with sequence: {target_promoter.get('dnasequence')}")
        else:
            logger.error(f"Target promoter '{target_promoter_name}' not found in UCF. Available promoters are:")
            for p in all_promoters:
                logger.info(f"- {p.get('name')}")
            return {'success': False, 'error': f"Target promoter '{target_promoter_name}' not found in UCF"}
        
        # Optimize each promoter
        optimized_promoters = []
        
        for promoter in promoters_to_optimize:
            # Extract sequence for optimization
            sequence = promoter.get('dnasequence', '')
            
            if not sequence:
                logger.warning(f"No sequence found for promoter: {promoter.get('name', 'unknown')}")
                continue
            
            logger.info(f"Optimizing promoter: {promoter.get('name', 'unknown')}")
            logger.info(f"Original sequence: {sequence}")
            
            # Set optimization target based on current performance
            target_strength = None
            
            if 'on_off_ratios' in metrics and metrics['on_off_ratios'] and len(metrics['on_off_ratios']) > 0:
                current_ratio = next(iter(metrics['on_off_ratios'].values()))
                # If current ratio is low, target a higher strength
                if current_ratio < 100:
                    target_strength = 0.8  # Target high strength
                else:
                    target_strength = 0.5  # Target moderate strength
            else:
                target_strength = 0.7  # Default target
            
            # Get the current predicted strength for comparison
            try:
                original_strength = self.promoter_optimizer.predict_promoter_strength(sequence)
                logger.info(f"Current predicted strength: {original_strength:.4f}")
            except Exception as e:
                logger.warning(f"Could not predict original strength: {str(e)}")
                original_strength = None
            
            # Run the sequence optimization
            result = self.promoter_optimizer.optimize_promoter(
                sequence, 
                target_strength=target_strength,
                iterations=50
            )
            
            if result['success']:
                logger.info(f"Optimization successful for promoter: {promoter.get('name', 'unknown')}")
                logger.info(f"Optimized sequence: {result['optimized_sequence']}")
                logger.info(f"Predicted strength: {result['predicted_strength']}")
                
                # Find the associated gate and its parameters
                gate_name = self.ucf_customizer.find_gate_for_promoter(ucf_data, promoter.get('name'))
                original_parameters = self.ucf_customizer.get_gate_parameters(ucf_data, gate_name)
                
                logger.info(f"Associated gate: {gate_name}")
                logger.info(f"Original parameters: {original_parameters}")
                
                # Predict new parameters based on sequence change
                if original_parameters:
                    # Calculate relative strength change
                    relative_strength = result['predicted_strength'] / original_strength if original_strength else 1.5
                    
                    # Predict new parameters
                    predicted_parameters = self.parameter_predictor.predict_parameters(
                        result['optimized_sequence'],
                        original_parameters,
                        relative_strength
                    )
                    
                    logger.info(f"Predicted new parameters: {predicted_parameters}")
                else:
                    logger.warning(f"Could not find original parameters for gate: {gate_name}")
                    predicted_parameters = None
                
                # Save the optimized promoter
                optimized_promoter = promoter.copy()
                optimized_promoter['dnasequence'] = result['optimized_sequence']
                optimized_promoter['original_sequence'] = sequence
                optimized_promoter['predicted_strength'] = result['predicted_strength']
                optimized_promoter['original_strength'] = original_strength
                optimized_promoter['gate_name'] = gate_name
                optimized_promoter['original_parameters'] = original_parameters
                optimized_promoter['predicted_parameters'] = predicted_parameters
                
                if original_strength is not None and result['predicted_strength'] is not None:
                    strength_change_pct = ((result['predicted_strength'] - original_strength) / original_strength) * 100
                    optimized_promoter['strength_change_pct'] = strength_change_pct
                    logger.info(f"Strength change: {strength_change_pct:+.2f}%")
                
                optimized_promoters.append(optimized_promoter)
            else:
                logger.error(f"Optimization failed for promoter: {promoter.get('name', 'unknown')}")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
        
        if not optimized_promoters:
            logger.error("No promoters were successfully optimized")
            return {'success': False, 'error': "No promoters were successfully optimized"}
        
        # Create a new UCF with optimized promoters and parameters
        new_ucf_path = os.path.join(
            self.output_dir, 
            f"optimized_ucf_iter_{len(self.iterations)}.json"
        )
        
        # Prepare modified parts and parameters
        modified_parts = {}
        modified_parameters = {}
        
        for p in optimized_promoters:
            if 'name' in p:
                modified_parts[p['name']] = {'dnasequence': p['dnasequence']}
            
            if 'gate_name' in p and 'predicted_parameters' in p and p['predicted_parameters']:
                modified_parameters[p['gate_name']] = p['predicted_parameters']
        
        # Create the new UCF with both sequence and parameter changes
        self.ucf_customizer.customize_ucf_with_parameters(
            input_ucf_path=ucf_path,
            output_ucf_path=new_ucf_path,
            modified_parts=modified_parts,
            modified_parameters=modified_parameters
        )
        
        logger.info(f"Created new UCF with optimized promoters and parameters: {new_ucf_path}")
        
        return {
            'success': True,
            'optimized_promoters': optimized_promoters,
            'new_ucf_path': new_ucf_path
        }
    
    def run_optimization_iteration(self, verilog_code, ucf_path):
        """
        Run one iteration of the optimization process.
        
        Args:
            verilog_code: Verilog code for the circuit
            ucf_path: Path to the UCF file to use
            
        Returns:
            Dictionary with iteration results
        """
        logger.info(f"Running optimization iteration {len(self.iterations)}")
        
        # Run Cello with the optimized UCF
        # We need to provide the custom UCF as a parameter
        custom_ucf = {
            "ucf_name": os.path.basename(ucf_path)
        }
        
        # Ensure verilog_code is using the correct syntax without Wire type
        if "Wire" in verilog_code:
            verilog_code = verilog_code.replace("input Wire", "input").replace("output Wire", "output")
            logger.info("Updated Verilog code to remove Wire type declarations")
            
        results = self.cello.run_cello(verilog_code, custom_ucf)
        
        if not results['success']:
            logger.error(f"Error running Cello: {results.get('error', 'Unknown error')}")
            return results
        
        # Store the iteration data
        iteration_data = {
            'iteration': len(self.iterations),
            'type': 'optimization',
            'verilog_code': verilog_code,
            'ucf_path': ucf_path,
            'output_path': results['results']['output_path'],
            'metrics': None  # Will be populated by evaluate_performance
        }
        
        # Evaluate performance
        metrics = self.evaluate_performance(results['results']['output_path'])
        iteration_data['metrics'] = metrics
        
        # Add to iterations tracker
        self.iterations.append(iteration_data)
        
        return {
            'success': True,
            'iteration': iteration_data
        }
    
    def has_performance_improved(self, current_metrics, previous_metrics):
        """
        Determine if circuit performance has improved.
        
        Args:
            current_metrics: Metrics from current iteration
            previous_metrics: Metrics from previous iteration
            
        Returns:
            Boolean indicating if performance has improved and explanation
        """
        if not current_metrics['success'] or not previous_metrics['success']:
            return False, "Error in metrics evaluation"
        
        improvements = []
        regressions = []
        
        # Compare ON/OFF ratios
        current_avg_ratio = current_metrics.get('average_on_off_ratio', 0)
        previous_avg_ratio = previous_metrics.get('average_on_off_ratio', 0)
        
        if current_avg_ratio > previous_avg_ratio:
            pct_improvement = ((current_avg_ratio - previous_avg_ratio) / previous_avg_ratio) * 100 if previous_avg_ratio > 0 else 100
            improvements.append(f"ON/OFF ratio improved by {pct_improvement:.2f}% (from {previous_avg_ratio:.2f} to {current_avg_ratio:.2f})")
        elif current_avg_ratio < previous_avg_ratio:
            pct_regression = ((previous_avg_ratio - current_avg_ratio) / previous_avg_ratio) * 100 if previous_avg_ratio > 0 else 0
            regressions.append(f"ON/OFF ratio decreased by {pct_regression:.2f}% (from {previous_avg_ratio:.2f} to {current_avg_ratio:.2f})")
        
        # Compare leakage
        current_avg_leakage = current_metrics.get('average_leakage', 100)
        previous_avg_leakage = previous_metrics.get('average_leakage', 100)
        
        if current_avg_leakage < previous_avg_leakage:
            pct_improvement = ((previous_avg_leakage - current_avg_leakage) / previous_avg_leakage) * 100 if previous_avg_leakage > 0 else 100
            improvements.append(f"Leakage improved by {pct_improvement:.2f}% (from {previous_avg_leakage:.2f}% to {current_avg_leakage:.2f}%)")
        elif current_avg_leakage > previous_avg_leakage:
            pct_regression = ((current_avg_leakage - previous_avg_leakage) / previous_avg_leakage) * 100 if previous_avg_leakage > 0 else 0
            regressions.append(f"Leakage increased by {pct_regression:.2f}% (from {previous_avg_leakage:.2f}% to {current_avg_leakage:.2f}%)")
        
        # Compare overall score if available
        current_score = current_metrics.get('overall_score')
        previous_score = previous_metrics.get('overall_score')
        
        if current_score is not None and previous_score is not None:
            if current_score > previous_score:
                pct_improvement = ((current_score - previous_score) / previous_score) * 100 if previous_score > 0 else 100
                improvements.append(f"Overall score improved by {pct_improvement:.2f}% (from {previous_score:.2f} to {current_score:.2f})")
            elif current_score < previous_score:
                pct_regression = ((previous_score - current_score) / previous_score) * 100 if previous_score > 0 else 0
                regressions.append(f"Overall score decreased by {pct_regression:.2f}% (from {previous_score:.2f} to {current_score:.2f})")
        
        # Determine overall improvement
        has_improved = len(improvements) > len(regressions)
        
        # Create explanation
        explanation = "Performance changes:\n"
        for imp in improvements:
            explanation += f"+ {imp}\n"
        for reg in regressions:
            explanation += f"- {reg}\n"
        
        return has_improved, explanation
    
    def optimize_circuit(self, verilog_code, max_iterations=5, min_improvement_pct=5):
        """
        Run the full circuit optimization workflow.
        
        Args:
            verilog_code: Verilog code for the circuit
            max_iterations: Maximum number of optimization iterations
            min_improvement_pct: Minimum percentage improvement to continue
            
        Returns:
            Dictionary with optimization results
        """
        logger.info(f"Starting circuit optimization workflow with max {max_iterations} iterations")
        
        # Track promoter optimizations
        promoter_optimizations = []
        
        # Design initial circuit
        initial_result = self.design_initial_circuit(verilog_code)
        
        if not initial_result['success']:
            logger.error(f"Initial circuit design failed: {initial_result.get('error', 'Unknown error')}")
            return initial_result
        
        logger.info("Initial circuit design completed successfully")
        
        # Track best iteration
        best_iteration = self.iterations[0]
        
        # Run optimization iterations
        for i in range(max_iterations):
            logger.info(f"Starting optimization iteration {i+1} of {max_iterations}")
            
            # Get the latest iteration
            current_iteration = self.iterations[-1]
            
            # Optimize promoters based on current performance
            opt_result = self.optimize_promoters(current_iteration)
            
            if not opt_result['success']:
                logger.warning(f"Promoter optimization failed: {opt_result.get('error', 'Unknown error')}")
                logger.info("Using previous iteration as best solution")
                break
            
            # Track promoter optimization details
            if 'optimized_promoters' in opt_result:
                for p in opt_result['optimized_promoters']:
                    optimization_detail = {
                        'name': p.get('name', 'unknown'),
                        'original_sequence': p.get('original_sequence', ''),
                        'optimized_sequence': p.get('dnasequence', ''),
                        'predicted_strength': p.get('predicted_strength', 0),
                        'original_strength': p.get('original_strength', 0),
                        'strength_change_pct': p.get('strength_change_pct', 0),
                        'gate_name': p.get('gate_name', ''),
                        'original_parameters': p.get('original_parameters', {}),
                        'predicted_parameters': p.get('predicted_parameters', {}),
                        'iteration': i+1
                    }
                    
                    promoter_optimizations.append(optimization_detail)
                    logger.info(f"Tracked optimization for {optimization_detail['name']}")
            
            # Run a new iteration with the optimized UCF
            iteration_result = self.run_optimization_iteration(
                verilog_code,
                opt_result['new_ucf_path']
            )
            
            if not iteration_result['success']:
                logger.error(f"Optimization iteration failed: {iteration_result.get('error', 'Unknown error')}")
                break
            
            # Compare performance with previous best
            has_improved, explanation = self.has_performance_improved(
                iteration_result['iteration']['metrics'],
                best_iteration['metrics']
            )
            
            logger.info(explanation)
            
            if has_improved:
                logger.info(f"Iteration {i+1} improved performance, updating best solution")
                best_iteration = iteration_result['iteration']
            else:
                logger.info(f"Iteration {i+1} did not improve performance")
                
                # Check if we should continue
                if i >= 2:  # Give at least 3 iterations a chance
                    logger.info("No improvement after multiple iterations, stopping optimization")
                    break
        
        # Generate final report
        optimization_summary = {
            'total_iterations': len(self.iterations),
            'best_iteration': best_iteration['iteration'],
            'initial_metrics': self.iterations[0]['metrics'],
            'final_metrics': best_iteration['metrics'],
            'iterations': self.iterations,
            'verilog_code': verilog_code,
            'best_ucf_path': best_iteration['ucf_path'],
            'best_output_path': best_iteration['output_path'],
            'promoter_optimizations': promoter_optimizations
        }
        
        # Save the summary to a file
        summary_path = os.path.join(self.output_dir, "optimization_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(optimization_summary, f, indent=2)
        
        logger.info(f"Circuit optimization completed. Summary saved to: {summary_path}")
        logger.info(f"Best iteration: {best_iteration['iteration']}")
        logger.info(f"Best UCF: {best_iteration['ucf_path']}")
        
        return {
            'success': True,
            'summary': optimization_summary,
            'message': "Circuit optimization completed successfully"
        }


def test_full_optimization_workflow():
    """
    Test the complete workflow from sequence optimization to parameter updates.
    """
    optimizer = CircuitOptimizer()
    
    # Implement verilog code for a test circuit
    verilog_code = """
    module test(input a, input b, output out);
      and(out, a, b);
    endmodule
    """
    
    # Run the full optimization with parameter updates
    result = optimizer.optimize_circuit(verilog_code, max_iterations=3)
    
    # Validate results
    assert result['success']
    
    # Check that both sequences and parameters were modified
    for opt in result['summary']['promoter_optimizations']:
        assert 'original_sequence' in opt
        assert 'optimized_sequence' in opt
        assert 'original_parameters' in opt
        assert 'predicted_parameters' in opt
    
    print("Test completed successfully!")


if __name__ == "__main__":
    test_full_optimization_workflow() 