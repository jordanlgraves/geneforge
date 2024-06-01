import os
import uuid
import sbol2
import requests
import random
import sbol2
import requests
import random
import libsbml
import tellurium as te
import numpy as np
import matplotlib.pyplot as plt


# Initialize SBOL document
sbol2.setHomespace('http://example.org')
doc = sbol2.Document()

# Placeholder functions for fetching sequences
def fetch_sequence(part_id):
    url = f'https://synbiohub.org/public/igem/{part_id}/1/sbol'
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception('Failed to fetch part sequence')

# Function to create a component and add it to the document
def create_component(doc, name, part_id, role):
    uri = f'https://synbiohub.org/public/igem/{part_id}/1'
    if uri in doc.componentDefinitions:
        return doc.componentDefinitions[uri]
    else:
        sbol_string = fetch_sequence(part_id)
        temp_doc = sbol2.Document()
        temp_doc.readString(sbol_string)
        component = temp_doc.componentDefinitions[0]
        component.name = name
        component.roles = [role]
        doc.addComponentDefinition(component)
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


# Generate different types of FFLs
coherent_ffl_type1 = {
    'A_B': 'activation',
    'A_C': 'activation',
    'B_C': 'activation'
}
coherent_ffl_type2 = {
    'A_B': 'repression',
    'A_C': 'repression',
    'B_C': 'repression'
}
coherent_ffl_type3 = {
    'A_B': 'activation',
    'A_C': 'repression',
    'B_C': 'repression'
}
coherent_ffl_type4 = {
    'A_B': 'repression',
    'A_C': 'activation',
    'B_C': 'activation'
}
incoherent_ffl_type1 = {
    'A_B': 'activation',
    'A_C': 'repression',
    'B_C': 'activation'
}
incoherent_ffl_type2 = {
    'A_B': 'activation',
    'A_C': 'activation',
    'B_C': 'repression'
}
incoherent_ffl_type3 = {
    'A_B': 'repression',
    'A_C': 'activation',
    'B_C': 'repression'
}
incoherent_ffl_type4 = {
    'A_B': 'repression',
    'A_C': 'repression',
    'B_C': 'activation'
}

# Generate circuits for each FFL type
coherent_ffl_type1_circuit = generate_ffl(doc, parts_catalog, coherent_ffl_type1)
coherent_ffl_type2_circuit = generate_ffl(doc, parts_catalog, coherent_ffl_type2)
coherent_ffl_type3_circuit = generate_ffl(doc, parts_catalog, coherent_ffl_type3)
coherent_ffl_type4_circuit = generate_ffl(doc, parts_catalog, coherent_ffl_type4)
incoherent_ffl_type1_circuit = generate_ffl(doc, parts_catalog, incoherent_ffl_type1)
incoherent_ffl_type2_circuit = generate_ffl(doc, parts_catalog, incoherent_ffl_type2)
incoherent_ffl_type3_circuit = generate_ffl(doc, parts_catalog, incoherent_ffl_type3)
incoherent_ffl_type4_circuit = generate_ffl(doc, parts_catalog, incoherent_ffl_type4)

# Save the document
doc.write('parts/ffl_gene_circuits.xml')


# Function to create an SBML model for a given circuit
def create_sbml_model(circuit, interactions=None):
    # Create a new SBML document
    document = libsbml.SBMLDocument(3, 1)
    model = document.createModel()

    # Add compartment
    compartment = model.createCompartment()
    compartment.setId('cell')
    compartment.setConstant(True)

    # Add species
    species_list = []
    for component in circuit.components:
        species_id = circuit.name # os.path.split(component.identity)[-1]
        species_list.append(species_id)
        species = model.createSpecies()
        species.setId(species_id)
        species.setCompartment('cell')
        species.setInitialConcentration(0)
        species.setConstant(False)

    # Add parameters
    parameter_list = ['k' + str(i+1) for i in range(len(species_list))]
    parameter_list.append('kd')
    for parameter_id in parameter_list:
        parameter = model.createParameter()
        parameter.setId(parameter_id)
        parameter.setValue(0.1)
        parameter.setConstant(True)

    # Add reactions
    for i, species_id in enumerate(species_list):
        reaction_id = species_id + '_production'
        reaction = model.createReaction()
        reaction.setId(reaction_id)
        reaction.setReversible(False)

        # Add reactants and products
        species_ref = reaction.createProduct()
        species_ref.setSpecies(species_id)
        species_ref.setStoichiometry(1)

        if interactions:
            for interaction, value in interactions.items():
                if species_id in interaction:
                    modifier = reaction.createModifier()
                    modifier.setSpecies(interaction.replace(species_id, '').strip('_'))
                    kinetic_law = reaction.createKineticLaw()
                    if value == 'repression':
                        math_ast = libsbml.parseL3Formula(f"k{i+1} / (1 + {interaction.replace(species_id, '').strip('_')})")
                    else:  # activation
                        math_ast = libsbml.parseL3Formula(f"k{i+1} * {interaction.replace(species_id, '').strip('_')}")
                    kinetic_law.setMath(math_ast)
        else:
            kinetic_law = reaction.createKineticLaw()
            math_ast = libsbml.parseL3Formula(f"k{i+1}")
            kinetic_law.setMath(math_ast)

        reaction_id = species_id + '_degradation'
        reaction = model.createReaction()
        reaction.setId(reaction_id)
        reaction.setReversible(False)

        species_ref = reaction.createReactant()
        species_ref.setSpecies(species_id)
        species_ref.setStoichiometry(1)

        kinetic_law = reaction.createKineticLaw()
        math_ast = libsbml.parseL3Formula(f"kd * {species_id}")
        kinetic_law.setMath(math_ast)

    return document


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

