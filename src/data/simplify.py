import json
import os
from rdflib import Graph
from sbol2 import *

from src.data.io import write_sbol_file
from src.data.ontology import PURL_URL, SO_OPERATOR, SYNBIO_TERMS_HTTP_URL, SYNBIO_TERMS_HTTPS_URL, SYNBIOHUB_IGEM_URL, URIS_TO_SIMPLE_NAMES

def remove_keys(json_data):
    if isinstance(json_data, list):
        for item in json_data:
            remove_keys(item)
    if isinstance(json_data, dict):
        items = list(json_data.items())
        for key, value in items:
            # These are assumed to be useless keys (e.g. ownedBy, createdAt, etc.)
            if key.startswith(PROV_URI) \
                    or key.startswith(SYNBIO_TERMS_HTTPS_URL) \
                    or key.startswith(SYNBIO_TERMS_HTTP_URL) \
                    or key.startswith(IGEM_URI) \
                    or key.startswith(SYNBIOHUB_IGEM_URL) \
                    or key.startswith(PURL_URL):
                    del json_data[key]
            elif isinstance(value, dict):
                remove_keys(value)
            elif isinstance(value, list):
                remove_keys(value)
            
                

# Simplify the URIs
def simplify_uris(json_data):
    # convert the json to a string and replace the uris with the simplified names
    item_str = json.dumps(json_data)
    
    # ensure no clashes
    assert(len(URIS_TO_SIMPLE_NAMES) == len(set(URIS_TO_SIMPLE_NAMES.values())))
    
    for uri, name in URIS_TO_SIMPLE_NAMES.items():
        item_str = item_str.replace(uri, name)
    
    # remove the synbiohub igem url
    item_str = item_str.replace(SYNBIOHUB_IGEM_URL, '')
    
    simple_item = json.loads(item_str)
    
    # remove the unnecessary keys
    remove_keys(simple_item)

    return simple_item
        
def json_to_simplified_json(json_data):
    simplified_json = simplify_uris(json_data)
    return simplified_json

def simplify_json_files(input_dir, output_dir):
    """
    Simplify URIs in all JSON files in a directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    for filename in os.listdir(input_dir):
        if filename.endswith('.json'):
            input_file_path = os.path.join(input_dir, filename)
            output_file_path = os.path.join(output_dir, filename)
            
            json_data = json.load(open(input_file_path))
            simplified_json = simplify_uris(json_data)
            with (open(output_file_path, 'w')) as f:
                json.dump(simplified_json, f, indent=2)


def simplified_json_to_sbol(simplified_json):
    def expand_uris(item):
        if isinstance(item, dict):
            return {URIS_TO_SIMPLE_NAMES.get(k, k): expand_uris(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [expand_uris(v) for v in item]
        else:
            return item
    
    expanded_json = expand_uris(simplified_json)
    graph = Graph()
    graph.parse(data=json.dumps(expanded_json), format='json-ld')
    
    sbol_document = Document()
    sbol_document.readString(graph.serialize(format='xml'))
    return sbol_document


if __name__ == "__main__":
    import sbol2 
    item = 'BBa_I721006'
    input_json = f'/Users/admin/repos/geneforge/data/syn_bio_hub/sbol/structured/{item}.json'
    simplified_json_file = f'/Users/admin/repos/geneforge/data/syn_bio_hub/sbol/simplified/{item}.json'
    output_sbol_file = f'/Users/admin/repos/geneforge/data/syn_bio_hub/sbol/simplified_to_sbol/{item}.sbol'

    json_data = json.load(open(input_json))

    json_simplified = simplify_uris(json_data)
    with (open(simplified_json_file, 'w')) as f:
        json.dump(json_simplified, f, indent=2)

    sbol_document = simplified_json_to_sbol(json_simplified)
    write_sbol_file(sbol_document, output_sbol_file)