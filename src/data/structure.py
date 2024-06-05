import json
import os

import sbol2

from src.data.io import read_sbol_file

def extract_structured_data(doc):
    """
    Extract and structure data from the SBOL document.
    """
    structured_data = []
    
    for obj in doc.SBOLObjects.values():
        if isinstance(obj, sbol2.ComponentDefinition):
            component_data = {
                'name': obj.name,
                'display_id': obj.displayId,
                'description': obj.description,
                'types': [_.split('/')[-1] for _ in obj.types] if obj.types else ['unknown'],
                'roles': [_.split('/')[-1] for _ in obj.roles] if obj.roles else ['unknown'],
                'components': [],
                'sequence_constraints': []
            }
            for component in obj.components:
                # component definition should be the parent of the component
                comp_def_parent = component.parent
                assert(isinstance(comp_def_parent, sbol2.ComponentDefinition))
                component_data['components'].append({
                    'name': component.name,
                    'display_id': component.displayId,
                    'definition': comp_def_parent.displayId,
                    'roles': [_.split('/')[-1] for _ in component.roles] if component.roles else ['unknown']
                })
            for sc in obj.sequenceConstraints:
                component_data['sequence_constraints'].append({
                    'subject': sc.subject,
                    'object': sc.object,
                    'restriction': sc.restriction
                })
            structured_data.append(component_data)
    return structured_data

def extract_and_structure_sbol_files(directory):
    """
    Extract and structure data from all SBOL files in a directory.
    """
    structured_dataset = []
    for filename in os.listdir(directory):
        if filename.endswith('.xml') or filename.endswith('.sbol'):
            file_path = os.path.join(directory, filename)
            doc = read_sbol_file(file_path)
            structured_data = extract_structured_data(doc)
            structured_dataset.extend(structured_data) # BBa_I721006
    return structured_dataset

if __name__ == '__main__':
    # input_dir = 'data/syn_bio_hub/sbol/normalized'
    # structured_data = extract_and_structure_sbol_files(input_dir)
    # with open('data/structured_dataset.json', 'w') as f:
    #     json.dump(structured_data, f, indent=2)

    input_file = 'data/syn_bio_hub/scraped/sbol/BBa_I721006.sbol'
    doc = read_sbol_file(input_file)
    structured_data = extract_structured_data(doc)
    os.makedirs('data/syn_bio_hub/sbol/structured', exist_ok=True)
    with open('data/syn_bio_hub/sbol/structured/BBa_I721006.json', 'w') as f:
        json.dump(structured_data, f, indent=2)