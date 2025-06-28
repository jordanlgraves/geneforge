import os
import sys
import pytest

# Ensure project root on PYTHONPATH for test discovery when run from repo root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.tools.rbs_calculator_integration import RBSCalculatorIntegration


def test_predict_initiation_rate_empty_sequence():
    """Calling with an empty sequence should return success=False and an error message."""
    result = RBSCalculatorIntegration.predict_initiation_rate("")
    assert result["success"] is False
    assert "error" in result and result["error"].strip() != ""


def test_predict_initiation_rate_basic():
    """A trivial mRNA string should be accepted and return the expected keys.

    The underlying legacy code may fail when external dependencies (NuPACK) are
    absent; in that case we still expect a well-formed dictionary with
    success=False.  If the dependencies are available the call should succeed
    and provide thermodynamic metrics.
    """
    mrna = "AGGAGGAAAAAAAAAATGAAATTTGGG"  # contains Shine-Dalgarno + start codon
    result = RBSCalculatorIntegration.predict_initiation_rate(mrna)

    # The wrapper **always** returns these keys regardless of success.
    assert "success" in result
    if result["success"]:
        # Positive path – check presence of core result fields
        for key in (
            "delta_g_total",
            "expression_levels",
            "start_positions",
            "best_delta_g_total",
            "best_expression",
        ):
            assert key in result, f"Missing key {key} in successful result"
    else:
        # Failure path – should include an informative error
        assert "error" in result and isinstance(result["error"], str)


def test_design_rbs_requires_target():
    """Omitting both target_tir and target_delta_g must fail gracefully."""
    out = RBSCalculatorIntegration.design_rbs("AAAAA", "ATGAAA")
    assert out["success"] is False
    assert "error" in out


def test_design_rbs_minimal_iterations():
    """Designing with a small iteration count should return a structured dict.

    We pass *max_iterations=10* to keep the test fast.  Success depends on
    external dependencies; regardless we validate the returned schema.
    """
    pre_seq = "TTTTT"
    post_seq = "ATGAAATTTCCC"
    result = RBSCalculatorIntegration.design_rbs(
        pre_sequence=pre_seq,
        post_sequence=post_seq,
        target_delta_g=-5.0,
        max_iterations=10,
    )

    assert "success" in result
    if result["success"]:
        for key in ("rbs_sequence", "predicted_delta_g"):
            assert key in result
    else:
        assert "error" in result

if __name__ == "__main__":
    import os, sys
    # run pytest only on this file
    sys.exit(pytest.main([os.path.abspath(__file__)]))