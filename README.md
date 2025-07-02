# Gene Forge: Automated Genetic Circuit Design and Optimization

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
- Allows the agent to select appropriate files based on the user's request (e.g. "I want a **NOT gate** for **E. coli** with input using **specific sensor X**, **specific sensor Y**. The output shoud be **YFP**")

### SynBioHub Integration
What can SynBioHub be used for?

SynBioHub can be used to publish a library of synthetic parts and designs as a service, to share designs with collaborators, and to store designs of biological systems locally. Data in SynBioHub can be accessed via the HTTP API, Java API, or Python API where it can then be integrated into CAD tools for building genetic designs. SynBioHub contains an interface for users to upload new biological data to the database, to visualize DNA parts, to perform queries to access desired parts, and to download SBOL, GenBank, FASTA, etc.


The agent can:
- **Search** the registry (`synbiohub_search`) using the same key–value parameters accepted by the `/search/` web API.
- **Download** any object or collection by URI in common formats such as SBOL, FASTA, GenBank, or GFF (`synbiohub_download_part`).
- **Run sequence similarity searches** against the global database (`synbiohub_sequence_search`).
- **Inspect related content** for provenance or design exploration (`synbiohub_get_related`).
- **Submit** new parts/collections when credentials are supplied (`synbiohub_submit`).

These helpers return the *raw* server response (JSON, XML, or text) so that downstream code or the LLM can interpret it flexibly.

#### Quick examples

```json
{"name": "synbiohub_search", "arguments": {"query": "objectType=ComponentDefinition&dcterms:title=pLac", "limit": 10}}
{"name": "synbiohub_download_part", "arguments": {"uri": "https://synbiohub.org/public/igem/BBa_R0010/1", "format": "gb"}}
{"name": "synbiohub_sequence_search", "arguments": {"search_params": "globalsequence=ATGCGTACGTAGCTAG&id=0.9&maxaccepts=50"}}
{"name": "synbiohub_get_related", "arguments": {"uri": "https://synbiohub.org/public/igem/BBa_R0010/1", "relation": "twins"}}
```

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


## References/Links

Tools/Core
- Cello [Github](https://github.com/CIDARLAB/Cello-v2-1-Core.git)
- Cello Libs [Github](https://github.com/CIDARLAB/Cello-UCF.git)
- Promoter Calculator [Github](https://github.com/barricklab/promoter-calculator.git)

Verilog Generation
- CodeV: Empowering LLMs for Verilog Generation through Multi-Level Summarization [Paper](https://arxiv.org/html/2407.10424v4)
- RTLCoder: Fully Open-Source and Efficient LLM-Assisted RTL Code Generation Technique [Paper](https://arxiv.org/pdf/2312.08617) [Model](https://huggingface.co/ishorn5/RTLCoder-Deepseek-v1.1)

Other 
- Anatomical Compiler [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10527237/)
- CLASSIC: Ultra-high throughput mapping of genetic design space [Paper](https://pubmed.ncbi.nlm.nih.gov/36993481/)
