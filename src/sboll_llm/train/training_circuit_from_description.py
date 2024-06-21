import os
import json
from sklearn.model_selection import train_test_split
from transformers import T5Tokenizer, T5ForConditionalGeneration
from transformers import Trainer, TrainingArguments, DataCollatorForSeq2Seq
from transformers import GPT2Tokenizer, GPT2LMHeadModel
from transformers import T5Config, T5Tokenizer, T5ForConditionalGeneration
import torch
from datasets import Dataset


def load_json_files(directory):
    json_files = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                json_files.append(data)
    return json_files

def find_main_component_definition(doc):
    max_components = 0
    main_component = None
    for item in doc:
        if "ComponentDefinition" in item["@type"]:
            num_components = len(item.get("component", []))
            if num_components > max_components:
                max_components = num_components
                main_component = item
    return main_component

def preprocess_data(json_files):
    descriptions = []
    circuits = []
    for doc in json_files:
        components = []
        main_component = find_main_component_definition(doc)
        if main_component:
            try:
                descriptions.append(main_component.get("description", [""])[0]["@value"])
                components.append(main_component)
                # Adding components referenced by main_component
                for item in doc:
                    if item["@id"] in [comp["@id"] for comp in main_component.get("component", [])]:
                        components.append(item)
            except:
                print("Error processing doc.")
                continue
            circuits.append(json.dumps(components))
    return descriptions, circuits

def format_data_for_model(descriptions, components):
    data = {'input_text': descriptions, 'target_text': components}
    return Dataset.from_dict(data)

def run(data_dir, results_dir):
    # Load and preprocess data
    json_files = load_json_files(data_dir)
    descriptions, components = preprocess_data(json_files)

    # Format data for the model
    dataset = format_data_for_model(descriptions, components)
    train_dataset, eval_dataset = train_test_split(dataset, test_size=0.2)


    # Load pre-trained model and tokenizer
    # Define a small T5 configuration
    tokenizer = T5Tokenizer.from_pretrained("t5-small")
    
    config = T5Config(
        d_model=8,  # Hidden size
        d_ff=12,  # Feed-forward layer size
        num_layers=2,  # Number of encoder/decoder layers
        num_heads=2,  # Number of attention heads
        vocab_size=32128,  # Vocabulary size
        d_kv=16,  # Size of key/value vectors
        dropout_rate=0.1,  # Dropout rate
        num_decoder_layers=1,  # Number of decoder layers
        decoder_start_token_id=tokenizer.pad_token_id,
    )

    # Create the model
    model = T5ForConditionalGeneration(config)

    # Tokenize the datasets
    def tokenize_function(examples):
        inputs = tokenizer(examples['input_text'], max_length=1000, truncation=False)
        targets = tokenizer(examples['target_text'], max_length=1000, truncation=False)
        return {'input_ids': inputs['input_ids'], 'attention_mask': inputs['attention_mask'], 'labels': targets['input_ids']}

    train_dataset = Dataset.from_dict((train_dataset))
    train_dataset = train_dataset.map(tokenize_function, batched=True)
    eval_dataset = Dataset.from_dict((eval_dataset))
    eval_dataset = eval_dataset.map(tokenize_function, batched=True)

    # Define data collator
    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    # Define training arguments
    training_args = TrainingArguments(
        output_dir=os.path.join(results_dir, 'output'),
        eval_strategy='epoch',
        learning_rate=2e-5,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        num_train_epochs=3,
        weight_decay=0.01,
        logging_dir=os.path.join(results_dir, 'logs'),
    )

    # Create Trainer instance
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    # Train the model
    trainer.train()


if __name__ == "__main__":
    # import argparse
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--data_dir', type=str, required=True)

    run('/Users/admin/repos/geneforge/data/syn_bio_hub/sbol/simplified', 
          '/Users/admin/repos/geneforge/training_results')

    # prompt: # retrieve files from git repo

    # !git init
    # !git remote add origin https://github.com/jordanlgraves/geneforge.git
    # !git fetch origin master
    # !git checkout master
    # !git pull origin main
    # !pip install -r requirements.txt
    # from src.train.training_circuit_from_description import run
    # run('/content/drive/MyDrive/Geneforge/data/syn_bio_hub/sbol/simplified', 
    #     '/content/drive/MyDrive/Geneforge/training_results')