# SBOL-LLM

## Overview

In this project, we aim to train and evaluate large languange models to generate compliant and correct SBOL circuit designs from natural languagen. Given the ability to "reason" and draw on a vast amount of textual knowledge, LLM's present an opportunity to engineer systems that incorporate these vast knowledge bases into their output. This presents an opportunty to leverage knowledge bases for genetic circuit and part design. This project encompasses several steps, including data collection, preprocessing, training and evaluation.

## Project Structure

```plaintext
│   ├── sboll_llm/
|       ├── data/         # for downloading and processing datasets
│       ├── repositories/ # for interacting with parts repos
│       ├── train/        # training scripts
|       ├── requirements.txt
```

## Goals
Train LLMs for SBOL editing and generation tasks:

- Assemble dataset of circuits using parts repositories such as SynBioHub and iGEM and language modeling techniques
- Train models through masked language modeling and next token prediction for editing and generating valid genetic circuits
- Incorporate knowledge bases, context and background information into model prompts
- Validate the ability to model and generate valid circuits
 
## Usage
Data Preprocessing:

Normalize and standardize genetic circuit data.
Extract descriptions and structure the data for model training.
```
python sboll_llm/data/pipeline.py
```
Model Training:

Train models for genetic circuit design and masked component modeling.
```
python sboll_llm/train/training_circuit_from_description.py
python sboll_llm/train/training_masked_component_modeling.py
```

## Future Work
- Joint embeddings for circuit diagrams (jpgs) and circuit specifications (json)
- Selection of desired pretrained text model
- Join component descriptions with component embeddings
- Simplified json circuit to SBOL
- Integrate additional datasets from other repositories and collections
