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

class UCFCustomizer:
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
        Filter UCF data to include only the selected parts and clean up any references.
        
        Args:
            ucf_data: The UCF data to filter
            selected_parts: List of part objects to keep
            
        Returns:
            Filtered UCF data with all references to removed parts cleaned up
        """
        # Step 1: Identify parts to keep and remove
        selected_part_types = set(p.get('type', '') for p in selected_parts)
        selected_part_names = set(p.get('name', '') for p in selected_parts)
        
        # Create a map of part types to their names for quick lookup
        parts_by_type = {}
        for item in ucf_data:
            if item.get("collection") == "parts":
                part_type = item.get("type", "")
                part_name = item.get("name", "")
                if part_type not in parts_by_type:
                    parts_by_type[part_type] = set()
                parts_by_type[part_type].add(part_name)
        
        # Identify removed promoters
        removed_promoters = set()
        if "promoter" in parts_by_type:
            removed_promoters = parts_by_type["promoter"] - selected_part_names
        
        # Step 2: Filter based on dependencies
        # First pass: collect structure names that reference removed promoters
        removed_structures = set()
        kept_structures = set()
        for item in ucf_data:
            if item.get("collection") == "structures":
                outputs = item.get("outputs", [])
                # If any output is a removed promoter, mark structure for removal
                if any(output in removed_promoters for output in outputs):
                    removed_structures.add(item.get("name", ""))
                # If any output is a kept promoter, mark structure to keep
                elif any(output in selected_part_names for output in outputs):
                    kept_structures.add(item.get("name", ""))
        
        # Second pass: collect gates that reference removed structures
        removed_gates = set()
        kept_gates = set()
        for item in ucf_data:
            if item.get("collection") == "gates":
                if item.get("structure") in removed_structures:
                    removed_gates.add(item.get("name", ""))
                elif item.get("structure") in kept_structures:
                    kept_gates.add(item.get("name", ""))
        
        # Third pass: collect models that reference removed gates
        removed_models = set()
        kept_models = set()
        for item in ucf_data:
            if item.get("collection") == "gates":
                gate_name = item.get("name", "")
                model_name = item.get("model", "")
                if gate_name in removed_gates:
                    removed_models.add(model_name)
                elif gate_name in kept_gates:
                    kept_models.add(model_name)
        
        # Final pass: build the filtered result
        result = []
        for item in ucf_data:
            # Skip items that should be removed
            if item.get("collection") == "parts":
                if item.get("type") == "promoter" and item.get("name") not in selected_part_names:
                    continue
            elif item.get("collection") == "structures":
                if item.get("name") in removed_structures:
                    continue
            elif item.get("collection") == "gates":
                if item.get("name") in removed_gates:
                    continue
            elif item.get("collection") == "models":
                if item.get("name") in removed_models:
                    continue
            elif item.get("collection") == "gate_parts":
                # Skip gate parts for removed gates
                if item.get("gate_name") in removed_gates:
                    continue
            elif item.get("collection") == "response_functions":
                # Skip response functions for removed gates
                if item.get("gate_name") in removed_gates:
                    continue
            
            # Keep everything else
            result.append(item)
        
        logger.info(f"Filtered UCF: removed {len(removed_promoters)} promoters, {len(removed_structures)} structures, "
                   f"{len(removed_gates)} gates, {len(removed_models)} models")
        return result
    
    def get_promoter_parameters(self, ucf_data: List[Dict], promoter_name: str) -> Dict:
        """
        Get the parameters associated with a promoter from its models.
        
        Args:
            ucf_data: The UCF data
            promoter_name: Name of the promoter
            
        Returns:
            Dictionary with merged parameters from all models associated with the promoter
        """
        # Find structures that output this promoter
        structures = []
        for item in ucf_data:
            if item.get("collection") == "structures" and promoter_name in item.get("outputs", []):
                structures.append(item.get("name"))
        
        # Find gates that use these structures
        gates = []
        gate_to_model = {}
        for item in ucf_data:
            if item.get("collection") == "gates" and item.get("structure") in structures:
                gates.append(item.get("name"))
                gate_to_model[item.get("name")] = item.get("model")
        
        # Find models for these gates and extract parameters
        parameters = {}
        for item in ucf_data:
            if item.get("collection") == "models" and item.get("name") in gate_to_model.values():
                for param in item.get("parameters", []):
                    param_name = param.get("name")
                    param_value = param.get("value")
                    if param_name and param_value is not None:
                        # Store or update parameter value (use the most conservative one)
                        if param_name == "ymin" and (param_name not in parameters or param_value < parameters[param_name]):
                            parameters[param_name] = param_value
                        elif param_name == "ymax" and (param_name not in parameters or param_value > parameters[param_name]):
                            parameters[param_name] = param_value
                        elif param_name == "K" and (param_name not in parameters or param_value > parameters[param_name]):
                            parameters[param_name] = param_value
                        elif param_name not in parameters:
                            parameters[param_name] = param_value
        
        return parameters
    
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
                         modified_parts: Dict[str, Dict] = None,
                         new_parts: List[Dict] = None,
                         ucf_name: str = None,
                         output_dir: str = "outputs/custom_ucf") -> str:
        """
        Create a custom UCF file with selected parts and modifications.
        
        Args:
            ucf_data: Base UCF data to customize
            selected_gates: List of gate IDs to include
            selected_parts: List of part objects to include
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
        
        # Handle selected parts (this now handles dependency cleanup)
        if selected_parts:
            logger.info(f"Filtering to {len(selected_parts)} selected parts")
            custom_ucf = self.filter_parts(custom_ucf, selected_parts)
        
        # Handle selected gates
        if selected_gates:
            # TODO: Implement gate filtering
            pass
        
        # Handle modified parts
        if modified_parts:
            for part_name, modifications in modified_parts.items():
                part = self.get_part_by_name(custom_ucf, part_name)
                if not part:
                    logger.warning(f"Part {part_name} not found in UCF, cannot modify")
                    continue
                
                # Apply modifications
                for key, value in modifications.items():
                    if key == "sequence":
                        part["dnasequence"] = value
                    elif key == "parameters":
                        # Handle parameters differently
                        for param_name, param_value in value.items():
                            # Find the parameter in the part
                            param_found = False
                            for param in part.get("parameters", []):
                                if param.get("name") == param_name:
                                    param["value"] = param_value
                                    param_found = True
                                    break
                            
                            # If parameter not found, add it
                            if not param_found:
                                if "parameters" not in part:
                                    part["parameters"] = []
                                part["parameters"].append({
                                    "name": param_name,
                                    "value": param_value
                                })
                    else:
                        # Direct property update
                        part[key] = value
        
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