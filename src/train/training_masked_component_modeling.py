import os
import json
import random
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM, Trainer, TrainingArguments
from datasets import Dataset, DatasetDict

def load_json_files(directory):
    json_files = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as file:
                json_files.append(json.load(file))
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

def mask_components(main_component, mask_token="[MASK]", mask_prob=0.15):
    # Mask components in the main_component with a specified probability.
    components = main_component.get("component", [])
    masked_components = []
    target_components = []

    for comp in components:
        if random.random() < mask_prob:
            masked_components.append(mask_token)
            target_components.append(comp["@id"])
        else:
            masked_components.append(comp["@id"])
            target_components.append(None)
    
    return masked_components, target_components

def preprocess_data(json_files, mask_token="[MASK]", mask_prob=0.15):
    input_sequences = []
    target_sequences = []
    
    for doc in json_files:
        main_component = find_main_component_definition(doc)
        if main_component:
            masked_components, target_components = mask_components(main_component, mask_token, mask_prob)
            input_sequences.append(str(masked_components))
            target_sequences.append(str(target_components))
    
    return input_sequences, target_sequences

if __name__ == "__main__":
    # Load JSON files from the directory
    data_dir = '/Users/admin/repos/geneforge/data/syn_bio_hub/sbol/simplified'
    results_dir = '/Users/admin/repos/geneforge/training_results'
    json_files = load_json_files(data_dir)

    # Preprocess the data for MLM
    input_sequences, target_sequences = preprocess_data(json_files)

    # Convert to Hugging Face datasets format
    dataset = DatasetDict({
        "train": Dataset.from_dict({"input_sequences": input_sequences, "target_sequences": target_sequences}),
        "test": Dataset.from_dict({"input_sequences": input_sequences, "target_sequences": target_sequences})
    })

    # Example of using a pre-trained model for MLM
    # Define a small BERT model configuration
    from transformers import BertConfig, BertForMaskedLM
    small_bert_config = BertConfig(
        vocab_size=30522,
        hidden_size=16,
        num_hidden_layers=2,
        num_attention_heads=2,
        intermediate_size=8,
        max_position_embeddings=128
    )

    # Initialize the tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    model = BertForMaskedLM(small_bert_config)

    # Tokenize the data
    def tokenize_function(examples):
        return tokenizer(examples["input_sequences"], truncation=True, padding=True, max_length=512)

    tokenized_datasets = dataset.map(tokenize_function, batched=True)

    # Data collator for masked language modeling
    from transformers import DataCollatorForLanguageModeling

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=0.15
    )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=os.path.join(results_dir, 'output'),
        num_train_epochs=3,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir=os.path.join(results_dir, 'logs'),
        logging_steps=10,
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        data_collator=data_collator
    )

    # Training
    trainer.train()
