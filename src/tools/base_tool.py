from typing import ClassVar, Dict, Any

from src.session_state import SessionState

class Tool:
    """Base class for all tools."""
    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[Dict[str, Any]]

    def __init__(self, session_state: SessionState):
        self.session_state = session_state
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool function with provided arguments."""
        raise NotImplementedError("Tool subclasses must implement execute method")
    
    @classmethod
    def get_openai_schema(cls) -> Dict[str, Any]:
        """Generate the OpenAI function schema for this tool."""
        return {
            "name": cls.name,
            "description": cls.description,
            "parameters": cls.parameters,
        }
