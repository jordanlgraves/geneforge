import json
import os

import sbol2

from geneforge.data.io import write_sbol_file

def create_component_definition(component_data, doc):
    """
    Create a ComponentDefinition object from the structured component data.
    """
    component_definition = sbol2.ComponentDefinition(component_data['display_id'])
    component_definition.name = component_data['name']
    component_definition.description = component_data['description']
    component_definition.types = component_data['types']
    component_definition.roles = component_data['roles']
    
    for component in component_data['components']:
        sub_component = sbol2.Component(component['display_id'])
        sub_component.name = component['name']
        sub_component.definition = component['definition']
        sub_component.roles = component['roles']
        component_definition.components.add(sub_component)

    for sc_data in component_data['sequence_constraints']:
        sc = sbol2.SequenceConstraint(sc_data['subject'], sc_data['object'], sc_data['restriction'])
        component_definition.sequenceConstraints.add(sc)
        
    doc.addComponentDefinition(component_definition)

def structured_data_to_sbol(structured_data):
    """
    Convert structured data to SBOL format.
    """
    doc = sbol2.Document()
    
    for component_data in structured_data:
        create_component_definition(component_data, doc)
    
    return doc

def create_module_definition(module_data, doc):
    """
    Create a ModuleDefinition object from the structured module data.
    """
    module_definition = sbol2.ModuleDefinition(module_data['display_id'])
    module_definition.name = module_data['name']
    module_definition.description = module_data['description']
    
    for func_comp_data in module_data['functional_components']:
        func_comp = sbol2.FunctionalComponent(func_comp_data['display_id'])
        func_comp.name = func_comp_data['name']
        func_comp.definition = func_comp_data['definition']
        func_comp.access = func_comp_data['access']
        func_comp.direction = func_comp_data['direction']
        module_definition.functionalComponents.add(func_comp)
    
    for interaction_data in module_data['interactions']:
        interaction = sbol2.Interaction(interaction_data['display_id'])
        interaction.name = interaction_data['name']
        interaction.types = interaction_data['types']
        for participation_data in interaction_data['participations']:
            participant = sbol2.Participation(participation_data['display_id'])
            participant.roles = participation_data['roles']
            participant.participant = participation_data['participant']
            interaction.participations.add(participant)
        module_definition.interactions.add(interaction)
    
    for module_data in module_data['modules']:
        sub_module = create_module_definition(module_data, doc)
        module_definition.modules.add(sub_module)
    
    doc.addModuleDefinition(module_definition)
    return module_definition

def structured_data_to_sbol(structured_data):
    """
    Convert structured data to SBOL format.
    """
    doc = sbol2.Document()
    
    for component_data in structured_data:
        if 'components' in component_data:
            create_component_definition(component_data, doc)
        elif 'modules' in component_data:
            create_module_definition(component_data, doc)
    
    return doc

if __name__ == "__main__":
    with open('data/syn_bio_hub/sbol/structured/BBa_I721006.json', 'r') as f:
        structured_data = json.load(f)
    
    doc = structured_data_to_sbol(structured_data)
    os.makedirs('data/syn_bio_hub/json_to_sbol', exist_ok=True)
    write_sbol_file(doc, 'data/syn_bio_hub/json_to_sbol/BBa_I721006.sbol')