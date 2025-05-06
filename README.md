# GeneForge: Automated Genetic Circuit Design and Optimization

This repository contains an the foundation work for developing an automated AI-driven system to design and optimize genetic circuits.

## Overview

To core features of the system include a master LLM-agent which plans and orchestrates the design of a genetic circuit. The agent uses tool calls handle different parts of the design process. The agent is able to generate verilog and manage a UCF, input and output library using other tools, allowing it to run Cello with custom parts and logic. The agent also uses retrieval augmented generation, allowing it to search through scientific literature to find relevant information to assist in the design process. Other tools allow for predicting and optimizing genetic parts and sequences. The high-level interface accepts an initial natural language prompt and with a design specification.

**State Management:** The system uses a `SessionState` object to manage the context (like the currently selected library, custom UCF files, etc.) across multiple tool calls within a single user design request..

## Examples and use cases:
Examples of prompts can be found in `examples_and_prompts`. These range from simple to complex to aspirational and are designed to guide the implementation of this project and outline the vision of more sophisticated systems.

## Tool Use

Several tools will be used to design and optimize genetic circuits. These tools are be wrapped in an integration layer which will be used by the agent. Listed below are some of the key tools that will be used:

Cello:
- Includes tools to search through and select a specific library (UCF, input and output files). This enables the agent to select appropriate parts for the design.
- Includes a tool to run the cello program and capture the output.
- Includes a tool to parse the results of the cello program, returning various metrics and data (e.g. truth tables, circuit scores).

Part Optimization:

- Promoter Calculator (https://salislab.net/software/predict_promoter_calculator) A tool for generating, optimizing and predicting the performance of promoters.
- RBS Calculator (https://salislab.net/software/predict_promoter_calculator) A tool for modifying RBS parts (e.g. specifying transcription rates).

UCF Library Manager:
- Scans directories for JSON files
- Extracts metadata from each file
- Determines file types based on filename patterns
- Validates file selections for compatibility
- Finds alternative files if the selected files are not valid
- Allows the agent to select appropriate files based on the user's request (e.g. "I want a **NOT gate** for **E. coli** with input using **specific sensor X**, **specific sensor Y**. The output shoud be **YFP**")

## Retrieval Augmented Generation 
Retrieval Augmented Generation: [https://arxiv.org/abs/2005.11401]
A narrow implementation of RAG is implemented through tool use. For example, the agent has the option to query available libraries and parts within those libraries. The responses from these tools calls allow the model to integrate drop-in libraries in the design process. 
While not yet fully implemented, RAG will be used to provide the agent with access to a wide range of background information. This will give the planning agent the ability to search through scientific literature to find relevant information to assist in the design process.

## Reinforcement learning
Reinforcement learning with verifiable rewards (RLVF): <https://arxiv.org/html/2503.23829v1>  
GeneForge is designed to be trainable because every design run produces artefacts (Cello output files, custom UCFs, etc.) that can be validated **programmatically**.  
Our proof-of-concept pipeline is split into two complementary stages:

### 1  Outer-loop policy learning (SB3)
1. **Environment** – Wrap `ExampleRunner` + `SessionState` in a Gymnasium-style env (`GeneCircuitToolEnv`).  
   • *Observation* = compact numeric vector summarising the current session (flags, counts, last circuit score, etc).  
   • *Action* = discrete choice of a `ToolIntegration` function and its argument indices.  
2. **Policy network** – a small MLP trained with PPO/A2C from `stable-baselines3`.  
   The network learns the best **sequence of tool calls** for a given design specification.  
3. **Reward** – computed by a standalone `RewardEvaluator` module:  
   • intermediate bonuses (correct library, valid sensor file, valid Verilog, etc)  
   • final reward, possibly incorporating a final Cello circuit score.
4. **Data collection** – all high-reward traces are saved as JSONL; they form the foundation for the next stage.

### 2  In-model fine-tuning (TRL / RLHF)
1. Export the best trajectories from stage 1 as supervised examples.  
2. Switch to an open-weights model (e.g. Llama, DeepSeek) and fine-tune with `trl`  (SFT warm-start → PPO/DPO for reward optimisation).  
3. The language model gradually learns to emit the needed tool calls directly in natural language, reducing reliance on the outer wrapper.

### Implementation roadmap
- [x] Build `RewardEvaluator` to verify Cello outputs and compute scalar rewards.  
- [x] Create `GeneCircuitToolEnv` and a minimal PPO training script.  
- [ ] Collect ≥ 500 high-reward traces with the SB3 policy.  
- [ ] Fine-tune an open model using `trl`, seeded with the collected traces.  
- [ ] Iterate: improved model replaces parts of the wrapper; new data refreshes fine-tuning.

This staged strategy lets us start learning **immediately** with the OpenAI API while producing verifiable data that directly powers full RLVF in the next phase.

## Examples

Example scripts are provided in the `examples` directory. These range from simple integration, library management, to system level orchestration.


## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Minimal Setup steps
1. git clone the repo
2. `cd geneforge`
3. `virtualenv venv --python=3.12` # create a virtual env -- Important: Use python version <3.13
4. `source venv/bin/activate` # activate the environment
5. `pip install -r requirements.txt` # install project requirements
6. `mkdir ext_repos` # create a directory to hold external repos 
7. `cd ext_repos`    # cd into the created repo
8. `git clone https://github.com/CIDARLAB/Cello-UCF.git`   # clone cello libs
9. `git clone https://github.com/CIDARLAB/Cello-v2-1-Core.git` # clone cello
10. `git clone https://github.com/barricklab/promoter-calculator.git` # clone promoter calculator
12. `pip install -r ext_repos/Cello-v2-1-Core/requirements.txt` # install cello requirements
13. `pip install -r ext_repos/Cello-UCF/requirements.txt` # install Cello-UCF requirements
14. `pip install -r ext_repos/promoter-calculator/requirements.txt` # install promoter-calculator requirements
15. `cd ..` # cd back into project root (geneforge directory)
16. `mkdir logs` # create the logs folder
17. `touch .env` # create file `.env` in geneforge folder (project root) to hold environment variables
18. Add the following keys to `.env`:
```
OPENAI_API_KEY={Your open ai api key}   # this or deepseek api key required to use LLMs
DEEPSEEK_API_KEY={Your deepseek api key (if using deepseek)} # not required
DEEPSEEK_BASE_URL=https://api.deepseek.com

PROMOTER_CALCULATOR_PATH=ext_repos/promoter-calculator/promoter-calculator
CELLO_UCF_ROOT=ext_repos/Cello-UCF
CELLO_ROOT=ext_repos/Cello-v2-1-Core
```
18. For using a debugger such as in VS Code or Cursor, set the PYTHONPATH in the config to the project root:
```
      "env": {
            "PYTHONPATH": "${workspaceFolder}"
      },
```
19. Test the setup by running `python src/examples/agent/design_simple_circuit.py` from `geneforge` directory.


## References/Links

- Cello [Github](https://github.com/CIDARLAB/Cello-v2-1-Core.git)
- Cello Libs [Github](https://github.com/CIDARLAB/Cello-UCF.git)
- Promoter Calculator [Github](https://github.com/barricklab/promoter-calculator.git)

### Verilog Generation
- CodeV: Empowering LLMs for Verilog Generation through Multi-Level Summarization [Paper](https://arxiv.org/html/2407.10424v4)
- RTLCoder: Fully Open-Source and Efficient LLM-Assisted RTL Code Generation Technique [Paper](https://arxiv.org/pdf/2312.08617) [Model](https://huggingface.co/ishorn5/RTLCoder-Deepseek-v1.1)
