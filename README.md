# Gene Forge: Automated Genetic Circuit Design and Optimization

This repository contains tools and frameworks for developing and training AI-agents for genetic engineering workflows.

## ModelClient 
The `ModelClient` provides an interface to an LLM of choice (currently only from `openai` or a local model via `vllm`).


**State Management:** The system uses a `SessionState` object to manage the context (like the currently selected library, custom UCF files, etc.) across multiple tool calls within a single user design request..

## Tool Use

Several tools will be used to design and optimize genetic circuits. These tools are be wrapped in an integration layer which will be used by the agent. Listed below are some of the key tools that will be used:

- Cello - includes library management tools for adding/editing parts in a library files and a tool for kicking off Cello's design algorithm
- SynBioHub - includes tools to search and download parts from SynBioHub 
- Part Optimization - ProD for promoter design, RBS Calculator for RBS design
- Scientific utilities - Count GC in a sequence, run sequence similarity, literature search

## Workflows 
A `Workflow` defines:
1. A natural language `prompt` describing a task
2. A `get_metrics` functions for computing the metrics based on the generated chat history and session state. This can be used for computing a `reward` or `score` for various forms of RL via policy-optimization. 
3. A `check_finished` function for optionally terminating the chat stream upon some condition
4. An optional `GRADING_RUBRIC` - instructions for assigning a grade/reward to the rolled our workflow

Workflows can be `run` which coordinates a multi-turn conversations with the `ModelClient`. Upon finishing, `get_metrics()` can be used.

ArtAdapter
- An `ArtAdapter` object wraps the `Workflow` and exposes the `async` `rollout` function. This allows multiple runs to
execute in parallel and can be dropped into `art` training scheme to fine-tune an LLM via GRPO.
- The optional `GRADING_RUBRIC` can be used in conjunction with LLM judges to compute reward (e.g. ART's RULER)

## Examples and use cases:
Examples of prompts can be found in `examples_and_prompts`. These range from simple to complex to aspirational and are designed to guide the implementation of this project and outline the vision of more sophisticated systems.

## Fine-tuning

The workflows provide a convenient means of "rolling" out scenarios and comparing outcomes. Their primary intention is to easily enable RL-training on the various implemented tools.

## UI
A basic `streamlit` UI allows for interactive chat sessions with an LLM agent (openai and models served via vllm supported)

## Examples

Example scripts are provided in the `examples` directory. 

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


## Notable References/Links

Tools/Core
- Cello [Github](https://github.com/CIDARLAB/Cello-v2-1-Core.git)
- Cello Libs [Github](https://github.com/CIDARLAB/Cello-UCF.git)
- Promoter Calculator [Github](https://github.com/barricklab/promoter-calculator.git)

RL/Fine-tuning
- openai
- art
- GRPO

Verilog Generation
- CodeV: Empowering LLMs for Verilog Generation through Multi-Level Summarization [Paper](https://arxiv.org/html/2407.10424v4)
- RTLCoder: Fully Open-Source and Efficient LLM-Assisted RTL Code Generation Technique [Paper](https://arxiv.org/pdf/2312.08617) [Model](https://huggingface.co/ishorn5/RTLCoder-Deepseek-v1.1)

Other 
- Anatomical Compiler [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10527237/)
- CLASSIC: Ultra-high throughput mapping of genetic design space [Paper](https://pubmed.ncbi.nlm.nih.gov/36993481/)
