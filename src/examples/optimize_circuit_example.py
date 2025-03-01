#!/usr/bin/env python3
"""
Design a genetic circuit in E. coli that implements a 2-input AND logic function.

The circuit should have two inputs: Input A (induced by arabinose) and Input B (induced by IPTG).
The output should be GFP expression, controlled by the pLac promoter in the final stage. Use the exact part name/ID for this promoter in the UCF to ensure it is recognized as "pLac" when you generate the verilog file and associated metadata.
Incorporate a library of gates and parts that support E. coli expression. For example, you can retrieve promoter, RBS, and terminator sequences from the standard Cello library or a custom library if available.
Generate the verilog design, the input file, the output file, and the UCF file so that Cello can produce an initial layout of the circuit.
After running Cello, read the performance metrics from the output (such as ON/OFF ratios, leakage, etc.).
Use GPro to optimize the sequence of the pLac promoter (and any other promoters if needed) to achieve a stronger ON/OFF ratio and minimal leakiness.
If the GPro-optimized promoter(s) differ from the standard pLac, incorporate the updated sequences back into a new UCF file.
Re-run Cello with the updated promoter(s).
Repeat this process until you find a design that improves the circuit's performance compared to the initial design.
Finally, return the updated verilog, the final UCF, and any relevant performance metrics or design files that illustrate how the circuit changed.
"""

import os
import sys
import logging
import json
from pathlib import Path

from src.tools.cello_integration import CelloIntegration
from src.tools.gpro_integration import PromoterOptimizer
from src.library.ucf_customizer import UCFCustomizer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CircuitOptimizer")

class CircuitOptimizer:
    """
    Manages the workflow of designing, evaluating, and optimizing genetic circuits.
    """
    
    def __init__(self, output_dir="outputs/circuit_optimization"):
        """Initialize the circuit optimizer."""
        self.cello = CelloIntegration()
        self.promoter_optimizer = PromoterOptimizer()
        self.ucf_customizer = UCFCustomizer()
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
        
        # Find appropriate UCF file
        ucf_result = self.cello.find_ucf_file(organism, inducers, gate_types)
        
        if 'error' in ucf_result:
            logger.error(f"Error finding UCF file: {ucf_result['error']}")
            return {'success': False, 'error': ucf_result['error']}
        
        # Use the first matching UCF file
        if 'matching_files' in ucf_result and ucf_result['matching_files']:
            ucf_path = ucf_result['matching_files'][0]['path']
            logger.info(f"Using UCF file: {os.path.basename(ucf_path)}")
        else:
            logger.error("No matching UCF files found")
            return {'success': False, 'error': "No matching UCF files found"}
        
        # Run Cello
        results = self.cello.run_cello(verilog_code, ucf_path)
        
        if not results['success']:
            logger.error(f"Error running Cello: {results.get('error', 'Unknown error')}")
            return results
        
        # Store the iteration data
        iteration_data = {
            'iteration': 0,
            'type': 'initial',
            'verilog_code': verilog_code,
            'ucf_path': ucf_path,
            'output_path': results['output_path'],
            'metrics': None  # Will be populated by evaluate_performance
        }
        
        # Evaluate performance
        metrics = self.evaluate_performance(results['output_path'])
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
        
        # Find parts with poor performance to optimize
        promoters_to_optimize = []
        
        # Extract all promoters from UCF
        all_promoters = self.ucf_customizer.extract_promoters(ucf_data)
        
        # Find pLac promoter (main target for optimization)
        plac_promoter = None
        for promoter in all_promoters:
            if 'name' in promoter and 'pLac' in promoter['name']:
                plac_promoter = promoter
                break
        
        if plac_promoter:
            promoters_to_optimize.append(plac_promoter)
            logger.info(f"Adding pLac promoter for optimization: {plac_promoter.get('name', 'unknown')}")
        
        # Add any other promoters with poor performance
        for part_id, standards in metrics.get('meets_performance_standards', {}).items():
            if not standards.get('on_off_ratio', True) or not standards.get('leakage', True):
                # Find promoters associated with this output
                for promoter in all_promoters:
                    if part_id in str(promoter):
                        promoters_to_optimize.append(promoter)
                        logger.info(f"Adding promoter for optimization due to poor performance: {promoter.get('name', 'unknown')}")
        
        if not promoters_to_optimize:
            logger.info("No promoters identified for optimization")
            return {'success': False, 'error': "No promoters identified for optimization"}
        
        # Optimize each promoter
        optimized_promoters = []
        
        for promoter in promoters_to_optimize:
            # Extract sequence for optimization
            sequence = promoter.get('sequence', '')
            
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
            
            # Run the optimization
            result = self.promoter_optimizer.optimize_promoter(
                sequence, 
                target_strength=target_strength,
                iterations=50
            )
            
            if result['success']:
                logger.info(f"Optimization successful for promoter: {promoter.get('name', 'unknown')}")
                logger.info(f"Optimized sequence: {result['optimized_sequence']}")
                logger.info(f"Predicted strength: {result['predicted_strength']}")
                
                # Save the optimized promoter
                optimized_promoter = promoter.copy()
                optimized_promoter['sequence'] = result['optimized_sequence']
                optimized_promoter['original_sequence'] = sequence
                optimized_promoter['predicted_strength'] = result['predicted_strength']
                
                optimized_promoters.append(optimized_promoter)
            else:
                logger.error(f"Optimization failed for promoter: {promoter.get('name', 'unknown')}")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
        
        if not optimized_promoters:
            logger.error("No promoters were successfully optimized")
            return {'success': False, 'error': "No promoters were successfully optimized"}
        
        # Create a new UCF with optimized promoters
        new_ucf_path = os.path.join(
            self.output_dir, 
            f"optimized_ucf_iter_{len(self.iterations)}.json"
        )
        
        # Customize the UCF with optimized promoters
        self.ucf_customizer.customize_ucf(
            input_ucf_path=ucf_path,
            output_ucf_path=new_ucf_path,
            modified_parts={p['name']: {'sequence': p['sequence']} for p in optimized_promoters if 'name' in p}
        )
        
        logger.info(f"Created new UCF with optimized promoters: {new_ucf_path}")
        
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
        results = self.cello.run_cello(verilog_code, ucf_path)
        
        if not results['success']:
            logger.error(f"Error running Cello: {results.get('error', 'Unknown error')}")
            return results
        
        # Store the iteration data
        iteration_data = {
            'iteration': len(self.iterations),
            'type': 'optimization',
            'verilog_code': verilog_code,
            'ucf_path': ucf_path,
            'output_path': results['output_path'],
            'metrics': None  # Will be populated by evaluate_performance
        }
        
        # Evaluate performance
        metrics = self.evaluate_performance(results['output_path'])
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
            'best_output_path': best_iteration['output_path']
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


