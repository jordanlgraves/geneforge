import uuid
import sbol2
import random
import sbol2
import random

from geneforge.sbol_llm.repositories.synbiohub import create_component


# Function to create an FFL with specific interaction types and components
def create_ffl(doc, components, interactions):
    upstream = create_component(doc, 'promoter_' + components['upstream'], components['upstream'], sbol2.SO_PROMOTER)
    downstream = create_component(doc, 'promoter_' + components['downstream'], components['downstream'], sbol2.SO_PROMOTER)
    target = create_component(doc, 'cds_' + components['target'], components['target'], sbol2.SO_CDS)
    
    upstream_regulator = create_component(doc, 'cds_' + components['upstream'], components['upstream'], sbol2.SO_CDS)
    downstream_regulator = create_component(doc, 'cds_' + components['downstream'], components['downstream'], sbol2.SO_CDS)
    
    if interactions['A_B'] == 'activation':
        downstream_promoter = create_component(doc, 'promoter_' + components['downstream'], components['upstream'], sbol2.SO_PROMOTER)
    else:
        downstream_promoter = create_component(doc, 'repressor_' + components['downstream'], components['upstream'], sbol2.SO_PROMOTER)
    
    if interactions['A_C'] == 'activation':
        target_promoter_direct = create_component(doc, 'promoter_' + components['target'], components['upstream'], sbol2.SO_PROMOTER)
    else:
        target_promoter_direct = create_component(doc, 'repressor_' + components['target'], components['upstream'], sbol2.SO_PROMOTER)
    
    if interactions['B_C'] == 'activation':
        target_promoter_indirect = create_component(doc, 'promoter_' + components['target'], components['downstream'], sbol2.SO_PROMOTER)
    else:
        target_promoter_indirect = create_component(doc, 'repressor_' + components['target'], components['downstream'], sbol2.SO_PROMOTER)
    
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

# General function to generate circuits based on provided components and interactions
def generate_circuit(doc, parts_catalog, interactions, motif_type, upstream_id=None, downstream_id=None, target_id=None):
    # Select unique components for upstream, downstream, and target if not provided
    if upstream_id is None:
        upstream_id = random.choice(parts_catalog['promoters'])
    if downstream_id is None:
        downstream_id = random.choice(parts_catalog['promoters'])
        while downstream_id == upstream_id:
            downstream_id = random.choice(parts_catalog['promoters'])
    if target_id is None:
        target_id = random.choice(parts_catalog['cds'])
    
    rbs_id = random.choice(parts_catalog['rbs'])
    terminator_id = random.choice(parts_catalog['terminators'])
    
    components = {
        'upstream': upstream_id,
        'downstream': downstream_id,
        'target': target_id,
        'rbs': rbs_id,
        'terminator': terminator_id
    }
    
    if motif_type == 'ffl':
        return create_ffl(doc, components, interactions), rbs_id, terminator_id
    else:
        raise ValueError(f"Motif type '{motif_type}' not supported")

# Function to assemble the primary structure of the circuit
def assemble_circuit(doc, circuit, random_ffl, rbs_id, terminator_id):
    # Create RBS and Terminator components
    rbs = create_component(doc, 'rbs_' + rbs_id, rbs_id, sbol2.SO_RBS)
    terminator = create_component(doc, 'terminator_' + terminator_id, terminator_id, sbol2.SO_TERMINATOR)
    
    # Assemble the primary structure in the correct order
    components = [
        random_ffl['upstream'],
        rbs,
        random_ffl['upstream_regulator'],
        random_ffl['downstream_promoter'],
        rbs,
        random_ffl['downstream_regulator'],
        random_ffl['target_promoter_direct'],
        rbs,
        random_ffl['target'],
        terminator,
        random_ffl['target_promoter_indirect'],
        rbs,
    ]
    
    circuit.assemblePrimaryStructure(components)

