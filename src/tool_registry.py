# tools/functions.py

import os
from typing import Dict, List, Any, ClassVar, Optional
import src.library.cello_utils as cello_utils
import logging
from src.session_state import SessionState
import traceback
import logging
import inspect


from langchain_community.tools import ReadFileTool
from langchain_core.utils.function_calling import convert_to_openai_function

import dotenv
dotenv.load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Register in existing TOOL_REGISTRY and expose schemas
# ---------------------------------------------------------------------------
from src.tools.cello_tools import *
from src.tools.promoter_tools import *
from src.tools.rbs_tools import *
from src.tools.synbiohub_tools import *
from src.tools.utility_tools import *
from src.tools.kinetic_model_tools import *
from src.tools.biomodel_tools import *

TOOL_REGISTRY = {}

# Cello design tools
TOOL_REGISTRY[DescribeAvailableLibrariesTool.name] = DescribeAvailableLibrariesTool
TOOL_REGISTRY[SelectLibraryTool.name] = SelectLibraryTool
TOOL_REGISTRY[QueryLibrariesByOrganismTool.name] = QueryLibrariesByOrganismTool
TOOL_REGISTRY[ListPromotersTool.name] = ListPromotersTool
TOOL_REGISTRY[ListRepressorsTool.name] = ListRepressorsTool
TOOL_REGISTRY[ListInputSensorsTool.name] = ListInputSensorsTool
TOOL_REGISTRY[GetDnaPartByNameTool.name] = GetDnaPartByNameTool
TOOL_REGISTRY[ListTerminatorsTool.name] = ListTerminatorsTool
TOOL_REGISTRY[AddPromoterVariantTool.name] = AddPromoterVariantTool
TOOL_REGISTRY[RemovePromoterTool.name] = RemovePromoterTool
TOOL_REGISTRY[GetCelloLibraryStatusTool.name] = GetCelloLibraryStatusTool
TOOL_REGISTRY[CreateCustomUcfTool.name] = CreateCustomUcfTool
TOOL_REGISTRY[CreateCustomInputSensorsFileTool.name] = CreateCustomInputSensorsFileTool
TOOL_REGISTRY[DesignWithCelloTool.name] = DesignWithCelloTool
TOOL_REGISTRY[EvaluateCircuitPerformanceTool.name] = EvaluateCircuitPerformanceTool

# Verilog generation tools
TOOL_REGISTRY[GenerateVerilogToolLLM.name] = GenerateVerilogToolLLM

# RBS Calculator tools
TOOL_REGISTRY[PredictInitiationRateWithRbsCalculatorTool.name] = PredictInitiationRateWithRbsCalculatorTool
TOOL_REGISTRY[DesignRbsWithRbsCalculatorTool.name] = DesignRbsWithRbsCalculatorTool

# Promoter design/generation tools
TOOL_REGISTRY[GeneratePromoterLibraryFromSpacerTool.name] = GeneratePromoterLibraryFromSpacerTool
TOOL_REGISTRY[GeneratePromoterLibraryFromPromoterTool.name] = GeneratePromoterLibraryFromPromoterTool
TOOL_REGISTRY[EstimatePromoterStrengthWithProDTool.name] = EstimatePromoterStrengthWithProDTool
TOOL_REGISTRY[GetSpacerFromPromoterTool.name] = GetSpacerFromPromoterTool

# Register SynBioHub tools
TOOL_REGISTRY[SynBioHubSearchTool.name] = SynBioHubSearchTool
TOOL_REGISTRY[SynBioHubDownloadPartTool.name] = SynBioHubDownloadPartTool
TOOL_REGISTRY[SynBioHubSubmitTool.name] = SynBioHubSubmitTool
TOOL_REGISTRY[SynBioHubSequenceSearchTool.name] = SynBioHubSequenceSearchTool
TOOL_REGISTRY[SynBioHubGetRelatedTool.name] = SynBioHubGetRelatedTool

# Kinetic modeling tools
TOOL_REGISTRY[SetParameterValueTool.name] = SetParameterValueTool
TOOL_REGISTRY[GetParameterTemplateTool.name] = GetParameterTemplateTool
TOOL_REGISTRY[GenerateKineticModelFromNaturalLanguageTool.name] = GenerateKineticModelFromNaturalLanguageTool
TOOL_REGISTRY[RunKineticModelSimulationTool.name] = RunKineticModelSimulationTool   
TOOL_REGISTRY[SetKineticModelFromSBMLTool.name] = SetKineticModelFromSBMLTool

# Utility tools
TOOL_REGISTRY[ScientificSearchTool.name] = ScientificSearchTool
TOOL_REGISTRY[ToolDocsQueryTool.name] = ToolDocsQueryTool
TOOL_REGISTRY[TranslateDnaTool.name] = TranslateDnaTool
TOOL_REGISTRY[GcContentTool.name] = GcContentTool
TOOL_REGISTRY[SearchBioNumbersTool.name] = SearchBioNumbersTool
TOOL_REGISTRY[ReportAnswerTool.name] = ReportAnswerTool
TOOL_REGISTRY[SequenceSimilarityTool.name] = SequenceSimilarityTool

# BioModels tools
TOOL_REGISTRY[DownloadBioModelSBMLTool.name] = DownloadBioModelSBMLTool

# Generate OpenAI function schemas from tools
_tool_schemas = [
    convert_to_openai_function(ReadFileTool()),
    *[tool_class.get_openai_schema() for tool_class in TOOL_REGISTRY.values()]
]
tool_functions = [{"type": "function", "function": schema} for schema in _tool_schemas]

class ToolIntegration:
    def __init__(self, session_state: SessionState, tool_registry: dict = TOOL_REGISTRY):
        self.session_state = session_state
        self.tools = {
            tool_name: tool_class(session_state) 
            for tool_name, tool_class in tool_registry.items()
        }
        self.tool_functions = tool_functions
        

    def call_tool_function(self, function_name, function_args):
        """
        Call a tool function with the provided arguments.
        
        Args:
            function_name: Name of the function to call
            function_args: Arguments for the function
            
        Returns:
            Result of the function call
        """
        # Handle ReadFileTool separately as it's from langchain
        if function_name == "read_file":
            try:
                result = ReadFileTool().run(function_args.get("file_path", function_args))
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": f"Error reading file: {e}"}
        
        # Use the tool from the registry if available
        if function_name in self.tools:
            tool_instance = self.tools[function_name]
            try:
                return tool_instance.execute(**function_args)
            except TypeError as e:
                if "missing" in str(e) and "required positional argument" in str(e):
                    sig = inspect.signature(tool_instance.execute)
                    required = [
                        p.name for p in sig.parameters.values()
                        if p.default is inspect.Parameter.empty and p.name != 'self'
                    ]
                    missing = [p for p in required if p not in function_args]
                    return {
                        "error": (
                            f"Invalid arguments for tool '{function_name}'. "
                            f"Missing required arguments: {missing}. "
                            f"Please provide all required arguments: {required}."
                        )
                    }
                else:
                    # Re-raise other TypeErrors or unexpected errors
                    raise e
        
        # If no tool found, return error
        return {"error": f"No such function: {function_name}"}
    
if __name__ == "__main__":
    for tool in tool_functions:
        print(tool["function"]["name"])
        print(tool["function"]["description"])
        print(tool["function"]["parameters"])
        print("--------------------------------")