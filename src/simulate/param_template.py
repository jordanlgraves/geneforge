import libsbml
import tellurium as te
from typing import Union

def build_param_template(sbml: Union[str, libsbml.SBMLDocument]) -> dict: # TODO: Add a function to build a param template from a SBML file
    """
    Scan an SBML model and return a dict with every species and
    parameter ID mapped to {'value': None, 'source': None}.
    
    ─ species → concentration / amount to set at t = 0
    ─ parameters → any global or local kinetic constants
    """
    if isinstance(sbml, str):
        sbml_doc = libsbml.readSBMLFromFile(sbml)
    else:
        sbml_doc = sbml

    model     = sbml_doc.getModel()
    template  = {'species': {}, 'parameters': {}}

    # 1. Species (floating + boundary)
    for sp in model.getListOfSpecies():
        template['species'][sp.getId()] = {
            'value': None,     # concentration or amount
            'unit' : sp.getUnits() or 'dimensionless',
            'source': None     # will hold BioNumbers ID, DOI, or 'heuristic'
        }

    # 2. Global parameters
    for gp in model.getListOfParameters():
        template['parameters'][gp.getId()] = {
            'value': None,
            'unit' : gp.getUnits() or 'dimensionless',
            'source': None
        }

    # 3. Local kinetic-law parameters (tag with reaction for uniqueness)
    for rxn in model.getListOfReactions():
        kl = rxn.getKineticLaw()
        if kl is None:
            continue
        for lp in kl.getListOfParameters():
            key = f"{rxn.getId()}::{lp.getId()}"   # unique within model
            template['parameters'][key] = {
                'value': None,
                'unit' : lp.getUnits() or 'dimensionless',
                'source': None
            }

    # Load the model into tellurium
    if isinstance(sbml, str):
        rr = te.loadSBMLModel(sbml)
    else:
        sbml_str = libsbml.writeSBMLToString(sbml_doc)
        rr = te.loadSBMLModel(sbml_str)

    # Set the parameters
    for param in template['parameters']:
        try:
            value = rr.getGlobalParameterByName(param)
            template['parameters'][param]['value'] = value
            template['parameters'][param]['source'] = 'from SBML'
        except:
            print('Skipping parameter: ', param)

    return template

def get_param_template_from_antimony(antimony_model: str):
    sbml_model = te.antimonyToSBML(antimony_model)
    doc = libsbml.readSBMLFromString(sbml_model)
    return build_param_template(doc)