# GeneForge: AI Driven Genetic Circuit Design

## Overview

GeneForge is a project aimed at developing a robust framework for generating and modeling genetic circuits. The ultimate goal is to create a model capable of designing and editing genetic circuits given an initial and target cell states (e.g. from RNA-seq data). 

![Geneforge](docs/geneforge.png)

## Project Structure

```plaintext
├── src/
│   ├── circuits/         # for generating circuits
│   ├── sboll_llm/        # sub-project for generating sbol compliant circuits designs from natural language
|       ├── data/         # for downloading and processing datasets
│       ├── repositories/ # for interacting with parts repos
│       ├── train/        # training scripts
├── notebooks/
├── docs/             # references and background material
├── .gitignore
├── README.md
├── requirements.txt
```


## Goals
Develop a Generative Model for Genetic Circuit Design:

- Train models to learn and generate valid genetic circuits using parts repositories such as SynBioHub and iGEM and language modeling techniques.
- Validate the ability to model and generate valid circuits.

Generate Circuits Based on Initial and Target Cell States:

- Use expression data (e.g., RNA-seq) to design genetic circuits that transition a cell from an initial expression state to a target expression state.
- Generate a large quantity of pseudo-random circuit design.
- Combine circuit design simulations (e.g. libSBML) with perturbation simulations (e.g., GEARs, GeneFormer).
 
## Installation
Clone the Repository:
```
git clone https://github.com/yourusername/geneforge.git
cd geneforge
```
Install Dependencies:

```sh
pip install -r requirements.txt
```

## Usage
Data Preprocessing:

Normalize and standardize genetic circuit data.
Extract descriptions and structure the data for model training.
```
python src/data/pipeline.py
```
Model Training:

Train models for genetic circuit design and masked component modeling.
```
python src/train/training_circuit_from_description.py
python src/train/training_masked_component_modeling.py
```

## References and Background Material

A bibliography of related publications can be found [in the docs  folder.](docs/bibliography.txt)

## Future Work
- Joint embeddings for circuit diagrams (jpgs) and circuit specifications (json)
- Encode part definitions using pretrained text model
- Learning/tuning scheme for component parameter optimization (e.g. binding constants, degradation and production rates)
- Graph representations and graph kernels
- Simplified json circuit to SBOL
- Integrate additional datasets from other repositories and collections
- Circuit simulations -> perturbation-seq simulations
