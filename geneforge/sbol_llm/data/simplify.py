import json
import os
from rdflib import Graph
from sbol2 import *

from geneforge.sbol_llm.data.io import write_sbol_file
from geneforge.sbol_llm.data.ontology import PURL_URL, SO_OPERATOR, SYNBIO_TERMS_HTTP_URL, SYNBIO_TERMS_HTTPS_URL, SYNBIOHUB_IGEM_URL, URIS_TO_SIMPLE_NAMES, VALID_ROLES

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
            
def sort_objects(objects_list):
    # Sort/order the objects by type
    sorted_objects = []
    obj_order = ['ComponentDefinition', 
                 'Component', 
                 'SequenceAnnotation', 
                 'SequenceConstraint', 
                 'Sequence', 
                 'Range', 
                 'Location']

    for next_type_in_order in obj_order:
        object_sorted_by_type_and_role = []
        obj_w_recognized_types = []
        for obj in objects_list:
            if next_type_in_order in obj['@type']:
                obj_w_recognized_types.append(obj)

        for role in VALID_ROLES:
            for obj in obj_w_recognized_types:
                if 'role' in obj and {'@id': role} in obj['role']:
                    object_sorted_by_type_and_role.append(obj)

        # add those with missing roles
        for obj in obj_w_recognized_types:
            if role in obj and obj['role']['@id'] not in VALID_ROLES:
                object_sorted_by_type_and_role.append(obj)
            if 'role' not in obj:
                object_sorted_by_type_and_role.append(obj)
        
        sorted_objects.extend(object_sorted_by_type_and_role)

    for obj in objects_list:
        if obj not in sorted_objects:
            print('Object was removed:', obj['@type'])
    return sorted_objects

def replace_ids(json_data):
    id_map = {}
    counters = {}

    # First pass: create mapping of old IDs to new standardized IDs
    for item in json_data:
        obj_type = item['@type'][0]
        if obj_type not in counters:
            counters[obj_type] = 0
        new_id = f"{obj_type}{counters[obj_type]}"
        id_map[item['@id']] = new_id
        counters[obj_type] += 1

    # Second pass: update all references and IDs
    for item in json_data:
        # Update object's own ID
        item['@id'] = id_map[item['@id']]
        
        # Update displayId
        if 'displayId' in item:
            item['displayId'][0]['@value'] = item['@id']

        # Update persistentIdentity
        if 'persistentIdentity' in item:
            old_persistent = item['persistentIdentity'][0]['@id']
            item['persistentIdentity'][0]['@id'] = id_map.get(old_persistent, old_persistent)

        # Update references in other attributes
        for attr, value in item.items():
            if isinstance(value, list):
                for val in value:
                    if isinstance(val, dict) and '@id' in val:
                        val['@id'] = id_map.get(val['@id'], val['@id'])
    # TODO: Fix
    return json_data




# Simplify the URIs
def simplify_json(json_data):
    # convert the json to a string and replace the uris with the simplified names
    item_str = json.dumps(json_data)
    
    # ensure no clashes
    assert(len(URIS_TO_SIMPLE_NAMES) == len(set(URIS_TO_SIMPLE_NAMES.values())))
    
    for uri, name in URIS_TO_SIMPLE_NAMES.items():
        item_str = item_str.replace(uri, name)
    
    # remove the synbiohub igem url
    item_str = item_str.replace(SYNBIOHUB_IGEM_URL, '')
    
    transformed_json = json.loads(item_str)
    
    # remove the unnecessary keys
    remove_keys(transformed_json)

    
    replace_ids(transformed_json)
    

    
    transformed_json = sort_objects(transformed_json)

    # REPLACE NAMES AND IDS WITH SIMPLE NAMES


    return transformed_json
        
def json_to_simplified_json(json_data):
    simplified_json = simplify_json(json_data)
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
            print(f'Simplifying {input_file_path}...')
            simplified_json = simplify_json(json_data)
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
    item = 'BBa_I719003' # 'BBa_I721006'
    input_json = f'/Users/admin/repos/geneforge/data/syn_bio_hub/sbol/structured/{item}.json'
    simplified_json_file = f'/Users/admin/repos/geneforge/data/syn_bio_hub/sbol/simplified/{item}.json'
    output_sbol_file = f'/Users/admin/repos/geneforge/data/syn_bio_hub/sbol/simplified_to_sbol/{item}.sbol'

    json_data = json.load(open(input_json))

    json_simplified = simplify_json(json_data)
    with (open(simplified_json_file, 'w')) as f:
        json.dump(json_simplified, f, indent=2)

    sbol_document = simplified_json_to_sbol(json_simplified)
    write_sbol_file(sbol_document, output_sbol_file)