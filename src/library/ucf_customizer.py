import json
import os
import uuid
import copy
import logging
import tempfile
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

import jsonschema
from jsonschema import ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ucf_customizer")

class CelloUCFCustomizer:
    """
    Creates customized UCF files with selected parts for Cello circuit design.
    Follows the UCF schema structure to ensure valid output files.
    
    This class is designed to be stateless - it doesn't store UCF data
    internally but operates on data passed to its methods.
    """
    def __init__(self, schema_path: str = "ext_repos/Cello-UCF/schemas/v2/ucf.schema.json"):
        """
        Initialize with schema for validation.
        
        Args:
            schema_path: Path to UCF schema file
        """
        self.schema_path = schema_path
        self.schema_dir = os.path.dirname(schema_path) if schema_path else None
        
        # Load schema
        self.schema = None
        self.validator = None
        
        # Check schema path
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema file not found at {schema_path}. Cannot validate UCF files.")
        
        # Load schema and set up validator
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
        
        # Cache resolved schemas to speed up validation
        self.resolved_schemas = {}
        
        # Scan and report the schema directory structure
        self._scan_schema_directory()
        
        # Set up a resolver for schema references
        schema_base_uri = f"file://{os.path.abspath(self.schema_dir)}/"
        self.resolver = jsonschema.RefResolver(base_uri=schema_base_uri, referrer=self.schema)
        
        # Create a validator with the resolver
        self.validator = jsonschema.Draft7Validator(
            schema=self.schema,
            resolver=self.resolver
        )
        
        logger.info(f"Loaded UCF schema from {schema_path}")
        
        # Pre-load common referenced schemas
        self._preload_referenced_schemas()
            
    def _scan_schema_directory(self):
        """Scan the schema directory structure and report missing schemas"""
        if not self.schema_dir or not os.path.exists(self.schema_dir):
            raise ValueError(f"Schema directory not found: {self.schema_dir}")
            
        # Check if we're in a Cello-UCF repo
        parent_dir = os.path.dirname(self.schema_dir)
        if os.path.basename(parent_dir) != "schemas":
            logger.warning(f"Unexpected schema directory structure: {self.schema_dir}")
            logger.warning("Expected to find schema directory within a 'schemas' directory in the Cello-UCF repository.")
        
        # List all schema files present
        schema_files = []
        self.missing_schemas = []
        
        # Check schema directory
        try:
            for file in os.listdir(self.schema_dir):
                if file.endswith('.schema.json'):
                    schema_files.append(file)
        except Exception as e:
            raise IOError(f"Error scanning schema directory {self.schema_dir}: {e}")
        
        # Look for required schemas from schema references
        if self.schema:
            self._find_schema_references(self.schema, schema_files)
            
        # Log the results
        if schema_files:
            logger.info(f"Found {len(schema_files)} schema files in {self.schema_dir}: {', '.join(schema_files)}")
        else:
            raise ValueError(f"No schema files found in {self.schema_dir}")
    
    def _find_schema_references(self, schema, found_schemas):
        """Recursively find schema references in a schema object"""
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
                if ref_filename not in found_schemas and ref_filename not in self.missing_schemas:
                    self.missing_schemas.append(ref_filename)
        
        # Recursively check all objects and arrays
        for key, value in schema.items():
            if isinstance(value, dict):
                self._find_schema_references(value, found_schemas)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._find_schema_references(item, found_schemas)
    
    def _preload_referenced_schemas(self):
        """Pre-load common schema references to speed up validation"""
        if not self.schema_dir:
            return
            
        try:
            # These are commonly referenced schema files
            common_schemas = [
                "gate.schema.json",
                "part.schema.json",
                "gate_parts.schema.json",
                "response_function.schema.json"
            ]
            
            for schema_name in common_schemas:
                schema_path = os.path.join(self.schema_dir, schema_name)
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        self.resolved_schemas[schema_name] = json.load(f)
                else:
                    logger.warning(f"Common schema reference not found: {schema_name}")
        except Exception as e:
            logger.error(f"Error preloading schema references: {e}")
    
    def validate_ucf(self, ucf_data: List[Dict]) -> Dict[str, Any]:
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
            self.validator.validate(ucf_data)
        except ValidationError as e:
            result["valid"] = False
            result["errors"].append(str(e))
            raise ValidationError(f"UCF validation failed: {e}")
        
        logger.info(f"UCF validation passed: no schema errors found")
        return result
    
    def index_collections(self, ucf_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Index UCF data by collection for easier access.
        
        Args:
            ucf_data: The UCF data to index
            
        Returns:
            Dictionary mapping collection names to lists of items
        """
        collections = {}
        
        for item in ucf_data:
            collection = item.get("collection")
            if collection:
                if collection not in collections:
                    collections[collection] = []
                collections[collection].append(item)
        
        return collections
    
    def get_parts_by_type(self, ucf_data: List[Dict], part_type: str) -> List[Dict]:
        """
        Get all parts of a specific type from UCF data.
        
        Args:
            ucf_data: The UCF data to search
            part_type: The type of parts to find (e.g., "promoter", "cds")
            
        Returns:
            List of matching parts
        """
        result = []
        
        for item in ucf_data:
            if item.get("collection") == "parts" and item.get("type") == part_type:
                result.append(item)
        
        return result
    
    def get_part_by_name(self, ucf_data: List[Dict], part_name: str) -> Optional[Dict]:
        """
        Get a specific part by name from UCF data.
        
        Args:
            ucf_data: The UCF data to search
            part_name: The name of the part to find
            
        Returns:
            The part dictionary if found, None otherwise
        """
        for item in ucf_data:
            if item.get("collection") == "parts" and item.get("name") == part_name:
                return item
        
        return None
    
    def filter_parts(self, ucf_data: List[Dict], selected_parts: List) -> List[Dict]:
        """
        Filter UCF data to remove parts that are not in the selected parts list (by name) 
        and share a type with a selected parts.
        Only removes parts if they share a type with the selected parts.
        Cleans up any references to removed parts.
        
        Args:
            ucf_data: The UCF data to filter
            selected_part_names: List of part names to keep
            
        Returns:
            Filtered UCF data
        """
        resulting_ucf = []

        selected_part_types = set([p['type'] for p in selected_parts])
        selected_part_names = set([p['name'] for p in selected_parts])
        removed_part_names = set()
        # Keep non-part items
        for item in ucf_data:
            if item.get("collection") != "parts":
                resulting_ucf.append(item)
                continue
                
            # Keep parts that match the selected names
            if item.get("type") in selected_part_types:
                if item.get("name") in selected_part_names:
                    resulting_ucf.append(item)
                else:
                    removed_part_names.add(item.get("name"))
            else:
                resulting_ucf.append(item)

        # Now, remove any structures that reference removed parts
        resulting_ucf_copy = copy.deepcopy(resulting_ucf)
        resulting_ucf = []
        for item in resulting_ucf_copy:
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
                        resulting_ucf.append(item)
            else:
                resulting_ucf.append(item)

        existing_structure_names = [item.get("name") for item in resulting_ucf if item.get("collection") == "structures"]
        # remove any gates that reference removed structures
        resulting_ucf_copy = copy.deepcopy(resulting_ucf)
        resulting_ucf = []
        for item in resulting_ucf_copy:
            if item.get("collection") == "gates":
                if item.get("structure") not in existing_structure_names:
                    continue
                else:
                    resulting_ucf.append(item)
            else:
                resulting_ucf.append(item)
        
        # remove any models that reference removed gates
        resulting_ucf_copy = copy.deepcopy(resulting_ucf)
        resulting_ucf = []
        existing_gate_names = [item.get("name") for item in resulting_ucf if item.get("collection") == "gates"]
        for item in resulting_ucf_copy:
            if item.get("collection") == "models":
                if item.get("gate") not in existing_gate_names:
                    continue
                else:
                    resulting_ucf.append(item)
            else:
                resulting_ucf.append(item)



        return resulting_ucf
    
    def _add_default_parameters(self, part):
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
    
    def create_custom_ucf(self, 
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

            custom_ucf = self.filter_parts(custom_ucf, selected_parts)
        
        # Handle selected gates
        if selected_gates:
            # TODO: Implement gate filtering
            raise NotImplementedError("Gate filtering not implemented yet")
            pass
        
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
                self._add_default_parameters(new_part)
                
                # Ensure it has a collection field
                if "collection" not in new_part:
                    new_part["collection"] = "parts"
                
                # Add it to the UCF
                custom_ucf.append(new_part)
        
        # Validate the custom UCF
        try:
            self.validate_ucf(custom_ucf)
        except ValidationError as e:
            logger.error(f"Custom UCF validation failed: {e}")
            raise
        
        # Save the custom UCF to a file
        with open(output_path, 'w') as f:
            json.dump(custom_ucf, f, indent=2)
            
        logger.info(f"Created custom UCF file: {output_path}")
        return output_path
    
    def customize_existing_ucf(self,
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
        return self.create_custom_ucf(
            ucf_data=ucf_data,
            selected_gates=selected_gates,
            selected_parts=selected_parts,
            modified_parts=modified_parts,
            new_parts=new_parts,
            ucf_name=os.path.basename(output_ucf_path),
            output_dir=os.path.dirname(output_ucf_path)
        )