# Function to generate a repressilator circuit
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

# Example usage
def generate_oscillator(doc, parts_catalog):
    unique_id = str(uuid.uuid4())
    circuit = sbol2.ComponentDefinition(f"repressilator_oscillator_{unique_id}")
    doc.addComponentDefinition(circuit)
    repressilator, rbs_id, terminator_id = generate_repressilator(doc, parts_catalog)
    assemble_repressilator(doc, circuit, repressilator, rbs_id, terminator_id)
    return circuit

# Function to simulate the SBML model and plot the results
def simulate_and_plot(doc, time_span):
    # Create a roadrunner instance and load the SBML model
    temp_file = 'temp_model.xml'
    libsbml.writeSBMLToFile(doc, temp_file)

    # Load the SBML model from the file
    r = te.loadSBMLModel(temp_file)

    # Simulate the model
    result = r.simulate(0, time_span, 100)

    # Plot the results
    plt.figure()
    for species_id in ['A', 'B', 'C']:
        plt.plot(result[:, 0], result[:, r.model.getFloatingSpeciesIds().index(species_id) + 1], label=species_id)
    plt.xlabel('Time')
    plt.ylabel('Concentration')
    plt.legend()
    plt.show()



# Function to create an SBML model for a repressilator circuit
def create_sbml_model_repressilator(circuit):
    # Create a new SBML document
    document = libsbml.SBMLDocument(3, 1)
    model = document.createModel()

    # Add compartment
    compartment = model.createCompartment()
    compartment.setId('cell')
    compartment.setConstant(True)

    # Add species
    species_list = ['repressor1', 'repressor2', 'repressor3']
    for species_id in species_list:
        species = model.createSpecies()
        species.setId(species_id)
        species.setCompartment('cell')
        species.setInitialConcentration(0)
        species.setConstant(False)

    # Add parameters
    parameter_list = ['k1', 'k2', 'k3', 'kd']
    for parameter_id in parameter_list:
        parameter = model.createParameter()
        parameter.setId(parameter_id)
        parameter.setValue(0.1)
        parameter.setConstant(True)

    # Add reactions
    reaction_list = ['repressor1_production', 'repressor2_production', 'repressor3_production',
                     'repressor1_degradation', 'repressor2_degradation', 'repressor3_degradation']
    for reaction_id in reaction_list:
        reaction = model.createReaction()
        reaction.setId(reaction_id)
        reaction.setReversible(False)

        # Add reactants and products
        if reaction_id.endswith('_production'):
            species_ref = reaction.createProduct()
            species_ref.setSpecies(reaction_id.split('_')[0])
            species_ref.setStoichiometry(1)
            modifier = reaction.createModifier()
            modifier.setSpecies('repressor' + str((int(reaction_id.split('_')[0][-1]) % 3) + 1))
            kinetic_law = reaction.createKineticLaw()
            math_ast = libsbml.parseL3Formula(f"k{reaction_id.split('_')[0][-1]} / (1 + repressor{(int(reaction_id.split('_')[0][-1]) % 3) + 1}^2)")
            kinetic_law.setMath(math_ast)
        else:  # degradation
            species_ref = reaction.createReactant()
            species_ref.setSpecies(reaction_id.split('_')[0])
            species_ref.setStoichiometry(1)
            kinetic_law = reaction.createKineticLaw()
            math_ast = libsbml.parseL3Formula(f"kd * {reaction_id.split('_')[0]}")
            kinetic_law.setMath(math_ast)

    return document

# Example usage
time_span = 10

# Simulate and plot each FFL type
ffl_types = [
    coherent_ffl_type1,
    coherent_ffl_type2,
    coherent_ffl_type3,
    coherent_ffl_type4,
    incoherent_ffl_type1,
    incoherent_ffl_type2,
    incoherent_ffl_type3,
    incoherent_ffl_type4
]

for ffl_type in ffl_types:
    ffl_circuit = generate_ffl(doc, parts_catalog, ffl_type)
    sbml_document = create_sbml_model(ffl_circuit, ffl_type)
    simulate_and_plot(sbml_document, time_span)



# For repressilator circuits
repressilator_circuit = generate_oscillator(doc, parts_catalog)
sbml_document = create_sbml_model(repressilator_circuit)
simulate_and_plot(sbml_document, time_span)