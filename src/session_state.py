import logging
from typing import Optional, Dict, Any

from src.library.library_manager import LibraryManager

logger = logging.getLogger(__name__)

class SessionState:
    """
    Manages the state for a single user design session.

    This includes the selected library, custom UCF data,
    intermediate results, etc.
    """
    def __init__(self):
        logger.info("Initializing new session state.")
        # Initialize LibraryManager once per session
        self.library_manager = LibraryManager()
        self.current_ucf_data: Optional[list] = None
        self.custom_ucf_path: Optional[str] = None
        self.custom_input_path: Optional[str] = None
        self.cello_results: Optional[Dict[str, Any]] = None
        
        self.design_spec: Optional[str] = None  # Natural-language high-level specification
        self.verilog_code: Optional[str] = None  # Latest generated/updated Verilog source
        self.chat_rounds: int = 0  # Number of LLM-tool interaction rounds in current session
        # Add other state variables as needed, e.g.:
        # self.design_requirements: Dict[str, Any] = {}

    def from_dict(self, **kwargs):
        """Initialize the session state from a dictionary."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        if "library_manager" in kwargs:
            self.library_manager = LibraryManager()
            self.library_manager.select_library(kwargs["library_manager"]["current_library_id"])

    def to_dict(self) -> Dict[str, Any]:
        """Convert the session state to a dictionary."""
        return {
            "library_manager": {"current_library_id": self.library_manager.current_library_id},
            "current_ucf_data": self.current_ucf_data,
            "custom_ucf_path": self.custom_ucf_path,
            "verilog_code": self.verilog_code,
            "design_spec": self.design_spec,
            "chat_rounds": self.chat_rounds,
            "cello_results": self.cello_results,
            "custom_input_path": self.custom_input_path,
        }

    def select_library(self, library_id: str) -> bool:
        """Selects a library and updates the session state."""
        logger.info(f"Session selecting library: {library_id}")
        success = self.library_manager.select_library(library_id)
        if success:
            # Update session state's copy of UCF data if needed
            self.current_ucf_data = self.library_manager.get_ucf_data()
            logger.info(f"Session state updated with UCF data for {library_id}")
        else:
            logger.error(f"Failed to select library {library_id} in session.")
        return success

    def get_library_manager(self) -> LibraryManager:
        """Returns the LibraryManager instance for this session."""
        return self.library_manager

    def get_current_library_id(self) -> Optional[str]:
        """Gets the currently selected library ID from the manager."""
        return self.library_manager.current_library_id

    def get_current_ucf_data(self) -> Optional[list]:
        """Gets the raw UCF data for the currently selected library."""
        # Return the session's copy, ensuring it's up-to-date
        if self.library_manager.current_library_id and self.current_ucf_data is None:
             # If library selected but data not loaded here, fetch it
             self.current_ucf_data = self.library_manager.get_ucf_data()
        elif not self.library_manager.current_library_id:
            self.current_ucf_data = None # Clear if no library selected

        return self.current_ucf_data
    
    def get_cello_results(self) -> Optional[Dict[str, Any]]:
        """Gets the Cello results for the current session."""
        return self.cello_results

    def set_design_spec(self, spec: str):
        """Store the high-level design specification for the session."""
        self.design_spec = spec

    def get_design_spec(self) -> Optional[str]:
        return self.design_spec

    def set_verilog_code(self, verilog: str):
        """Persist Verilog code generated during this session."""
        self.verilog_code = verilog

    def get_verilog_code(self) -> Optional[str]:
        return self.verilog_code

    def get_chat_rounds(self) -> int:
        return self.chat_rounds

    # ------------------------------------------------------------------
    #  Automatic ProD calibration when a library is selected
    # ------------------------------------------------------------------

    def auto_calibrate_prod(self, min_refs: int = 3, max_refs: int = 10):
        """Calibrate ProD class→RPU mapping using promoters in the selected library.

        The routine looks for promoter parts in the UCF that have a numeric
        `ymax` parameter, extracts their spacers, evaluates them with ProD
        and fits a log-linear mapping (slope & intercept).  The calibration
        is stored inside the session-specific `ProDIntegration` instance so
        all subsequent ProD calls use the updated mapping automatically.

        Args:
            min_refs: minimum number of reference promoters required to fit
                      a line. If fewer are found, calibration is skipped.
            max_refs: maximum number of promoters to sample (for speed).

        Returns:
            Dict summarising the calibration (or reason for skipping).
        """
        from src.tools.pro_d_integration import ProDIntegration
        import random, math

        ucf_data = self.get_current_ucf_data()
        if not ucf_data:
            return {"success": False, "error": "No UCF loaded"}

        # Collect promoters with ymax parameter
        refs = []
        for item in ucf_data:
            if item.get("collection") != "parts" or item.get("type") != "promoter":
                continue
            # parameters is list of dicts; find ymax
            for p in item.get("parameters", []):
                if p.get("parameter", "").lower() in ("ymax", "y_max"):
                    try:
                        ymax_val = float(p.get("value"))
                    except (TypeError, ValueError):
                        continue
                    seq = item.get("dnasequence") or item.get("sequence")
                    if seq and ymax_val > 0:
                        refs.append({"sequence": seq, "ymax": ymax_val})
                    break  # stop after first parameter match

        if len(refs) < min_refs:
            return {
                "success": False,
                "error": f"Only found {len(refs)} promoters with ymax; need {min_refs} to calibrate.",
            }

        random.shuffle(refs)
        refs = refs[:max_refs]

        # Get (or create) ProDIntegration attached to this session
        if not hasattr(self, "prod_integration"):
            setattr(self, "prod_integration", ProDIntegration())
        prod = getattr(self, "prod_integration")

        try:
            result = prod.calibrate_rpu_scale(refs)
            return result
        except Exception as e:
            logger.warning("ProD calibration failed: %s", e)
            return {"success": False, "error": str(e)}

    # Add methods to update and retrieve other state variables as needed
    # e.g., set_custom_ucf_path, get_cello_results, etc. 