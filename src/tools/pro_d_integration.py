import os
import logging
import subprocess
import tempfile
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Union, Any
from pathlib import Path
import sys
import traceback

# Configure logging
logger = logging.getLogger(__name__)
import dotenv
dotenv.load_dotenv()
PRO_D_ROOT = os.getenv("PRO_D_ROOT")
# add to PYTHONPATH
sys.path.append(PRO_D_ROOT)

# Default path to the ProD model
DEFAULT_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ext_repos/ProD/models/model_RPOD.pt'))

# ---------------------------------------------------------------------------
#  CLASS → RPU DEFAULT MAP  (rough, log-uniform; can be re-calibrated)
# ---------------------------------------------------------------------------

# Equivalent to ≈ ×2 change in RPU per class with class-8 ≈ 1 RPU.
_DEFAULT_CLASS_TO_RPU = {
    0: 0.0001,
    1: 0.001,
    2: 0.01,
    3: 0.03,
    4: 0.06,
    5: 0.12,
    6: 0.25,
    7: 0.50,
    8: 1.0,
    9: 2.0,
    10: 4.0,
}

# Calibration parameters (module-level so they survive new class instantiation)
_CALIBRATED = False
_CAL_SLOPE: float | None = None
_CAL_INTERCEPT: float | None = None


def class_to_rpu(cls_val: int) -> float:
    """Return RPU for a ProD ordinal class.

    Uses calibrated linear model if available, otherwise default lookup.
    """
    if not (0 <= cls_val <= 10):
        raise ValueError("Class must be between 0 and 10")

    global _CALIBRATED, _CAL_SLOPE, _CAL_INTERCEPT

    if _CALIBRATED and _CAL_SLOPE is not None and _CAL_INTERCEPT is not None:
        import math
        return 10 ** (_CAL_SLOPE * cls_val + _CAL_INTERCEPT)
    else:
        return _DEFAULT_CLASS_TO_RPU[cls_val]


