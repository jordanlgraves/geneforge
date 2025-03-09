import os
import logging
import subprocess
import tempfile
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Union, Any
from pathlib import Path
import sys

# Add ProD to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ext_repos/ProD'))
from ProD import run_tool

# Configure logging
logger = logging.getLogger(__name__)

# Default path to the ProD model
DEFAULT_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ext_repos/ProD/models/model_RPOD.pt'))

def extract_id_ecoli_spacer(sequence: str) -> Optional[str]:
    """
    Extract the spacer sequence from an E. coli promoter by identifying -35 and -10 boxes.
    Uses an advanced algorithm with position weight matrices and extended -10 considerations.
    
    Args:
        sequence: The full promoter sequence
        
    Returns:
        The extracted spacer sequence if found, otherwise None
    """
    # Convert to uppercase
    sequence = sequence.upper()
    
    # Define consensus sequences and score matrices
    minus35_consensus = "TTGACA"
    minus10_consensus = "TATAAT"
    extended_minus10 = "TG"
    
    # Position weight matrices (simplified version)
    # Values represent importance of match at each position
    minus35_weights = [1.5, 1.5, 2.0, 1.0, 1.0, 1.0]  # More weight on TTG
    minus10_weights = [1.5, 1.0, 1.5, 1.0, 1.0, 1.0]  # More weight on TAT
    
    def score_match(subseq, consensus, weights):
        """Score a subsequence against a consensus with position weights."""
        if len(subseq) != len(consensus):
            return 0
        score = 0
        for i in range(len(consensus)):
            if subseq[i] == consensus[i]:
                score += weights[i]
        return score / sum(weights)
    
    # Scan sequence for potential -35 and -10 regions
    candidates_35 = []
    candidates_10 = []
    ext10_candidates = []
    
    for i in range(len(sequence) - 5):
        # Score potential -35 regions
        subseq_35 = sequence[i:i+6]
        score_35 = score_match(subseq_35, minus35_consensus, minus35_weights)
        if score_35 > 0.4:  # Threshold to filter weak matches
            candidates_35.append((i, score_35))
        
        # Score potential -10 regions
        subseq_10 = sequence[i:i+6]
        score_10 = score_match(subseq_10, minus10_consensus, minus10_weights)
        if score_10 > 0.4:
            candidates_10.append((i, score_10))
        
        # Check for extended -10 motif
        if i < len(sequence) - 1:
            if sequence[i:i+2] == extended_minus10:
                ext10_candidates.append(i)
    
    # Find best promoter configuration
    best_score = 0
    best_config = None
    
    for pos35, score35 in candidates_35:
        for pos10, score10 in candidates_10:
            # -10 region must be downstream of -35
            if pos10 <= pos35 + 5:
                continue
                
            # Calculate spacer length
            spacer_length = pos10 - (pos35 + 6)
            
            # Check if spacer length is in acceptable range
            if 15 <= spacer_length <= 19:
                # Calculate spacer score (1.0 for 17bp, less for others)
                spacer_score = 1.0 - abs(spacer_length - 17) * 0.1
                
                # Check for extended -10 element
                ext10_bonus = 0
                for ext_pos in ext10_candidates:
                    if ext_pos == pos10 - 2:  # TG should be 2bp upstream of -10
                        ext10_bonus = 0.2
                        # Extended -10 can compensate for weaker -35
                        if score35 < 0.6:
                            score35 += 0.1
                        break
                
                # Calculate combined score
                combined_score = (score35 * 0.4 + score10 * 0.4) * spacer_score + ext10_bonus
                
                # Store best configuration
                if combined_score > best_score:
                    best_score = combined_score
                    spacer = sequence[pos35+6:pos10]
                    best_config = {
                        'spacer': spacer,
                        'minus35_pos': pos35,
                        'minus10_pos': pos10,
                        'score': combined_score
                    }
    
    # Log the result
    if best_config:
        logger.debug(f"Spacer extraction found: {best_config['spacer']} with score {best_config['score']:.2f}")
        return best_config['spacer']
    else:
        logger.warning("Spacer extraction found no promoter")
        return None

