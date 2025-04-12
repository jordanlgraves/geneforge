import json
import os
import uuid
import copy
import logging
import tempfile
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import dotenv

dotenv.load_dotenv()

CELLO_UCF_ROOT = os.getenv("CELLO_UCF_ROOT")

import jsonschema
from jsonschema import ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("part_library_customizer")

VERBOSE = False

# Initialize global schema variables
UCF_SCHEMA_PATH = os.path.join(CELLO_UCF_ROOT, "schemas", "v2", "ucf.schema.json")
SCHEMA_DIR = os.path.dirname(UCF_SCHEMA_PATH)
INPUT_SENSOR_SCHEMA_PATH = os.path.join(CELLO_UCF_ROOT, "schemas", "v2", "input_sensor_file.schema.json")
OUTPUT_DEVICE_SCHEMA_PATH = os.path.join(CELLO_UCF_ROOT, "schemas", "v2", "output_device_file.schema.json")

# Initialize validators
def _initialize_validators():
    """Initialize and return schema validators"""
    # Check schema path
    if not os.path.exists(UCF_SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found at {UCF_SCHEMA_PATH}. Cannot validate UCF files.")
    
    # Load schemas
    with open(UCF_SCHEMA_PATH, 'r') as f:
        ucf_schema = json.load(f)

    with open(INPUT_SENSOR_SCHEMA_PATH, 'r') as f:
        input_sensor_schema = json.load(f)

    with open(OUTPUT_DEVICE_SCHEMA_PATH, 'r') as f:
        output_device_schema = json.load(f)
    
    # Set up resolvers for schema references
    schema_base_uri = f"file://{os.path.abspath(SCHEMA_DIR)}/"
    ucf_resolver = jsonschema.RefResolver(base_uri=schema_base_uri, referrer=ucf_schema)
    input_sensor_resolver = jsonschema.RefResolver(base_uri=schema_base_uri, referrer=input_sensor_schema)
    output_device_resolver = jsonschema.RefResolver(base_uri=schema_base_uri, referrer=output_device_schema)
    
    # Create validators with the resolvers
    ucf_validator = jsonschema.Draft7Validator(
        schema=ucf_schema,
        resolver=ucf_resolver
    )
    input_sensor_validator = jsonschema.Draft7Validator(
        schema=input_sensor_schema,
        resolver=input_sensor_resolver
    )
    output_device_validator = jsonschema.Draft7Validator(
        schema=output_device_schema,
        resolver=output_device_resolver
    )

    if VERBOSE:
        logger.info(f"Loaded UCF schema from {UCF_SCHEMA_PATH}")   
        logger.info(f"Loaded input sensor schema from {INPUT_SENSOR_SCHEMA_PATH}")
        logger.info(f"Loaded output device schema from {OUTPUT_DEVICE_SCHEMA_PATH}")
    
    return ucf_validator, input_sensor_validator, output_device_validator, ucf_schema

# Initialize validators once
ucf_validator, input_sensor_validator, output_device_validator, ucf_schema = _initialize_validators()
missing_schemas = []

def _find_schema_references(schema, found_schemas):
    """Recursively find schema references in a schema object"""
    global missing_schemas
    
    if not isinstance(schema, dict):
        return
        
    # Look for $ref fields
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#"):
            # Internal reference
            pass
        elif ref.startswith("file:"):
            # External file reference
            ref_filename = os.path.basename(ref.replace("file:", ""))
            if ref_filename not in found_schemas and ref_filename not in missing_schemas:
                missing_schemas.append(ref_filename)
    
    # Recursively check all objects and arrays
    for key, value in schema.items():
        if isinstance(value, dict):
            _find_schema_references(value, found_schemas)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _find_schema_references(item, found_schemas)

def _scan_schema_directory():
    """Scan the schema directory structure and report missing schemas"""
    global missing_schemas
    
    if not SCHEMA_DIR or not os.path.exists(SCHEMA_DIR):
        raise ValueError(f"Schema directory not found: {SCHEMA_DIR}")
        
    # Check if we're in a Cello-UCF repo
    parent_dir = os.path.dirname(SCHEMA_DIR)
    if os.path.basename(parent_dir) != "schemas":
        logger.warning(f"Unexpected schema directory structure: {SCHEMA_DIR}")
        logger.warning("Expected to find schema directory within a 'schemas' directory in the Cello-UCF repository.")
    
    # List all schema files present
    schema_files = []
    missing_schemas = []
    
    # Check schema directory
    try:
        for file in os.listdir(SCHEMA_DIR):
            if file.endswith('.schema.json'):
                schema_files.append(file)
    except Exception as e:
        raise IOError(f"Error scanning schema directory {SCHEMA_DIR}: {e}")
    
    # Look for required schemas from schema references
    if ucf_schema:
        _find_schema_references(ucf_schema, schema_files)
        
    # Log the results
    if schema_files:
        if VERBOSE:
            logger.info(f"Found {len(schema_files)} schema files in {SCHEMA_DIR}: {', '.join(schema_files)}")
    else:
        raise ValueError(f"No schema files found in {SCHEMA_DIR}")

# Scan schema directory on module initialization
_scan_schema_directory()

def validate_ucf(ucf_data: List[Dict]) -> Dict[str, Any]:
    """
    Validate UCF data against the schema.
    
    Args:
        ucf_data: The UCF data to validate
        
    Returns:
        Validation result dictionary
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(ucf_data, list):
        raise ValueError(f"Invalid UCF format: Expected a list, got {type(ucf_data)}")
        
    # Prepare validation result
    result = {
        "valid": True,
        "errors": []
    }
    
    try:
        # Validate the whole UCF
        ucf_validator.validate(ucf_data)
    except ValidationError as e:
        result["valid"] = False
        result["errors"].append(str(e))
        raise ValidationError(f"UCF validation failed: {e}")
    
    if VERBOSE:
        logger.info(f"UCF validation passed: no schema errors found")
    return result

def get_parts_by_type(data: List[Dict], part_type: str) -> List[Dict]:
    """
    Get all parts of a specific type from UCF data.
    
    Args:
        data: The UCF data to search
        part_type: The type of parts to find (e.g., "promoter", "cds")
        
    Returns:
        List of matching parts
    """
    result = []
    
    for item in data:
        if item.get("collection") == "parts" and item.get("type") == part_type:
            result.append(item)
    
    return result

def get_part_by_name(data: List[Dict], part_name: str) -> Optional[Dict]:
    """
    Get a specific part by name from UCF data.
    
    Args:
        data: The UCF data to search
        part_name: The name of the part to find
        
    Returns:
        The part dictionary if found, None otherwise
    """
    for item in data:
        if item.get("collection") == "parts" and item.get("name") == part_name:
            return item
    
    return None

def filter_parts(data: List[Dict], selected_parts: List) -> List[Dict]:
    """
    Filter UCF data to remove parts that are not in the selected parts list (by name) 
    and share a type with a selected parts.
    Only removes parts if they share a type with the selected parts.
    Cleans up any references to removed parts.
    
    Args:
        data: The UCF data to filter
        selected_parts: List of part objects to keep
        
    Returns:
        Filtered UCF data
    """
    resulting_data = []

    selected_part_types = set([p['type'] for p in selected_parts])
    selected_part_names = set([p['name'] for p in selected_parts])
    removed_part_names = set()
    
    # Keep non-part items
    for item in data:
        if item.get("collection") != "parts":
            resulting_data.append(item)
            continue
            
        # Keep parts that match the selected names
        if item.get("type") in selected_part_types:
            if item.get("name") in selected_part_names:
                resulting_data.append(item)
            else:
                removed_part_names.add(item.get("name"))
        else:
            resulting_data.append(item)

    # Now, remove any structures that reference removed parts
    resulting_copy = copy.deepcopy(resulting_data)
    resulting_data = []
    for item in resulting_copy:
        keep_item = True
        if item.get("collection") == "structures":
            outputs = item.get("outputs", [])
            if any(output in removed_part_names for output in outputs):
                keep_item = False
            else:
                # check device components
                devices = item.get("devices", [])
                for device in devices:
                    device_components = device.get("components", [])
                    for component in device_components:
                        if component in removed_part_names:
                            keep_item = False
                if keep_item:
                    resulting_data.append(item)
        else:
            resulting_data.append(item)

    existing_structure_names = [item.get("name") for item in resulting_data if item.get("collection") == "structures"]
    
    # Remove any gates that reference removed structures
    resulting_copy = copy.deepcopy(resulting_data)
    resulting_data = []
    for item in resulting_copy:
        if item.get("collection") == "gates":
            if item.get("structure") not in existing_structure_names:
                continue
            else:
                resulting_data.append(item)
        else:
            resulting_data.append(item)
    
    # Remove any models that reference removed gates
    resulting_copy = copy.deepcopy(resulting_data)
    resulting_data = []
    existing_gate_names = [item.get("name") for item in resulting_data if item.get("collection") == "gates"]
    for item in resulting_copy:
        if item.get("collection") == "models":
            if item.get("gate") not in existing_gate_names:
                continue
            else:
                resulting_data.append(item)
        else:
            resulting_data.append(item)

    return resulting_data

def _add_default_parameters(part):
    """
    Add default parameters to a part if needed.
    
    Args:
        part: Part object
    """
    # Skip if part is not a dictionary
    if not isinstance(part, dict):
        return
        
    # Add parameters object if not present
    if "parameters" not in part:
        part["parameters"] = {}

def create_custom_ucf(
                     ucf_data: List[Dict],
                     selected_gates: List[str] = None,
                     selected_parts: List[Dict] = None,
                     modified_parts: List[Dict] = None,
                     new_parts: List[Dict] = None,
                     ucf_name: str = None,
                     output_dir: str = "outputs/custom_ucf") -> str:
    """
    Create a custom UCF file with selected parts and modifications.
    
    Args:
        ucf_data: Base UCF data to customize
        selected_gates: List of gate IDs to include
        selected_parts: List of part objects or IDs to include
        modified_parts: Dict of part_id -> modified properties
        new_parts: List of new part definitions to add
        ucf_name: Optional name for the UCF file
        output_dir: Optional directory to save the UCF file
        
    Returns:
        Path to the created UCF file
    """
    # Create a deep copy of the UCF data to avoid modifying the original
    custom_ucf = copy.deepcopy(ucf_data)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a UCF name if not provided
    if not ucf_name:
        ucf_name = f"custom_ucf_{str(uuid.uuid4())[:8]}.UCF.json"
    
    # Construct the output path
    output_path = os.path.join(output_dir, ucf_name)
    
    # Handle selected parts
    if selected_parts:
        # Extract part names from selected_parts if they are dictionaries
        custom_ucf = filter_parts(custom_ucf, selected_parts)
    
    # Handle selected gates
    if selected_gates:
        # TODO: Implement gate filtering
        raise NotImplementedError("Gate filtering not implemented yet")
    
    # Handle modified parts
    if modified_parts:
        for modified_part in modified_parts:
            part_name = modified_part.get("name")
            collection = modified_part.get("collection")
            
            # Find the existing part in the UCF
            found = False
            for i, part in enumerate(custom_ucf):
                if part.get("collection") == collection and part.get("name") == part_name:
                    found = True
                    
                    # For each parameter in the modified part, update the corresponding parameter in the existing part
                    if "parameters" in modified_part:
                        # Initialize parameters array if it doesn't exist
                        if "parameters" not in part:
                            part["parameters"] = []
                        
                        # Update existing parameters
                        for mod_param in modified_part.get("parameters", []):
                            param_name = mod_param.get("name")
                            param_value = mod_param.get("value")
                            
                            # Find and update the parameter if it exists
                            param_found = False
                            for j, existing_param in enumerate(part["parameters"]):
                                if existing_param.get("name") == param_name:
                                    part["parameters"][j]["value"] = param_value
                                    param_found = True
                                    break
                            
                            # If parameter doesn't exist, add it
                            if not param_found:
                                part["parameters"].append({"name": param_name, "value": param_value})
                    
                    # Update other fields from the modified part (except parameters which we've handled)
                    for key, value in modified_part.items():
                        if key != "parameters":
                            part[key] = value
                    
                    # The existing part is now updated
                    break
            
            if not found:
                logger.warning(f"Part {part_name} (collection: {collection}) not found in UCF, cannot modify")
    
    # Handle new parts
    if new_parts:
        for new_part in new_parts:
            # Add default parameters if needed
            _add_default_parameters(new_part)
            
            # Ensure it has a collection field
            if "collection" not in new_part:
                new_part["collection"] = "parts"
            
            # Add it to the UCF
            custom_ucf.append(new_part)
    
    # Validate the custom UCF
    try:
        validate_ucf(custom_ucf)
    except ValidationError as e:
        logger.error(f"Custom UCF validation failed: {e}")
        raise
    
    # Save the custom UCF to a file
    with open(output_path, 'w') as f:
        json.dump(custom_ucf, f, indent=2)
        
    if VERBOSE:
        logger.info(f"Created custom UCF file: {output_path}")
    return output_path

def customize_existing_ucf(
                          input_ucf_path: str,
                          output_ucf_path: str = None,
                          selected_gates: List[str] = None,
                          selected_parts: List[Dict] = None,
                          modified_parts: Dict[str, Dict] = None,
                          new_parts: List[Dict] = None) -> str:
    """
    Customize an existing UCF file.
    
    Args:
        input_ucf_path: Path to the input UCF file
        output_ucf_path: Path to save the output UCF file
        selected_gates: List of gate IDs to include
        selected_parts: List of part objects or IDs to include
        modified_parts: Dict of part_id -> modified properties
        new_parts: List of new part definitions to add
        
    Returns:
        Path to the created UCF file
    """
    # Load the input UCF
    with open(input_ucf_path, 'r') as f:
        ucf_data = json.load(f)
    
    # Generate an output path if not provided
    if not output_ucf_path:
        output_dir = os.path.dirname(input_ucf_path)
        filename = os.path.basename(input_ucf_path)
        output_ucf_path = os.path.join(output_dir, f"custom_{filename}")
    
    # Create the custom UCF
    return create_custom_ucf(
        ucf_data=ucf_data,
        selected_gates=selected_gates,
        selected_parts=selected_parts,
        modified_parts=modified_parts,
        new_parts=new_parts,
        ucf_name=os.path.basename(output_ucf_path),
        output_dir=os.path.dirname(output_ucf_path)
    )