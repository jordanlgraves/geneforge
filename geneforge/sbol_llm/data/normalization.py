import sbol2
import os
from sbol2 import TextProperty

from geneforge.sbol_llm.data.io import read_sbol_file, write_sbol_file
from geneforge.sbol_llm.data.ontology import *
from sbol2.constants import *
from xml.etree import ElementTree as ET


# Mapping for non-standard roles to standard roles
ROLE_MAPPING = {
    "Regulatory": SO_PROMOTER,
    "Composite": SO_ENGINEERED_REGION,
    "Reporter": SO_REPORTER,
    "Terminator": SO_TERMINATOR,
    "Coding": SO_CDS,
    "RBS": SO_RBS,
    "Intermediate": SO_ENGINEERED_REGION,
    "DNA": BIOPAX_DNA,
    "RNA": BIOPAX_RNA,
    "Protein": BIOPAX_PROTEIN,
    "Plasmid": SO_PLASMID,
    "Spacer": SO_SPACER,
    "Insulator": SO_INSULATOR,
    "Operator": SO_OPERATOR,
    "Enhancer": SO_ENHANCER,
    "Primer": SO_PRIMER,
    "Origin of Replication": SO_ORIGIN_OF_REPLICATION,
}

# Mapping for non-standard types to standard types
TYPE_MAPPING = {
    "DNA": BIOPAX_DNA,
    "RNA": BIOPAX_RNA,
    "Protein": BIOPAX_PROTEIN,
    "Small Molecule": BIOPAX_SMALL_MOLECULE,
    "Complex": BIOPAX_COMPLEX,
    # Add other mappings as necessary
}
DEFAULT_TYPE = BIOPAX_DNA

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

# check if role in standard ontology (starts with one of the above)
# if not, check if role in ROLE_MAPPING
def map_role_to_standard_ontology(role, default=None):
    """
    Map a role to a standard ontology term based on the ROLE_MAPPING.
    """
    role_key = role.split('/')[-1]
    if role_key in ROLE_MAPPING:
        return ROLE_MAPPING[role_key]
    return default


def map_roles_to_standard_ontology(roles):
    """
    Map roles to standard ontology terms based on the ROLE_MAPPING.
    """
    mapped_roles = []
    standardized_roles = []
    for role in roles:
        uris = [SBOL_URI, SO, BIOPAX_URI]
        role_key = None
        for uri in uris:
            if role.startswith(uri):
                role_key = role
                standardized_roles.append(role)
                break

    if not standardized_roles:
        # Try determine getting a standard ontology term from the role
        for role in roles:
            standardized_role = map_role_to_standard_ontology(role, default=None)
            if standardized_role is not None:
                standardized_roles.append(standardized_role)

    if not standardized_roles:
        standardized_roles.append(SO_ENGINEERED_REGION)
    return list(set(standardized_roles))  # Remove duplicates

def map_types_to_standardized_ontology(types):
    """
    Map types to standard ontology terms based on the TYPE_MAPPING.
    """
    mapped_types = []
    for type_uri in types:
        standardized_type = TYPE_MAPPING.get(type_uri.split('/')[-1], DEFAULT_TYPE)
        mapped_types.append(standardized_type)
    return list(set(mapped_types))  # Remove duplicates

def apply_standard_ontologies(doc):
    """
    Apply standard ontologies to the types and roles of components in the SBOL document.
    
    Types and roles are applied based on the component name or other criteria using predefined ontology terms.
    """
    unique_ids = set()
    to_remove = []
    for obj in doc.SBOLObjects.values():
        if isinstance(obj, sbol2.Activity):
            # remove the activity objects
            to_remove.append(obj)
            continue

        if isinstance(obj, sbol2.ComponentDefinition) \
            or isinstance(obj, sbol2.FunctionalComponent) \
            or isinstance(obj, sbol2.Component) \
            or isinstance(obj, sbol2.SequenceAnnotation):
            # Apply type ontologies based on component name or other criteria
            obj.types = map_types_to_standardized_ontology(obj.types)
            if not obj.types:
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
            obj.roles = map_roles_to_standard_ontology(obj.roles)
            if not obj.roles:
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
            
            # Print out any components that have empty roles or types after mapping
            if not obj.roles:
                print(f"Component {obj.displayId} has no recognized roles.")
            if not obj.types:
                print(f"Component {obj.displayId} has no recognized types.")

        elif isinstance(obj, sbol2.Interaction):
            # Apply ontology terms to Interaction
            obj.types = map_types_to_standardized_ontology(obj.types)
            if not obj.types:
                if 'activation' in obj.name.lower():
                    add_type_if_empty(obj, SBO_STIMULATION)
                elif 'inhibition' in obj.name.lower():
                    add_type_if_empty(obj, SBO_INHIBITION)
                elif 'degradation' in obj.name.lower():
                    add_type_if_empty(obj, SBO_DEGRADATION)
                elif 'genetic production' in obj.name.lower():
                    add_type_if_empty(obj, SBO_GENETIC_PRODUCTION)
                elif 'control' in obj.name.lower():
                    add_type_if_empty(obj, SBO_CONTROL)

        elif isinstance(obj, sbol2.Participation):
            # Apply ontology terms to Participation roles
            obj.roles = map_roles_to_standard_ontology(obj.roles)
            if not obj.roles:
                if 'controller' in obj.roles:
                    add_role_if_empty(obj, SBO_CONTROLLER)
                elif 'controlled' in obj.roles:
                    add_role_if_empty(obj, SBO_CONTROLLED)

        unique_ids.add(obj.identity)

    for obj in to_remove:
        doc.SBOLObjects.pop(obj)
        
    return doc

def remove_unused_namespaces(doc):
    """
    Remove unused namespace prefixes from the SBOL document.
    """
    xml_string = doc.writeString()
    root = ET.fromstring(xml_string)

    # Get the list of prefix definitions
    prefix_defs = {}
    for key, value in root.attrib.items():
        if key.startswith('{http://www.w3.org/2000/xmlns/}'):
            prefix = key[len('{http://www.w3.org/2000/xmlns/}'):]
            prefix_defs[prefix] = value

    # Find the prefixes that are actually used in the XML
    used_prefixes = set()
    for elem in root.iter():
        for key in elem.attrib:
            if ':' in key:
                prefix = key.split(':')[0]
                used_prefixes.add(prefix)

    # Remove unused prefix definitions
    for prefix, uri in prefix_defs.items():
        if prefix not in used_prefixes:
            del root.attrib['{http://www.w3.org/2000/xmlns/}' + prefix]

    # Convert the modified XML back to an SBOL document
    new_xml_string = ET.tostring(root, encoding='unicode')
    new_doc = sbol2.Document()
    new_doc.readString(new_xml_string)

    return new_doc

def normalize_sbol_document(doc):
    """
    Normalize and apply standard ontologies to the SBOL document, then validate it.
    """
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

if __name__ == "__main__":
    file_id = 'BBa_I719003'
    file_name = f'data/syn_bio_hub/scraped/sbol/{file_id}.sbol'
    doc = read_sbol_file(file_name)
    normalized_doc = normalize_sbol_document(doc)
    write_sbol_file(doc, f'data/syn_bio_hub/sbol/normalized/{file_id}.sbol')
