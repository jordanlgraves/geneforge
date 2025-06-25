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

class KineticModelingGPTIntegration:
    def __init__(self):
        self.sys_prompt = get_kinmod_prompt()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_kinetic_model(self, spec: str):
        messages = [
            {
                "role": "system",
                "content": self.sys_prompt,
            },
            {"role": "user", "content": spec},
        ]
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=1,
        )
        antimony_model = clean_GPT_output(response.choices[0].message.content)
        return antimony_model
    
    