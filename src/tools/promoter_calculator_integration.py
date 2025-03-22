import os
import sys
import logging
import tempfile
import shutil
import subprocess
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple, Union, Any
import time
import random
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("promoter_calculator_integration")

PROMOTER_CALCULATOR_PATH = os.getenv("PROMOTER_CALCULATOR_PATH")
# add promoter calculator to system/python path
sys.path.append(PROMOTER_CALCULATOR_PATH)

from promoter_calculator import Promoter_Calculator, PromoCalcResults


class PromoterCalculatorIntegration:
    def __init__(self):
        self.organism = "Escherichia coli str. K-12 substr. MG1655"
        self.calculator = Promoter_Calculator(organism=self.organism)

    def predict_promoter_strength(self, 
                                  sequence: str, 
                                  organism: str = None) -> float:
        """
        Run the promoter calculator on a sequence.
        
        Args:
            sequence: DNA sequence of the promoter
            organism: organism to use for the calculation
        Returns:
            Prediction result from the promoter calculator
        """
        # Format the sequence for the model
        formatted_seq = sequence.upper()
        
        if organism:
            calculator = Promoter_Calculator(organism=organism)
        else:
            calculator = self.calculator
            
        calculator.run(formatted_seq)
        result = calculator.output()
        return result
    
    def optimize_promoter(self, 
                          sequence: str, 
                          target_strength: float = None, 
                          iterations: int = 50,
                          preserve_operators: bool = True,
                          operator_regions: List[Tuple[int, int]] = None) -> Dict[str, Any]:
        """
        Optimize a promoter sequence to achieve a target strength or maximize strength.
        
        Args:
            sequence: Original promoter sequence
            target_strength: Target promoter strength (if None, will maximize strength)
            iterations: Number of optimization iterations to perform
            preserve_operators: Whether to preserve operator sites (repressor binding sites)
            operator_regions: List of (start, end) tuples defining operator regions to preserve
                             If None and preserve_operators=True, will use default regions
                             
        Returns:
            Dict containing optimized sequence, strength, and optimization history
        """
        logger.info(f"Starting promoter optimization with {iterations} iterations")
        
        # Default operator regions (example positions - should be adjusted based on actual promoter)
        # Typically, operators are upstream of the -35 box or between -35 and -10
        if operator_regions is None and preserve_operators:
            # These are example regions that should be adjusted for real promoters
            operator_regions = [(0, 20)]  # Example: first 20bp might be an operator
            logger.warning("Using default operator regions. For accurate results, provide actual operator positions.")
        
        # Ensure sequence is uppercase
        sequence = sequence.upper()
        best_sequence = sequence
        
        # Get initial strength
        initial_strength = self.predict_promoter_strength(sequence)
        best_strength = initial_strength
        
        if target_strength is None:
            # If no target, aim to maximize strength
            target_strength = float('inf')
            optimization_goal = "maximize"
        else:
            optimization_goal = "target"
        
        logger.info(f"Initial promoter strength: {initial_strength}")
        logger.info(f"Optimization goal: {optimization_goal} " + 
                   (f"(target: {target_strength})" if optimization_goal == "target" else "(maximize)"))
        
        # Define the RNAP binding regions (these are typical locations in E. coli promoters)
        # -35 box: typically around positions 40-45 in a 100bp promoter
        # -10 box: typically around positions 65-70 in a 100bp promoter
        # UP element: upstream of -35 box
        # We'll create a mask of positions that can be modified
        sequence_length = len(sequence)
        modifiable = [True] * sequence_length
        
        # Mask out operator regions to preserve them
        if preserve_operators and operator_regions:
            for start, end in operator_regions:
                for i in range(max(0, start), min(end, sequence_length)):
                    modifiable[i] = False
            
            modifiable_count = sum(modifiable)
            logger.info(f"Preserving {sequence_length - modifiable_count} bp in operator regions")
            logger.info(f"Modifiable positions: {modifiable_count} bp")
        
        # Track optimization history
        history = []
        
        # Run optimization iterations
        for i in range(iterations):
            # Create a mutated sequence
            mutated_sequence = list(best_sequence)
            
            # Decide how many positions to mutate (1-3 positions)
            num_mutations = min(random.randint(1, 3), sum(modifiable))
            
            # Choose random positions to mutate (only from modifiable positions)
            modifiable_positions = [j for j in range(sequence_length) if modifiable[j]]
            positions_to_mutate = random.sample(modifiable_positions, num_mutations)
            
            # Apply mutations
            for pos in positions_to_mutate:
                current_base = mutated_sequence[pos]
                # Choose a different base
                new_base = random.choice([b for b in "ACGT" if b != current_base])
                mutated_sequence[pos] = new_base
            
            mutated_sequence = ''.join(mutated_sequence)
            
            # Evaluate the mutated sequence
            mutated_strength = self.predict_promoter_strength(mutated_sequence)
            
            # Determine if this is better based on our goal
            if optimization_goal == "maximize":
                is_better = mutated_strength > best_strength
            else:
                # For target optimization, closer to target is better
                current_distance = abs(best_strength - target_strength)
                new_distance = abs(mutated_strength - target_strength)
                is_better = new_distance < current_distance
            
            # Update best if improved
            if is_better:
                best_sequence = mutated_sequence
                best_strength = mutated_strength
                logger.info(f"Iteration {i+1}: Improved strength to {best_strength:.2f}")
            
            # Record history
            history.append({
                "iteration": i+1,
                "sequence": mutated_sequence,
                "strength": mutated_strength,
                "is_better": is_better
            })
        
        # Calculate improvement
        improvement = best_strength - initial_strength
        improvement_percent = (improvement / initial_strength) * 100 if initial_strength > 0 else float('inf')
        
        logger.info(f"Optimization complete:")
        logger.info(f"  Initial strength: {initial_strength:.2f}")
        logger.info(f"  Final strength: {best_strength:.2f}")
        logger.info(f"  Improvement: {improvement:.2f} ({improvement_percent:.1f}%)")
        
        return {
            "original_sequence": sequence,
            "original_strength": initial_strength,
            "optimized_sequence": best_sequence,
            "optimized_strength": best_strength,
            "improvement": improvement,
            "improvement_percent": improvement_percent,
            "iterations": iterations,
            "history": history
        }
    
    def optimize_promoter_regions(self, 
                              sequence: str, 
                              target_strength: float = None, 
                              iterations: int = 50,
                              preserve_operators: bool = True) -> Dict[str, Any]:
        """
        Optimize a promoter sequence by intelligently targeting RNAP binding regions.
        
        This method uses the promoter calculator to identify the different regions
        of the promoter (UP element, -35 box, spacer, -10 box, etc.) and only
        mutates regions responsible for RNAP binding while preserving operator sites.
        
        Args:
            sequence: Original promoter sequence
            target_strength: Target promoter strength (if None, will maximize strength)
            iterations: Number of optimization iterations to perform
            preserve_operators: Whether to preserve operator sites (repressor binding sites)
            
        Returns:
            Dict containing optimized sequence, strength, and optimization history
        """
        logger.info(f"Starting promoter region-specific optimization with {iterations} iterations")
        
        # First, analyze the promoter to identify its regions
        initial_analysis = self.predict_promoter_strength(sequence)
        
        # Get the strongest promoter prediction (highest Tx_rate)
        best_prediction = None
        best_tx_rate = 0
        
        # Check forward predictions
        for tss, prediction in initial_analysis['Forward_Predictions_per_TSS'].items():
            if prediction['Tx_rate'] > best_tx_rate:
                best_prediction = prediction
                best_tx_rate = prediction['Tx_rate']
        
        # Check reverse predictions
        for tss, prediction in initial_analysis['Reverse_Predictions_per_TSS'].items():
            if prediction['Tx_rate'] > best_tx_rate:
                best_prediction = prediction
                best_tx_rate = prediction['Tx_rate']
        
        if not best_prediction:
            logger.warning("No promoter regions identified in the sequence. Using standard optimization.")
            return self.optimize_promoter(sequence, target_strength, iterations)
        
        # Extract regions from the prediction
        promoter_regions = {
            'UP': (best_prediction['UP_position'][0], best_prediction['UP_position'][1]),
            'hex35': (best_prediction['hex35_position'][0], best_prediction['hex35_position'][1]), 
            'spacer': (best_prediction['spacer_position'][0], best_prediction['spacer_position'][1]),
            'hex10': (best_prediction['hex10_position'][0], best_prediction['hex10_position'][1]),
            'disc': (best_prediction['disc_position'][0], best_prediction['disc_position'][1])
        }
        
        logger.info(f"Identified promoter regions: {promoter_regions}")
        
        # Define which regions to modify (RNAP binding regions) and which to preserve (operator regions)
        # For E. coli, operators often overlap with or are near -35 and/or -10 boxes
        # We'll focus on modifying the spacer and disc regions which are less likely to contain operators
        modifiable_regions = []
        
        if preserve_operators:
            # More conservative approach: only modify spacer and discriminator regions
            modifiable_regions = [
                promoter_regions['spacer'],
                promoter_regions['disc']
            ]
            logger.info("Conservative optimization: only modifying spacer and discriminator regions")
        else:
            # Less conservative: modify all RNAP binding regions
            modifiable_regions = [
                promoter_regions['UP'],
                promoter_regions['hex35'],
                promoter_regions['spacer'],
                promoter_regions['hex10'],
                promoter_regions['disc']
            ]
            logger.info("Aggressive optimization: modifying all promoter regions")
        
        # Create a mask for modifiable positions
        sequence_length = len(sequence)
        modifiable = [False] * sequence_length
        
        # Set modifiable positions based on the identified regions
        for start, end in modifiable_regions:
            for i in range(max(0, start), min(end, sequence_length)):
                modifiable[i] = True
        
        modifiable_count = sum(modifiable)
        logger.info(f"Identified {modifiable_count} modifiable positions")
        
        # Now run the optimization with the intelligent mask
        # Reuse most of the logic from the original optimize_promoter method
        best_sequence = sequence
        
        # Get initial strength
        initial_strength = best_tx_rate  # Use the Tx_rate from our analysis
        best_strength = initial_strength
        
        if target_strength is None:
            # If no target, aim to maximize strength
            target_strength = float('inf')
            optimization_goal = "maximize"
        else:
            optimization_goal = "target"
        
        logger.info(f"Initial promoter strength: {initial_strength}")
        logger.info(f"Optimization goal: {optimization_goal} " + 
                   (f"(target: {target_strength})" if optimization_goal == "target" else "(maximize)"))
        
        # Track optimization history
        history = []
        
        # Run optimization iterations
        for i in range(iterations):
            # Create a mutated sequence
            mutated_sequence = list(best_sequence)
            
            # Decide how many positions to mutate (1-3 positions)
            num_mutations = min(random.randint(1, 3), modifiable_count)
            
            # Choose random positions to mutate (only from modifiable positions)
            modifiable_positions = [j for j in range(sequence_length) if modifiable[j]]
            positions_to_mutate = random.sample(modifiable_positions, num_mutations)
            
            # Apply mutations
            for pos in positions_to_mutate:
                current_base = mutated_sequence[pos]
                # Choose a different base
                new_base = random.choice([b for b in "ACGT" if b != current_base])
                mutated_sequence[pos] = new_base
            
            mutated_sequence = ''.join(mutated_sequence)
            
            # Evaluate the mutated sequence
            mutation_analysis = self.predict_promoter_strength(mutated_sequence)
            
            # Find the best promoter prediction in the mutated sequence
            mutated_strength = 0
            for tss, prediction in mutation_analysis['Forward_Predictions_per_TSS'].items():
                if prediction['Tx_rate'] > mutated_strength:
                    mutated_strength = prediction['Tx_rate']
            
            for tss, prediction in mutation_analysis['Reverse_Predictions_per_TSS'].items():
                if prediction['Tx_rate'] > mutated_strength:
                    mutated_strength = prediction['Tx_rate']
            
            # Determine if this is better based on our goal
            if optimization_goal == "maximize":
                is_better = mutated_strength > best_strength
            else:
                # For target optimization, closer to target is better
                current_distance = abs(best_strength - target_strength)
                new_distance = abs(mutated_strength - target_strength)
                is_better = new_distance < current_distance
            
            # Update best if improved
            if is_better:
                best_sequence = mutated_sequence
                best_strength = mutated_strength
                logger.info(f"Iteration {i+1}: Improved strength to {best_strength:.2f}")
            
            # Record history
            history.append({
                "iteration": i+1,
                "sequence": mutated_sequence,
                "strength": mutated_strength,
                "is_better": is_better
            })
        
        # Calculate improvement
        improvement = best_strength - initial_strength
        improvement_percent = (improvement / initial_strength) * 100 if initial_strength > 0 else float('inf')
        
        logger.info(f"Optimization complete:")
        logger.info(f"  Initial strength: {initial_strength:.2f}")
        logger.info(f"  Final strength: {best_strength:.2f}")
        logger.info(f"  Improvement: {improvement:.2f} ({improvement_percent:.1f}%)")
        
        return {
            "original_sequence": sequence,
            "original_strength": initial_strength,
            "optimized_sequence": best_sequence,
            "optimized_strength": best_strength,
            "improvement": improvement,
            "improvement_percent": improvement_percent,
            "iterations": iterations,
            "history": history,
            "promoter_regions": promoter_regions,
            "modifiable_regions": modifiable_regions
        }
    
    def calculator_to_rpu(self, calculator_value: float, reference_value: float = 1.0, 
                        reference_rpu: float = 1.0) -> float:
        """
        Convert a promoter calculator value to Relative Promoter Units (RPU).
        
        Args:
            calculator_value: The value from the promoter calculator
            reference_value: A reference value from the calculator for a known promoter
            reference_rpu: The RPU value corresponding to the reference promoter
            
        Returns:
            The calculated RPU value
        """
        # Simple linear mapping
        # This assumes a linear relationship between calculator values and RPU
        if reference_value == 0:
            logger.warning("Reference value is zero, setting to small value to avoid division by zero")
            reference_value = 1e-6
            
        rpu = (calculator_value / reference_value) * reference_rpu
        return rpu
    