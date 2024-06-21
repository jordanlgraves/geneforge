# Predefined ontology terms for types
import sbol2
from sbol2 import *

SYNBIOHUB_IGEM_URL = 'https://synbiohub.org/public/igem/'
SYNBIO_TERMS_HTTPS_URL = 'https://wiki.synbiohub.org/wiki/Terms/synbiohub#'
SYNBIO_TERMS_HTTP_URL = 'http://wiki.synbiohub.org/wiki/Terms/synbiohub#'
PURL_URL = 'http://purl.org/dc'

# ADDED TERMS NOT IN SBOL2
BIOPAX_URI = "http://www.biopax.org/release/biopax-level3.owl#"
BIOPAX_GENERIC = BIOPAX_URI + 'PhysicalEntity'

# Predefined ontology terms for roles
SO_ORIGIN_OF_REPLICATION = 'http://identifiers.org/so/SO:0000296'
SO_OPERATOR = 'http://identifiers.org/so/SO:0000057'
SO_ENHANCER = 'http://identifiers.org/so/SO:0000165'
SO_INSULATOR = 'http://identifiers.org/so/SO:0000627'
SO_REPORTER = 'http://identifiers.org/so/SO:0000628'
SO_SPACER = 'http://identifiers.org/so/SO:0001624'
SO_PRIMER = 'http://identifiers.org/so/SO:0000112'
SO_STEM_LOOP = 'http://identifiers.org/so/SO:0000313'
SO_BINDING = 'http://identifiers.org/so/SO:0001091'
SO_GENERIC = 'http://identifiers.org/so/SO:0000001'
SO_ENGINEERED_REGION = 'http://identifiers.org/so/SO:0000804'
SO_TAG = 'http://identifiers.org/so/SO:0000324'
SO_POLYA = 'http://identifiers.org/so/SO:0000553'
SO_ENGINEERED_TAG = 'http://identifiers.org/so/SO:0000807'
SO_SIGNATURE = 'http://identifiers.org/so/SO:0001978'
SO_NC_CONSERVERED_REGION = 'http://identifiers.org/so/SO:0000334'
SO_CONSERVED_REGION = 'http://identifiers.org/so/SO:0000330'
SO_STOP_CODON = 'http://identifiers.org/so/SO:0000319'
SO_START_CODON = 'http://identifiers.org/so/SO:0000318'
SO_MISC = 'http://identifiers.org/so/SO:0000110'
SO_POINT_MUTATION = 'http://identifiers.org/so/SO:1000008'
SO_ORIGIN_OF_TRANSFER = "http://identifiers.org/so/SO:0000724"
SO_MATURE_TRANSCRIPT = "http://identifiers.org/so/SO:0000834"
SO_MUTATION = "http://identifiers.org/so/SO:0001059"
SO_CHROMOSOME = "http://identifiers.org/so/SO:0000340"
SO_PRIMER_BINDING_SITE = "http://identifiers.org/so/SO:0005850"
SO_NUCLEOTIDE_BS = 'http://identifiers.org/so/SO:0001655'
SO_POLYPEPTIDE_DOMAIN = 'http://identifiers.org/so/SO:0000417'

SBO_STIMULATION = 'http://identifiers.org/biomodels.sbo/SBO:0000170'
SBO_INHIBITION = 'http://identifiers.org/biomodels.sbo/SBO:0000169'
SBO_CONTROLLER = 'http://identifiers.org/biomodels.sbo/SBO:0000019'
SBO_CONTROLLED = 'http://identifiers.org/biomodels.sbo/SBO:0000645'
SBO_MODIFIER = 'http://identifiers.org/biomodels.sbo/SBO:0000019'
SBO_MODIFIED = 'http://identifiers.org/biomodels.sbo/SBO:0000644'
SBO_GENERIC = 'http://identifiers.org/biomodels.sbo/SBO:0000000'


# USEFUL SYNBIOHUB keys
# http://wiki.synbiohub.org/wiki/Terms/synbiohub#mutableProvenance
# http://wiki.synbiohub.org/wiki/Terms/synbiohub#mutableNotes
# http://wiki.synbiohub.org/wiki/Terms/synbiohub#mutableDescription

