from src.tools.base_tool import Tool
from typing import ClassVar, Dict, Any, Optional, List
import dotenv
import os
dotenv.load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

# RBS Calculator Tools
class PredictInitiationRateWithRbsCalculatorTool(Tool):
    name = "predict_initiation_rate_with_rbs_calculator"
    description = (
        "Predict translation initiation metrics (ΔG_total, expression level) for an "
        "mRNA sequence using the Salis-lab RBS Calculator."
    )
    parameters = {
        "type": "object",
        "properties": {
            "mrna_sequence": {
                "type": "string",
                "description": "Full mRNA (or DNA) sequence containing at least one start codon.",
            },
            "start_range": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Optional [start, end] indices delimiting the scan window for start codons (0-based).",
            },
            "name": {"type": "string", "description": "Optional identifier for the sequence."},
            "verbose": {"type": "boolean", "description": "Set to true to print the legacy calculator output."},
        },
        "required": ["mrna_sequence"],
    }

    def execute(
        self,
        mrna_sequence: str,
        start_range: Optional[list] = None,
        name: Optional[str] = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        # RBS Calculator integration
        from src.integrations.rbs_calculator_integration import RBSCalculatorIntegration

        # Convert start_range to tuple[int, int] if provided.
        sr_tuple = tuple(start_range) if start_range else None  # type: ignore[arg-type]
        return RBSCalculatorIntegration.predict_initiation_rate(
            mrna_sequence=mrna_sequence,
            start_range=sr_tuple,  # type: ignore[arg-type]
            name=name,
            verbose=verbose,
        )


class DesignRbsWithRbsCalculatorTool(Tool):
    name = "design_rbs_with_rbs_calculator"
    description = (
        "Design a synthetic ribosome-binding site achieving a desired translation initiation rate "
        "or ΔG_total using the Salis-lab Monte Carlo optimiser."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pre_sequence": {"type": "string", "description": "Sequence upstream of the RBS (5′ UTR)."},
            "post_sequence": {"type": "string", "description": "Sequence starting with the start codon and into the CDS."},
            "target_tir": {"type": "number", "description": "Desired translation initiation rate (arbitrary units)."},
            "target_delta_g": {"type": "number", "description": "Desired ΔG_total (kcal/mol)."},
            "max_iterations": {"type": "integer", "description": "Maximum optimisation iterations.", "default": 10000},
            "verbose": {"type": "boolean", "description": "Return verbose legacy output."},
        },
        "required": ["pre_sequence", "post_sequence"],
    }

    def execute(
        self,
        pre_sequence: str,
        post_sequence: str,
        target_tir: Optional[float] = None,
        target_delta_g: Optional[float] = None,
        max_iterations: int = 10000,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        # RBS Calculator integration
        from src.integrations.rbs_calculator_integration import RBSCalculatorIntegration

        return RBSCalculatorIntegration.design_rbs(
            pre_sequence=pre_sequence,
            post_sequence=post_sequence,
            target_tir=target_tir,
            target_delta_g=target_delta_g,
            max_iterations=max_iterations,
            verbose=verbose,
        )
