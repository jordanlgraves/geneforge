from pathlib import Path
from src.tools.base_tool import Tool
import os
import dotenv
from typing import Dict, Any    
dotenv.load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

class SetParameterValueTool(Tool):
    name = "set_parameter_value"
    description = (
        "Bulk-update values inside the current parameter template for the loaded kinetic model. "
        "Supply an *updates* JSON object that mirrors the parameter template hierarchy. "
        "Missing keys are ignored.  "
        "Example with AraC and k_syn in the parameter template::\n\n"
        "{\"updates\": {\"species\": {\"AraC\": 1.0}, \"parameters\": {\"k_syn\": 0.05} } }"
    )
    parameters = {
        "type": "object",
        "properties": {
            "updates": {
                "type": "object",
                "description": "Nested mapping matching the parameter template (species/parameters → IDs). Values can be number or string.",
                "additionalProperties": True,
            }
        },
        "required": ["updates"],
    }

    def execute(self, updates: Dict[str, Any]):
        if not self.session_state.parameter_template:
             return {"error": "No model loaded and no parameter template initialized. Run `generate_model_from_natural_language` or upload and SBML file first."}

        template = self.session_state.parameter_template
        changes: Dict[str, Dict[str, Any]] = {}

        for section, inner in updates.items():
            if section not in template:
                continue  # silently ignore unknown top-level keys
            if not isinstance(inner, dict):
                continue
            for key, value in inner.items():
                if key not in template[section]:
                    continue  # unknown ID → ignore
                old = template[section][key]["value"]
                template[section][key]["value"] = value
                template[section][key]["source"] = "agent"
                changes.setdefault(section, {})[key] = {"old": old, "new": value}

        return {"success": True, "changes": changes, "parameter_template": template}

class GetParameterTemplateTool(Tool):
    name = "get_parameter_template"
    description = "Return the current kinetic model parameters stored in the session."
    parameters = {"type": "object", "properties": {}, "required": []}

    def execute(self):
        template = self.session_state.parameter_template
        if not template:
            return {"error": "No parameter template initialized yet. Generate a model with `generate_model_from_natural_language` or upload an SBML file first."}
        return {"success": True, "parameter_template": template}



class GenerateKineticModelFromNaturalLanguageTool(Tool):
    """
    https://github.com/kmaeda16/KinModGPT/
    """
    name = "generate_model_from_natural_language"
    description = "Create a kinetic model from a natural language description of biochemical reactions. This tool creates a kinetic model and returns the various parameters and species. The model is stored in the session state for further use."
    parameters = { "type": "object",
                   "properties": { 
                       "spec": 
                        {
                           "type": "string",
                           "description": "A description of the biochemical reactions to model (e.g. 'Protein P decays. The initial concentration is 1 uM.', 'mRNA_s32 is upregurated by Pg_s70_RNAP. Similarly, mRNA_DnaK and mRNA_FtsH are positively regulated by Ph_RNAP_s32. mRNA_Protein is transcribed without regulation. s32, FtsH, DnaK, and Pfold are translated from mRNA_s32, mRNA_FtsH, mRNA_DnaK, and mRNA_Protein, respectively. All the mRNAs (mRNA_s32, mRNA_DnaK, mRNA_FtsH, and mRNA_Protein) decay. s32, s32_DnaK, s32_FtsH, s32_DnaK_FtsH, FtsH, DnaK, Punfold_DnaK, Pfold, and Punfold decay. RNAP_s32 is degraded into RNAP. Similarly, Ph_RNAP_s32 is degraded into Ph and RNAP. D_RNAP_s32 is degraded into RNAP_D.')"
                        }, 
                    },
                   "required": ["spec"] }

    num_attempts = 3
    
    def execute(self, spec: str):
        from src.integrations.kinmod_gpt_integration import KineticModelingGPTIntegration
        import tellurium as te, libsbml, os, uuid

        gpt = KineticModelingGPTIntegration()
        messages = None
        previous_attempt_message = None
        antimony = None
        for attempt in range(self.num_attempts):
            try:
                antimony, messages = gpt.generate_kinetic_model(spec, 
                                                                previous_messages=messages, 
                                                                previous_attempt_message=previous_attempt_message)
                sbml_xml = te.antimonyToSBML(antimony)
                sbml_doc = libsbml.readSBMLFromString(sbml_xml)
                break
            except Exception as exc:
                if attempt == self.num_attempts - 1:
                    return {"error": f"Antimony→SBML conversion failed: {exc}"}
                else:
                    if antimony is None:
                        previous_attempt_message = f"The generated model from specification is invalid: Spec: {spec} \n\n due to error: {exc}."
                    else:
                        previous_attempt_message = f"The generated model from specification is invalid: Antimony: \n{antimony} \n\nSpec: {spec} \n\n due to error: {exc}."

        from src.simulation_utils import build_param_template
        template = build_param_template(sbml_doc)

        # Persist in session
        self.session_state.antimony  = antimony
        self.session_state.sbml_doc  = sbml_doc

        outdir = self.session_state.output_directory or Path("uploads")
        outdir.mkdir(exist_ok=True, parents=True)
        fn = outdir / f"model_{uuid.uuid4().hex[:8]}.xml"
        libsbml.writeSBMLToFile(sbml_doc, str(fn))
        self.session_state.sbml_file = fn
        self.session_state.initialise_parameter_template(template)
        # Track SBML file for download in UI
        try:
            self.session_state.add_generated_file(fn, label="Generated SBML model")
        except Exception:
            pass
        return {"success": True,
                "sbml_path": str(fn),
                "antimony": antimony,
                "parameter_template": template}