# NONUSEFUL SYNBIOHUB keys
# http://wiki.synbiohub.org/wiki/Terms/synbiohub#ownedBy
# http://wiki.synbiohub.org/wiki/Terms/synbiohub#topLevel
# http://wiki.synbiohub.org/wiki/Terms/synbiohub#ownedBy
# http://wiki.synbiohub.org/wiki/Terms/synbiohub#ownedBy
# http://wiki.synbiohub.org/wiki/Terms/synbiohub#bookmark
# http://wiki.synbiohub.org/wiki/Terms/synbiohub#star
SYNBIO_MUTABLE_PROVENANCE = SYNBIO_TERMS_HTTPS_URL + 'mutableProvenance'
SYNBIO_MUTABLE_NOTES = SYNBIO_TERMS_HTTPS_URL + 'mutableNotes'
SYNBIO_MUTABLE_DESCRIPTION = SYNBIO_TERMS_HTTPS_URL + 'mutableDescription'

IGEM_DIRECTION_URI = IGEM_URI + '#direction'
IGEM_DIRECTION_REVERSE = IGEM_DIRECTION_URI + '/reverse'
IGEM_DIRECTION_FORWARD = IGEM_DIRECTION_URI + '/forward'

# Dictionary of valid types and roles allows in stanrdardization/normalization
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
    'SO:0000313': SO_STEM_LOOP,
    'SO:0000001': SO_GENERIC,
    'SO:0001091': SO_BINDING,
    'SO:0000804': SO_ENGINEERED_REGION,
    'SO:0000324': SO_TAG,
    'SO:0000553': SO_POLYA,
    'SO:0000807': SO_ENGINEERED_TAG,
    'SO:0001978': SO_SIGNATURE,
    'SO:0001091': SO_BINDING,
    'SO:0000334': SO_NC_CONSERVERED_REGION,
    'SO:0000330': SO_CONSERVED_REGION,
    'SO:0000319': SO_STOP_CODON,
    'SO:0000318': SO_START_CODON,
    'SO:0000110': SO_MISC,
    'SO:1000008': SO_POINT_MUTATION,
    'SO:0000724': SO_ORIGIN_OF_TRANSFER,
    'SO:0000155': SO_PLASMID,
    'SO:0000834': SO_MATURE_TRANSCRIPT,
    'SO:0001059': SO_MUTATION,
    'SO:0000340': SO_CHROMOSOME,
    'SO:0001655': SO_NUCLEOTIDE_BS,
    'SO:0005850': SO_PRIMER_BINDING_SITE,
    'SO:0000417': SO_POLYPEPTIDE_DOMAIN,
    'SBO:0000170': SBO_STIMULATION,
    'SBO:0000169': SBO_INHIBITION,
    'SBO:0000019': SBO_CONTROLLER,
    'SBO:0000645': SBO_CONTROLLED,
    'SBO:0000019': SBO_MODIFIER,
    'SBO:0000644': SBO_MODIFIED,
    'SBO:0000000': SBO_GENERIC
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
    'CDS': SO_CDS,
    'Plasmid': BIOPAX_DNA,
    'Regulatory': SO_PROMOTER,
    'RNA': BIOPAX_RNA,
    'DNA': BIOPAX_DNA,
    'Temporary': SO_GENERIC,
    'Project': SO_GENERIC,
    'Other': SO_GENERIC,
    'RBS': SO_RBS,
    'Spacer': SO_SPACER,
    'Insulator': SO_INSULATOR,
    'Operator': SO_OPERATOR,
    'Enhancer': SO_ENHANCER,
    'Primer': SO_PRIMER,
    'Origin of Replication': SO_ORIGIN_OF_REPLICATION,
    'Stem Loop': SO_STEM_LOOP,
    'Binding': SO_BINDING,
    'Tag': SO_TAG,
    'Protein': BIOPAX_PROTEIN,
    'Engineered Region': SO_ENGINEERED_REGION,
    'PolyA': SO_POLYA,
    'Engineered Tag': SO_ENGINEERED_TAG,
    'Signature': SO_SIGNATURE,
    'SO_SEQUENCE_FEATURE': SO_MISC,
    'Non-coding Conserved Region': SO_NC_CONSERVERED_REGION,
    'Conserved Region': SO_CONSERVED_REGION,
    'Inhibitor': SBO_INHIBITION,
    'Stimulator': SBO_STIMULATION,
    'Controller': SBO_CONTROLLER,
    'Controlled': SBO_CONTROLLED,
    'Modifier': SBO_MODIFIER,
    'Modified': SBO_MODIFIED,
    'Generic': SBO_GENERIC,
    'Stop Codon': SO_STOP_CODON,
    'Start Codon': SO_START_CODON,
    'Misc': SO_MISC,
    'Point Mutation': SO_POINT_MUTATION,
    'Transfer Initiation Region': SO_ORIGIN_OF_TRANSFER,
    'Mature Transcript': SO_MATURE_TRANSCRIPT,
    'Mutation': SO_MUTATION,
    'Chromosome': SO_CHROMOSOME,
    'Nucleotide Binding Site': SO_NUCLEOTIDE_BS,
    'Primer Binding Site': SO_PRIMER_BINDING_SITE,
    'Polypeptide Domain': SO_POLYPEPTIDE_DOMAIN
}

