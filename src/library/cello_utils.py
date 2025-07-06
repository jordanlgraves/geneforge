import json
import os
import io
import uuid
import copy
import logging
import tempfile
from typing import Dict, List, Optional, Tuple, Union, Any, Set
from pathlib import Path
import dotenv
import pandas as pd
import functools

dotenv.load_dotenv()

CELLO_UCF_ROOT = os.getenv("CELLO_UCF_ROOT")

import jsonschema
from jsonschema import ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cello_utils")

VERBOSE = True

# Initialize global schema variables
UCF_SCHEMA_PATH = os.path.join(CELLO_UCF_ROOT, "schemas", "v2", "ucf.schema.json")
SCHEMA_DIR = os.path.dirname(UCF_SCHEMA_PATH)
INPUT_SENSOR_SCHEMA_PATH = os.path.join(CELLO_UCF_ROOT, "schemas", "v2", "input_sensor_file.schema.json")
OUTPUT_DEVICE_SCHEMA_PATH = os.path.join(CELLO_UCF_ROOT, "schemas", "v2", "output_device_file.schema.json")

# ---------------------------------------------------------------------------
#  Schema / validator utilities (lazy-loaded, no globals)
# ---------------------------------------------------------------------------

# NOTE: We keep the heavy work (reading JSON schema files, building JSONSchema
# validators, scanning the schema directory) behind a lazily-evaluated cache so
# that importing this module incurs zero overhead unless validation is actually
# requested.  In addition, we avoid mutable module-level state – everything is
# created once and cached via ``functools.lru_cache``.

# Internal helper that *creates* the validators (no caching!).  Do **NOT** call
# this directly – use :pyfunc:`_get_validators` instead.

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

# ---------------------------------------------------------------------------
#  Public accessor – returns cached validators
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _get_validators():
    """Return *(ucf_validator, input_sensor_validator, output_device_validator)*.

    The heavy lifting is performed only on the *first* call thanks to the
    ``lru_cache`` decorator.  Subsequent calls reuse the cached objects.
    """

    ucf_validator, input_sensor_validator, output_device_validator, ucf_schema = _initialize_validators()

    # Perform a one-off sanity check that all referenced schemas are available
    # inside the schema directory.  This is *informational* – we only log the
    # outcome so that validation can still proceed even when some ancillary
    # schemas are missing.
    _scan_schema_directory(ucf_schema)

    return ucf_validator, input_sensor_validator, output_device_validator

def _find_schema_references(schema, found_schemas, missing_schemas):
    """Recursively collect external schema references found in *schema*."""
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
            if ref_filename not in found_schemas:
                missing_schemas.add(ref_filename)
    
    # Recursively check all objects and arrays
    for key, value in schema.items():
        if isinstance(value, dict):
            _find_schema_references(value, found_schemas, missing_schemas)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _find_schema_references(item, found_schemas, missing_schemas)

def _scan_schema_directory(ucf_schema) -> None:
    """Scan *SCHEMA_DIR* and log any schema files referenced from *ucf_schema*
    that are missing on disk.
    """
    if not SCHEMA_DIR or not os.path.exists(SCHEMA_DIR):
        raise ValueError(f"Schema directory not found: {SCHEMA_DIR}")
        
    # Check if we're in a Cello-UCF repo
    parent_dir = os.path.dirname(SCHEMA_DIR)
    if os.path.basename(parent_dir) != "schemas":
        logger.warning(f"Unexpected schema directory structure: {SCHEMA_DIR}")
        logger.warning("Expected to find schema directory within a 'schemas' directory in the Cello-UCF repository.")
    
    # List all schema files present
    schema_files = []
    missing_schemas: Set[str] = set()
    
    # Check schema directory
    try:
        for file in os.listdir(SCHEMA_DIR):
            if file.endswith('.schema.json'):
                schema_files.append(file)
    except Exception as e:
        raise IOError(f"Error scanning schema directory {SCHEMA_DIR}: {e}")
    
    # Look for required schemas from schema references
    if ucf_schema:
        _find_schema_references(ucf_schema, schema_files, missing_schemas)
        
    # Log the results
    if schema_files:
        if VERBOSE:
            logger.info(f"Found {len(schema_files)} schema files in {SCHEMA_DIR}: {', '.join(schema_files)}")
    else:
        raise ValueError(f"No schema files found in {SCHEMA_DIR}")

    # Report any missing external schemas – purely informational.
    if missing_schemas and VERBOSE:
        logger.warning(
            "Missing {n} referenced schema file(s): {lst}".format(
                n=len(missing_schemas), lst=", ".join(sorted(missing_schemas))
            )
        )

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
        # Validate the whole UCF – grab the cached validator on demand.
        ucf_validator, _, _ = _get_validators()
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

