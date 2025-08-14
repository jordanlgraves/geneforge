import logging
from typing import Optional, Dict, Any, Literal
from pathlib import Path
import time
import os
from src.library.cello_library import CelloLibrary
from src.library.cello_utils import get_promoter_dependencies
import copy

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
#  New design-specific container
# ------------------------------------------------------------------

class SessionState:
    """
    Manages the state for a single user design session.

    This includes the selected library, custom UCF data,
    intermediate results, etc.
    """
    def __init__(self):
        logger.debug("Initializing new session state.")
        # Initialize CelloLibrary once per session
        self.cello_library = CelloLibrary()
        self.cello_results: Optional[Dict[str, Any]] = None
        
        # For OpenAI Assistants API
        self.assistant_id: Optional[str] = None
        self.thread_id: Optional[str] = None
        
        self.design_spec: Optional[str] = None  # Natural-language high-level specification
        self.verilog_code: Optional[str] = None  # Latest generated/updated Verilog source
        self.chat_rounds: int = 0  # Number of LLM-tool interaction rounds in current session

        self.output_directory: Optional[Path] = None

        # ------------------------------------------------------------------
        #  Chat history logging (optional, depends on env var)
        # ------------------------------------------------------------------
        try:
            from src.chat_history import ChatHistoryLogger
            self.chat_logger: Optional[ChatHistoryLogger] = ChatHistoryLogger()
            logger.debug(f"Chat history will be saved to {self.chat_logger.get_path()}")
        except Exception as exc:
            # Do not crash the session if logging cannot be initialised
            logger.warning("Chat history logger not initialised – %s", exc)
            self.chat_logger = None

        try:
            #  Determine a unique output directory for *this* session.  If the
            #  environment variable ``SESSION_STATE_OUTDIR`` is set we treat it
            #  as the *root* folder; otherwise we default to
            #  ``outputs/session_runs``.  A timestamp sub-directory guarantees
            #  that concurrent or subsequent sessions never overwrite each
            #  other.

            import dotenv

            dotenv.load_dotenv()

            # Root folder can be customised via env-var; fall back to project
            # relative path.
            root_dir = os.getenv("SESSION_STATE_OUTDIR") or "outputs/session_runs"

            # Use YYYYMMDD_HHMMSS so lexical order matches chronological order
            timestamp = time.strftime("%Y%m%d_%H%M%S")

            self.output_directory = Path(root_dir) / timestamp

            # Ensure the directory exists
            os.makedirs(self.output_directory, exist_ok=True)
        except Exception as exc:
            # Should rarely happen but keep the previous behaviour as a safety
            logger.warning("Output directory not initialised – %s", exc)
            self.output_directory = None

        # ------------------------------------------------------------------
        #  Generated artefacts (plots, SBML files, data tables, etc.) tracked
        #  for convenient download links in the UI.
        # ------------------------------------------------------------------
        self.generated_files: list[dict[str, str]] = []  # each: {path, label}

        # ------------------------------------------------------------------
        #  Design artefacts (previously DesignState)
        # ------------------------------------------------------------------

        self.sbol_file: Optional[Path] = None
        self.sbml_file: Optional[Path] = None
        self.sbml_doc = None  # libSBML document – keep type generic to avoid heavy import
        self.antimony: Optional[str] = None  # textual Antimony representation, if any

        # Kinetic-model parameter template and provenance
        self.parameter_template: Dict[str, Any] = {}
        self.last_editor: Optional[Literal["agent", "user"]] = None

        # Initialize _history attribute
        self._history = []

        # SynBioHub client – lazy init
        self._synbiohub_client = None

    def from_dict(self, **kwargs):
        """Restore the session state from a serialised dict representation."""
        for key, value in kwargs.items():
            # Special-case nested library_manager info
            if key == "library_manager" and isinstance(value, dict):
                self.cello_library = CelloLibrary()
                if value.get("current_library_id"): 
                    self.cello_library.select_library(value.get("current_library_id"))
                continue

            # Normal flat attributes
            setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the session state to a dictionary."""
        return {
            "cello_library": self.cello_library.to_dict(),
            "cello_results": self.cello_results,
            "verilog_code": self.verilog_code,
            "design_spec": self.design_spec,
            "chat_rounds": self.chat_rounds,
            "assistant_id": self.assistant_id,  
            "thread_id": self.thread_id,
            "parameter_template": self.parameter_template,
            "sbol_file": str(self.sbol_file) if self.sbol_file else None,
            "sbml_file": str(self.sbml_file) if self.sbml_file else None,
            "sbml_doc": None,  # not serialisable; omit for now
            "antimony": self.antimony,
        }

    def select_library(self, library_id: str) -> bool:
        """Selects a library and updates the session state."""
        logger.debug(f"Session selecting library: {library_id}")
        success = self.cello_library.select_library(library_id)
        if success:
            # Update session state's copy of UCF data if needed
            self.cello_library.user_constraints = self.cello_library.get_ucf_data()
            logger.debug(f"Session state updated with UCF data for {library_id}")
            
            # Automatically calibrate ProD
            calibration_result = self.auto_calibrate_prod()
            if calibration_result.get("success"):
                logger.debug(f"ProD calibrated successfully: {calibration_result}")
            else:
                logger.warning(f"ProD calibration failed or was skipped: {calibration_result.get('error')}")

        else:
            logger.error(f"Failed to select library {library_id} in session.")
        return success

    def query_libraries_by_organism(self, organism: str) -> bool:
        """Filter the available libraries by organism."""
        logger.debug(f"Session filtering libraries by organism: {organism}")
        success = self.cello_library.filter_libraries_by_organism(organism)
        return success

    def get_cello_library(self) -> CelloLibrary:
        """Returns the LibraryManager instance for this session."""
        return self.cello_library

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
            from src.integrations.pro_d_integration import ProDIntegration
        except ImportError:
            logger.error("ProDIntegration not found. Please install ProD.")
            return {"success": False, "error": "ProDIntegration not found. Please install ProD."}
        
        import random, math

        ucf_data = self.cello_library.user_constraints
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
                from src.integrations.synbiohub_integration import SynBioHubClient
                self._synbiohub_client = SynBioHubClient()
            except Exception as exc:
                logger.error("Failed to initialise SynBioHub client: %s", exc)
                raise
        return self._synbiohub_client

    # ------------------------------------------------------------------
    #  Parameter template helpers
    # ------------------------------------------------------------------

    def initialise_parameter_template(self, template: Dict[str, Any]):
        """Attach a freshly generated parameter template (species/parameters)."""
        self.parameter_template = template or {}
        self.last_editor = None

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
        template = self.parameter_template.setdefault(section, {})
        entry = template.setdefault(key, {"value": None, "unit": None, "source": None})
        entry["value"] = value
        if unit is not None:
            entry["unit"] = unit
        if source is not None:
            entry["source"] = source

        self.last_editor = editor

    # ------------------------------------------------------------------
    #  SBML file helper
    # ------------------------------------------------------------------

    def set_sbml_file(self, path: str | Path):
        """Persist the path of an SBML file uploaded or generated during the session."""
        try:
            self.sbml_file = Path(path)
        except Exception as exc:
            logger.error("Failed to set SBML file path: %s", exc)
            raise

    # ------------------------------------------------------------------
    #  Generated-file helpers
    # ------------------------------------------------------------------

    def add_generated_file(self, path: str | Path, label: str | None = None):
        """Register *path* so the UI can offer a download button.

        Parameters
        ----------
        path
            Location on disk.
        label
            Optional human-readable label (defaults to filename).
        """
        p = Path(path)
        if not p.exists():
            logger.warning("Generated file not found: %s", p)
            return
        # Avoid duplicates
        for entry in self.generated_files:
            if entry.get("path") == str(p):
                return  # already tracked
        self.generated_files.append({"path": str(p), "label": label or p.name})


    def record_snapshot(self, msg_index: int | None = None):
        """Record a snapshot of the current session state.

        Parameters
        ----------
        msg_index
            Index of the chat message this snapshot corresponds to. When every
            chat message triggers exactly one snapshot this lets downstream
            scorers map *state n* ⇄ *message n* unambiguously. For snapshots
            created outside the chat flow (rare) this can be left *None*.
        """
        snapshot = {
            "timestamp": time.time(),
            "msg_index": msg_index,
            "state": copy.deepcopy(self.to_dict()),
        }
        self._history.append(snapshot)

    def get_history(self):
        """Get the history of session snapshots."""
        return self._history 
    
    def write_file(self, content: str, path: str):
        """Write a file to the output directory."""
        p = Path(self.output_directory) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p
    
    def read_file(self, path: str):
        """Read a file from the output directory."""
        p = Path(path)
        if not p.exists():
            p = Path(self.output_directory) / path
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        return p.read_text()