# GeneForge: A Framework for Genetic Circuit Design and Modeling

## Overview

GeneForge is a project aimed at developing a robust framework for generating and modeling genetic circuits. The ultimate goal is to create a model capable of designing and editing genetic circuits given an initial and target cell states, based on expression data (e.g., RNA-seq). This project encompasses several steps, including data collection, model training, and circuit and expression perturbation simulation.

## Project Structure

```plaintext
├── src/
│   ├── circuits/     # for generating circuits
│   ├── data/         # for downloading and processing datasets
│   ├── repositories/ # for interacting with parts repos
│   ├── train/        # training scripts
├── notebooks/
├── docs/             # references and background material
├── .gitignore
├── README.md
├── requirements.txt
```

## Goals
Develop a Model for Genetic Circuit Design:

- Train models to learn and generate valid genetic circuits using parts repositories such as SynBioHub and iGEM.
- Validate the ability to model and generate circuits accurately.

Generate Circuits Based on Initial and Target Cell States:

- Use expression data (e.g., RNA-seq) to design genetic circuits that transition an initial cell state to a target cell state.
- Generate synthetic data by simulating the circuits and their effects on cell states using circuit simulation libraries and perturbation simulations (e.g., GEARS or GeneFormer).
 
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

A bibliography of related publications can be found {root}/docs/bibliography.txt

## Future Work
- Experiment with graph representations and GNNs
- Simplified JSON to SBOL converter
- Integrate additional datasets from other repositories and collections to enhance training data.
- Implement circuit simulations and validate conversion on SBOL to SBML.
- Integrate circuit simulation outputs into perturbation-seq simulations.
- Generate dataset of circuit, intitial and final cell states fro training and refining circuit generation.
- Explore advanced training strategies to refine the model's ability to design complex genetic circuits.
