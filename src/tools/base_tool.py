from typing import ClassVar, Dict, Any

from src.session_state import SessionState

class Tool:
    """Base class for all tools.
    
    MCP Schema:
    {
        "name": string;          // Unique identifier for the tool
        "description": string;  // Human-readable description
        "inputSchema": {         // JSON Schema for the tool's parameters
            "type": "object",
            "properties": { ... }  // Tool-specific parameters
        },
        "annotations": {        // Optional hints about tool behavior
            "title": string;      // Human-readable title for the tool
            "readOnlyHint": boolean;    // If true, the tool does not modify its environment
            "destructiveHint": boolean; // If true, the tool may perform destructive updates
            "idempotentHint": boolean;  // If true, repeated calls with same args have no additional effect
            "openWorldHint": boolean;   // If true, tool interacts with external entities
    } 
    
    """
    # Class variables
    name: ClassVar[str] = None
    description: ClassVar[str] = None
    parameters: ClassVar[Dict[str, Any]] = None
    annotations: ClassVar[Dict[str, Any]] = None

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

    @classmethod
    def get_mcp_schema(cls) -> Dict[str, Any]:
        """Generate the MCP schema for this tool.
        
        https://modelcontextprotocol.io/docs/concepts/tools
        {
            "name": string;          // Unique identifier for the tool
            "description": string;  // Human-readable description
            "inputSchema": {         // JSON Schema for the tool's parameters
                "type": "object",
                "properties": { ... }  // Tool-specific parameters
            },
            "annotations": {        // Optional hints about tool behavior
                "title": string;      // Human-readable title for the tool
                "readOnlyHint": boolean;    // If true, the tool does not modify its environment
                "destructiveHint": boolean; // If true, the tool may perform destructive updates
                "idempotentHint": boolean;  // If true, repeated calls with same args have no additional effect
                "openWorldHint": boolean;   // If true, tool interacts with external entities
        } 
        
        
        """
        return {
            "name": cls.name,
            "description": cls.description,
            "inputSchema": cls.parameters,
            "annotations": cls.annotations,
        }