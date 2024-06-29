import sbol2
import os
from sbol2.constants import *
from geneforge.data.io import read_sbol_file, write_sbol_file
from geneforge.data.ontology import SO_ENHANCER, SO_INSULATOR, SO_ORIGIN_OF_REPLICATION, SO_PRIMER, SO_SPACER
from geneforge.data.validation import validate_sbol_document

def enrich_component_description(component, additional_description):
    """
    Enrich the component description by appending additional information if it doesn't already contain it.
    """
    if component.description:
        if additional_description not in component.description:
            component.description += f" {additional_description}"
    else:
        component.description = additional_description

def add_role_if_missing(component, role):
    """
    Add a role to the component if it's not already present.
    """
    if role not in component.roles:
        component.roles.append(role)


def annotate_component(component):
    """
    Add detailed annotations to a component without overwriting existing useful descriptions.
    """
    if 'promoter' in component.name.lower():
        enrich_component_description(component, 'Promoter: A region of DNA that initiates transcription of a particular gene.')
        add_role_if_missing(component, SO_PROMOTER)
    elif 'cds' in component.name.lower() or 'gene' in component.name.lower():
        enrich_component_description(component, 'CDS: Coding sequence of a gene.')
        add_role_if_missing(component, SO_CDS)
    elif 'terminator' in component.name.lower():
        enrich_component_description(component, 'Terminator: A sequence that signals the end of transcription.')
        add_role_if_missing(component, SO_TERMINATOR)
    elif 'rbs' in component.name.lower():
        enrich_component_description(component, 'RBS: Ribosome binding site, a sequence where ribosomes bind to initiate translation.')
        add_role_if_missing(component, SO_RBS)
    elif 'origin of replication' in component.name.lower():
        enrich_component_description(component, 'Origin of Replication: A sequence where DNA replication begins.')
        add_role_if_missing(component, SO_ORIGIN_OF_REPLICATION)
    elif 'operator' in component.name.lower():
        enrich_component_description(component, 'Operator: A segment of DNA to which a transcription factor binds to regulate gene expression.')
        add_role_if_missing(component, SO_OPERATOR)
    elif 'enhancer' in component.name.lower():
        enrich_component_description(component, 'Enhancer: A DNA sequence that increases the efficiency of transcription.')
        add_role_if_missing(component, SO_ENHANCER)
    elif 'insulator' in component.name.lower():
        enrich_component_description(component, 'Insulator: A DNA sequence that blocks the interaction between enhancers and promoters.')
        add_role_if_missing(component, SO_INSULATOR)
    elif 'reporter' in component.name.lower():
        enrich_component_description(component, 'Reporter: A gene used to attach a measurable marker to a regulatory sequence.')
        add_role_if_missing(component, SO_REPORTER)
    elif 'spacer' in component.name.lower():
        enrich_component_description(component, 'Spacer: A short DNA sequence located between genes.')
        add_role_if_missing(component, SO_SPACER)
    elif 'primer' in component.name.lower():
        enrich_component_description(component, 'Primer: A short nucleic acid sequence that provides a starting point for DNA synthesis.')
        add_role_if_missing(component, SO_PRIMER)

def annotate_sbol_document(doc):
    """
    Annotate the SBOL document to add detailed metadata without overwriting useful existing descriptions.
    """
    for obj in doc.SBOLObjects.values():
        if isinstance(obj, sbol2.ComponentDefinition) or isinstance(obj, sbol2.FunctionalComponent) or isinstance(obj, sbol2.Component):
            annotate_component(obj)

    return doc

def annotate_sbol_directory(input_dir, output_dir):
    """
    Annotate all SBOL files in a directory to add detailed metadata.
    
    Save the annotated files to a specified output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    for filename in os.listdir(input_dir):
        if filename.endswith('.xml') or filename.endswith('.sbol'):
            file_path = os.path.join(input_dir, filename)
            doc = read_sbol_file(file_path)
            annotated_doc = annotate_sbol_document(doc)
            output_path = os.path.join(output_dir, filename)
            write_sbol_file(annotated_doc, output_path)