def remove_part_and_dependencies(ucf_data: List[Dict], part_name: str) -> Tuple[List[Dict], Dict[str, List[str]]]:
    """Remove *part_name* and all dependent structures, gates and models.

    Parameters
    ----------
    ucf_data : list
        The full UCF list (will **not** be modified in-place).
    part_name : str
        Name of the part (e.g. promoter ID) to remove.

    Returns
    ------
    new_ucf : list
        A deep-copy list that excludes the removed items.
    summary : dict
        Keys ``parts``, ``structures``, ``gates``, ``models`` with lists of
        names that were removed.
    """
    import copy

    # ------------------------------------------------------------ build maps
    part_to_structures: Dict[str, List[str]] = {}
    structure_to_gates: Dict[str, List[str]] = {}
    gate_to_models: Dict[str, List[str]] = {}
    model_to_gate: Dict[str, str] = {}

    gates = [item for item in ucf_data if item.get("collection") == "gates"]
    models = [item for item in ucf_data if item.get("collection") == "models"]

    for item in ucf_data:
        if item.get("collection") == "structures":
            for promoter_part in item.get("outputs", []):
                if promoter_part not in part_to_structures:
                    part_to_structures[promoter_part] = []
                part_to_structures[promoter_part].append(item["name"])

        elif item.get("collection") == "gates":
            struct = item.get("structure")
            if struct:
                if struct not in structure_to_gates:
                    structure_to_gates[struct] = []
                structure_to_gates[struct].append(item["name"])

            model = item.get("model")
            if model:
                if model not in gate_to_models:
                    gate_to_models[model] = []
                gate_to_models[model].append(item["name"])
                model_to_gate[item["name"]] = model

    # some models are not explicitly linked from gates...
    for model in models:
        if model["name"] in gate_to_models:
            continue
        # v2-style: gate is implicitly <model_name> without "_model"
        if model["name"].endswith("_model"):
            gate_name = model["name"][:-len("_model")]
            if gate_name in [g["name"] for g in gates]:
                 if model["name"] not in gate_to_models:
                    gate_to_models[model["name"]] = []
                 gate_to_models[model["name"]].append(gate_name)
                 model_to_gate[gate_name] = model["name"]


    # ------------------------------------------------------------ find items to remove
    to_remove: Dict[str, Set[str]] = {
        "parts": {part_name},
        "structures": set(),
        "gates": set(),
        "models": set(),
    }

    # parts -> structures
    for p in to_remove["parts"]:
        if p in part_to_structures:
            for s in part_to_structures[p]:
                to_remove["structures"].add(s)

    # structures -> gates
    structures_to_process = list(to_remove["structures"])
    processed_structures = set()
    while structures_to_process:
        s = structures_to_process.pop(0)
        if s in processed_structures:
            continue
        processed_structures.add(s)
        if s in structure_to_gates:
            for g in structure_to_gates[s]:
                to_remove["gates"].add(g)

    # gates -> models
    models_to_check = set()
    for g in to_remove["gates"]:
        if g in model_to_gate:
            models_to_check.add(model_to_gate[g])

    for m in models_to_check:
        # A model should be removed only if all gates that use it are also being removed.
        if m in gate_to_models:
            all_gates_removed = all(g in to_remove["gates"] for g in gate_to_models[m])
            if all_gates_removed:
                to_remove["models"].add(m)
        else:
            # If model is not in gate_to_models map, it means no gate refers to it, so it's safe to remove.
            to_remove["models"].add(m)

    # ------------------------------------------------------------ find dangling rules
    # In some libraries, "device_rules" and "circuit_rules" may reference gates.
    # This is a shallow removal; it doesn't handle cascading rule dependencies.
    dangling_rules = set()
    for item in ucf_data:
        coll = item.get("collection")
        if coll not in ("device_rules", "circuit_rules"):
            continue
        for g in to_remove["gates"]:
            if g in item.get("components", []):
                dangling_rules.add(item["name"])
                break  # next rule

    # ------------------------------------------------------------ filter
    new_ucf = []
    for item in ucf_data:
        coll = item.get("collection", "")
        if coll.endswith("s"):
            coll = coll[:-1] # "parts" -> "part"
        
        name = item.get("name")
        if f"{coll}s" in to_remove and name in to_remove[f"{coll}s"]:
            continue
        if name in dangling_rules:
            continue
        
        # Deep-copy to avoid modifying original ucf_data
        item_copy = copy.deepcopy(item)
        
        # Also clean up component lists within rules
        if item_copy.get("collection") in ("device_rules", "circuit_rules"):
            if "components" in item_copy:
                item_copy["components"] = [c for c in item_copy["components"] if c not in to_remove["gates"]]
        
        new_ucf.append(item_copy)

    summary = {
        "parts": sorted(list(to_remove["parts"])),
        "structures": sorted(list(to_remove["structures"])),
        "gates": sorted(list(to_remove["gates"])),
        "models": sorted(list(to_remove["models"])),
        "rules": sorted(list(dangling_rules)),
    }

    return new_ucf, summary

