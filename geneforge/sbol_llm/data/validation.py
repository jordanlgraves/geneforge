import os

from geneforge.data.io import read_sbol_file, write_sbol_file

def validate_sbol_document(doc):
    validation_errors = doc.validate()
    if validation_errors:
        
        print(f"Validation error: {validation_errors}")
    else:
        print("SBOL document is valid")

def validate_sbol_directory(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for filename in os.listdir(input_dir):
        if filename.endswith('.sbol') or filename.endswith('.xml'):
            file_path = os.path.join(input_dir, filename)
            doc = read_sbol_file(file_path)
            validate_sbol_document(doc)
            output_path = os.path.join(output_dir, filename)
            write_sbol_file(doc, output_path)