# LIST OF URIS FOR MAPPING TO AND FROM SIMPLE NAMES
SBOL_URIS = [
    SBOL_DOCUMENT,
    SBOL_IDENTIFIED,
    SBOL_DOCUMENTED,
    SBOL_TOP_LEVEL,
    SBOL_GENERIC_TOP_LEVEL,
    SBOL_SEQUENCE_ANNOTATION,
    SBOL_COMPONENT,
    SBOL_FUNCTIONAL_COMPONENT,
    SBOL_COMPONENT_DEFINITION,
    SBOL_SEQUENCE,
    SBOL_MODULE_DEFINITION,
    SBOL_MODULE,
    SBOL_MODEL,
    SBOL_MAPS_TO,
    SBOL_INTERACTION,
    SBOL_PARTICIPATION,
    SBOL_SEQUENCE_CONSTRAINT,
    SBOL_LOCATION,
    SBOL_RANGE,
    SBOL_CUT,
    SBOL_COLLECTION,
    SBOL_GENERIC_LOCATION,
    SBOL_VARIABLE_COMPONENT,
    SBOL_COMBINATORIAL_DERIVATION,
    SBOL_ATTACHMENT,
    SBOL_IMPLEMENTATION,
    SBOL_EXPERIMENT,
    SBOL_EXPERIMENTAL_DATA,
    UNDEFINED,
    SBOL_IDENTITY,
    SBOL_PERSISTENT_IDENTITY,
    SBOL_VERSION,
    SBOL_DISPLAY_ID,
    SBOL_TYPES,
    SBOL_START,
    SBOL_END,
    SBOL_SEQUENCE_ANNOTATIONS,
    SBOL_COMPONENTS,
    SBOL_COMPONENT_PROPERTY,
    SBOL_ROLES,
    SBOL_ELEMENTS,
    SBOL_ENCODING,
    SBOL_SEQUENCE_PROPERTY,
    SBOL_DEFINITION,
    SBOL_ACCESS,
    SBOL_DIRECTION,
    SBOL_MODELS,
    SBOL_MODULES,
    SBOL_FUNCTIONAL_COMPONENTS,
    SBOL_INTERACTIONS,
    SBOL_MAPS_TOS,
    SBOL_PARTICIPATIONS,
    SBOL_PARTICIPANT,
    SBOL_LOCAL,
    SBOL_REMOTE,
    SBOL_REFINEMENT,
    SBOL_SOURCE,
    SBOL_LANGUAGE,
    SBOL_FRAMEWORK,
    SBOL_SEQUENCE_CONSTRAINTS,
    SBOL_SUBJECT,
    SBOL_OBJECT,
    SBOL_RESTRICTION,
    SBOL_ORIENTATION,
    SBOL_LOCATIONS,
    SBOL_SOURCE_LOCATIONS,
    SBOL_ROLE_INTEGRATION,
    SBOL_MEMBERS,
    SBOL_AT,
    SBOL_OPERATOR,
    SBOL_VARIABLE_COMPONENTS,
    SBOL_VARIABLE,
    SBOL_VARIANTS,
    SBOL_VARIANT_COLLECTIONS,
    SBOL_VARIANT_DERIVATIONS,
    SBOL_STRATEGY,
    SBOL_TEMPLATE,
    SBOL_ATTACHMENTS,
    SBOL_MEASUREMENTS,
    SBOL_UNIT,
    SBOL_VALUE,
    SBOL_ACCESS_PRIVATE,
    SBOL_ACCESS_PUBLIC,
    SBOL_DIRECTION_IN,
    SBOL_DIRECTION_OUT,
    SBOL_DIRECTION_IN_OUT,
    SBOL_DIRECTION_NONE,
    SBOL_RESTRICTION_PRECEDES,
    SBOL_RESTRICTION_SAME_ORIENTATION_AS,
    SBOL_RESTRICTION_OPPOSITE_ORIENTATION_AS,
    SBOL_ORIENTATION_INLINE,
    SBOL_ORIENTATION_REVERSE_COMPLEMENT,
    SBOL_REFINEMENT_USE_REMOTE,
    SBOL_REFINEMENT_USE_LOCAL,
    SBOL_REFINEMENT_VERIFY_IDENTICAL,
    SBOL_REFINEMENT_MERGE,
    SBOL_ROLE_INTEGRATION_MERGE,
    SBOL_ROLE_INTEGRATION_OVERRIDE,
    SBOL_DESIGN,
    SBOL_BUILD,
    SBOL_TEST,
    SBOL_LEARN
]

