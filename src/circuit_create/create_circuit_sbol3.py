import sbol3
from sbol2 import PartShop
import requests
import random

# Initialize SBOL document
namespace = 'http://sys-bio.org'
sbol3.set_namespace(namespace)
doc = sbol3.Document()



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
    upstream = create_component(doc, 'promoter_' + upstream_id, upstream_id, sbol3.SO_PROMOTER)
    downstream = create_component(doc, 'promoter_' + downstream_id, downstream_id, sbol3.SO_PROMOTER)
    target = create_component(doc, 'cds_' + target_id, target_id, sbol3.SO_CDS)
    
    upstream_regulator = create_component(doc, 'cds_' + upstream_id, upstream_id, sbol3.SO_CDS)
    downstream_regulator = create_component(doc, 'cds_' + downstream_id, downstream_id, sbol3.SO_CDS)
    
    if interactions['A_B'] == 'activation':
        downstream_promoter = create_component(doc, 'promoter_' + downstream_id, upstream_id, sbol3.SO_PROMOTER)
    else:
        downstream_promoter = create_component(doc, 'repressor_' + downstream_id, upstream_id, sbol3.SO_PROMOTER)
    
    if interactions['A_C'] == 'activation':
        target_promoter_direct = create_component(doc, 'promoter_' + target_id, upstream_id, sbol3.SO_PROMOTER)
    else:
        target_promoter_direct = create_component(doc, 'repressor_' + target_id, upstream_id, sbol3.SO_PROMOTER)
    
    if interactions['B_C'] == 'activation':
        target_promoter_indirect = create_component(doc, 'promoter_' + target_id, downstream_id, sbol3.SO_PROMOTER)
    else:
        target_promoter_indirect = create_component(doc, 'repressor_' + target_id, downstream_id, sbol3.SO_PROMOTER)
    
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
circuit = sbol3.Component('random_ffl_gene_circuit', sbol3.SBO_FUNCTIONAL_ENTITY)
doc.add(circuit)
random_ffl, rbs_id, terminator_id = generate_random_ffl(doc, parts_catalog)

# Create RBS and Terminator components
rbs = create_component(doc, 'rbs_' + rbs_id, rbs_id, sbol3.SO_RBS)
terminator = create_component(doc, 'terminator_' + terminator_id, terminator_id, sbol3.SO_TERMINATOR)

# Create SubComponents and constraints for the circuit
subcomponents = [
    sbol3.SubComponent(random_ffl['upstream']),
    sbol3.SubComponent(rbs),
    sbol3.SubComponent(random_ffl['upstream_regulator']),
    sbol3.SubComponent(random_ffl['downstream_promoter']),
    sbol3.SubComponent(rbs),
    sbol3.SubComponent(random_ffl['downstream_regulator']),
    sbol3.SubComponent(random_ffl['target_promoter_direct']),
    sbol3.SubComponent(rbs),
    sbol3.SubComponent(random_ffl['target']),
    sbol3.SubComponent(terminator),
    sbol3.SubComponent(random_ffl['target_promoter_indirect']),
    sbol3.SubComponent(rbs),
]

circuit.features = subcomponents

# Save the document
doc.write('parts/random_ffl_gene_circuit_3.xml')

# Print the components for verification
for key, value in random_ffl.items():
    print(f"{key}: {value.identity}")
