import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union

# Add GPro to system path
sys.path.append('ext_repos/GPro')

# Import GPro modules (these paths may need adjustment based on actual GPro structure)
from gpro.predictor.densenet.densenet import DenseNet_language
from gpro.optimizer.heuristic.genetic import GeneticAlgorithm
from gpro.generator.wgan.wgan import WGAN_language
from gpro.evaluator.kmer import plot_kmer_with_model

class PromoterOptimizer:
    """
    Integration with GPro toolkit for promoter optimization and generation.
    """
    def __init__(self, model_dir: str = "outputs/gpro_models"):
        """Initialize with model directory for saving/loading models."""
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Initialize models as None - they'll be loaded on demand
        self.predictor = None
        self.generator = None
        self.optimizer = None
    
    def _ensure_predictor_loaded(self):
        """Ensure promoter strength prediction model is loaded."""
        if self.predictor is None:
            # Try to load a saved model if available
            model_path = os.path.join(self.model_dir, "promoter_predictor.h5")
            if os.path.exists(model_path):
                self.predictor = DenseNet_language()
                self.predictor.load(model_path)
            else:
                # Initialize a new model - would need training before use
                self.predictor = DenseNet_language()
                print("Warning: Predictor model needs training before use")
    
    def _ensure_generator_loaded(self):
        """Ensure promoter generator model is loaded."""
        if self.generator is None:
            # Try to load a saved generator model
            model_path = os.path.join(self.model_dir, "promoter_generator.h5")
            if os.path.exists(model_path):
                self.generator = WGAN_language()
                self.generator.load(model_path)
            else:
                # Initialize a new model - would need training
                self.generator = WGAN_language()
                print("Warning: Generator model needs training before use")
    
    def predict_promoter_strength(self, sequence: str) -> float:
        """
        Predict the strength of a promoter sequence.
        
        Args:
            sequence: DNA sequence of the promoter
            
        Returns:
            Predicted strength value
        """
        self._ensure_predictor_loaded()
        
        # Format the sequence for the model
        # This might need adjustment based on GPro's specific requirements
        formatted_seq = sequence.upper()
        
        # Make prediction
        prediction = self.predictor.predict([formatted_seq])[0]
        
        return float(prediction)
    
    def optimize_promoter(self, 
                        seed_sequence: str, 
                        target_strength: float,
                        iterations: int = 100) -> Dict:
        """
        Optimize a promoter to reach a target strength.
        
        Args:
            seed_sequence: Starting sequence for optimization
            target_strength: Desired promoter strength
            iterations: Number of optimization iterations
            
        Returns:
            Dict with optimized sequence and predicted strength
        """
        self._ensure_predictor_loaded()
        
        # Initialize the genetic algorithm optimizer
        self.optimizer = GeneticAlgorithm(
            predictor=self.predictor,
            target=target_strength,
            seed_sequence=seed_sequence,
            population_size=100,
            mutation_rate=0.05
        )
        
        # Run optimization
        best_sequence, best_score = self.optimizer.optimize(iterations)
        
        return {
            "sequence": best_sequence,
            "predicted_strength": self.predict_promoter_strength(best_sequence),
            "target_strength": target_strength,
            "iterations": iterations
        }
    
    def generate_promoters(self, 
                         count: int = 10, 
                         min_strength: float = None,
                         max_strength: float = None) -> List[Dict]:
        """
        Generate novel promoter sequences with optional strength filtering.
        
        Args:
            count: Number of promoters to generate
            min_strength: Minimum acceptable strength (optional)
            max_strength: Maximum acceptable strength (optional)
            
        Returns:
            List of generated promoters with their predicted strengths
        """
        self._ensure_generator_loaded()
        self._ensure_predictor_loaded()
        
        # Generate sequences
        generated_seqs = self.generator.generate(count * 2)  # Generate extra to allow for filtering
        
        results = []
        for seq in generated_seqs:
            strength = self.predict_promoter_strength(seq)
            
            # Apply strength filters if specified
            if min_strength is not None and strength < min_strength:
                continue
            if max_strength is not None and strength > max_strength:
                continue
                
            results.append({
                "sequence": seq,
                "predicted_strength": strength
            })
            
            # Stop once we have enough sequences
            if len(results) >= count:
                break
                
        return results[:count]  # Ensure we return exactly the requested number
    
    def train_predictor(self, sequences: List[str], strengths: List[float], epochs: int = 100):
        """
        Train the promoter strength predictor on new data.
        
        Args:
            sequences: List of promoter sequences
            strengths: Corresponding strength measurements
            epochs: Number of training epochs
        """
        # Initialize a new predictor
        self.predictor = DenseNet_language()
        
        # Train the model
        self.predictor.train(sequences, strengths, epochs=epochs)
        
        # Save the trained model
        model_path = os.path.join(self.model_dir, "promoter_predictor.h5")
        self.predictor.save(model_path)
        
        return {"status": "success", "message": f"Model trained for {epochs} epochs and saved"}

class RepressorOptimizer:
    """
    Class for optimizing repressor-based genetic parts.
    This is a placeholder that would need implementation based on available tools.
    """
    def __init__(self):
        pass
    
    def optimize_binding_site(self, 
                             repressor_id: str, 
                             starting_site: str,
                             target_repression: float) -> Dict:
        """
        Optimize a repressor binding site for target repression level.
        
        Args:
            repressor_id: ID of the repressor protein
            starting_site: Starting binding site sequence
            target_repression: Desired repression level (0-1)
            
        Returns:
            Dict with optimized binding site and predicted repression
        """
        # This would need to be implemented with proper models
        # For now, return a placeholder
        return {
            "original_site": starting_site,
            "optimized_site": starting_site,  # No actual optimization yet
            "target_repression": target_repression,
            "predicted_repression": 0.5,  # Placeholder
            "message": "Repressor optimization not yet implemented"
        } 