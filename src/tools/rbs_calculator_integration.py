import sys
import os
import logging
from typing import Dict, Any, Tuple, Optional

import dotenv

# -----------------------------------------------------------------------------
#  Ensure RBS Calculator sources are on the PYTHONPATH
# -----------------------------------------------------------------------------

dotenv.load_dotenv()
RBS_CALCULATOR_ROOT = os.getenv("RBS_CALCULATOR_ROOT")
if RBS_CALCULATOR_ROOT and RBS_CALCULATOR_ROOT not in sys.path:
    sys.path.append(RBS_CALCULATOR_ROOT)

# -----------------------------------------------------------------------------
#  Legacy compatibility patches
# -----------------------------------------------------------------------------
# The original RBS Calculator code (Python 2 era) relies on the deprecated
# 'sets' and 'popen2' modules.  In Python 3 we shim them to modern
# equivalents so the import succeeds without modifying third-party code.

try:
    import sets  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – executed on modern Pythons
    import types  # noqa: E402 – late import

    sets = types.ModuleType("sets")
    sets.Set = set  # type: ignore[attr-defined]
    sys.modules["sets"] = sets

# -- popen2 shim --------------------------------------------------------------

try:
    import popen2  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – executed on modern Pythons
    import subprocess  # noqa: E402 – late import
    import types  # noqa: E402 – late import

    def _mk_popen3_class():
        """Return a minimal drop-in replacement for popen2.Popen3."""

        class _Popen3:  # pylint: disable=too-few-public-methods
            def __init__(self, cmd: str, mode: str = "r") -> None:  # noqa: D401
                # The legacy API accepted a *cmd* string and returned file-like
                # objects .fromchild / .tochild / .childerr.  We replicate the
                # minimal subset used by NuPACK.py.
                self.process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    text=True,
                )
                self.fromchild = self.process.stdout  # type: ignore[attr-defined]
                self.childerr = self.process.stderr  # type: ignore[attr-defined]
                self.tochild = self.process.stdin  # type: ignore[attr-defined]

            # Legacy helper proxies
            def poll(self):  # noqa: D401
                return self.process.poll()

            def wait(self, timeout: float | None = None):  # noqa: D401
                return self.process.wait(timeout)

        return _Popen3

    popen2 = types.ModuleType("popen2")
    popen2.Popen3 = _mk_popen3_class()  # type: ignore[attr-defined]
    # Popen4 is rarely used; simple alias capturing combined stdout/stderr.
    popen2.Popen4 = lambda cmd, mode="r": subprocess.Popen(  # type: ignore  # noqa: E731
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        text=True,
    )
    sys.modules["popen2"] = popen2

# -----------------------------------------------------------------------------
#  Third-party dependencies provided by the Salis-lab repository
# -----------------------------------------------------------------------------

from RBS_Calculator import RBS_Calculator  # noqa: E402  – after path/patch
from RBS_MC_Design import Monte_Carlo_Design  # noqa: E402

logger = logging.getLogger(__name__)


class RBSCalculatorIntegration:  # pylint: disable=too-few-public-methods
    """Wrapper around the legacy *Ribosome Binding Site Calculator* library.

    The goal is to expose a *clean* and *robust* API for use by higher-level
    tools in the GeneForge project while hiding the complexity of the original
    implementation.  All public methods return plain Python dictionaries to
    make them JSON-serialisable and therefore directly consumable by the LLM
    tool layer.
    """

    # ------------------------------------------------------------------
    #  Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def predict_initiation_rate(
        mrna_sequence: str,
        start_range: Optional[Tuple[int, int]] = None,
        name: str | None = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Predict *ΔG_total* and translation initiation rate for an mRNA.

        Parameters
        ----------
        mrna_sequence:
            Full input mRNA sequence (DNA or RNA alphabet).
        start_range:
            Optional *[start, end]* indices (0-based, inclusive start, exclusive
            end) restricting the search for start codons.  When *None* the
            entire sequence is scanned.
        name:
            Human-readable identifier used only for logging/debugging.
        verbose:
            When *True*, the underlying `RBS_Calculator` will print its classic
            detailed table to *stdout*.

        Returns
        -------
        dict
            A JSON-serialisable dictionary containing the prediction results or
            an *error* key when the evaluation failed.
        """
        mrna_sequence = (mrna_sequence or "").strip()
        if not mrna_sequence:
            return {"success": False, "error": "Empty mRNA sequence provided."}

        try:
            # Default start range is the whole sequence.
            if start_range is None:
                start_range = [0, len(mrna_sequence)]

            name = name or "mRNA"
            calc = RBS_Calculator(mrna_sequence, list(start_range), name, verbose)
            calc.calc_dG()

            if verbose:
                calc.print_dG(print_expression=True)

            # For convenience pick the minimum ΔG_total entry as the *best* RBS.
            if not calc.dG_total_list:
                return {
                    "success": False,
                    "error": "No start codons found in the provided sequence.",
                }

            min_idx = int(min(range(len(calc.dG_total_list)), key=calc.dG_total_list.__getitem__))

            return {
                "success": True,
                "start_positions": calc.start_pos_list,
                "delta_g_total": calc.dG_total_list,
                "expression_levels": calc.Expression_list,
                "kinetic_scores": calc.kinetic_score_list,
                "best_start_pos": calc.start_pos_list[min_idx],
                "best_delta_g_total": calc.dG_total_list[min_idx],
                "best_expression": calc.Expression_list[min_idx],
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("RBS_Calculator failed")
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    #  Synthetic RBS design helper
    # ------------------------------------------------------------------

    @staticmethod
    def design_rbs(
        pre_sequence: str,
        post_sequence: str,
        target_tir: float | None = None,
        target_delta_g: float | None = None,
        max_iterations: int = 10_000,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Design a synthetic RBS achieving a desired initiation strength.

        Either *target_tir* (preferred) or *target_delta_g* **must** be
        provided.  The *pre_sequence* should contain the upstream 5′ UTR region
        immediately before the RBS whereas *post_sequence* starts at the start
        codon and continues into the coding sequence.
        """
        if target_tir is None and target_delta_g is None:
            return {
                "success": False,
                "error": "Either 'target_tir' or 'target_delta_g' must be provided.",
            }

        try:
            result = Monte_Carlo_Design(
                pre_seq=pre_sequence,
                post_seq=post_sequence,
                RBS_init=None,
                TIR_target=target_tir,
                dG_target=target_delta_g,
                MaxIter=max_iterations,
                verbose=verbose,
            )
            # The tuple shape depends on which target was used.
            if target_tir is not None:
                predicted_tir, rbs_seq, estimator, iterations = result  # type: ignore
                predicted_dg = estimator.dG_total_list[0]
            else:
                predicted_dg, rbs_seq, estimator, iterations = result  # type: ignore
                predicted_tir = estimator.Expression_list[0]

            return {
                "success": True,
                "rbs_sequence": rbs_seq,
                "predicted_tir": predicted_tir,
                "predicted_delta_g": predicted_dg,
                "iterations": iterations,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Monte_Carlo_Design failed")
            return {"success": False, "error": str(exc)}