def evaluate_promoter_spacers(spacer_sequences: List[str], 
                             output_path: Optional[str] = None,
                             use_cuda: bool = False,
                             model_path: str = DEFAULT_MODEL_PATH) -> pd.DataFrame:
    """
    Evaluate the strength of given promoter spacer sequences using ProD.
    
    Args:
        spacer_sequences: List of 17bp spacer sequences to evaluate
        output_path: Path where to save the output CSV (optional)
        use_cuda: Whether to use CUDA acceleration if available
        model_path: Path to the ProD model file
        
    Returns:
        DataFrame with prediction results
    """
    if not spacer_sequences:
        raise ValueError("No spacer sequences provided")
    
    # Validate model path
    if not os.path.exists(model_path):
        logger.error(f"Model file not found at {model_path}")
        return pd.DataFrame()
    
    # Convert all sequences to uppercase
    spacer_sequences = [seq.upper() for seq in spacer_sequences]
    
    # Validate spacer length
    for i, seq in enumerate(spacer_sequences):
        if len(seq) != 17:
            logger.warning(f"Spacer sequence at index {i} has length {len(seq)}, expected 17bp")
    
    # Generate temporary output path if not provided
    if not output_path:
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            output_path = tmp.name
    
    # Run ProD tool
    try:
        logger.info(f"Evaluating {len(spacer_sequences)} spacer sequences with ProD")
        result = run_tool(
            spacer_sequences, 
            output_path=output_path,
            lib=False,
            cuda=use_cuda,
            model_path=model_path
        )
        
        if result is False:
            logger.error("ProD evaluation failed - no valid sequences found")
            return pd.DataFrame()
            
        return result
        
    except Exception as e:
        logger.error(f"Error evaluating promoter spacers: {str(e)}")
        return pd.DataFrame()

def generate_promoter_library(blueprint: str,
                            desired_strengths: List[int] = None,
                            library_size: int = 5,
                            output_path: Optional[str] = None,
                            use_cuda: bool = False,
                            model_path: str = DEFAULT_MODEL_PATH) -> pd.DataFrame:
    """
    Generate a library of promoter spacer sequences based on a degenerate blueprint.
    
    Args:
        blueprint: Degenerate sequence (e.g., "NNNCGGGNCCNGGGNNN") as a template
        desired_strengths: List of desired promoter strengths (0-10)
        library_size: Number of sequences to generate per strength class
        output_path: Path where to save the output CSV (optional)
        use_cuda: Whether to use CUDA acceleration if available
        model_path: Path to the ProD model file
        
    Returns:
        DataFrame with the generated library
    """
    if not blueprint:
        raise ValueError("No blueprint sequence provided")
    
    # Convert to uppercase
    blueprint = blueprint.upper()
    
    # Validate model path
    if not os.path.exists(model_path):
        logger.error(f"Model file not found at {model_path}")
        return pd.DataFrame()
    
    if len(blueprint) != 17:
        logger.warning(f"Blueprint sequence has length {len(blueprint)}, expected 17bp")
    
    # Set default strengths if not provided
    if desired_strengths is None or len(desired_strengths) == 0:
        desired_strengths = list(range(11))  # 0-10
    else:
        # Validate strength values
        for strength in desired_strengths:
            if strength < 0 or strength > 10:
                raise ValueError(f"Invalid strength value: {strength}. Must be between 0 and 10.")
    
    # Generate temporary output path if not provided
    if not output_path:
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            output_path = tmp.name
    
    # Run ProD tool
    try:
        logger.info(f"Generating promoter library from blueprint {blueprint}")
        result = run_tool(
            [blueprint], 
            output_path=output_path,
            lib=True,
            lib_size=library_size,
            strengths=desired_strengths,
            cuda=use_cuda,
            model_path=model_path
        )
        
        if result is False:
            logger.error("ProD library generation failed")
            return pd.DataFrame()
            
        return result
        
    except Exception as e:
        logger.error(f"Error generating promoter library: {str(e)}")
        return pd.DataFrame()

def compose_full_promoter(spacer: str, 
                        upstream_region: str = "GGTCTATGAGTGGTTGCTGGATAACTTTACG", 
                        downstream_region: str = "TATAATATATTCAGGGAGAGCACAACGGTTTCCCTCTACAAATAATTTTGTTTAACTTT") -> str:
    """
    Compose a full promoter by combining a spacer with the standard E. coli regions.
    
    Args:
        spacer: The 17bp spacer sequence
        upstream_region: The upstream region including the -35 box
        downstream_region: The downstream region including the -10 box and UTR
        
    Returns:
        The complete promoter sequence
    """
    # Convert to uppercase
    spacer = spacer.upper()
    upstream_region = upstream_region.upper()
    downstream_region = downstream_region.upper()
    
    if len(spacer) != 17:
        logger.warning(f"Spacer sequence has length {len(spacer)}, expected 17bp")
    
    return f"{upstream_region}{spacer}{downstream_region}"

