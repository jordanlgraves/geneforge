# main.py

import logging
import sys
from pathlib import Path

from src.core.llm import LLMModule
from src.core.knowledge_graph import KnowledgeBase
from src.integrations.cello import CelloIntegration
from src.integrations.ibiosim import iBioSimIntegration
# from src.core.optimization import RLOptimizer
from src.geneforge_config import Config
from src.core.logging_config import setup_logging

logger = logging.getLogger(__name__)

def main():
    try:
        # Load configuration and setup logging
        config = Config()
        setup_logging(config)
        
        logger.info("Initializing GeneForge components")
        
        # Initialize components
        llm = LLMModule(config)
        knowledge_graph = KnowledgeBase(config)
        cello = CelloIntegration(config)
        ibiosim = iBioSimIntegration(config)
        optimizer = RLOptimizer(config)

        # Process specification
        spec_file = Path("examples/spec_delayed_fluorescence.txt")
        if not spec_file.exists():
            raise FileNotFoundError(f"Specification file not found: {spec_file}")
            
        with open(spec_file, 'r') as f:
            user_spec = f.read().strip()
        
        logger.info("Processing specification: %s", user_spec)
        
        # 1. Parse spec using LLM
        circuit_design = llm.parse_spec(user_spec)
        logger.info("Generated circuit design")
        
        # 2. Query Knowledge Graph for parts and constraints
        available_parts = knowledge_graph.query_parts(circuit_design)
        logger.info("Retrieved available parts")
        
        # 3. Generate circuit using Cello
        cello_output = cello.design_circuit(circuit_design, available_parts)
        logger.info("Generated circuit implementation")
        
        # 4. Simulate using iBioSim
        simulation_results = ibiosim.simulate(cello_output)
        logger.info("Completed circuit simulation")
        
        # 5. Optimize if needed
        if not optimizer.meets_requirements(simulation_results, user_spec):
            logger.info("Initial design does not meet requirements, starting optimization")
            optimized_design = optimizer.optimize(circuit_design, simulation_results)
            # Repeat steps 3-4 with optimized design
            cello_output = cello.design_circuit(optimized_design, available_parts)
            simulation_results = ibiosim.simulate(cello_output)
            logger.info("Completed optimization and verification")
            
        logger.info("Circuit design process completed successfully")
        return 0
        
    except Exception as e:
        logger.error("Fatal error in main process: %s", str(e), exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
