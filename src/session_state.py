import logging
from typing import Optional, Dict, Any, Literal
from pathlib import Path
import time
import os
from src.library.library_manager import LibraryManager
from src.library.part_library_customizer import get_promoter_dependencies

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
#  New design-specific container
# ------------------------------------------------------------------

try:
    from src.design_state import DesignState
except ImportError as exc:  # pragma: no cover – should never happen in production
    raise ImportError("DesignState module not found – did you forget to add it?") from exc

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
        
        # For OpenAI Assistants API
        self.assistant_id: Optional[str] = None
        self.thread_id: Optional[str] = None
        
        self.design_spec: Optional[str] = None  # Natural-language high-level specification
        self.verilog_code: Optional[str] = None  # Latest generated/updated Verilog source
        self.chat_rounds: int = 0  # Number of LLM-tool interaction rounds in current session

        self.output_directory: Optional[Path] = None

        # ------------------------------------------------------------------
        #  New design artefacts container
        # ------------------------------------------------------------------
        self.design_state: DesignState = DesignState()

        # SynBioHub client – lazy init in get_synbiohub_client()
        self._synbiohub_client = None

        # ------------------------------------------------------------------
        #  Chat history logging (optional, depends on env var)
        # ------------------------------------------------------------------
        try:
            from src.chat_history import ChatHistoryLogger
            self.chat_logger: Optional[ChatHistoryLogger] = ChatHistoryLogger()
            logger.info(f"Chat history will be saved to {self.chat_logger.get_path()}")
        except Exception as exc:
            # Do not crash the session if logging cannot be initialised
            logger.warning("Chat history logger not initialised – %s", exc)
            self.chat_logger = None

        try:
            # try setting the output directory from the env vars
            import dotenv
            
            dotenv.load_dotenv()
            out_folder_name = time.strftime("%Y%m%d_%H%M%S")
            self.output_directory = Path(os.getenv("SESSION_STATE_OUTDIR")) / out_folder_name
            os.makedirs(self.output_directory, exist_ok=True)
        except Exception as exc:
            logger.warning("Output directory not set – %s", exc)
            self.output_directory = None

    def from_dict(self, **kwargs):
        """Initialize the session state from a dictionary."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        if "library_manager" in kwargs:
            self.library_manager = LibraryManager()
            self.library_manager.select_library(kwargs["library_manager"]["current_library_id"])

        # Restore DesignState if serialised
        if "design_state" in kwargs and kwargs["design_state"] is not None:
            self.design_state = DesignState.from_dict(kwargs["design_state"])
        else:
            self.design_state = DesignState()

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
            "assistant_id": self.assistant_id,
            "thread_id": self.thread_id,
            "design_state": self.design_state.as_dict(),
        }

    def select_library(self, library_id: str) -> bool:
        """Selects a library and updates the session state."""
        logger.info(f"Session selecting library: {library_id}")
        success = self.library_manager.select_library(library_id)
        if success:
            # Update session state's copy of UCF data if needed
            self.current_ucf_data = self.library_manager.get_ucf_data()
            logger.info(f"Session state updated with UCF data for {library_id}")
            
            # Automatically calibrate ProD
            calibration_result = self.auto_calibrate_prod()
            if calibration_result.get("success"):
                logger.info(f"ProD calibrated successfully: {calibration_result}")
            else:
                logger.warning(f"ProD calibration failed or was skipped: {calibration_result.get('error')}")

        else:
            logger.error(f"Failed to select library {library_id} in session.")
        return success

    def query_libraries_by_organism(self, organism: str) -> bool:
        """Filter the available libraries by organism."""
        logger.info(f"Session filtering libraries by organism: {organism}")
        success = self.library_manager.filter_libraries_by_organism(organism)
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

        # Keep design_state in sync if user wishes
        self.design_state.verilog = verilog

    def get_verilog_code(self) -> Optional[str]:
        return self.verilog_code

    def get_chat_rounds(self) -> int:
        return self.chat_rounds

    def set_assistant(self, assistant_id: str, thread_id: str):
        """Store Assistant and Thread IDs for the session."""
        self.assistant_id = assistant_id
        self.thread_id = thread_id

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
        try:
            from src.tools.pro_d_integration import ProDIntegration
        except ImportError:
            logger.error("ProDIntegration not found. Please install ProD.")
            return {"success": False, "error": "ProDIntegration not found. Please install ProD."}
        
        import random, math

        ucf_data = self.get_current_ucf_data()
        if not ucf_data:
            return {"success": False, "error": "No UCF loaded"}

        # Collect promoters with ymax parameter from their models
        refs = []
        promoter_parts = [p for p in ucf_data if p.get("collection") == "parts" and p.get("type") == "promoter"]

        for part in promoter_parts:
            promoter_name = part.get("name")
            if not promoter_name:
                continue

            dependencies = get_promoter_dependencies(ucf_data, promoter_name)
            model = next(iter(dependencies.get("models", [])), None)

            if not model:
                continue

            # Find ymax parameter in the model
            for p in model.get("parameters", []):
                if p.get("name", "").lower() in ("ymax", "y_max"):
                    try:
                        ymax_val = float(p.get("value"))
                    except (TypeError, ValueError):
                        continue
                    
                    seq = part.get("dnasequence") or part.get("sequence")
                    if seq and ymax_val > 0:
                        refs.append({"sequence": seq, "ymax": ymax_val, "promoter": promoter_name})
                    break # stop after first ymax match in model

        if len(refs) < min_refs:
            return {
                "success": False,
                "error": f"Only found {len(refs)} promoters with valid ymax models; need {min_refs} to calibrate.",
            }

        random.shuffle(refs)
        refs = refs[:max_refs]

        # Get (or create) ProDIntegration attached to this session
        if not hasattr(self, "prod_integration"):
            setattr(self, "prod_integration", ProDIntegration())
        prod = getattr(self, "prod_integration")

        try:
            result = prod.calibrate_rpu_scale(refs)
            # Add the promoter names to the result for better logging
            if result.get("success"):
                result["reference_promoters"] = [r["promoter"] for r in refs]
            return result
        except Exception as e:
            logger.warning("ProD calibration failed: %s", e)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  SynBioHub integration
    # ------------------------------------------------------------------

    def get_synbiohub_client(self):
        """Return (and lazily create) a SynBioHubClient bound to this session."""
        if self._synbiohub_client is None:
            try:
                from src.tools.synbiohub_integration import SynBioHubClient
                self._synbiohub_client = SynBioHubClient()
            except Exception as exc:
                logger.error("Failed to initialise SynBioHub client: %s", exc)
                raise
        return self._synbiohub_client

    # ------------------------------------------------------------------
    #  Parameter template helpers
    # ------------------------------------------------------------------

    def initialise_parameter_template(self, template: Dict[str, Any]):
        """Attach a freshly generated parameter *template* to the DesignState."""
        self.design_state.parameter_template = template
        self.design_state.last_editor = None

    def set_parameter_value(
        self,
        section: Literal["species", "parameters"],
        key: str,
        value: Any,
        unit: str | None = None,
        source: str | None = None,
        editor: Literal["agent", "user"] = "agent",
    ) -> None:
        """Update a single entry inside the parameter template.

        Parameters
        ----------
        section
            Either ``"species"`` or ``"parameters"``.
        key
            The ID inside that section (e.g. *AraC* or *deg::P1*).
        value
            Numeric or string value to assign.
        unit
            New unit string. If *None* the existing unit is kept.
        source
            Provenance tag (BNID, DOI…). If *None* the existing source is kept.
        editor
            Who made the change – used for conflict handling.
        """
        tmpl = self.design_state.parameter_template.setdefault(section, {})
        entry = tmpl.setdefault(key, {"value": None, "unit": None, "source": None})
        entry["value"] = value
        if unit is not None:
            entry["unit"] = unit
        if source is not None:
            entry["source"] = source

        self.design_state.last_editor = editor

    # ------------------------------------------------------------------
    #  SBML file helper
    # ------------------------------------------------------------------

    def set_sbml_file(self, path: str | Path):
        """Persist the path of the SBML file uploaded by the user.

        The path is stored inside the session-scoped ``DesignState`` so that
        downstream tools (e.g. parameter extraction, simulations) can access
        it without needing to pass the filename around explicitly.
        """
        try:
            self.design_state.sbml_file = Path(path)
        except Exception as exc:
            logger.error("Failed to set SBML file path: %s", exc)
            raise

    # Add methods to update and retrieve other state variables as needed
    # e.g., set_custom_ucf_path, get_cello_results, etc. 