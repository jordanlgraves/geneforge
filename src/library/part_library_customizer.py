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

def get_input_sensors(data: List[Dict]) -> List[Dict]:
    """
    Get all input sensors
    
    Args:
        data: The UCF data to search
        
    Returns:
        List of input sensors
    """
    result = []
    
    for item in data:
        if item.get("collection") == "input_sensors":
            result.append(item)
    
    return result
    

def filter_parts(data: List[Dict], selected_parts: List) -> List[Dict]:
    """
    Filter UCF data to keep only parts that are needed based on the selected parts
    and their dependencies. Dependencies include any parts referenced in structures,
    gates, and models that relate back to the selected parts.
    
    Args:
        data: The UCF data to filter
        selected_parts: List of part objects to keep
        
    Returns:
        Filtered UCF data
    """
    # Step 1: Extract initial set of selected part names
    selected_part_names = set(p['name'] for p in selected_parts)
    
    # Step 2: Build dependency graph by identifying what references what
    # Map of part names to the structures that use them
    part_to_structures = {}
    # Map of structure names to the gates that use them
    structure_to_gates = {}
    # Map of gate names to the models that use them
    gate_to_models = {}
    
    # Build the mappings
    for item in data:
        collection = item.get("collection")
        
        # Map parts to structures
        if collection == "structures":
            structure_name = item.get("name")
            # Check outputs
            for output in item.get("outputs", []):
                if output.startswith("#"):
                    continue
                if output not in part_to_structures:
                    part_to_structures[output] = []
                part_to_structures[output].append(structure_name)
            
            # Check device components
            for device in item.get("devices", []):
                for component in device.get("components", []):
                    if component.startswith("#"):
                        continue
                    if component not in part_to_structures:
                        part_to_structures[component] = []
                    part_to_structures[component].append(structure_name)
        
        # Map structures to gates
        elif collection == "gates":
            gate_name = item.get("name")
            structure_name = item.get("structure")
            if structure_name not in structure_to_gates:
                structure_to_gates[structure_name] = []
            structure_to_gates[structure_name].append(gate_name)
        
        # Map gates to models
        elif collection == "models":
            model_name = item.get("name")
            gate_name = item.get("gate")
            if not gate_name and model_name.endswith("_model"): # Some models might not directly reference a gate
                gate_name = '_'.join(model_name.split("_model")[:-1])
            if gate_name:  
                if gate_name not in gate_to_models:
                    gate_to_models[gate_name] = []
                gate_to_models[gate_name].append(model_name)
    
    # Step 3: Traverse dependencies to find all required parts, structures, gates, and models
    required_parts = set(selected_part_names)
    required_structures = set()
    required_gates = set()
    required_models = set()
    
    # Find dependent structures for selected parts
    for part_name in required_parts:
        structures = part_to_structures.get(part_name, [])
        required_structures.update(structures)
    
    # Find dependent gates for required structures
    for structure_name in required_structures:
        gates = structure_to_gates.get(structure_name, [])
        required_gates.update(gates)
    
    # Find dependent models for required gates
    for gate_name in required_gates:
        models = gate_to_models.get(gate_name, [])
        required_models.update(models)
    
    # Step 4: Find all parts referenced by required structures
    # This needs a second pass to capture parts used in structures but not directly selected
    temp_required_parts = set(required_parts)
    
    for item in data:
        if item.get("collection") == "structures" and item.get("name") in required_structures:
            # Add output parts
            temp_required_parts.update(item.get("outputs", []))
            
            # Add device component parts
            for device in item.get("devices", []):
                temp_required_parts.update(device.get("components", []))
    
    # Update required parts with the additional dependencies
    required_parts = temp_required_parts
    
    # Step 5: Filter UCF data to keep only required elements
    filtered_data = []
    
    for item in data:
        collection = item.get("collection")
        name = item.get("name")
        
        if collection == "parts":
            if name in required_parts:
                filtered_data.append(item)
        elif collection == "structures":
            if name in required_structures:
                filtered_data.append(item)
        elif collection == "gates":
            if name in required_gates:
                filtered_data.append(item)
        elif collection == "models":
            if name in required_models:
                filtered_data.append(item)
        else:
            # Keep all other collection types (header, measurement_std, etc.)
            filtered_data.append(item)
    
    return filtered_data

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

