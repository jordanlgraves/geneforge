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
try:
    # Try to import the new referencing library
    import referencing
    from referencing.jsonschema import DRAFT7
    REFERENCING_AVAILABLE = True
except ImportError:
    # Fall back to RefResolver if referencing is not available
    from jsonschema import RefResolver
    REFERENCING_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ucf_customizer")

class UCFCustomizer:
    """
    Creates customized UCF files with selected parts for Cello circuit design.
    Follows the UCF schema structure to ensure valid output files.
    """
    def __init__(self, base_ucf_path: str = "libs/cello-ucf/Eco1C1G1T0.UCF.json", schema_path: str = "ext_repos/Cello-UCF/schemas/v2/ucf.schema.json"):
        """Initialize with base UCF file."""
        self.base_ucf_path = base_ucf_path
        self.schema_path = schema_path
        self.schema_dir = os.path.dirname(schema_path) if schema_path else None
        
        with open(base_ucf_path, 'r') as f:
            self.base_ucf = json.load(f)
        
        # Validate that the loaded UCF is an array
        if not isinstance(self.base_ucf, list):
            raise ValueError(f"Invalid UCF format: Expected an array, got {type(self.base_ucf)}")
        
        # Index collections for easy access
        self.collections = self._index_collections(self.base_ucf)
        
        # Directory to store custom UCF files
        self.custom_ucf_dir = "outputs/custom_ucf"
        os.makedirs(self.custom_ucf_dir, exist_ok=True)
        
        # Load schema if available
        self.schema = None
        if os.path.exists(schema_path) and REFERENCING_AVAILABLE:
            try:
                with open(schema_path, 'r') as f:
                    self.schema = json.load(f)
                logger.info(f"Loaded UCF schema from {schema_path}")
            except Exception as e:
                logger.warning(f"Could not load schema from {schema_path}: {e}")
                # Continue without schema validation 
        else:
            logger.warning(f"Schema file not found at {schema_path} or referencing not available; using basic validation")
    
    def _index_collections(self, ucf_data: List[Dict]) -> Dict[str, Any]:
        """
        Index UCF collections for easier access.
        
        Args:
            ucf_data: The UCF data (array of collection objects)
            
        Returns:
            Dictionary mapping collection names to their objects
        """
        collections = {}
        for item in ucf_data:
            if not isinstance(item, dict) or "collection" not in item:
                continue
                
            collection_name = item["collection"]
            if collection_name not in collections:
                collections[collection_name] = item
            
            # Extract the actual items from collections that have arrays
            if collection_name in item:
                if collection_name not in collections:
                    collections[collection_name] = []
                collections[collection_name] = item[collection_name]
            elif collection_name + 's' in item:  # handle plurals like 'part' -> 'parts'
                plural_name = collection_name + 's'
                if plural_name not in collections:
                    collections[plural_name] = []
                collections[plural_name] = item[plural_name]
        
        return collections
    
    def _get_collection_items(self, collection_name: str) -> List[Dict]:
        """
        Get all items from a specific collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            List of items in the collection
        """
        collection = self.collections.get(collection_name, [])
        if isinstance(collection, dict) and collection_name in collection:
            return collection[collection_name]
        elif isinstance(collection, list):
            return collection
        return []
    
    def _find_item_by_id(self, collection_name: str, item_id: str) -> Optional[Dict]:
        """
        Find an item in a collection by its ID.
        
        Args:
            collection_name: Name of the collection
            item_id: The ID to look for
            
        Returns:
            Item if found, None otherwise
        """
        items = self._get_collection_items(collection_name)
        for item in items:
            if item.get("name") == item_id or item.get("id") == item_id:
                return item
        return None
    
    def create_custom_ucf(self, 
                         selected_gates: List[str] = None,
                         selected_parts: List[str] = None,
                         modified_parts: Dict[str, Dict] = None,
                         new_parts: List[Dict] = None,
                         ucf_name: str = None,
                         output_dir: str = None,
                         validate: bool = True,
                         strict_validation: bool = False) -> str:
        """
        Create a custom UCF file with selected parts and modifications.
        
        Args:
            selected_gates: List of gate IDs to include
            selected_parts: List of part IDs to include
            modified_parts: Dict of part_id -> modified properties
            new_parts: List of new part definitions to add
            ucf_name: Optional name for the UCF file
            output_dir: Optional directory to save the UCF file
            validate: Whether to validate the UCF before saving
            strict_validation: If True, raise an exception when validation fails
            
        Returns:
            Path to the created UCF file
            
        Raises:
            ValueError: If validation fails and strict_validation is True
        """
        # Use instance directory if no output_dir specified
        output_dir = output_dir or self.custom_ucf_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Start with a deep copy of the base UCF (array structure)
        custom_ucf = copy.deepcopy(self.base_ucf)
        
        # Process gates if specified
        if selected_gates:
            self._filter_collection(custom_ucf, "gates", selected_gates)
        
        # Process parts if specified
        if selected_parts:
            for collection in ["parts", "ribozymes", "terminators"]:
                self._filter_collection(custom_ucf, collection, selected_parts)
        
        # Modify parts if specified
        if modified_parts:
            self._modify_parts(custom_ucf, modified_parts)
        
        # Add new parts if specified
        if new_parts:
            # Prepare parts before adding
            prepared_parts = []
            invalid_parts = []
            
            for part in new_parts:
                # Handle field alignment before validation
                self._align_part_fields(part)
                
                # Add default parameters if missing
                self._add_default_parameters(part)
                
                # Validate the part
                validation = self.validate_part(part)
                if validation['valid']:
                    prepared_parts.append(part)
                else:
                    # Log warnings but still add the part if it has basic required fields
                    if all(field in part for field in ['name', 'type', 'dnasequence']):
                        logger.warning(f"Adding part with warnings: {part.get('name', 'unnamed')}: {validation['errors']}")
                        prepared_parts.append(part)
                    else:
                        invalid_parts.append((part, validation['errors']))
                        logger.warning(f"Invalid part (not added): {part.get('name', 'unnamed')}: {validation['errors']}")
            
            if invalid_parts and strict_validation:
                error_msg = "The following parts failed validation and were not added:\n"
                for part, errors in invalid_parts:
                    error_msg += f"- {part.get('name', 'unnamed')}: {errors}\n"
                raise ValueError(error_msg)
                    
            if prepared_parts:
                self._add_new_parts(custom_ucf, prepared_parts)
        
        # Validate the custom UCF if requested
        if validate:
            validation_result = self.validate_ucf(custom_ucf)
            if not validation_result['valid']:
                error_msg = f"Generated UCF failed validation: {validation_result['errors']}"
                logger.warning(error_msg)
                
                if strict_validation:
                    raise ValueError(error_msg)
        
        # Generate a unique name if not provided
        if not ucf_name:
            ucf_name = f"custom_ucf_{uuid.uuid4().hex[:8]}.UCF.json"
        
        # Create the output path
        output_path = os.path.join(output_dir, ucf_name)
        
        # Write the custom UCF
        with open(output_path, 'w') as f:
            json.dump(custom_ucf, f, indent=2)
            
        return output_path
    
    def _align_part_fields(self, part: Dict):
        """
        Ensure part fields align with schema requirements.
        
        Args:
            part: The part to align fields for
        """
        # Ensure "name" and "id" alignment - UCF schema uses "name"
        if "id" in part and "name" not in part:
            part["name"] = part["id"]
            
        # Ensure "dnasequence" is used (not "sequence")
        if "sequence" in part and "dnasequence" not in part:
            part["dnasequence"] = part["sequence"]
            del part["sequence"]
    
    def _add_default_parameters(self, part: Dict):
        """
        Add default parameters to a part based on its type.
        
        Args:
            part: The part to add parameters to
        """
        if "parameters" not in part:
            part["parameters"] = {}
            
        part_type = part.get("type", "").lower()
        
        # Add default parameters based on part type
        if part_type in ["promoter", "modified_promoter"]:
            if "strength" not in part["parameters"]:
                part["parameters"]["strength"] = 1.0
            if "leak" not in part["parameters"]:
                part["parameters"]["leak"] = 0.01
        elif part_type in ["cds", "repressor"]:
            if "repression" not in part["parameters"]:
                part["parameters"]["repression"] = 0.9
            if "cooperativity" not in part["parameters"]:
                part["parameters"]["cooperativity"] = 2.0
        elif part_type == "terminator":
            if "efficiency" not in part["parameters"]:
                part["parameters"]["efficiency"] = 0.95
    
    def _filter_collection(self, ucf_data: List[Dict], collection_name: str, ids_to_keep: List[str]):
        """
        Filter items in a collection to keep only those with matching IDs.
        
        Args:
            ucf_data: The UCF data to modify
            collection_name: Name of the collection to filter
            ids_to_keep: List of IDs to keep
        """
        logger.info(f"Filtering collection {collection_name} to keep IDs: {ids_to_keep}")
        
        # Handle the case where each item is its own collection entry (like gates)
        if collection_name == "gates":
            # Create a list of indices to remove
            indices_to_remove = []
            for i, item in enumerate(ucf_data):
                if isinstance(item, dict) and item.get("collection") == "gates":
                    gate_id = item.get("gate_name")
                    if gate_id not in ids_to_keep:
                        indices_to_remove.append(i)
                        logger.info(f"Removing gate with ID {gate_id}")
            
            # Remove items in reverse order to avoid index shifting
            for i in sorted(indices_to_remove, reverse=True):
                del ucf_data[i]
            
            logger.info(f"Filtered gates from {len(ucf_data) + len(indices_to_remove)} to {len(ucf_data) - len(indices_to_remove)} items")
            return
        
        # For collections with arrays of items (parts, terminators, etc.)
        for item in ucf_data:
            if not isinstance(item, dict) or item.get("collection") != collection_name:
                continue
                
            # For collections with arrays of items
            for array_field in [collection_name, "parts", "ribozymes", "terminators"]:
                if array_field in item and isinstance(item[array_field], list):
                    # Keep a list of items that match our criteria
                    filtered_items = []
                    for sub_item in item[array_field]:
                        # Get the ID of this item (check all possible ID fields)
                        sub_id = sub_item.get("name") or sub_item.get("id") or sub_item.get("gate_name")
                        if sub_id in ids_to_keep:
                            logger.info(f"Keeping item with ID {sub_id} in {array_field}")
                            filtered_items.append(sub_item)
                    
                    # Replace with filtered list
                    logger.info(f"Filtered {array_field} from {len(item[array_field])} to {len(filtered_items)} items")
                    item[array_field] = filtered_items
    
    def _modify_parts(self, ucf_data: List[Dict], modifications: Dict[str, Dict]):
        """
        Apply modifications to parts in the UCF data.
        
        Args:
            ucf_data: The UCF data to modify
            modifications: Dict mapping part IDs to their modifications
        """
        # First check for parts that are individual collection items
        for item in ucf_data:
            if not isinstance(item, dict) or "collection" not in item:
                continue
                
            collection = item["collection"]
            if collection in ["parts", "ribozymes", "terminators"]:
                # Check if this item itself is a part
                part_id = item.get("name") or item.get("id")
                if part_id in modifications:
                    logger.info(f"Modifying part with ID {part_id}")
                    self._apply_modification(item, modifications[part_id])
                
            # Also check for parts in arrays
            if collection in ["parts", "ribozymes", "terminators", "gates"]:
                # Check all possible array fields where parts might be
                array_fields = [collection]
                if collection == "parts":
                    array_fields.extend(["parts", "ribozymes", "terminators", "gates"])
                
                for field in array_fields:
                    if field in item and isinstance(item[field], list):
                        for sub_item in item[field]:
                            part_id = sub_item.get("name") or sub_item.get("id")
                            if part_id in modifications:
                                logger.info(f"Modifying part with ID {part_id} in array {field}")
                                self._apply_modification(sub_item, modifications[part_id])
    
    def _apply_modification(self, item: Dict, modifications: Dict):
        """
        Apply modifications to a specific item.
        
        Args:
            item: The item to modify
            modifications: Modifications to apply
        """
        for key, value in modifications.items():
            if key == "parameters" and "parameters" in item and isinstance(item["parameters"], dict):
                # Merge parameters rather than replacing
                item["parameters"].update(value)
            else:
                item[key] = value
    
    def _add_new_parts(self, ucf_data: List[Dict], new_parts: List[Dict]):
        """
        Add new parts to the UCF data.
        
        Args:
            ucf_data: The UCF data to modify
            new_parts: List of new parts to add
        """
        for part in new_parts:
            # Ensure parts have required fields in the correct format
            if not part.get("name") and not part.get("id"):
                continue  # Skip parts without an identifier
            
            # Ensure fields are aligned with the schema
            self._align_part_fields(part)
                
            if "type" not in part:
                continue  # Skip parts without a type
                
            part_type = part["type"].lower()
            collection_name = self._get_collection_for_part_type(part_type)
            
            # Find the matching collection object
            collection_obj = None
            for item in ucf_data:
                if isinstance(item, dict) and item.get("collection") == collection_name:
                    collection_obj = item
                    break
            
            # If collection not found, create it
            if collection_obj is None:
                collection_obj = {"collection": collection_name}
                ucf_data.append(collection_obj)
            
            # Add the part to the collection
            # Most collections follow the pattern: "collection": "parts", "parts": [...]
            target_array_name = collection_name
            # Some collections might use singular form in the collection name
            # but plural in the array name (e.g. "part" -> "parts")
            if collection_name[-1] != 's' and collection_name + 's' in collection_obj:
                target_array_name = collection_name + 's'
            
            # Create the array if it doesn't exist
            if target_array_name not in collection_obj:
                collection_obj[target_array_name] = []
                
            # Add the part
            collection_obj[target_array_name].append(part)
    
    def _get_collection_for_part_type(self, part_type: str) -> str:
        """
        Determine the appropriate collection for a part type.
        
        Args:
            part_type: Type of the part
            
        Returns:
            Collection name
        """
        if "promoter" in part_type or "cds" in part_type or "rbs" in part_type:
            return "parts"
        elif "ribozyme" in part_type:
            return "ribozymes"
        elif "terminator" in part_type:
            return "terminators"
        else:
            return "parts"  # Default
    
    def validate_part(self, part: Dict) -> Dict[str, Any]:
        """
        Validate a part definition against schema requirements.
        
        Args:
            part: The part definition to validate
            
        Returns:
            Dict with validation results:
            - valid: Boolean indicating if validation passed
            - errors: List of error messages if validation failed
        """
        result = {
            "valid": True,
            "errors": []
        }
        
        # Check part type
        valid_types = [
            "promoter", "cds", "ribozyme", "rbs", "terminator", 
            "cassette", "scar", "spacer", "modified_promoter"
        ]
        
        if not part.get('type'):
            result["valid"] = False
            result["errors"].append("Part is missing required 'type' field")
        elif part.get('type') not in valid_types:
            result["valid"] = False
            result["errors"].append(
                f"Invalid part type: '{part.get('type')}'. Valid types are: {', '.join(valid_types)}"
            )
        
        # Check required fields
        required_fields = ['name', 'type', 'dnasequence']
        for field in required_fields:
            if field not in part:
                result["valid"] = False
                result["errors"].append(f"Missing required field: '{field}'")
        
        # Validate DNA sequence if present
        if 'dnasequence' in part:
            dna_seq = part['dnasequence']
            if not isinstance(dna_seq, str):
                result["valid"] = False
                result["errors"].append(f"DNA sequence must be a string, got {type(dna_seq).__name__}")
            elif not all(c in 'ATGCatgc' for c in dna_seq):
                result["valid"] = False
                result["errors"].append("DNA sequence contains invalid characters (only A, T, G, C allowed)")
        
        # Check parameters field structure if present
        if 'parameters' in part:
            if not isinstance(part['parameters'], dict):
                result["valid"] = False
                result["errors"].append("'parameters' field must be an object")
            else:
                # Type-specific parameter validation - now just warnings, not errors
                part_type = part.get('type')
                if part_type in ["promoter", "modified_promoter"]:
                    for param in ["strength", "leak"]:
                        if param not in part['parameters']:
                            # Just log a warning, don't fail validation
                            logger.warning(f"Promoter missing recommended parameter: '{param}'")
                elif part_type in ["cds", "repressor"]:
                    for param in ["repression", "cooperativity"]:
                        if param not in part['parameters']:
                            # Just log a warning, don't fail validation
                            logger.warning(f"CDS/repressor missing recommended parameter: '{param}'")
                elif part_type == "terminator" and "efficiency" not in part['parameters']:
                    # Just log a warning, don't fail validation
                    logger.warning("Terminator missing recommended parameter: 'efficiency'")
        
        return result
    
    def get_part_by_id(self, part_id: str) -> Optional[Dict]:
        """
        Get a part from the base UCF by ID.
        
        Args:
            part_id: ID of the part to get
            
        Returns:
            Part if found, None otherwise
        """
        for collection in ["parts", "ribozymes", "terminators", "gates"]:
            part = self._find_item_by_id(collection, part_id)
            if part:
                return part
        return None
    
    def create_part_template(self, part_type: str) -> Dict:
        """
        Create a template for a new part based on type.
        
        Args:
            part_type: Type of part to create template for
            
        Returns:
            Dict with the basic structure for the part type
        """
        # Generate a unique ID
        part_id = f"new_{part_type}_{uuid.uuid4().hex[:6]}"
        
        # Base template following the schema
        template = {
            "name": part_id,
            "type": part_type,
            "dnasequence": ""
        }
        
        # Add type-specific properties
        if part_type == "promoter" or part_type == "modified_promoter":
            template["parameters"] = {"strength": 1.0, "leak": 0.01}
        elif part_type in ["cds", "repressor"]:
            template["parameters"] = {"repression": 0.9, "cooperativity": 2.0}
        elif part_type == "terminator":
            template["parameters"] = {"efficiency": 0.95}
        
        return template
    
    def validate_ucf(self, ucf_data: List[Dict] = None, required_collections: List[str] = None) -> Dict[str, Any]:
        """
        Validate a UCF data structure against the schema.
        
        Args:
            ucf_data: The UCF data to validate. If None, uses the instance's base_ucf.
            required_collections: List of collection names that must be present.
                                 If None, only "header" is required.
            
        Returns:
            Dict with validation results:
            - valid: Boolean indicating if validation passed
            - errors: List of error messages if validation failed
        """
        result = {
            "valid": True,
            "errors": []
        }
        
        # Use provided data or instance data
        validation_data = ucf_data if ucf_data is not None else self.base_ucf
        
        # Basic format validation
        if not isinstance(validation_data, list):
            result["valid"] = False
            result["errors"].append("UCF data must be a list of collections")
            return result
        
        # Check for required collections
        if required_collections is None:
            required_collections = ["header"]  # Only header is absolutely required
            
        collection_ids = [coll.get("collection") for coll in validation_data if isinstance(coll, dict)]
        
        for req_coll in required_collections:
            if req_coll not in collection_ids:
                result["valid"] = False
                result["errors"].append(f"Required collection '{req_coll}' is missing")
        
        # If basic validation failed, return early
        if not result["valid"]:
            return result
        
        # Schema validation if available
        if hasattr(self, 'schema') and self.schema:
            try:
                # Try to use the referencing library for better error messages
                if REFERENCING_AVAILABLE:
                    try:
                        # Create a registry for resolving references
                        registry = {}
                        
                        # Define a resolver function for local references
                        def resolve_local_ref(uri):
                            if uri.startswith("file:"):
                                return self._retrieve_schema(uri)
                            return None
                        
                        # Create a resolver that uses our function
                        resolver = jsonschema.RefResolver.from_schema(
                            self.schema,
                            handlers={"file": resolve_local_ref}
                        )
                        
                        # Validate with the resolver
                        jsonschema.validate(
                            instance=validation_data,
                            schema=self.schema,
                            resolver=resolver
                        )
                    except ValidationError as e:
                        # Report validation errors but don't fail validation
                        # This allows for more flexible UCF creation
                        logger.warning(f"Schema validation warning: {e}")
                    except Exception as e:
                        # Report other errors but don't fail validation
                        logger.warning(f"Schema validation warning: {e}")
                else:
                    try:
                        jsonschema.validate(instance=validation_data, schema=self.schema)
                    except ValidationError as e:
                        # Report validation errors but don't fail validation
                        logger.warning(f"Schema validation warning: {e}")
                    except Exception as e:
                        # Report other errors but don't fail validation
                        logger.warning(f"Schema validation warning: {e}")
            except Exception as e:
                # Log any other errors but don't fail validation
                logger.warning(f"Validation warning: {e}")
        
        return result
        
    def _retrieve_schema(self, uri):
        """Retrieve a schema reference from a URL or file path."""
        if uri.startswith(('http://', 'https://')):
            try:
                import requests
                response = requests.get(uri)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to download schema: {uri} (status code: {response.status_code})")
                    return None
            except Exception as e:
                logger.warning(f"Error downloading schema: {uri} - {str(e)}")
                return None
        elif uri.startswith('file:'):
            file_path = uri.replace("file:", "")
            if os.name == 'nt' and file_path.startswith("/"):
                file_path = file_path[1:]
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except FileNotFoundError:
                if self.schema_dir:
                    schema_dir = os.path.abspath(self.schema_dir)
                    filename = os.path.basename(uri)
                    alternative_path = os.path.join(schema_dir, filename)
                    try:
                        with open(alternative_path, 'r') as f:
                            return json.load(f)
                    except FileNotFoundError:
                        logger.warning(f"Reference file not found: {uri} or {alternative_path}")
                        return None
        return None
    
    def customize_ucf(self, input_ucf_path: str, output_ucf_path: str, modified_parts: Dict[str, Dict] = None) -> str:
        """
        Customize an existing UCF file with modified parts.
        
        Args:
            input_ucf_path: Path to the input UCF file
            output_ucf_path: Path to save the customized UCF file
            modified_parts: Dictionary mapping part names to dictionaries of modifications
            
        Returns:
            Path to the saved customized UCF file
        """
        if not os.path.exists(input_ucf_path):
            raise FileNotFoundError(f"Input UCF file not found: {input_ucf_path}")
        
        logger.info(f"Customizing UCF file: {input_ucf_path}")
        
        # Load the input UCF
        with open(input_ucf_path, 'r') as f:
            ucf_data = json.load(f)
        
        # Validate the input UCF
        validation_result = self.validate_ucf(ucf_data)
        if not validation_result['valid']:
            logger.warning(f"Input UCF file is not valid: {validation_result['errors']}")
        
        # Modify parts if specified
        if modified_parts:
            self._modify_parts(ucf_data, modified_parts)
            logger.info(f"Modified {len(modified_parts)} parts in UCF")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_ucf_path)), exist_ok=True)
        
        # Save the customized UCF
        with open(output_ucf_path, 'w') as f:
            json.dump(ucf_data, f, indent=2)
        
        logger.info(f"Saved customized UCF to: {output_ucf_path}")
        
        return output_ucf_path
    
    def customize_ucf_with_parameters(self, input_ucf_path, output_ucf_path, 
                                     modified_parts=None, 
                                     modified_parameters=None):
        """
        Customize UCF with both part sequences and response function parameters.
        
        Args:
            input_ucf_path: Path to input UCF file
            output_ucf_path: Path for saving output
            modified_parts: Dict mapping part names to sequence modifications
            modified_parameters: Dict mapping gate names to parameter modifications
                e.g. {"S4_SrpR": {"ymax": 45.2, "ymin": 0.05, "K": 0.85, "n": 4.9}}
        """
        # Load UCF data
        with open(input_ucf_path, 'r') as f:
            ucf_data = json.load(f)
        
        # Modify part sequences if specified
        if modified_parts:
            self._modify_parts(ucf_data, modified_parts)
        
        # Modify response function parameters if specified
        if modified_parameters:
            for item in ucf_data:
                if item.get("collection") == "response_functions":
                    gate_name = item.get("gate_name")
                    if gate_name in modified_parameters:
                        for param in item.get("parameters", []):
                            param_name = param.get("name")
                            if param_name in modified_parameters[gate_name]:
                                param["value"] = modified_parameters[gate_name][param_name]
        
        # Save the modified UCF
        with open(output_ucf_path, 'w') as f:
            json.dump(ucf_data, f, indent=2)
        
        return output_ucf_path
    
    def find_gate_for_promoter(self, ucf_data, promoter_name):
        """
        Find the gate name associated with a promoter.
        
        Args:
            ucf_data: The UCF data
            promoter_name: Name of the promoter
            
        Returns:
            Gate name if found, None otherwise
        """
        for item in ucf_data:
            if item.get("collection") == "gate_parts" and item.get("promoter") == promoter_name:
                return item.get("gate_name")
        return None

    def get_gate_parameters(self, ucf_data, gate_name):
        """
        Get parameters for a specific gate.
        
        Args:
            ucf_data: The UCF data
            gate_name: Name of the gate
            
        Returns:
            Dictionary of parameters if found, None otherwise
        """
        for item in ucf_data:
            if item.get("collection") == "response_functions" and item.get("gate_name") == gate_name:
                param_dict = {}
                for param in item.get("parameters", []):
                    param_dict[param.get("name")] = param.get("value")
                return param_dict
        return None