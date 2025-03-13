# GeneForge: Automated Genetic Circuit Design and Optimization

This repository contains an the foundation work for developing an automated AI-driven system to design and optimize genetic circuits.

## Overview

To core features of the system include a master LLM-agent which plans and orchestrates the design of a genetic circuit. This agent deploys worker agents to handle different parts of the design process. For example, a cello design agent is responsible for generating verilog, managing a UCF library, and running the cello program. Another analysis agent is responsible for parsing the results of the cello program and providing feedback to the design agent. Each agent is given it's own file to manage internal memory and reasoning streaming. Each agent is also provided with the user's initial prompt and design specification. The master agent is responsible for coordinating the work of the other agents and for providing feedback to the user as well as deciding on the next steps in the design process. 

## Examples and use cases:
Examples of prompts cane b found in `examples_and_prompts`. These range from simple to complex and are designed to guide the implementation of this project and outline the vision of the system.

## Agents:

Listed below are examples of the agents that will be used to design and optimize genetic circuits.

Master Agent:

1. **Planning**: Plans the design of the genetic circuit.
2. **Coordination**: Coordinates the work of the other agents.
3. **Feedback**: Provides feedback to the user.

Cello Designer:

1. **File Selection**: Automatically selects appropriate UCF, input, and output files based on user requests.
2. **Part Selection**: Selects appropriate genetic parts (gates, sensors, reporters) based on user requests.
3. **Verilog Generation**: Generates Verilog code based on the selected parts and user requirements.
4. **Explanations**: Provides detailed explanations for why specific files and parts were selected.

Promoter Optimizer:

1. **Sequence Analysis**: Analyzes the sequence of the promoter to determine it's strength.
2. **Optimization**: Optimizes the sequence of the promoter for the desired expression level.
3. **Explanations**: Provides numerical values for the strength of the promoter.

## Tool Use

Several tools will be used to design and optimize genetic circuits. These tools will be wrapped by an integration layer which will be used by the agents. Listed below are the key tools that will be used:

Cello:
- Includes tools to search through as well as manage a custom UCF library. This enables the agent to select appropriate parts for the design.
- Includes a tool to run the cello program and capture the output.
- Includes a tool to parse the results of the cello program, returning various metrics and data.

Deepseed:
- A tool for generating, optimizing and predicting the performance of promoters.

UCF Library Manager:
- Scans directories for JSON files
- Extracts metadata from each file
- Determines file types based on filename patterns
- Validates file selections for compatibility
- Finds alternative files if the selected files are not valid
- Allows the agent to select appropriate files based on the user's request (e.g. "I want a **NOT gate** for **E. coli**")


## Retrieval Augmented Generation
While not yet implemented, RAG will be used to provide the agents with access to a wide range of information. This will give the planning agent the ability to search through scientific literature to find relevant information to assist in the design process.

## Reinforcement learning
Another core feature of the system is it's amenability to reinforcement learning. The initial reinforcement learning goal is to establish successful outputs from a wide range of prompts with high temperature values to ensure a wide range of outputs. Successful outputs, determined using in-silico validation/simulation, will be used as training data to improve the agents performance.

## Integrations

Currently, each integration is managed separately in the `ext_repos` directory. My current workflow adds the individual repos to the `PYTHONPATH` and then imports them in the individual integration files. This allows me to use the tools in the rest of the project. This will need to be revisited in the future to prevent dependency conflicts.

## Examples

Example scripts are provided in the `examples` directory. These range from simple integration, library management, to system level orchestration.


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.




