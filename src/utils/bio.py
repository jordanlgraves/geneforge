from typing import Optional
import logging

logger = logging.getLogger(__name__)

def extract_id_ecoli_spacer(sequence: str) -> Optional[str]:
    """
    Extract the spacer sequence from an E. coli promoter by identifying -35 and -10 boxes.
    Uses an advanced algorithm with position weight matrices and extended -10 considerations.

    Args:
        sequence: The full promoter sequence

    Returns:
        The extracted spacer sequence if found, otherwise None
    """
    logger = logging.getLogger(__name__)
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

def translate_dna_to_protein(dna_sequence: str) -> str:
    """
    Translate a DNA sequence to a protein sequence.
    """
    import Bio.Seq
    return Bio.Seq.translate(dna_sequence)

if __name__ == "__main__":
    print(translate_dna_to_protein("ATGCTGATC"))