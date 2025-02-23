import logging
import json
from typing import List, Dict, Any
from openai import OpenAI
from pathlib import Path

from src.geneforge_config import Config

logger = logging.getLogger(__name__)

class LLMModule:
    def __init__(self, config: Config):
        """
        Initialize the LLM module with configuration.
        
        Args:
            config: Project configuration instance
        """
        self.config = config
        self._setup_client()
        
    def _setup_client(self):
        """Initialize the appropriate LLM client based on configuration."""
        if self.config.client_mode == "OPENAI":
            self.client = OpenAI(api_key=self.config.openai_api_key)
        elif self.config.client_mode == "DEEPSEEK":
            self.client = OpenAI(
                api_key=self.config.deepseek_api_key,
                base_url=self.config.deepseek_base_url
            )
        else:
            raise ValueError(f"Unsupported client mode: {self.config.client_mode}")
            
    def parse_spec(self, spec: str) -> Dict[str, Any]:
        """
        Parse a natural language specification into a formal circuit design.
        
        Args:
            spec: Natural language description of desired circuit
            
        Returns:
            dict: Formal circuit specification including:
                - Circuit type (e.g., 'logic_gate', 'delayed_reporter')
                - Input/output signals
                - Timing requirements
                - Constraints
        """
        logger.info("Parsing specification: %s", spec)
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert in synthetic biology circuit design. "
                          "Convert natural language specifications into formal circuit designs."
            },
            {
                "role": "user",
                "content": spec
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.default_model,
                messages=messages,
                temperature=0.1  # Low temperature for more deterministic outputs
            )
            
            # Parse the response into a structured format
            circuit_design = self._parse_llm_response(response.choices[0].message.content)
            logger.info("Successfully parsed specification into circuit design")
            return circuit_design
            
        except Exception as e:
            logger.error("Failed to parse specification: %s", str(e))
            raise
            
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Convert the LLM's text response into a structured circuit design.
        
        Args:
            response: Raw text response from LLM
            
        Returns:
            dict: Structured circuit design
        """
        try:
            # TODO: Implement proper parsing of LLM response
            # This is a placeholder implementation
            return {
                "circuit_type": "placeholder",
                "inputs": [],
                "outputs": [],
                "constraints": {},
                "raw_response": response
            }
        except Exception as e:
            logger.error("Failed to parse LLM response: %s", str(e))
            raise
            
    def generate_verilog(self, circuit_design: Dict[str, Any]) -> str:
        """
        Generate Verilog code from a circuit design.
        
        Args:
            circuit_design: Structured circuit specification
            
        Returns:
            str: Verilog code implementing the circuit
        """
        logger.info("Generating Verilog code for circuit")
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert in converting synthetic biology circuit designs "
                          "to Verilog code for use with genetic circuit design tools."
            },
            {
                "role": "user",
                "content": f"Convert this circuit design to Verilog: {json.dumps(circuit_design, indent=2)}"
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.default_model,
                messages=messages,
                temperature=0.1
            )
            
            verilog_code = response.choices[0].message.content
            logger.info("Successfully generated Verilog code")
            return verilog_code
            
        except Exception as e:
            logger.error("Failed to generate Verilog code: %s", str(e))
            raise 