def get_strength_band(strength: int) -> str:
    """
    Convert a numeric strength to a descriptive band.
    
    Args:
        strength: Numeric strength value (0-10)
        
    Returns:
        Descriptive strength band
    """
    if strength < 0 or strength > 10:
        raise ValueError(f"Invalid strength value: {strength}. Must be between 0 and 10.")
        
    if strength <= 2:
        return "zero_to_low"
    elif strength <= 5:
        return "low_to_medium"
    elif strength <= 8:
        return "medium_to_high"
    else:
        return "high_to_very_high"

class ProDIntegration:
    """
    Main class for integrating with the ProD tool.
    """
    
    def __init__(self, use_cuda: bool = False, model_path: str = DEFAULT_MODEL_PATH):
        """
        Initialize ProD integration.
        
        Args:
            use_cuda: Whether to use CUDA acceleration if available
            model_path: Path to the ProD model file
        """
        self.use_cuda = use_cuda
        self.model_path = model_path
        
        # Validate model path
        if not os.path.exists(self.model_path):
            logger.warning(f"Model file not found at {self.model_path}. ProD functions may fail.")
        else:
            logger.info(f"Initialized ProD integration with model at {self.model_path}")
    
    def evaluate_spacers(self, spacers: List[str], output_path: Optional[str] = None) -> Dict[str, float]:
        """
        Evaluate promoter spacer sequences and return a dictionary mapping each sequence to its strength.
        
        Args:
            spacers: List of spacer sequences to evaluate
            output_path: Path where to save the output CSV (optional)
            
        Returns:
            Dictionary mapping spacer sequences to their predicted strengths
        """
        # Convert all sequences to uppercase
        original_spacers = spacers.copy()  # Keep original case for dictionary keys
        spacers = [seq.upper() for seq in spacers]
        
        results = evaluate_promoter_spacers(
            spacers, 
            output_path, 
            self.use_cuda, 
            self.model_path
        )
        
        if results.empty:
            return {}
            
        # Convert results to dictionary, ensuring keys match input case
        spacer_to_strength = {}
        spacer_upper_to_original = {s.upper(): s for s in original_spacers}
        
        for _, row in results.iterrows():
            # Use the original case of the input spacer as the key
            original_spacer = spacer_upper_to_original.get(row['sequence'].upper(), row['sequence'])
            spacer_to_strength[original_spacer] = float(row['strength'])
            
        return spacer_to_strength
    
    def generate_library(self, 
                       blueprint: str,
                       desired_strengths: List[int] = None,
                       library_size: int = 5,
                       output_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Generate a library of promoter spacer sequences and return detailed information.
        
        Args:
            blueprint: Degenerate sequence as template
            desired_strengths: List of desired promoter strengths (0-10)
            library_size: Number of sequences to generate per strength class
            output_path: Path where to save the output CSV (optional)
            
        Returns:
            Dictionary mapping spacer sequences to their properties
        """
        # Convert to uppercase
        blueprint = blueprint.upper()
        
        results = generate_promoter_library(
            blueprint, 
            desired_strengths, 
            library_size, 
            output_path, 
            self.use_cuda,
            self.model_path
        )
        
        if results.empty:
            return {}
            
        # Convert results to dictionary with detailed information
        library_dict = {}
        for _, row in results.iterrows():
            spacer = row['sequence']
            strength = float(row['strength'])
            class_val = int(row['class'])
            prob = float(row['probability'])
            
            library_dict[spacer] = {
                'strength': strength,
                'class': class_val,
                'probability': prob,
                'strength_band': get_strength_band(class_val),
                'full_promoter': compose_full_promoter(spacer)
            }
            
        return library_dict
    
    def extract_spacer(self, promoter_seq: str) -> Optional[str]:
        """
        Extract the spacer from a full promoter sequence.
        
        Args:
            promoter_seq: Full promoter sequence
            
        Returns:
            Extracted spacer sequence if found, otherwise None
        """
        # Convert to uppercase
        promoter_seq = promoter_seq.upper()
        
        return extract_id_ecoli_spacer(promoter_seq)
    
    def get_full_promoter(self, spacer: str) -> str:
        """
        Get a full promoter sequence from a spacer.
        
        Args:
            spacer: The 17bp spacer sequence
            
        Returns:
            The complete promoter sequence
        """
        # Convert to uppercase
        spacer = spacer.upper()
        
        return compose_full_promoter(spacer)

