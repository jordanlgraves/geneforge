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
    def predict_promoter_strength(self, 
                                  sequence: str, 
                                  organism: str = "Escherichia coli str. K-12 substr. MG1655") -> float:
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
        
        calculator = Promoter_Calculator(organism=organism)
            
        calculator.run(formatted_seq)
        result = calculator.output()
        return result
    
    def optimize_promoter(self, 
                          sequence: str, 
                          target_strength: float = None, 
                          iterations: int = 50,
                          preserve_operators: bool = True,
                          operator_regions: List[Tuple[int, int]] = None,
                          organism: str = "Escherichia coli str. K-12 substr. MG1655") -> Dict[str, Any]:
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
        
        # Get initial strength (numeric Tx_rate)
        initial_out = self.predict_promoter_strength(sequence, organism=organism)
        initial_strength = self._best_tx_rate(initial_out)
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
            
            # Evaluate the mutated sequence (numeric Tx_rate)
            mutated_out = self.predict_promoter_strength(mutated_sequence, organism=organism)
            mutated_strength = self._best_tx_rate(mutated_out)
            
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
                              preserve_operators: bool = True,
                              organism: str = "Escherichia coli str. K-12 substr. MG1655") -> Dict[str, Any]:
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
        initial_analysis = self.predict_promoter_strength(sequence, organism=organism)
        
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
            return self.optimize_promoter(sequence, target_strength, iterations, organism=organism)
        
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
        
        # Get initial strength (numeric Tx_rate)
        initial_out = self.predict_promoter_strength(sequence, organism=organism)
        initial_strength = self._best_tx_rate(initial_out)
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
            
            # Evaluate the mutated sequence (numeric Tx_rate)
            mutated_out = self.predict_promoter_strength(mutated_sequence, organism=organism)
            mutated_strength = self._best_tx_rate(mutated_out)
            
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
    
    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    def _best_tx_rate(self, calc_out: dict, *, include_reverse: bool = False) -> float:
        """Return the highest Tx_rate from a Promoter-Calculator output dict.

        Parameters
        ----------
        calc_out : dict
            The raw dict returned by `predict_promoter_strength`.
        include_reverse : bool, default=False
            Whether to also scan `Reverse_Predictions_per_TSS`.
            In most synthetic-biology tasks we care only about promoters that
            drive transcription in the **forward** direction, hence the
            default is *False*.
        """
        if not isinstance(calc_out, dict):
            return float(calc_out) if isinstance(calc_out, (int, float)) else 0.0

        best = 0.0
        # Always consider forward predictions
        for pred in calc_out.get("Forward_Predictions_per_TSS", {}).values():
            best = max(best, pred.get("Tx_rate", 0.0))

        if include_reverse:
            for pred in calc_out.get("Reverse_Predictions_per_TSS", {}).values():
                best = max(best, pred.get("Tx_rate", 0.0))

        return best

import json
import re
from pathlib import Path
from typing import Tuple




def get_reference_promoter_from_ucf(
    ucf_path: str | Path,
    promoter_label: str = "J23101",
    upstream: int = 70,
    downstream: int = 20
) -> str:
    """
    Return the promoter (with context) needed for Promoter Calculator.

    Parameters
    ----------
    ucf_path :  path to the UCF JSON file
    promoter_label :  '/label=' string that marks the reference promoter feature
    upstream :  number of nucleotides to include before the promoter (default 70)
    downstream :  number of nucleotides after the +1 position to include (default 20)

    Returns
    -------
    str :  DNA sequence 5'→3' with specified context
    """
    def _clean_dna(raw: str) -> str:
        """Remove line numbers, whitespace and non‑ACGT letters from a GenBank ORIGIN block."""
        return re.sub(r'[^ACGTacgt]', '', raw)

    def _extract_origin(genbank: str) -> str:
        """Return the raw DNA string from an embedded GenBank record."""
        m = re.search(r'ORIGIN(.*)//', genbank, re.S | re.I)
        if not m:
            raise ValueError("Could not find ORIGIN section.")
        return _clean_dna(m.group(1))

    def _find_feature_coords(genbank: str, label: str) -> Tuple[int, int]:
        """
        Locate the genomic coordinates (1‑based, inclusive) of the feature whose
        /label= matches *label*.  Works for simple single‑segment locations.
        """
        # find the feature block containing `/label=label`
        pattern = rf'misc_feature\s+([^\n]+).*?/label={re.escape(label)}'
        m = re.search(pattern, genbank, re.S | re.I)
        if not m:
            raise ValueError(f"Feature with label '{label}' not found.")
        loc = m.group(1).strip()          # e.g. "20..54" or "complement(214..243)"
        # strip complement() if present
        loc = re.sub(r'complement\(([^)]+)\)', r'\1', loc)
        start, end = map(int, loc.split('..'))
        return start, end                 # 1‑based coordinates
    
    ucf = json.loads(Path(ucf_path).read_text())
    # 1) grab the measurement_std block
    ms_block = next(
        block for block in ucf if block.get("collection") == "measurement_std"
    )
    genbank_str = "\n".join(ms_block["plasmid_sequence"])

    # 2) extract full plasmid sequence & promoter coords
    full_seq = _extract_origin(genbank_str).upper()
    start, end = _find_feature_coords(genbank_str, promoter_label)

    # 3) build context window (convert 1‑based → 0‑based indices)
    left = max(0, start - 1 - upstream)
    right = min(len(full_seq), start - 1 + downstream)  # +1 position is start‑1
    context_seq = full_seq[left:right]

    return context_seq