class RunKineticModelSimulationTool(Tool):
    name = "run_kinetic_model_simulation"
    description = "Simulate the currently loaded kinetic model with the current parameters."
    parameters = {"type": "object", "properties": {
        "start": {"type": "number", "description": "The start time of the simulation. default: 0.0"},
        "end": {"type": "number", "description": "The end time of the simulation. default: 100.0"},
        "steps": {"type": "integer", "description": "The number of steps in the simulation. default: 100"},
        "events": {
            "type": "array",
            "description": "A list of event objects to schedule. Each event must include 'time', 'species', and 'value'. Example: [{\"time\": 50, \"species\": \"P\", \"value\": 10}]",
            "items": {
                "type": "object",
                "properties": {
                    "time": {"type": "number"},
                    "species": {"type": "string"},
                    "value": {"type": "number"}
                },
                "required": ["time", "species", "value"]
            }
        }
    }, "required": []}

    def execute(self, start: float = 0.0, end: float = 100.0, steps: int = 100, events: list[dict] | None = None):
        from src.simulation_utils import run_kinetic_model_tellurium
        import uuid, os, json, io, matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import pandas as pd
        from pathlib import Path
        try:
            from openai import OpenAI
        except ImportError:
            OpenAI = None

        template = self.session_state.parameter_template
        result = run_kinetic_model_tellurium(
            self.session_state.sbml_doc,
            template.get('parameters', {}),
            template.get('species', {}),
            events=events,
            start=start,
            end=end,
            steps=steps,
        )

        outdir = self.session_state.output_directory or Path("uploads")
        outdir.mkdir(parents=True, exist_ok=True)

        # Create plot
        df = pd.DataFrame(result.tolist(), columns=result.colnames)
        if df.shape[1] >= 2:
            time_col = df.columns[0]
            df.set_index(time_col, inplace=True)
        fig, ax = plt.subplots(figsize=(6, 4))
        df.plot(ax=ax, legend=False)
        ax.set_xlabel("Time")
        ax.set_ylabel("Concentration / Value")
        plot_path = outdir / f"sim_{uuid.uuid4().hex[:8]}.png"
        fig.tight_layout()
        fig.legend()
        fig.savefig(plot_path, dpi=150)
        plt.close(fig)

        # Track generated plot
        try:
            self.session_state.add_generated_file(plot_path, label="Simulation plot")
        except Exception:
            pass

        # Optionally upload to OpenAI if client available
        file_id = None
        if OpenAI and os.getenv("OPENAI_API_KEY"):
            try:
                client = OpenAI()
                with open(plot_path, "rb") as fp:
                    up_file = client.files.create(file=fp, purpose="assistants")
                    file_id = up_file.id
            except Exception:
                file_id = None

        return {
            "success": True,
            "columns": result.colnames,
            "result": result.tolist(),
            "plot_path": str(plot_path),
            **({"file_id": file_id} if file_id else {}),
        }