SBO_URIS = [
    SBO_INTERACTION,
    SBO_INHIBITION,
    SBO_GENETIC_PRODUCTION,
    SBO_NONCOVALENT_BINDING,
    SBO_STIMULATION,
    SBO_DEGRADATION,
    SBO_CONTROL,
    SBO_BIOCHEMICAL_REACTION,
    SBO_STIMULATED,
    SBO_CONVERSION,
    SBO_PROMOTER,
    SBO_GENE,
    SBO_INHIBITOR,
    SBO_INHIBITED,
    SBO_STIMULATOR,
    SBO_REACTANT,
    SBO_PRODUCT,
    SBO_LIGAND,
    SBO_NONCOVALENT_COMPLEX,
    SBO_BINDING_SITE,
    SBO_SUBSTRATE,
    SBO_COFACTOR,
    SBO_SIDEPRODUCT,
    SBO_ENZYME,
    SBO_CONTINUOUS,
    SBO_DISCRETE
]

SO_URIS = [
    SO_MISC,
    SO_GENE,
    SO_PROMOTER,
    SO_CDS,
    SO_RBS,
    SO_TERMINATOR,
    SO_SGRNA,
    SO_LINEAR,
    SO_CIRCULAR,
    SO_PLASMID,
    SO_ORIGIN_OF_REPLICATION,
    SO_OPERATOR,
    SO_ENHANCER,
    SO_INSULATOR,
    SO_REPORTER,
    SO_SPACER,
    SO_PRIMER,
    SO_STEM_LOOP,
    SO_BINDING,
    SO_GENERIC,
    SO_ENGINEERED_REGION,
    SO_TAG,
    SO_POLYA,
    SO_ENGINEERED_TAG,
    SO_SIGNATURE,
    SO_NC_CONSERVERED_REGION,
    SO_CONSERVED_REGION,
    SO_STOP_CODON,
    SO_START_CODON,
    SO_POINT_MUTATION,
    SO_MISC,
    SO_ORIGIN_OF_TRANSFER,
    SO_OPERATOR,
    SO_MATURE_TRANSCRIPT,
    SO_MUTATION,
    SO_CHROMOSOME,
    SO_NUCLEOTIDE_BS,
    SO_PRIMER_BINDING_SITE,
    SO_POLYPEPTIDE_DOMAIN
]

BIOPAX_URIS = [
    BIOPAX_DNA,
    BIOPAX_RNA,
    BIOPAX_PROTEIN,
    BIOPAX_SMALL_MOLECULE,
    BIOPAX_COMPLEX,
    BIOPAX_GENERIC
]

PURL_URI = [
    SBOL_NAME,
    SBOL_DESCRIPTION
]

IGEM_URIS = [
    IGEM_DIRECTION_REVERSE,
    IGEM_DIRECTION_FORWARD
]

SYNBIO_TERMS_URIS = [
    SYNBIO_MUTABLE_PROVENANCE,
    SYNBIO_MUTABLE_NOTES,
    SYNBIO_MUTABLE_DESCRIPTION
]

SBOL_URIS_TO_NAMES = {k: k.split('#')[-1] for k in SBOL_URIS}
SO_URIS_TO_NAMES = {k: k.split('/')[-1] for k in SO_URIS}
BIOPAX_URIS_TO_NAMES = {k: k.split('#')[-1] for k in BIOPAX_URIS}
PURL_URIS_TO_NAMES = {k: k.split('/')[-1] for k in PURL_URI}
IGEM_URIS_TO_NAMES = {k: k.split('#')[-1] for k in IGEM_URIS}
SYNBIO_TERMS_URIS_TO_NAMES = {k: k.split('#')[-1] for k in SYNBIO_TERMS_URIS}

URIS_TO_SIMPLE_NAMES = {
    **SBOL_URIS_TO_NAMES, 
    **SO_URIS_TO_NAMES, 
    **BIOPAX_URIS_TO_NAMES, 
    **PURL_URIS_TO_NAMES,
    **IGEM_URIS_TO_NAMES,
    **SYNBIO_TERMS_URIS_TO_NAMES
}
SIMPLE_NAMES_TO_URIS = {v: k for k, v in URIS_TO_SIMPLE_NAMES.items()}
assert(len(URIS_TO_SIMPLE_NAMES) == len(SIMPLE_NAMES_TO_URIS))