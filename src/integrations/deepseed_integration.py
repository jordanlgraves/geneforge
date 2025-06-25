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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deepseed_integration")

# Add DeepSEED to system path
sys.path.append('ext_repos/deepseed')

# Import DeepSEED modules - no fallback
from ext_repos.deepseed.Optimizer.optimizer_module import optimizer_fix_flank, one_hot, decode_oneHot
from ext_repos.deepseed.Optimizer.SeqRegressionModel import Seq2Scalar

from ext_repos.deepseed.Generator.cGAN_training import WGAN, Generator, Discriminator, ResBlock, EncoderLayer
import torch
torch.serialization.add_safe_globals([Generator, Discriminator, ResBlock, EncoderLayer])

GENERATOR_MODEL_PATH = os.getenv("DEEPSEED_GENERATOR_MODEL_PATH")
PREDICTOR_MODEL_PATH = os.getenv("DEEPSEED_PREDICTOR_MODEL_PATH")

class DeepSeedIntegration:
    """
    Integration with DeepSEED toolkit for promoter optimization and generation.
    DeepSEED uses a combined ML approach with GANs and a DenseNet-LSTM model for
    promoter sequence optimization.
    
    This class requires DeepSEED to be installed and properly configured.
    """
    def __init__(self, 
                cache_dir: str = "outputs/deepseed_cache",
                seqL: int = 165):
        """
        Initialize DeepSEED integration.
        
        Args:
            model_dir: Directory containing trained DeepSEED models
            cache_dir: Directory for temporary files and results
            seqL: Sequence length (default 165 for DeepSEED)
        """
        self.cache_dir = cache_dir
        self.seqL = seqL
        
        # Create necessary directories
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(os.path.join(self.cache_dir, "results"), exist_ok=True)
        
        # Default paths for DeepSEED models
        self.predictor_path = os.path.join(PREDICTOR_MODEL_PATH)
        self.generator_path = os.path.join(GENERATOR_MODEL_PATH)
        
        # Check if DeepSEED models are available - required
        if not self._check_models():
            raise FileNotFoundError(f"Required DeepSEED models not found at {self.predictor_path} and {self.generator_path}")
        
        # Initialize optimizer and predictor as None - will be loaded on demand
        self.generator = None
        self.optimizer = None
        self.predictor = None
        
        # Set flags for device
        self.is_gpu = torch.cuda.is_available()
        logger.info(f"GPU Available: {self.is_gpu}")
        
        # For storing sequence strings 
        self.seqs_string = []
        
        # Initialize logger
        self.logger = logger
    
    def _check_models(self) -> bool:
        """
        Check if DeepSEED models are available.
        
        Returns:
            True if models are available, False otherwise
        """
        predictor_available = os.path.exists(self.predictor_path)
        generator_available = os.path.exists(self.generator_path)
        
        if not predictor_available:
            logger.error(f"Predictor model not found at {self.predictor_path}")
        if not generator_available:
            logger.error(f"Generator model not found at {self.generator_path}")
        
        return predictor_available and generator_available
    
    def _ensure_optimizer_loaded(self):
        """
        Ensure the DeepSEED optimizer is loaded.
        Raises an exception if models aren't available.
        """
        if self.optimizer is None:
            # Initialize the DeepSEED optimizer
            self.optimizer = optimizer_fix_flank(
                predictor_path=self.predictor,
                generator_path=self.generator,
                is_gpu=self.is_gpu,
                seqL=self.seqL,
                gen_num=3,  # Number of generated sequences to return
                similarity_penalty=0.8,  # Penalty for similar sequences
                size_pop=320,  # Population size for optimization
                max_iter=50,  # Max iterations
                prob_mut=0.005  # Mutation probability
            )
            logger.info("DeepSEED optimizer loaded successfully")
    
    def _ensure_predictor_loaded(self):
        """
        Ensure the DeepSEED predictor is loaded.
        Raises an exception if model isn't available.
        """
        if self.predictor is None:
            # Load the predictor model
            if 'denselstm' in self.predictor_path:
                self.predictor = Seq2Scalar(input_nc=4, seqL=165, mode='denselstm')
            else:
                raise ValueError(f"Unsupported predictor model: {self.predictor_path}")
            self.predictor.load_state_dict(torch.load(self.predictor_path, weights_only=True, map_location=torch.device('cuda' if self.is_gpu else 'cpu')))
            if self.is_gpu:
                self.predictor = self.predictor.cuda()
            logger.info("DeepSEED predictor loaded successfully")

    def _ensure_generator_loaded(self):
        """
        Ensure the DeepSEED generator is loaded.
        Raises an exception if model isn't available.
        """
        if self.generator is None:
            # Initialize with the same seqL that was used during training
            gpu_ids = ['0'] if self.is_gpu else []
            WGAN(input_nc=4, output_nc=4, seqL=self.seqL, l1_w=50, gpu_ids=gpu_ids)
            # Pass the seqL parameter explicitly to match the trained model
            self.generator = Generator(input_nc=4, output_nc=4, seqL=self.seqL)
            self.generator.load_state_dict(torch.load(self.generator_path, map_location=torch.device('cuda' if self.is_gpu else 'cpu')))
            if self.is_gpu:
                self.generator = self.generator.cuda()
            logger.info("DeepSEED generator loaded successfully")


    def predict_promoter_strength(self, sequence: str) -> float:
        """
        Predict the strength of a promoter sequence using DeepSEED.
        
        Args:
            sequence: DNA sequence of the promoter
            
        Returns:
            Predicted strength value (between 0 and 1)
        """
        # Ensure predictor is loaded
        self._ensure_predictor_loaded()
        
        # Format the sequence for the model
        formatted_seq = sequence.upper()
        
        # Pad or truncate to expected length
        if len(formatted_seq) < self.seqL:
            formatted_seq = formatted_seq + "A" * (self.seqL - len(formatted_seq))
        elif len(formatted_seq) > self.seqL:
            formatted_seq = formatted_seq[:self.seqL]
        
        # Create one-hot encoding
        seq_tensor = torch.tensor(one_hot(formatted_seq)).float().unsqueeze(0)
        
        if self.is_gpu:
            seq_tensor = seq_tensor.cuda()
        
        # Get prediction
        with torch.no_grad():
            prediction = self.predictor(seq_tensor)
            # Convert from log2 scale used by DeepSEED
            strength = 2 ** prediction.item()
            
            # Normalize to 0-1 range (DeepSEED typically outputs values around 2-16)
            normalized_strength = min(1.0, max(0.0, strength / 16.0))
            
        logger.info(f"Predicted strength: {normalized_strength:.4f}")
        return float(normalized_strength)

    def _prepare_input_file(self, seed_sequence: str, fixed_regions: List[Tuple[int, int]] = None) -> str:
        """
        Prepare input file for DeepSEED optimizer.
        
        Args:
            seed_sequence: Starting sequence for optimization
            fixed_regions: List of (start, end) tuples for regions to keep fixed
            
        Returns:
            Path to the created input file
        """
        # Create a file for input
        input_file = os.path.join(self.cache_dir, "input_promoters.txt")
        
        # DeepSEED expects sequences with an 'M' character to mark regions that can be changed
        # Convert the entire sequence to DeepSEED compatible format with fixed regions preserved
        
        # Start with all regions marked as modifiable
        modified_seq = list("M" * len(seed_sequence))
        
        # Mark fixed regions with their original bases
        if fixed_regions:
            for start, end in fixed_regions:
                for i in range(start, min(end, len(seed_sequence))):
                    modified_seq[i] = seed_sequence[i]
        
        modified_seq = "".join(modified_seq)
        
        # Write to input file
        with open(input_file, "w") as f:
            f.write(">seq1\n")  # Header for the sequence
            f.write(f"{modified_seq}\n")  # Modified sequence with M markers
            f.write(f"{seed_sequence}\n")  # Original sequence
        
        logger.info(f"Created input file at {input_file}")
        return input_file
    
    def optimize_promoter(self, 
                        seed_sequence: str, 
                        target_strength: float,
                        iterations: int = 50,
                        fixed_regions: List[Tuple[int, int]] = None) -> Dict:
        """
        Optimize a promoter sequence using DeepSEED.
        
        Args:
            seed_sequence: Starting sequence for optimization
            target_strength: Desired promoter strength (0-1)
            iterations: Number of optimization iterations
            fixed_regions: List of tuples (start, end) for regions to keep fixed
            
        Returns:
            Dict with optimized sequence and predicted strength
        """
        start_time = time.time()
        
        # Calculate original strength for comparison
        original_strength = self.predict_promoter_strength(seed_sequence)
        logger.info(f"Original sequence strength: {original_strength:.4f}")
        logger.info(f"Target strength: {target_strength:.4f}")

        # Optimize using DeepSEED
        return self._optimize_with_deepseed(seed_sequence, target_strength, iterations, fixed_regions)
    
    def _optimize_with_deepseed(self, 
                              seed_sequence: str, 
                              target_strength: float,
                              iterations: int,
                              fixed_regions: List[Tuple[int, int]] = None) -> Dict:
        """
        Optimize a promoter sequence using the DeepSEED optimizer.
        
        Args:
            seed_sequence: Starting sequence for optimization
            target_strength: Desired promoter strength (0-1)
            iterations: Number of optimization iterations  
            fixed_regions: List of tuples (start, end) for regions to keep fixed
            
        Returns:
            Dict with optimization results
        """
        # Ensure optimizer is loaded
        self._ensure_optimizer_loaded()
        
        # Calculate original strength
        original_strength = self.predict_promoter_strength(seed_sequence)
        
        # Prepare modified sequence with fixed regions preserved
        modified_seq = list("M" * len(seed_sequence))
        
        # Mark fixed regions
        if fixed_regions:
            for start, end in fixed_regions:
                for i in range(start, min(end, len(seed_sequence))):
                    modified_seq[i] = seed_sequence[i]
        else:
            # Default fixed regions: approximate -35 and -10 regions
            for i in range(15, min(21, len(seed_sequence))):
                modified_seq[i] = seed_sequence[i]
            for i in range(30, min(36, len(seed_sequence))):
                modified_seq[i] = seed_sequence[i]
        
        modified_seq = "".join(modified_seq)
        
        # Format sequences for DeepSEED
        polish_seqs = [modified_seq]
        control_seqs = [seed_sequence]
        
        # Store sequence for reference - needed for results lookup
        self.seqs_string = ["seq1"]
        
        # Set input sequences
        self.optimizer.set_input(polish_seqs, control_seqs)
        
        # Run optimization - use higher population size and iterations for better results
        logger.info("Starting DeepSEED optimization")
        self.optimizer.size_pop = 320  # Population size
        self.optimizer.max_iter = iterations  # Use the specified number of iterations
        self.optimizer.optimization()
        
        # Get results
        if hasattr(self.optimizer, 'seq_results') and self.seqs_string[0] in self.optimizer.seq_results:
            optimized_sequence = self.optimizer.seq_results[self.seqs_string[0]][0]
            optimized_strength = self.predict_promoter_strength(optimized_sequence)
            
            logger.info(f"Optimization complete: {optimized_sequence}")
            logger.info(f"Optimized sequence strength: {optimized_strength:.4f}")
            
            return {
                'success': True,
                'original_sequence': seed_sequence,
                'optimized_sequence': optimized_sequence,
                'original_strength': original_strength,
                'predicted_strength': optimized_strength,
                'target_strength': target_strength,
                'iterations': iterations
            }
        else:
            logger.error("No results returned from DeepSEED optimization")
            raise RuntimeError("DeepSEED optimization failed to produce results")

    def generate_promoters(self, count: int, min_strength: float = None, max_strength: float = None) -> List[Dict]:
        """
        Generate new promoter sequences using DeepSEED.
        
        Args:
            count: Number of promoters to generate
            min_strength: Minimum acceptable strength (optional)
            max_strength: Maximum acceptable strength (optional)
            
        Returns:
            List of dicts containing generated sequences and predicted strengths
        """
        logger.info(f"Generating {count} promoters")
        
        # Ensure the generator model is loaded
        self._ensure_optimizer_loaded()
        
        # Storage for results
        results = []
        attempts = 0
        max_attempts = count * 3
        
        # Use DeepSEED's generator to create sequences
        while len(results) < count and attempts < max_attempts:
            attempts += 1
            
            # Generate random parameters for the generator
            params = torch.randn(1, 4*self.seqL)
            if self.is_gpu:
                params = params.cuda()
            
            # Generate sequence with the optimizer's generator model
            with torch.no_grad():
                seq_onehot = self.optimizer.generator(params)
                # Convert one-hot to sequence
                sequence = decode_oneHot(seq_onehot[0].cpu().numpy())
            
            # Predict strength
            strength = self.predict_promoter_strength(sequence)
            
            # Apply strength filters if specified
            if min_strength is not None and strength < min_strength:
                continue
            if max_strength is not None and strength > max_strength:
                continue
                
            results.append({
                "sequence": sequence,
                "predicted_strength": strength
            })
        
        if len(results) < count:
            logger.warning(f"Only generated {len(results)} of {count} requested promoters after {attempts} attempts")
        else:
            logger.info(f"Generated {len(results)} promoters")
        
        return results 