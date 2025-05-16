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

    # Add methods to update and retrieve other state variables as needed
    # e.g., set_custom_ucf_path, get_cello_results, etc. 