import sbol2
import sbol2

import requests
import random

# Initialize SBOL document
namespace = 'http://sys-bio.org'
sbol2.set_namespace(namespace)
doc = sbol2.Document()

# Function to fetch sequences from SynBioHub
def fetch_sequence(part_id):
    url = f'https://synbiohub.org/public/igem/{part_id}/1/sbol'
    response = requests.get(url)
    if response.status_code == 200:
        content_type = response.headers.get('Content-Type')
        if 'application/rdf+xml' in content_type or 'application/xml' in content_type:
            return response.text
        else:
            raise Exception(f'Unexpected content type: {content_type}')
    else:
        raise Exception(f'Failed to fetch part sequence: HTTP {response.status_code}')

# Function to sanitize display IDs
def sanitize_display_id(display_id):
    if display_id[0].isdigit():
        display_id = '_' + display_id
    return ''.join(e for e in display_id if e.isalnum() or e == '_')

# Function to convert SBOL2 document to sbol2
def convert_sbol2_to_sbol2(sbol2_doc):
    sbol2_doc = sbol2.Document()
    for component_def in sbol2_doc.componentDefinitions:
        sanitized_id = sanitize_display_id(component_def.displayId)
        sbol2_component = sbol2.Component(sanitized_id, sbol2.SBO_DNA)
        sbol2_component.name = component_def.name
        sbol2_component.description = component_def.description
        sbol2_component.roles = component_def.roles
        for seq in component_def.sequences:
            sbol2_seq = sbol2.Sequence(sanitize_display_id(seq))
            sbol2_doc.add(sbol2_seq)
            sbol2_component.sequences.append(sbol2_seq)
        sbol2_doc.add(sbol2_component)
    return sbol2_doc

# Function to create a component and add it to the document
def create_component(doc, name, part_id, role):
    uri = f'https://synbiohub.org/public/igem/{part_id}/1'
    part_identity = f'{namespace}/{part_id}'

    existing_component = doc.find(part_identity)
    if existing_component:
        return existing_component
    else:
        sbol_string = fetch_sequence(part_id)
        temp_doc = sbol2.Document()
        temp_doc.readString(sbol_string)
        sbol2_doc = convert_sbol2_to_sbol2(temp_doc)
        component = sbol2_doc.find(namespace + '/' + part_id)
        if component is None:
            print(f"Component with URI {uri} not found in temporary document.")
            for obj in sbol2_doc.objects:
                print(f"Found object: {obj.identity}")
        else:
            component.name = name
            component.roles.append(role)
            doc.add(component)
            return component
        return component


# Define parts catalog
parts_catalog = {
    'promoters': ['BBa_J23100', 'BBa_J23119'],
    'rbs': ['BBa_B0034'],
    'cds': ['BBa_E0040', 'BBa_C0040'],
    'terminators': ['BBa_B0015'],
    'repressors': ['BBa_C0012'],
    'activators': ['BBa_C0080']
}

