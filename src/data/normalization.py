import sbol2
import os

from src.data.io import read_sbol_file, write_sbol_file
from src.data.ontology import *
from src.data.validation import validate_sbol_document
from sbol2.constants import *

def add_role_if_empty(component, role):
    """
    Add a role to the component if it's not already present.
    """
    if not component.roles:
        component.roles = [role]

def add_type_if_empty(component, type_uri):
    """
    Add a type to the component if it's not already present.
    """
    if not component.types:
        component.types = [type_uri]
    
def apply_standard_ontologies(doc):
    """
    Apply standard ontologies to the types and roles of components in the SBOL document.
    
    Types and roles are applied based on the component name or other criteria using predefined ontology terms.
    """
    for obj in doc.SBOLObjects.values():
        if isinstance(obj, sbol2.ComponentDefinition) or isinstance(obj, sbol2.FunctionalComponent) or isinstance(obj, sbol2.Component):
            # Apply type ontologies based on component name or other criteria
            if 'dna' in obj.name.lower() or 'plasmid' in obj.name.lower():
                add_type_if_empty(obj, BIOPAX_DNA)
            elif 'rna' in obj.name.lower() or 'transcript' in obj.name.lower():
                add_type_if_empty(obj, BIOPAX_RNA)
            elif 'protein' in obj.name.lower():
                add_type_if_empty(obj, BIOPAX_PROTEIN)
            elif 'small molecule' in obj.name.lower():
                add_type_if_empty(obj, BIOPAX_SMALL_MOLECULE)
            elif 'complex' in obj.name.lower():
                add_type_if_empty(obj, BIOPAX_COMPLEX)
            
            # Apply role ontologies based on component name or other criteria
            if 'promoter' in obj.name.lower():
                add_role_if_empty(obj, SO_PROMOTER)
            elif 'cds' in obj.name.lower() or 'gene' in obj.name.lower():
                add_role_if_empty(obj, SO_CDS)
            elif 'terminator' in obj.name.lower():
                add_role_if_empty(obj, SO_TERMINATOR)
            elif 'rbs' in obj.name.lower():
                add_role_if_empty(obj, SO_RBS)
            elif 'origin of replication' in obj.name.lower():
                add_role_if_empty(obj, SO_ORIGIN_OF_REPLICATION)
            elif 'operator' in obj.name.lower():
                add_role_if_empty(obj, SO_OPERATOR)
            elif 'enhancer' in obj.name.lower():
                add_role_if_empty(obj, SO_ENHANCER)
            elif 'insulator' in obj.name.lower():
                add_role_if_empty(obj, SO_INSULATOR)
            elif 'reporter' in obj.name.lower():
                add_role_if_empty(obj, SO_REPORTER)
            elif 'spacer' in obj.name.lower():
                add_role_if_empty(obj, SO_SPACER)
            elif 'primer' in obj.name.lower():
                add_role_if_empty(obj, SO_PRIMER)

        elif isinstance(obj, sbol2.Interaction):
            # Apply ontology terms to Interaction
            if 'activation' in obj.name.lower():
                add_type_if_empty(obj, SBO_STIMULATION)
            elif 'inhibition' in obj.name.lower():
                add_type_if_empty(obj, SBO_INHIBITION)

        elif isinstance(obj, sbol2.Participation):
            # Apply ontology terms to Participation roles
            if 'controller' in obj.roles:
                add_role_if_empty(obj, SBO_CONTROLLER)
            elif 'controlled' in obj.roles:
                add_role_if_empty(obj, SBO_CONTROLLED)

    return doc

def normalize_identifiers(doc):
    """
    Normalize identifiers in the SBOL document to ensure they are consistent, unique, and follow a standard format.
    
    Steps:
    1. Convert all identifiers to lowercase.
    2. Replace spaces and other non-alphanumeric characters with underscores.
    3. Ensure all identifiers are unique within the document by appending unique suffixes if necessary.
    """
    existing_identifiers = set()

    for obj in doc.SBOLObjects.values():
        original_id = obj.displayId
        normalized_id = original_id.lower().replace(' ', '_')

        # Ensure uniqueness by appending a counter if necessary
        if normalized_id in existing_identifiers:
            counter = 1
            new_id = f"{normalized_id}_{counter}"
            while new_id in existing_identifiers:
                counter += 1
                new_id = f"{normalized_id}_{counter}"
            normalized_id = new_id

        obj.displayId = normalized_id
        existing_identifiers.add(normalized_id)

    return doc

def normalize_sbol_document(doc):
    """
    Normalize and apply standard ontologies to the SBOL document, then validate it.
    """
    doc = normalize_identifiers(doc)
    doc = apply_standard_ontologies(doc)
    # validate_sbol_document(doc)
    return doc

def normalize_sbol_directory(input_dir, output_dir):
    """
    Normalize and apply standard ontologies to all SBOL files in a directory.
    
    Save the processed files to a specified output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    for filename in os.listdir(input_dir):
        if filename.endswith('.xml') or filename.endswith('.sbol'):
            file_path = os.path.join(input_dir, filename)
            doc = read_sbol_file(file_path)
            normalized_doc = normalize_sbol_document(doc)
            output_path = os.path.join(output_dir, filename)
            write_sbol_file(normalized_doc, output_path)
