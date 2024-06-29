import json
import os

from rdflib import Graph
import sbol2
sbol2.SO_PLASMID
from geneforge.data.io import read_sbol_file, write_sbol_file

def sbol_to_json(sbol_file, output_file):
    """
    Extract and structure data from the SBOL document.
    """
    graph = Graph()
    graph.parse(sbol_file, format='xml')
    graph.serialize(destination=output_file, format='json-ld', indent=4)

def jsonld_to_sbol(jsonld_file, output_file):
    graph = Graph()
    graph.parse(source=jsonld_file, format='json-ld')
    graph.serialize(destination=output_file, format='xml')

def convert_sbol_files_to_json(in_directory, out_directory):
    """
    Extract and structure data from all SBOL files in a directory.
    """
    os.makedirs(out_directory, exist_ok=True)
    for filename in os.listdir(in_directory):
        if filename.endswith('.xml') or filename.endswith('.sbol'):
            new_filename = filename.split('.')[0] + '.json'
            in_file_path = os.path.join(in_directory, filename)
            sbol_to_json(in_file_path, os.path.join(out_directory, new_filename))
    

if __name__ == '__main__':
    # input_dir = 'data/syn_bio_hub/sbol/normalized'
    # structured_data = extract_and_structure_sbol_files(input_dir)
    # with open('data/structured_dataset.json', 'w') as f:
    #     json.dump(structured_data, f, indent=2)

    input_file = 'data/syn_bio_hub/sbol/normalized/BBa_I719003.sbol'
    output_file = 'data/syn_bio_hub/sbol/structured/BBa_I719003.json'

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    sbol_to_json(input_file, output_file)
    json_data = json.load(open(output_file))

    structued_to_sbol_path = 'data/syn_bio_hub/sbol/structured_to_sbol/BBa_I719003.sbol'
    os.makedirs(os.path.dirname(structued_to_sbol_path), exist_ok=True)

    jsonld_to_sbol(output_file, structued_to_sbol_path)
    doc = read_sbol_file(structued_to_sbol_path)
    write_sbol_file(doc, structued_to_sbol_path)