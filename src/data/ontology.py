# Predefined ontology terms for types
import sbol2
sbol2.SO_PROMOTER

BIOPAX_DNA = 'http://www.biopax.org/release/biopax-level3.owl#Dna'
BIOPAX_RNA = 'http://www.biopax.org/release/biopax-level3.owl#Rna'
BIOPAX_PROTEIN = 'http://www.biopax.org/release/biopax-level3.owl#Protein'
BIOPAX_SMALL_MOLECULE = 'http://www.biopax.org/release/biopax-level3.owl#SmallMolecule'
BIOPAX_COMPLEX = 'http://www.biopax.org/release/biopax-level3.owl#Complex'
BIOPAX_GENERIC = 'http://www.biopax.org/release/biopax-level3.owl#PhysicalEntity'

# Predefined ontology terms for roles
SO_PROMOTER = 'http://identifiers.org/so/SO:0000167'
SO_CDS = 'http://identifiers.org/so/SO:0000316'
SO_TERMINATOR = 'http://identifiers.org/so/SO:0000141'
SO_RBS = 'http://identifiers.org/so/SO:0000139'
SO_ORIGIN_OF_REPLICATION = 'http://identifiers.org/so/SO:0000296'
SO_OPERATOR = 'http://identifiers.org/so/SO:0000057'
SO_ENHANCER = 'http://identifiers.org/so/SO:0000165'
SO_INSULATOR = 'http://identifiers.org/so/SO:0000627'
SO_REPORTER = 'http://identifiers.org/so/SO:0000628'
SO_SPACER = 'http://identifiers.org/so/SO:0001624'
SO_PRIMER = 'http://identifiers.org/so/SO:0000112'
SO_GENERIC = 'http://identifiers.org/so/SO:0000001'

SBO_STIMULATION = 'http://identifiers.org/biomodels.sbo/SBO:0000170'
SBO_INHIBITION = 'http://identifiers.org/biomodels.sbo/SBO:0000169'
SBO_CONTROLLER = 'http://identifiers.org/biomodels.sbo/SBO:0000019'
SBO_CONTROLLED = 'http://identifiers.org/biomodels.sbo/SBO:0000645'
SBO_MODIFIER = 'http://identifiers.org/biomodels.sbo/SBO:0000019'
SBO_MODIFIED = 'http://identifiers.org/biomodels.sbo/SBO:0000644'
SBO_GENERIC = 'http://identifiers.org/biomodels.sbo/SBO:0000000'

# Dictionary of valid types and roles
VALID_TYPES = {
    'biopax-level3.owl#Dna': BIOPAX_DNA,
    'biopax-level3.owl#Rna': BIOPAX_RNA,
    'biopax-level3.owl#Protein': BIOPAX_PROTEIN,
    'biopax-level3.owl#SmallMolecule': BIOPAX_SMALL_MOLECULE,
    'biopax-level3.owl#Complex': BIOPAX_COMPLEX,
}

VALID_ROLES = {
    'SO:0000167': SO_PROMOTER,
    'SO:0000316': SO_CDS,
    'SO:0000141': SO_TERMINATOR,
    'SO:0000139': SO_RBS,
    'SO:0000296': SO_ORIGIN_OF_REPLICATION,
    'SO:0000057': SO_OPERATOR,
    'SO:0000165': SO_ENHANCER,
    'SO:0000627': SO_INSULATOR,
    'SO:0000628': SO_REPORTER,
    'SO:0001624': SO_SPACER,
    'SO:0000112': SO_PRIMER,
    'SO:0000001': SO_GENERIC,
    'SBO:0000170': SBO_STIMULATION,
    'SBO:0000169': SBO_INHIBITION,
    'SBO:0000019': SBO_CONTROLLER,
    'SBO:0000645': SBO_CONTROLLED,
    'SBO:0000019': SBO_MODIFIER,
    'SBO:0000644': SBO_MODIFIED,
    'SBO:0000000': SBO_GENERIC,
}

# Role mapping to standardize roles
ROLE_MAPPING = {
    'Composite': SO_GENERIC,
    'Reporter': SO_REPORTER,
    'Measurement': SO_GENERIC,
    'Intermediate': SO_GENERIC,
    'Device': SO_GENERIC,
    'Signalling': SO_GENERIC,
    'Generator': SO_GENERIC,
    'Terminator': SO_TERMINATOR,
    'Inverter': SO_GENERIC,
    'Coding': SO_CDS,
    'Plasmid': BIOPAX_DNA,
    'Regulatory': SO_PROMOTER,
    'RNA': BIOPAX_RNA,
    'DNA': BIOPAX_DNA,
    'Temporary': SO_GENERIC,
    'Project': SO_GENERIC,
    'Other': SO_GENERIC
}
