from src.prompt_manager import get_kinmod_prompt
from openai import OpenAI  # Local import to avoid mandatory dependency at import time
import os
from src.llm_module import get_llm_client
from src.simulate.param_template import build_param_template
import libsbml
import tellurium as te

def clean_GPT_output(GPT_output):
        cleaned = ''
        for line in GPT_output.splitlines():
            line = line.strip()
            if line != '' and ( line[0] == '-' or line[0] == '•' or line[0] == '*'):
                cleaned += line[1:].strip() + '\n'
            if ':' in line:
                line = line.split(':')[-1]
        return(cleaned)

# -----------------------------
# Utility helpers
# -----------------------------

def _ensure_parameters_initialized(antimony_model: str) -> str:
    """Return an Antimony string where every *global* parameter has
    an explicit numeric value.  Some LLM-generated models reference
    parameters (e.g., stimulus or inducer levels) without assigning a
    value.  RoadRunner requires each global parameter to be
    initialised, otherwise ``loadSBMLModel`` raises a RuntimeError.

    The routine converts the Antimony into SBML, walks through all
    global parameters and assigns a default value of **0.0** whenever
    a value is missing.  If any modifications are applied, the updated
    SBML is converted back to Antimony and returned.  Local parameters
    inside kinetic laws are ignored because they always carry a value
    when present in Antimony.
    """

    # Convert → SBML
    try:
        sbml_xml = te.antimonyToSBML(antimony_model)
    except Exception as exc:
        # If the antimony cannot be parsed we propagate the exception –
        # the caller will surface a useful error message.
        raise exc

    doc = libsbml.readSBMLFromString(sbml_xml)
    model = doc.getModel()

    patched = False
    for param in model.getListOfParameters():
        if not param.isSetValue():
            param.setValue(0.0)
            patched = True

    if not patched:
        # Nothing to do – return original model.
        return antimony_model

    # Convert back → Antimony after patching.
    sbml_str = libsbml.writeSBMLToString(doc)
    return te.sbmlToAntimony(sbml_str)

class KineticModelingGPTIntegration:
    def __init__(self):
        self.sys_prompt = get_kinmod_prompt()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_kinetic_model(self, spec: str, previous_messages: list[dict] = None, previous_attempt_message: str = None):
        messages = [
            {
                "role": "system",
                "content": self.sys_prompt,
            },
        ]
        if previous_messages is not None:
            messages.extend(previous_messages)
        if previous_attempt_message is not None:
            messages.append({"role": "user", "content": previous_attempt_message + ". Please try again, taking into account the error." + "\n\n" + spec})
        else:
            messages.append({"role": "user", "content": spec})
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=1,
        )
        antimony_model = clean_GPT_output(response.choices[0].message.content)

        # Ensure that the model is RoadRunner-friendly by explicitly
        # initialising all global parameters.
        antimony_model = _ensure_parameters_initialized(antimony_model)

        return antimony_model, messages
    
    