def main():
    """Main entry point for the script."""
    # Create the Verilog code for a 2-input AND gate
    verilog_code = """
module main(input Wire a, input Wire b, output Wire out);
  and(out, a, b);
endmodule
    """
    
    # Initialize the circuit optimizer
    optimizer = CircuitOptimizer()
    
    # Run the optimization workflow
    result = optimizer.optimize_circuit(verilog_code)
    
    if result['success']:
        logger.info("Circuit optimization completed successfully!")
        
        # Print summary of improvements
        initial_metrics = result['summary']['initial_metrics']
        final_metrics = result['summary']['final_metrics']
        
        logger.info("Performance improvements:")
        
        # ON/OFF ratio improvement
        initial_ratio = initial_metrics.get('average_on_off_ratio', 0)
        final_ratio = final_metrics.get('average_on_off_ratio', 0)
        ratio_improvement = ((final_ratio - initial_ratio) / initial_ratio) * 100 if initial_ratio > 0 else 0
        
        logger.info(f"  ON/OFF ratio: {initial_ratio:.2f} → {final_ratio:.2f} ({ratio_improvement:+.2f}%)")
        
        # Leakage improvement
        initial_leakage = initial_metrics.get('average_leakage', 100)
        final_leakage = final_metrics.get('average_leakage', 100)
        leakage_improvement = ((initial_leakage - final_leakage) / initial_leakage) * 100 if initial_leakage > 0 else 0
        
        logger.info(f"  Leakage: {initial_leakage:.2f}% → {final_leakage:.2f}% ({leakage_improvement:+.2f}%)")
        
        # Overall score improvement
        initial_score = initial_metrics.get('overall_score', 0)
        final_score = final_metrics.get('overall_score', 0)
        score_improvement = ((final_score - initial_score) / initial_score) * 100 if initial_score > 0 else 0
        
        logger.info(f"  Overall score: {initial_score:.2f} → {final_score:.2f} ({score_improvement:+.2f}%)")
    else:
        logger.error(f"Circuit optimization failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()

