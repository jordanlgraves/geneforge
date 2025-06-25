import tellurium as te
import libsbml

def run_kinetic_model_tellurium(sbml_doc: libsbml.SBMLDocument, 
                                parameters: dict,
                                initial_concentrations: dict):
    """
    
    'initial_concentrations': {'P': {'value': None,
        'unit': 'uM_litre',
    'source': None}}
    
    'parameters': {'kdeg_P': {'value': 1.0, 
    'unit': 'dimensionless',
    'source': 'from SBML'}}}}
    """
    sbml_str = libsbml.writeSBMLToString(sbml_doc)
    rr = te.loadSBMLModel(sbml_str)

    # Set the parameters
    print(parameters)
    for param_name, param_spec in parameters.items():
        rr[param_name] = param_spec['value']
        

    # Set the initial concentrations
    print(initial_concentrations)
    for species_name, species_spec in initial_concentrations.items():
        rr[species_name] = species_spec['value']
        

    # Simulate
    
    return rr.simulate()