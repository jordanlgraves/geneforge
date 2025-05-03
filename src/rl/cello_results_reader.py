import csv
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def get_circuit_score(cello_results: Dict[str, Any]) -> Optional[float]:
    """Return the circuit score if available.

    circuit_score is a ratio of the transcription in the ON and OFF states for every output of the circuit

    Tries multiple fallbacks:
    1. Direct key ``overall_score`` if present (used by evaluate_circuit_performance).
    2. Load the ``*_circuit-score.csv`` referenced in
       ``cello_results['results']['dna_design']['circuit_score']``.
    3. If neither is present, return ``None``.
    """
    try:
        circuit_score_path = (
            cello_results.get("results", {})
            .get("dna_design", {})
            .get("circuit_score")
        )
        if circuit_score_path and Path(circuit_score_path).exists():
            with open(circuit_score_path, "r", newline="") as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    # Expect either ["circuit_score", value] or [value]
                    if not row:
                        continue
                    if len(row) == 1:
                        return float(row[0])
                    if len(row) >= 2 and row[1]:
                        return float(row[1])
    except Exception as exc:
        logger.warning("Failed to extract circuit score: %s", exc)
    return None 