def filter_forward_promoters(
    pc_out: dict,
    require_sigma70: bool = True,
    sigma_min: float = 0.8,
    dg10_max: float = 0.0,
    dg35_max: float = 0.0,
    spacing_range: tuple[int, int] = (16, 18),
) -> list:
    """
    Keep Forward‑strand promoters that satisfy:
      • σ70 ≥ sigma_min  (unless require_sigma70 = False)
      • –35/–10 spacing in spacing_range
      • dG10 and dG35 not worse than dg*_max
    Returns a list sorted by descending Tx_rate.
    """

    # σ‑factor fraction comes from the *global* dict
    sigma70_frac = pc_out.get("sigmaLevels", {}).get("70", 1.0)

    if require_sigma70 and sigma70_frac < sigma_min:
        raise ValueError(
            f"Run appears not to be σ70 (sigma70 = {sigma70_frac:.2f} < {sigma_min})."
        )

    forward = pc_out["Forward_Predictions_per_TSS"]

    def spacing_ok(h35: tuple[int, int], h10: tuple[int, int]) -> bool:
        return spacing_range[0] <= (h10[0] - h35[1]) <= spacing_range[1]

    good = []
    for obj in forward.values():
        if not spacing_ok(obj.hex35_position, obj.hex10_position):
            continue
        if obj.dG_10 > dg10_max or obj.dG_35 > dg35_max:
            continue
        good.append(obj)

    return sorted(good, key=lambda p: p.Tx_rate, reverse=True)

def get_new_promoter_sequences(parent_seq: str,
                               pc: PromoterCalculatorIntegration,
                               n_best: int = 10,
                               spacing_ok: tuple[int, int] = (16, 18)
                              ) -> list[tuple[str, float]]:
    """
    Return up to n_best mutated promoter sequences with higher Tx_rate than parent.
    Returns list of (sequence, Tx_rate) sorted by descending Tx_rate.
    """

    # 1. Run calculator once on the parent to locate TSS and motifs
    parent_out   = pc.predict_promoter_strength(parent_seq)
    parent_best  = filter_forward_promoters(parent_out)[0]
    motifs       = {
        "hex35": parent_best.hex35_position,
        "hex10": parent_best.hex10_position,
        "disc" : parent_best.disc_position,
        "UP"   : parent_best.UP_position,
    }
    parent_rate  = parent_best.Tx_rate

    # 2. Enumerate all single‑nt mutations in −35 and −10 hexamers
    cand_seqs = []
    bases = "ATGC"
    for tag in ("hex35", "hex10"):
        i0, i1 = motifs[tag]                    # 0‑based inclusive/exclusive
        for idx in range(i0, i1):
            for b in bases:
                if b == parent_seq[idx]:
                    continue
                mut = parent_seq[:idx] + b + parent_seq[idx+1:]
                cand_seqs.append(mut)

    # 3. Optional: add spacer‑length edits if spacing is off
    spacing = motifs["hex10"][0] - motifs["hex35"][1]
    if spacing < spacing_ok[0]:
        # insert 'A' right after −35
        pos = motifs["hex35"][1]
        cand_seqs.append(parent_seq[:pos] + "A" + parent_seq[pos:])
    elif spacing > spacing_ok[1]:
        # delete 1 nt at spacer midpoint
        pos = motifs["hex35"][1] + (spacing // 2)
        cand_seqs.append(parent_seq[:pos] + parent_seq[pos+1:])

    # 4. Batch‑evaluate (vectorised calculator call if available, else loop)
    better = []
    for seq in cand_seqs:
        out = pc.predict_promoter_strength(seq)
        best = filter_forward_promoters(out)
        if not best:
            continue
        rate = best[0].Tx_rate
        if rate > parent_rate * 1.05:           # require ≥5 % improvement
            better.append((seq, rate))

    # 5. Sort and return top n_best
    better.sort(key=lambda t: t[1], reverse=True)
    return better[:n_best]


if __name__ == "__main__":
    calculator = PromoterCalculatorIntegration()

    ucf_file = "ext_repos/Cello-UCF/files/v2/ucf/Eco/Eco1C1G1T1.UCF.json"
    seq = get_reference_promoter_from_ucf(ucf_file, upstream=70, downstream=20)
    ref_output = calculator.predict_promoter_strength(seq)
    
    candidates = filter_forward_promoters(ref_output)
    if not candidates:
        raise RuntimeError("No forward strand promoters passed the filters!")
    best = candidates[0]      # highest Tx_rate that looks biologically sound
    
    # current_promoter = seq # 'ACCAGGAATCTGAACGATTCGTTACCAATTGACATATTTAAAATTCTTGTTTAAAatgctagc'
    # current_promoter = 'CGCTCATTCACTAGGTCTGATTCGTTACCAATTGACAACTGGTGGTCGAATCAAGATAATAGACCAGTCACTATATTT'
    # current_strength = calculator.predict_promoter_strength(current_promoter)
    
    new_promoters = get_new_promoter_sequences(seq, calculator)
    print(new_promoters)



    