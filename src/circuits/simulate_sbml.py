import libsbml
from matplotlib import pyplot as plt

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