# ---------------------------------------------------------------------------
#  Helper utilities for promoter-variant duplication
# ---------------------------------------------------------------------------

def _deepcopy_jsonable(obj):
    """json-safe deepcopy that never fails."""
    try:
        return copy.deepcopy(obj)
    except Exception:  # pragma: no cover
        import json
        return json.loads(json.dumps(obj))


def _replace_tokens(obj, mapping: Dict[str, str], replace: bool = True):
    """
    Recursively walk *obj* and either replace (replace=True) or
    append (replace=False) any string that matches a key in *mapping*.

    If replace is False the original string is kept and the new one is
    appended (lists) or ignored (scalar str).
    """
    if isinstance(obj, str):
        for _old, _new in mapping.items():
            if obj == _old:
                return _new if replace else obj
        return obj

    if isinstance(obj, list):
        out = [_replace_tokens(i, mapping, replace) for i in obj]
        if not replace:
            for _old, _new in mapping.items():
                if _old in out and _new not in out:
                    out.append(_new)
        return out

    if isinstance(obj, dict):
        return {k: _replace_tokens(v, mapping, replace) for k, v in obj.items()}

    return obj


def get_promoter_dependencies(ucf_data: List[Dict], promoter_name: str) -> Dict[str, Dict]:
    """
    Find all items (part, structures, gates, models) that are linked
    to a specific promoter part.
    """
    dependencies = {
        "part": None,
        "structures": [],
        "gates": [],
        "models": [],
    }

    part = get_part_by_name(ucf_data, promoter_name)
    if not part:
        return dependencies
    dependencies["part"] = part

    # Find structures that use the promoter
    for item in ucf_data:
        if item.get("collection") == "structures":
            if promoter_name in item.get("outputs", []):
                dependencies["structures"].append(item)

    # Find gates that use those structures
    structure_names = {s["name"] for s in dependencies["structures"]}
    for item in ucf_data:
        if item.get("collection") == "gates":
            if item.get("structure") in structure_names:
                dependencies["gates"].append(item)

    # Find models linked to those gates
    gate_names = {g["name"] for g in dependencies["gates"]}
    for item in ucf_data:
        if item.get("collection") == "models":
            # Check for direct link by 'gate' field
            if item.get("gate") in gate_names:
                dependencies["models"].append(item)
            # Check for implicit link by name (e.g., "pPhlF_model" for "pPhlF" gate)
            elif item.get("name").startswith(tuple(gate_names)):
                dependencies["models"].append(item)

    return dependencies