def filter_input_sensors(data: List[Dict], selected_sensors: List[str]) -> List[Dict]:
    """
    Filter input sensor file data to keep only sensors that are selected
    and their dependencies (models, structures, parts, functions).
    
    Args:
        data: The input sensor file data to filter
        selected_sensors: List of input sensor names to keep
        
    Returns:
        Filtered input sensor file data
    """
    # Step 1: Extract selected sensor names
    selected_sensor_names = set(selected_sensors)
    
    # Step 2: Build dependency graph
    # Map sensor names to their models and structures
    sensor_to_model = {}
    sensor_to_structure = {}
    # Map structure names to the parts they use
    structure_to_parts = {}
    # Map model names to the functions they use
    model_to_functions = {}
    
    # Build the mappings
    for item in data:
        collection = item.get("collection")
        
        # Map sensors to models and structures
        if collection == "input_sensors":
            sensor_name = item.get("name")
            model_name = item.get("model")
            structure_name = item.get("structure")
            
            sensor_to_model[sensor_name] = model_name
            sensor_to_structure[sensor_name] = structure_name
        
        # Map structures to parts
        elif collection == "structures":
            structure_name = item.get("name")
            output_parts = item.get("outputs", [])
            
            if structure_name not in structure_to_parts:
                structure_to_parts[structure_name] = set()
            structure_to_parts[structure_name].update(output_parts)
        
        # Map models to functions
        elif collection == "models":
            model_name = item.get("name")
            functions = item.get("functions", {})
            
            if model_name not in model_to_functions:
                model_to_functions[model_name] = set()
            
            for function_ref in functions.values():
                model_to_functions[model_name].add(function_ref)
    
    # Step 3: Traverse dependencies to find all required elements
    required_sensors = set(selected_sensor_names)
    required_models = set()
    required_structures = set()
    required_functions = set()
    required_parts = set()
    
    # Find required models and structures from sensors
    for sensor_name in required_sensors:
        model_name = sensor_to_model.get(sensor_name)
        structure_name = sensor_to_structure.get(sensor_name)
        
        if model_name:
            required_models.add(model_name)
        
        if structure_name:
            required_structures.add(structure_name)
    
    # Find required functions from models
    for model_name in required_models:
        functions = model_to_functions.get(model_name, set())
        required_functions.update(functions)
    
    # Find required parts from structures
    for structure_name in required_structures:
        parts = structure_to_parts.get(structure_name, set())
        required_parts.update(parts)
    
    # Step 4: Filter the data to keep only required elements
    filtered_data = []
    
    for item in data:
        collection = item.get("collection")
        name = item.get("name")
        
        if collection == "input_sensors":
            if name in required_sensors:
                filtered_data.append(item)
        elif collection == "models":
            if name in required_models:
                filtered_data.append(item)
        elif collection == "structures":
            if name in required_structures:
                filtered_data.append(item)
        elif collection == "functions":
            if name in required_functions:
                filtered_data.append(item)
        elif collection == "parts":
            if name in required_parts:
                filtered_data.append(item)
    
    return filtered_data

