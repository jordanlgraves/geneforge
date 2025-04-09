# GeneForge: Automated Genetic Circuit Design and Optimization

This repository contains an the foundation work for developing an automated AI-driven system to design and optimize genetic circuits.

## Overview

To core features of the system include a master LLM-agent which plans and orchestrates the design of a genetic circuit. The agent uses tool calls handle different parts of the design process. For example, a cell tool is used to assist with circuit simulation. The agent is able to generate verilog and manage a UCF, input and output library using other tools, allowing it to run the program with custom parts and logic. The agent also uses retrieval augmented generation, allowing it to search through scientific literature to find relevant information to assist in the design process. Other tools allow for predicting and optimizing genetic parts and sequences. The is should be used by providing an initial prompt and design specification.

**State Management:** The system uses a `SessionState` object to manage the context (like the currently selected library, custom UCF files, etc.) across multiple tool calls within a single user design request, ensuring consistency throughout the workflow.

## Examples and use cases:
Examples of prompts can be found in `examples_and_prompts`. These range from simple to complex to aspirational and are designed to guide the implementation of this project and outline the vision of more sophisticated systems.


## Tool Use

Several tools will be used to design and optimize genetic circuits. These tools are be wrapped in an integration layer which will be used by the agents. Listed below are some of the key tools that will be used:

Cello:
- Includes tools to search through as well as manage a custom UCF library. This enables the agent to select appropriate parts for the design.
- Includes a tool to run the cello program and capture the output.
- Includes a tool to parse the results of the cello program, returning various metrics and data.

PromoterCalculator:
- A tool for generating, optimizing and predicting the performance of promoters.

UCF Library Manager:
- Scans directories for JSON files
- Extracts metadata from each file
- Determines file types based on filename patterns
- Validates file selections for compatibility
- Finds alternative files if the selected files are not valid
- Allows the agent to select appropriate files based on the user's request (e.g. "I want a **NOT gate** for **E. coli**")


## Retrieval Augmented Generation
While not yet implemented, RAG will be used to provide the agent with access to a wide range of information. This will give the planning agent the ability to search through scientific literature to find relevant information to assist in the design process.

## Reinforcement learning
Another core feature of the system is it's amenability to reinforcement learning. The initial reinforcement learning goal is to establish successful outputs from a wide range of prompts with high temperature values to ensure a wide range of reasoning streams. Successful outputs, determined using in-silico validation/simulation, will be used as training data to improve the agent's performance.

## Examples

Example scripts are provided in the `examples` directory. These range from simple integration, library management, to system level orchestration.


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.