def duplicate_promoter_dependencies(
    ucf_data: List[Dict],
    parent_promoter: str,
    new_promoter_name: str,
    new_sequence: str,
    y_max: float,
) -> Tuple[List[Dict], Dict[str, str]]:
    """
    Duplicate *parent_promoter* together with all dependent structures,
    gates and models under the new names.

    Returns
    -------
    new_items   : list   – new part / structure / gate / model objects
    gate_map    : dict   – {old_gate_name: new_gate_name}
    """
    new_items: List[Dict] = []

    parent_part = get_part_by_name(ucf_data, parent_promoter)
    if not parent_part:
        raise ValueError(f"Promoter '{parent_promoter}' not found in UCF")

    parent_regulator = parent_promoter[1:] if parent_promoter.startswith("p") else parent_promoter
    new_regulator = new_promoter_name[1:] if new_promoter_name.startswith("p") else new_promoter_name
    
    # ------------------------------------------------------------------ parts
    new_part = _deepcopy_jsonable(parent_part)
    new_part["name"] = new_promoter_name
    if "dnasequence" in new_part:
        new_part["dnasequence"] = new_sequence
    else:
        new_part["sequence"] = new_sequence

    # update / insert ymax
    found = False
    for p in new_part.get("parameters", []):
        if p.get("parameter", "").lower() in ("ymax", "y_max"):
            p["value"] = y_max
            found = True
            break
    if not found:
        new_part.setdefault("parameters", []).append(
            {"parameter": "ymax", "value": y_max}
        )

    new_items.append(new_part)

    # ---------- locate structures that reference the original promoter
    structure_map: Dict[str, str] = {}
    for item in ucf_data:
        if item.get("collection") != "structures":
            continue
        uses_prom = (
            parent_promoter in item.get("outputs", [])
            or any(
                parent_promoter in dev.get("components", [])
                for dev in item.get("devices", [])
            )
        )
        if uses_prom:
            # remove the 'p' from the structure name
            new_struct_name = item["name"].replace(parent_regulator, new_regulator)
            structure_map[item["name"]] = new_struct_name
            struct_copy = _deepcopy_jsonable(item)
            struct_copy["name"] = new_struct_name

            # Build a map of all names being changed within this structure
            rename_map = {parent_promoter: new_promoter_name}
            # Iterate original item's devices to get old names and map them to new names
            for dev in item.get("devices", []):
                old_name = dev['name']
                new_name = old_name.replace(parent_regulator, new_regulator)
                rename_map[old_name] = new_name

            # Apply renames to outputs and components using the map
            struct_copy["outputs"] = [
                rename_map.get(x, x) for x in struct_copy.get("outputs", [])
            ]
            for dev in struct_copy.get("devices", []):
                dev["name"] = rename_map.get(dev["name"], dev["name"])
                dev["components"] = [
                    rename_map.get(comp, comp) if not comp.startswith("#") else comp
                    for comp in dev.get("components", [])
                ]

            new_items.append(struct_copy)

    # ---------- duplicate gates that point at those structures
    gate_map: Dict[str, str] = {}
    for item in ucf_data:
        if item.get("collection") != "gates":
            continue
        old_structure = item.get("structure")
        if old_structure not in structure_map:
            continue
        new_gate_name = item["name"].replace(parent_regulator, new_regulator)
        gate_map[item["name"]] = new_gate_name
        gate_copy = _deepcopy_jsonable(item)
        gate_copy["name"] = new_gate_name
        gate_copy["structure"] = structure_map[old_structure]
        if "model" in gate_copy and isinstance(gate_copy["model"], str):
            gate_copy["model"] = gate_copy["model"].replace(parent_regulator, new_regulator)
        new_items.append(gate_copy)

    # ---------- duplicate models that reference the old gates
    for item in ucf_data:
        if item.get("collection") != "models":
            continue

        # Two formats observed:
        #  (a) explicit "gate" key  – v1 libraries
        #  (b) name pattern "<gate>_model" with NO gate key  – v2 libraries

        old_gate = item.get("gate")
        by_name_match = False

        if not old_gate:
            # infer from name suffix
            name_val = item.get("name", "")
            if name_val.endswith("_model"):
                inferred_gate = name_val[:-6]  # strip suffix
                if inferred_gate in gate_map:
                    old_gate = inferred_gate
                    by_name_match = True

        if not old_gate or old_gate not in gate_map:
            continue

        model_copy = _deepcopy_jsonable(item)

        # update name – replace parent promoter substring with new promoter name
        model_copy["name"] = model_copy["name"].replace(parent_regulator, new_regulator)

        # update explicit gate field when present
        if "gate" in model_copy:
            model_copy["gate"] = gate_map[old_gate]
        elif by_name_match:
            # nothing else needed – downstream components reference by name
            pass

        new_items.append(model_copy)

    return new_items, gate_map


def patch_rules(
    ucf_data: List[Dict], gate_map: Dict[str, str], remove_old: bool = False
) -> None:
    """Patch device_rules / circuit_rules in-place."""
    for item in ucf_data:
        if item.get("collection") in ("device_rules", "circuit_rules"):
            item["rules"] = _replace_tokens(item["rules"], gate_map, replace=remove_old)

            
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
            # Add default parameters to a part if needed.
            if new_part.get("collection") == "parts":
                _add_default_parameters(new_part)
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
    

def parse_activity_table(table_str_or_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if os.path.exists(table_str_or_path):
        table_str = open(table_str_or_path, 'r').read()
    
    # skip the first line
    table_lines = table_str.split('\n')[1:]

    # split into the two tables. 
    # Table 1 is all lines before the first occurrence of '""'
    split_idx = table_lines.index('""')

    table_str_scores = '\n'.join(table_lines[:split_idx])
    table_str_binary = '\n'.join(table_lines[split_idx + 2:]) # skip the '""' line and the 'Binary' line

    df_scores = pd.read_csv(io.StringIO(table_str_scores), index_col=None)
    df_binary = pd.read_csv(io.StringIO(table_str_binary), index_col=None)

    return df_scores, df_binary