# Function to create an FFL with specific interaction types
def create_ffl(doc, upstream_id, downstream_id, target_id, interactions):
    upstream = create_component(doc, 'promoter_' + upstream_id, upstream_id, sbol2.SO_PROMOTER)
    downstream = create_component(doc, 'promoter_' + downstream_id, downstream_id, sbol2.SO_PROMOTER)
    target = create_component(doc, 'cds_' + target_id, target_id, sbol2.SO_CDS)
    
    upstream_regulator = create_component(doc, 'cds_' + upstream_id, upstream_id, sbol2.SO_CDS)
    downstream_regulator = create_component(doc, 'cds_' + downstream_id, downstream_id, sbol2.SO_CDS)
    
    if interactions['A_B'] == 'activation':
        downstream_promoter = create_component(doc, 'promoter_' + downstream_id, upstream_id, sbol2.SO_PROMOTER)
    else:
        downstream_promoter = create_component(doc, 'repressor_' + downstream_id, upstream_id, sbol2.SO_PROMOTER)
    
    if interactions['A_C'] == 'activation':
        target_promoter_direct = create_component(doc, 'promoter_' + target_id, upstream_id, sbol2.SO_PROMOTER)
    else:
        target_promoter_direct = create_component(doc, 'repressor_' + target_id, upstream_id, sbol2.SO_PROMOTER)
    
    if interactions['B_C'] == 'activation':
        target_promoter_indirect = create_component(doc, 'promoter_' + target_id, downstream_id, sbol2.SO_PROMOTER)
    else:
        target_promoter_indirect = create_component(doc, 'repressor_' + target_id, downstream_id, sbol2.SO_PROMOTER)
    
    return {
        'upstream': upstream,
        'downstream': downstream,
        'target': target,
        'upstream_regulator': upstream_regulator,
        'downstream_regulator': downstream_regulator,
        'downstream_promoter': downstream_promoter,
        'target_promoter_direct': target_promoter_direct,
        'target_promoter_indirect': target_promoter_indirect
    }

# Generate a random FFL
def generate_random_ffl(doc, parts_catalog):
    ffl_types = [
        {'A_B': 'activation', 'A_C': 'activation', 'B_C': 'activation'},  # Type 1
        {'A_B': 'activation', 'A_C': 'activation', 'B_C': 'repression'},  # Type 2
        {'A_B': 'repression', 'A_C': 'activation', 'B_C': 'activation'},  # Type 3
        {'A_B': 'repression', 'A_C': 'activation', 'B_C': 'repression'},  # Type 4
        {'A_B': 'activation', 'A_C': 'repression', 'B_C': 'activation'},  # Type 5
        {'A_B': 'repression', 'A_C': 'activation', 'B_C': 'repression'},  # Type 6
        {'A_B': 'activation', 'A_C': 'repression', 'B_C': 'activation'},  # Type 7
        {'A_B': 'activation', 'A_C': 'repression', 'B_C': 'repression'}   # Type 8
    ]
    
    interactions = random.choice(ffl_types)
    upstream_id = random.choice(parts_catalog['promoters'])
    downstream_id = random.choice(parts_catalog['promoters'])
    target_id = random.choice(parts_catalog['cds'])
    rbs_id = random.choice(parts_catalog['rbs'])
    terminator_id = random.choice(parts_catalog['terminators'])
    
    return create_ffl(doc, upstream_id, downstream_id, target_id, interactions), rbs_id, terminator_id

# Example usage
circuit = sbol2.Component('random_ffl_gene_circuit', sbol2.SBO_FUNCTIONAL_ENTITY)
doc.add(circuit)
random_ffl, rbs_id, terminator_id = generate_random_ffl(doc, parts_catalog)

# Create RBS and Terminator components
rbs = create_component(doc, 'rbs_' + rbs_id, rbs_id, sbol2.SO_RBS)
terminator = create_component(doc, 'terminator_' + terminator_id, terminator_id, sbol2.SO_TERMINATOR)

# Create SubComponents and constraints for the circuit
subcomponents = [
    sbol2.SubComponent(random_ffl['upstream']),
    sbol2.SubComponent(rbs),
    sbol2.SubComponent(random_ffl['upstream_regulator']),
    sbol2.SubComponent(random_ffl['downstream_promoter']),
    sbol2.SubComponent(rbs),
    sbol2.SubComponent(random_ffl['downstream_regulator']),
    sbol2.SubComponent(random_ffl['target_promoter_direct']),
    sbol2.SubComponent(rbs),
    sbol2.SubComponent(random_ffl['target']),
    sbol2.SubComponent(terminator),
    sbol2.SubComponent(random_ffl['target_promoter_indirect']),
    sbol2.SubComponent(rbs),
]

circuit.features = subcomponents

# Save the document
doc.write('parts/random_ffl_gene_circuit.xml')

# Print the components for verification
for key, value in random_ffl.items():
    print(f"{key}: {value.identity}")