def create_custom_input_sensors_file(
                                   input_sensor_data: List[Dict],
                                   selected_sensors: List[str] = None,
                                   modified_models: List[Dict] = None,
                                   new_sensors: List[Dict] = None,
                                   output_filename: str = None,
                                   output_dir: str = "outputs/custom_sensors") -> str:
    """
    Create a custom input sensor file with selected sensors and modifications.
    
    Args:
        input_sensor_data: Base input sensor data to customize
        selected_sensors: List of sensor names to include
        modified_models: List of model objects with modified parameters
        new_sensors: List of new sensor definitions to add
        output_filename: Optional name for the output file
        output_dir: Optional directory to save the output file
        
    Returns:
        Path to the created input sensor file
    """
    # Create a deep copy of the input data to avoid modifying the original
    custom_data = copy.deepcopy(input_sensor_data)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate an output filename if not provided
    if not output_filename:
        output_filename = f"custom_input_sensors_{str(uuid.uuid4())[:8]}.input.json"
    
    # Construct the output path
    output_path = os.path.join(output_dir, output_filename)
    
    # Make sure the selected sensors are in the data
    if selected_sensors:
        for sensor in selected_sensors:
            if sensor not in [s['name'] for s in custom_data]:
                raise ValueError(f"Sensor {sensor} not found in input sensor data")

    # Handle selected sensors
    if selected_sensors:
        custom_data = filter_input_sensors(custom_data, selected_sensors)
    
    # Handle modified models
    if modified_models:
        for modified_model in modified_models:
            model_name = modified_model.get("name")
            
            # Find the existing model in the data
            found = False
            for i, model in enumerate(custom_data):
                if model.get("collection") == "models" and model.get("name") == model_name:
                    found = True
                    
                    # Update parameters
                    if "parameters" in modified_model:
                        # Initialize parameters array if it doesn't exist
                        if "parameters" not in model:
                            model["parameters"] = []
                        
                        # Update existing parameters
                        for mod_param in modified_model.get("parameters", []):
                            param_name = mod_param.get("name")
                            param_value = mod_param.get("value")
                            
                            # Find and update the parameter if it exists
                            param_found = False
                            for j, existing_param in enumerate(model["parameters"]):
                                if existing_param.get("name") == param_name:
                                    custom_data[i]["parameters"][j]["value"] = param_value
                                    param_found = True
                                    break
                            
                            # If parameter doesn't exist, add it
                            if not param_found:
                                model["parameters"].append({"name": param_name, "value": param_value})
                    
                    # Update functions if specified
                    if "functions" in modified_model:
                        for func_name, func_value in modified_model["functions"].items():
                            model["functions"][func_name] = func_value
                    
                    # The existing model is now updated
                    break
            
            if not found and VERBOSE:
                logger.warning(f"Model {model_name} not found in input sensor data, cannot modify")
    
    # Handle new sensors
    if new_sensors:
        for new_sensor in new_sensors:
            # Ensure it has a collection field
            if "collection" not in new_sensor:
                new_sensor["collection"] = "input_sensors"
            
            # Add it to the custom data
            custom_data.append(new_sensor)
    
    # Validate the custom data
    try:
        # Use input_sensor_validator when available
        # TODO: Implement proper validation against input_sensor_file schema
        pass
    except ValidationError as e:
        logger.error(f"Custom input sensor file validation failed: {e}")
        raise
    
    # Save the custom data to a file
    with open(output_path, 'w') as f:
        json.dump(custom_data, f, indent=2)
        
    if VERBOSE:
        logger.info(f"Created custom input sensor file: {output_path}")
    
    return output_path

def customize_existing_input_sensors_file(
                                        input_file_path: str,
                                        output_file_path: str = None,
                                        selected_sensors: List[str] = None,
                                        modified_models: List[Dict] = None,
                                        new_sensors: List[Dict] = None) -> str:
    """
    Customize an existing input sensor file.
    
    Args:
        input_file_path: Path to the input sensor file
        output_file_path: Path to save the output file
        selected_sensors: List of sensor names to include
        modified_models: List of model objects with modified parameters
        new_sensors: List of new sensor definitions to add
        
    Returns:
        Path to the created input sensor file
    """
    # Load the input file
    with open(input_file_path, 'r') as f:
        input_data = json.load(f)
    
    # Generate an output path if not provided
    if not output_file_path:
        output_dir = os.path.dirname(input_file_path)
        filename = os.path.basename(input_file_path)
        output_file_path = os.path.join(output_dir, f"custom_{filename}")
    
    # Create the custom input sensor file
    return create_custom_input_sensors_file(
        input_sensor_data=input_data,
        selected_sensors=selected_sensors,
        modified_models=modified_models,
        new_sensors=new_sensors,
        output_filename=os.path.basename(output_file_path),
        output_dir=os.path.dirname(output_file_path)
    )