# Example usage
def generate_ffl(doc, parts_catalog, interactions, upstream_id=None, downstream_id=None, target_id=None):
    unique_id = str(uuid.uuid4())
    circuit = sbol2.ComponentDefinition(f"ffl_gene_circuit_{unique_id}")
    doc.addComponentDefinition(circuit)
    random_ffl, rbs_id, terminator_id = generate_circuit(doc, parts_catalog, interactions, 'ffl', upstream_id, downstream_id, target_id)
    assemble_circuit(doc, circuit, random_ffl, rbs_id, terminator_id)
    return circuit



def create_repressilator(doc, components):
    repressor1 = create_component(doc, 'cds_' + components['repressor1'], components['repressor1'], sbol2.SO_CDS)
    repressor2 = create_component(doc, 'cds_' + components['repressor2'], components['repressor2'], sbol2.SO_CDS)
    repressor3 = create_component(doc, 'cds_' + components['repressor3'], components['repressor3'], sbol2.SO_CDS)
    
    promoter1 = create_component(doc, 'promoter_' + components['repressor1'], components['repressor1'], sbol2.SO_PROMOTER)
    promoter2 = create_component(doc, 'promoter_' + components['repressor2'], components['repressor2'], sbol2.SO_PROMOTER)
    promoter3 = create_component(doc, 'promoter_' + components['repressor3'], components['repressor3'], sbol2.SO_PROMOTER)
    
    return {
        'repressor1': repressor1,
        'repressor2': repressor2,
        'repressor3': repressor3,
        'promoter1': promoter1,
        'promoter2': promoter2,
        'promoter3': promoter3
    }



def generate_repressilator(doc, parts_catalog, repressor1_id=None, repressor2_id=None, repressor3_id=None):
    # Select unique components for repressors if not provided
    if repressor1_id is None:
        repressor1_id = random.choice(parts_catalog['repressors'])
    if repressor2_id is None:
        repressor2_id = random.choice(parts_catalog['repressors'])
        while repressor2_id == repressor1_id:
            repressor2_id = random.choice(parts_catalog['repressors'])
    if repressor3_id is None:
        repressor3_id = random.choice(parts_catalog['repressors'])
        while repressor3_id in [repressor1_id, repressor2_id]:
            repressor3_id = random.choice(parts_catalog['repressors'])
    
    rbs_id = random.choice(parts_catalog['rbs'])
    terminator_id = random.choice(parts_catalog['terminators'])
    
    components = {
        'repressor1': repressor1_id,
        'repressor2': repressor2_id,
        'repressor3': repressor3_id,
        'rbs': rbs_id,
        'terminator': terminator_id
    }
    
    return create_repressilator(doc, components), rbs_id, terminator_id

# Function to assemble the repressilator circuit
def assemble_repressilator(doc, circuit, repressilator, rbs_id, terminator_id):
    # Create RBS and Terminator components
    rbs = create_component(doc, 'rbs_' + rbs_id, rbs_id, sbol2.SO_RBS)
    terminator = create_component(doc, 'terminator_' + terminator_id, terminator_id, sbol2.SO_TERMINATOR)
    
    # Assemble the primary structure in the correct order
    components = [
        repressilator['promoter1'],
        rbs,
        repressilator['repressor1'],
        terminator,
        repressilator['promoter2'],
        rbs,
        repressilator['repressor2'],
        terminator,
        repressilator['promoter3'],
        rbs,
        repressilator['repressor3'],
        terminator
    ]
    
    circuit.assemblePrimaryStructure(components)


def generate_oscillator(doc, parts_catalog):
    unique_id = str(uuid.uuid4())
    circuit = sbol2.ComponentDefinition(f"repressilator_oscillator_{unique_id}")
    doc.addComponentDefinition(circuit)
    repressilator, rbs_id, terminator_id = generate_repressilator(doc, parts_catalog)
    assemble_repressilator(doc, circuit, repressilator, rbs_id, terminator_id)
    return circuit


