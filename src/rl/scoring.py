from __future__ import annotations

"""Utility functions to score GeneForge chat sessions for Offline RL/ORPO.

Each scoring helper accepts two core inputs:

1. **session_state** – the final `src.session_state.SessionState` instance
   after the conversation finished.  It contains design artefacts such as
   the selected library, any generated Verilog, Cello results, etc.
2. **messages** – the *complete* list of chat messages (as produced by
   `ExampleRunner.messages`).  Tool calls are represented by messages with
   `role == 'tool'` and the specific tool name stored in the `name` field.

All functions return either a *numeric score* (0–1 or arbitrary units) or a
boolean which can be mapped to 1/0 by downstream code.  The helpers are
*stateless* so they can be freely combined in higher-level evaluation
pipelines.
"""

from typing import List, Dict, Any, Sequence, Optional, Tuple
from math import isclose

from src.session_state import SessionState

def get_tools_called(messages: List[Dict[str, Any]]) -> List[str]:
    """Return an ordered list of tool names used in the conversation."""
    return [m.get("name") for m in messages if m.get("role") == "tool" and m.get("name")]


def was_tool_called(messages: List[Dict[str, Any]], tool_name: str) -> bool:
    """True if *tool_name* appears at least once in the tool messages."""
    return tool_name in get_tools_called(messages)


def tool_call_order_score(messages: List[Dict[str, Any]], expected_sequence: Sequence[str]) -> float:
    """Score how closely the tool-call order matches *expected_sequence*.

    Returns a value between 0 and 1 where 1 means the exact sequence appears
    **in order** (not necessarily consecutively).  The score is the fraction
    of expected tools found in correct order.
    """
    if not expected_sequence:
        return 1.0  # trivial – nothing expected

    called = get_tools_called(messages)
    idx = 0
    hits = 0
    for tool in called:
        if tool == expected_sequence[idx]:
            hits += 1
            idx += 1
            if idx == len(expected_sequence):
                break
    return hits / len(expected_sequence)

# ---------------------------------------------------------------------------
#  Design-level helpers (analyse *session_state*)
# ---------------------------------------------------------------------------

def _extract_design_parts(session_state: SessionState) -> List[str]:
    """Return a list of part IDs referenced in the final design.

    Tries, in order:
    1. Parts listed in `session_state.cello_results['results']['dna_design']`
       (preferred – comes directly from Cello).
    2. Part names mentioned in `session_state.verilog_code` (fallback).
    """
    parts: set[str] = set()

    # 1) Cello JSON output (preferred)
    try:
        design_data = session_state.cello_results.get("results", {}).get("dna_design", [])  # type: ignore[attr-defined]
        for item in design_data:
            name = item.get("name") or item.get("id") or item
            if isinstance(name, str):
                parts.add(name)
    except Exception:
        pass

    return sorted(parts)


def design_contains_parts(session_state: SessionState, parts: Sequence[str]) -> float:
    """Return the fraction of *parts* present in the final design (0–1)."""
    if not parts:
        return 1.0
    available = set(_extract_design_parts(session_state))
    hits = sum(1 for p in parts if p in available)
    return hits / len(parts)


def num_parts_used(session_state: SessionState) -> int:
    """Count the number of unique parts in the final design."""
    return len(_extract_design_parts(session_state))


# ---------------------------------------------------------------------------
#  Example metrics for downstream preference-optimisation
# ---------------------------------------------------------------------------

def circuit_score(session_state: SessionState, perfect: float = 400.0) -> Optional[float]:
    """Return normalised circuit score if available in Cello results.

    If `session_state.cello_results` contains a numeric `overall_score` field
    (as produced by the *evaluate_circuit_performance* tool) that value is
    divided by *perfect* (default 100) to yield a 0–1 score. If not found,
    returns ``None`` so downstream code can skip the metric.
    """
    try:
        score = float(session_state.cello_results.get("overall_score"))  # type: ignore[attr-defined]
        return max(0.0, min(score / perfect, 1.0))
    except Exception:
        return 0.0


def gc_content_score(sequence: str, target: Tuple[float, float] = (40.0, 60.0)) -> float:
    """Helper to score a DNA sequence GC% within a target range.

    Returns 1 if within range, otherwise a linear drop-off to 0 at 0/100 %.
    Stand-alone utility independent from session/messages – can be used to
    grade individual sequences extracted elsewhere.
    """
    seq = sequence.upper().replace("\n", "").replace(" ", "")
    if not seq:
        return 0.0
    gc = (seq.count("G") + seq.count("C")) / len(seq) * 100
    lo, hi = target
    if lo <= gc <= hi:
        return 1.0
    # Linear ramp outside the band
    if gc < lo:
        return max(0.0, (gc / lo))
    else:  # gc > hi
        return max(0.0, (100 - gc) / (100 - hi))    