# ---------------------------------------------------------------------------
#  ProDIntegration – new calibration method
# ---------------------------------------------------------------------------

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
    best_config_17 = None  # highest-scoring exact-17-bp spacer
    
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
                
                spacer = sequence[pos35+6:pos10]

                # Record best exact-17bp spacer separately
                if spacer_length == 17 and combined_score > (best_config_17 or {}).get('score', 0):
                    best_config_17 = {
                        'spacer': spacer,
                        'minus35_pos': pos35,
                        'minus10_pos': pos10,
                        'score': combined_score
                    }
                # Always keep track of global best (any length 15-19)
                if combined_score > best_score:
                    best_score = combined_score
                    best_config = {
                        'spacer': spacer,
                        'minus35_pos': pos35,
                        'minus10_pos': pos10,
                        'score': combined_score,
                        'length': spacer_length
                    }
    
    # Prefer an exact-17 bp spacer if available
    if best_config_17:
        logger.debug(
            "Spacer extraction picked 17-bp spacer %s with score %.2f",
            best_config_17['spacer'],
            best_config_17['score'],
        )
        return best_config_17['spacer']

    # Otherwise fall back to best_config (length 15-19) and adjust to 17 bp
    if best_config:
        from ProD import run_tool
        spacer = best_config['spacer']
        if len(spacer) == 16:
            # Pad with 1 nt downstream of spacer if available
            end = best_config['minus10_pos']
            if end < len(sequence):
                spacer = spacer + sequence[end]
            else:
                spacer = sequence[best_config['minus35_pos'] + 5] + spacer
        elif len(spacer) == 18:
            # Trim 1 nt from middle of spacer
            spacer = spacer[:8] + spacer[9:]
        logger.debug(
            "Adjusted spacer to 17-bp: %s (original len %d)",
            spacer,
            best_config['length'],
        )
        return spacer if len(spacer) == 17 else None

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
    from ProD import run_tool
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
        # Attempt to extract spacer blueprint automatically (keep N's)
        maybe_spacer = extract_id_ecoli_spacer(blueprint)
        if maybe_spacer and len(maybe_spacer) == 17:
            logger.info("Auto-extracted spacer blueprint %s from full promoter", maybe_spacer)
            blueprint = maybe_spacer
        else:
            logger.warning(
                "Blueprint length %d is not 17 and extraction failed; results likely invalid.",
                len(blueprint),
            )
    
    # check that it is a valid blueprint
    SEQ_DICT = {'A': [0], 'T': [1], 'C': [2], 'G': [3], 'R': [0,3],
            'Y': [1,2], 'S': [2,3], 'W': [0,1], 'K': [1,3],
            'M': [0,2], 'B': [1,2,3], 'D': [0,1,3], 
            'H': [0,1,2], 'V': [0,2,3], 'N':[0,1,2,3]}

    valid_chars = set(SEQ_DICT.keys())
    if not set(blueprint).issubset(valid_chars):
        invalid_char = next(c for c in blueprint if c not in valid_chars)
        raise ValueError(
            f"Blueprint contains invalid character '{invalid_char}'. "
            f"Valid characters are: {', '.join(sorted(list(valid_chars)))}"
        )

    if all(c in "ATCG" for c in blueprint):
        raise ValueError(
            f"The provided blueprint sequence '{blueprint}' is not degenerate. "
            "A blueprint must contain at least one IUPAC ambiguity code (e.g., N, R, Y, etc.)."
        )
    
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
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Run ProD tool
    try:
        from ProD import run_tool
        logger.info(f"Generating promoter library from blueprint {blueprint}")
        result = run_tool(
            [blueprint] if isinstance(blueprint, str) else blueprint,
            output_path=output_path,
            lib=True,
            lib_size=library_size,
            strengths=desired_strengths,
            cuda=use_cuda,
        )
        
        if result is False:
            logger.error("ProD library generation failed")
            return pd.DataFrame()
            
        return result
        
    except Exception as e:
        
        traceback.print_exc()
        logger.error(f"Error generating promoter library: {str(e)}")
        return pd.DataFrame()

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
        # Convert all sequences to uppercase and, if necessary, auto-extract
        # 17 bp spacer from full promoters.
        processed = []
        original_map = {}
        for seq in spacers:
            seq_up = seq.upper()
            if len(seq_up) != 17:
                maybe_spacer = extract_id_ecoli_spacer(seq_up)
                if not maybe_spacer:
                    logger.warning(
                        "Could not extract 17 bp spacer from provided promoter; skipping: %s",
                        seq[:30] + ("…" if len(seq) > 30 else ""),
                    )
                    continue
                seq_up = maybe_spacer.upper()
                logger.info("Auto-extracted spacer %s from full promoter", seq_up)
            processed.append(seq_up)
            original_map[seq_up] = seq  # preserve original key

        if not processed:
            logger.error("No valid 17 bp spacer sequences to evaluate.")
            return {}

        results = evaluate_promoter_spacers(
            processed,
            output_path,
            self.use_cuda,
            self.model_path,
        )
        
        if results.empty:
            return {}
            
        # Convert results to dictionary, ensuring keys match input case
        spacer_to_strength = {}
        for _, row in results.iterrows():
            # ProD returns column named "spacer" (17-bp promoter spacer)
            seq_col = "spacer" if "spacer" in row else "sequence"
            spacer_seq = row[seq_col]
            orig_key = original_map.get(spacer_seq.upper(), spacer_seq)
            spacer_to_strength[orig_key] = float(row["strength"])  # 0-10 class
            # also provide calibrated RPU
            spacer_to_strength[orig_key + "_ymax"] = class_to_rpu(int(row["strength"]))
            
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
            return {"error": "Tool returned empty results. It is likely that no variants could be found for the given blueprint and desired strengths."}
            
        # Convert results to dictionary with detailed information
        # Harmonise column names: ProD (run_tool) gives [ID, spacer, strength, promoter]
        # Build a richer dict even if probabilities per class are not retained.
        library_dict: Dict[str, Dict[str, Any]] = {}
        for _, row in results.iterrows():
            spacer = row.get('spacer') or row.get('sequence')
            if spacer is None:
                continue  # skip unexpected rows
            strength_class = int(row['strength'])

            # If the probability columns exist, pick probability of the predicted class.
            prob_col = f'P(Class {strength_class}|spacer)'
            prob_val = float(row[prob_col]) if prob_col in row else 1.0  # default 1.0 if missing

            library_dict[spacer] = {
                'strength': strength_class,  # keep same numeric scale
                'class': strength_class,
                'probability': prob_val,
                'strength_band': get_strength_band(strength_class),
                'ymax': class_to_rpu(strength_class),
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
    
    # ------------------------------------------------------------------
    #  Calibration helper
    # ------------------------------------------------------------------

    def calibrate_rpu_scale(self, reference_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calibrate class→RPU mapping from reference promoters.

        Args:
            reference_data: list of { 'sequence': str, 'ymax': float }

        Returns:
            dict with slope, intercept and number of points used.
        """
        if not reference_data:
            raise ValueError("No reference data provided for calibration")

        seqs = [item['sequence'] for item in reference_data]
        ymax_vals = [float(item['ymax']) for item in reference_data]

        # Evaluate classes with ProD
        class_dict = self.evaluate_spacers(seqs)
        if not class_dict:
            raise RuntimeError("ProD failed to evaluate reference sequences")

        cls_list = []
        log_rpu_list = []
        import math
        for seq, ymax in zip(seqs, ymax_vals):
            if seq not in class_dict:
                logger.warning("Sequence %s not evaluated – skipping", seq[:20])
                continue
            cls = class_dict[seq]
            cls_list.append(cls)
            log_rpu_list.append(math.log10(ymax))

        if len(cls_list) < 2:
            raise RuntimeError("Need at least two reference points for calibration")

        # Simple linear regression in log space
        import numpy as np
        C = np.array(cls_list, dtype=float)
        L = np.array(log_rpu_list, dtype=float)
        meanC = C.mean()
        meanL = L.mean()
        slope = float(((C - meanC) * (L - meanL)).sum() / ((C - meanC) ** 2).sum())
        intercept = float(meanL - slope * meanC)

        # store globally
        global _CALIBRATED, _CAL_SLOPE, _CAL_INTERCEPT
        _CALIBRATED = True
        _CAL_SLOPE = slope
        _CAL_INTERCEPT = intercept

        logger.info("ProD class→RPU calibration stored: log10(RPU) = %.3f*class + %.3f", slope, intercept)

        return {
            'success': True,
            'n_points': len(cls_list),
            'slope': slope,
            'intercept': intercept,
        }

if __name__ == "__main__":
    # --------------------------------------------------------------------------
    # Pull promoter from UCF
    # --------------------------------------------------------------------------
    from src.library.library_manager import LibraryManager
    import random

    # randomly select one promoter
    lm = LibraryManager()
    lm.select_library('Eco1C1G1T1')
    ucf_data = lm.get_ucf_data()
    promoters = [item for item in ucf_data if item.get("collection") == "parts" and item.get("type") == "promoter"]

    prod = ProDIntegration()
 
    ptac = 'AACGATCGTTGGCTGTGTTGACAATTAATCATCGGCTCGTATAATGTGTGGAATTGTGAGCGCTCACAATT'
    pTac_eval = prod.evaluate_spacers([ptac])
    print(f'pTac_eval: {pTac_eval}')

    ptet = 'TACTCCACCGTTGGCTTTTTTCCCTATCAGTGATAGAGATTGACATCCCTATCAGTGATAGAGATAATGAGCAC'
    pTet_eval = prod.evaluate_spacers([ptet])
    print(f'pTet_eval: {pTet_eval}')

    # --------------------------------------------------------------------------
    # Generate library
    # --------------------------------------------------------------------------
    """
    For σ70 promoters the 17-bp spacer mainly tunes strength through DNA
    mechanical properties (twist, roll, GC content, intrinsic curvature).
    Positions in the middle of the spacer (≈ nt 7-11) have the greatest effect on
    RNA-polymerase alignment; the first two and last two bases matter least.
    """
    from itertools import product
    delta = []
    
    blueprint  = "".join("N" if i in (5,6,7,8,9) else b
                     for i,b in enumerate(spacer))
    out_path = f'outputs/pro_d/{blueprint}_lib.csv'
    lib = prod.generate_library(blueprint,
                                desired_strengths=list(range(11)),  
                                library_size=5,
                                output_path=out_path)
    print(lib)