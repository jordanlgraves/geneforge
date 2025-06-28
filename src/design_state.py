from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Literal

__all__ = ["DesignState"]


@dataclass
class DesignState:
    """Container for artefacts generated during a single design session.

    The class centralises all *design-specific* files (SBOL, SBML, Verilog) **and**
    the parameter template used for kinetic simulations.

    The template follows the structure returned by
    ``build_param_template(sbml_doc)``::

        {
            "species": {
                "AraC":     {"value": 1.2, "unit": "µM", "source": "BNID:101955"},
                "TetR":     {"value": None, "unit": "µM", "source": None},
            },
            "parameters": {
                "k_syn":    {"value": 0.05, "unit": "s^-1", "source": "heuristic"},
                "deg::P1":  {"value": None, "unit": "s^-1", "source": None},
            }
        }

    Attributes
    ----------
    sbol_file
        Path to the latest SBOL file produced by Cello.
    sbml_file
        Path to the SBML file obtained after SBOL→SBML conversion.
    verilog
        Verilog source text associated with the current design.
    parameter_template
        Dict mapping *species* and *parameters* to their simulation values.
    last_editor
        Tracks whether the last edit came from the *agent* or the *user*. Can be
        useful for conflict resolution / UI highlighting.
    """

    sbol_file: Optional[Path] = None
    sbml_file: Optional[Path] = None
    verilog: Optional[str] = None
    # Simulation-related data
    parameter_template: Dict[str, Any] = field(default_factory=dict)
    last_editor: Optional[Literal["agent", "user"]] = None

    # ------------------------------------------------------------------
    #  Helper methods
    # ------------------------------------------------------------------

    def is_template_filled(self) -> bool:
        """Return *True* if **all** entries have a non-None ``value`` field."""
        tmpl = self.parameter_template or {}
        if not tmpl:
            return False

        def _all_filled(section: Dict[str, Any]) -> bool:
            return all(v.get("value") is not None for v in section.values())

        species_ok = _all_filled(tmpl.get("species", {}))
        params_ok = _all_filled(tmpl.get("parameters", {}))
        return species_ok and params_ok

    # ------------------------------------------------------------------
    #  (De)serialisation helpers so SessionState.to_dict() stays simple
    # ------------------------------------------------------------------

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dict representation."""
        data = asdict(self)
        # Convert Path → str for JSON safety
        if data["sbol_file"] is not None:
            data["sbol_file"] = str(data["sbol_file"])
        if data["sbml_file"] is not None:
            data["sbml_file"] = str(data["sbml_file"])
        return data

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DesignState":
        """Instantiate *DesignState* from ``SessionState.from_dict()`` payload."""
        # Convert string paths back to Path objects when present
        sbol_file = payload.get("sbol_file")
        sbml_file = payload.get("sbml_file")
        if isinstance(sbol_file, str):
            payload["sbol_file"] = Path(sbol_file)
        if isinstance(sbml_file, str):
            payload["sbml_file"] = Path(sbml_file)
        return cls(**payload) 