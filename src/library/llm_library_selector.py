import logging
import re
import os
import json
from typing import Dict, List, Optional, Union, Any, Tuple
import openai

from src.library.library_manager import LibraryManager
from src.library.parse_ucf import parse_ecoli_ucf
from src.library.ucf_retrieval import get_all_parts, get_all_gates

logger = logging.getLogger("library_selector")

class RuleBasedLibrarySelector:
    """
    A class that helps select appropriate libraries based on user requests using rule-based matching.
    This class analyzes user requests, extracts relevant information, and selects
    the most appropriate library based on predefined rules.
    """
    
    def __init__(self, library_manager: Optional[LibraryManager] = None):
        """
        Initialize the library selector with a library manager.
        
        Args:
            library_manager: Library manager instance. If None, a new one will be created.
        """
        self.library_manager = library_manager or LibraryManager()
        
        # Common terms for organisms, parts, and gates
        self.organism_terms = {
            "e. coli": ["e. coli", "e.coli", "ecoli", "escherichia coli", "eco"],
            "yeast": ["yeast", "s. cerevisiae", "saccharomyces cerevisiae", "sc"],
            "bacillus": ["bacillus", "b. subtilis", "bacillus subtilis", "bth"]
        }
        
        self.part_terms = {
            "promoters": ["promoter", "prom", "p"],
            "terminators": ["terminator", "term", "t"],
            "ribosome_binding_sites": ["rbs", "ribosome binding site"],
            "coding_sequences": ["cds", "coding sequence", "gene", "protein"]
        }
        
        self.gate_terms = {
            "not": ["not", "inverter", "invert"],
            "nor": ["nor"],
            "and": ["and"],
            "or": ["or"],
            "nand": ["nand"],
            "xor": ["xor"]
        }
        
        self.reporter_terms = {
            "gfp": ["gfp", "green fluorescent protein", "green"],
            "rfp": ["rfp", "red fluorescent protein", "red"],
            "yfp": ["yfp", "yellow fluorescent protein", "yellow"],
            "cfp": ["cfp", "cyan fluorescent protein", "cyan", "blue"]
        }
        
        self.inducer_terms = {
            "arabinose": ["arabinose", "ara", "pbad"],
            "iptg": ["iptg", "isopropyl", "ptac", "plac"],
            "atc": ["atc", "anhydrotetracycline", "tetracycline", "tet", "ptet"],
            "hsl": ["hsl", "homoserine lactone", "ahl", "acyl", "plux"]
        }
    
    def analyze_user_request(self, user_request: str) -> Dict[str, Any]:
        """
        Analyze a user request to extract relevant information for library selection.
        
        Args:
            user_request: The user's request as a string
            
        Returns:
            Dict containing extracted information:
            - organisms: List of identified organisms
            - parts: List of identified part types
            - gates: List of identified gate types
            - reporters: List of identified reporters
            - inducers: List of identified inducers
            - raw_request: The original user request
        """
        # Convert to lowercase for easier matching
        request_lower = user_request.lower()
        
        # Extract information
        organisms = self._extract_terms(request_lower, self.organism_terms)
        parts = self._extract_terms(request_lower, self.part_terms)
        gates = self._extract_terms(request_lower, self.gate_terms)
        reporters = self._extract_terms(request_lower, self.reporter_terms)
        inducers = self._extract_terms(request_lower, self.inducer_terms)
        
        # Log the extracted information
        logger.info(f"Extracted from user request: organisms={organisms}, parts={parts}, "
                   f"gates={gates}, reporters={reporters}, inducers={inducers}")
        
        return {
            "organisms": organisms,
            "parts": parts,
            "gates": gates,
            "reporters": reporters,
            "inducers": inducers,
            "raw_request": user_request
        }
    
    def _extract_terms(self, text: str, term_dict: Dict[str, List[str]]) -> List[str]:
        """
        Extract terms from text based on a dictionary of terms.
        
        Args:
            text: Text to search in
            term_dict: Dictionary mapping categories to lists of terms
            
        Returns:
            List of categories that were found in the text
        """
        found_terms = []
        
        for category, terms in term_dict.items():
            for term in terms:
                # Use word boundary to avoid partial matches
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, text):
                    found_terms.append(category)
                    break  # Once we find one term in a category, we can move on
        
        return found_terms
    
    def select_library(self, user_request: str) -> Dict[str, Any]:
        """
        Select the most appropriate library based on a user request.
        
        Args:
            user_request: The user's request as a string
            
        Returns:
            Dict containing:
            - success: Boolean indicating if a library was found
            - library_id: ID of the selected library (if success is True)
            - message: Human-readable message explaining the selection
            - analysis: The analysis of the user request
            - alternatives: List of alternative libraries (if available)
        """
        # Analyze the user request
        analysis = self.analyze_user_request(user_request)
        
        # Get available libraries
        available_libraries = self.library_manager.get_available_libraries()
        
        if not available_libraries:
            return {
                "success": False,
                "message": "No libraries are available in the system.",
                "analysis": analysis
            }
        
        # First, try to select based on organism
        selected_library = None
        if analysis["organisms"]:
            # Try each organism in order
            for organism in analysis["organisms"]:
                # Try to select a library for this organism
                if self.library_manager.select_library(organism):
                    selected_library = self.library_manager.current_library_id
                    break
        
        # If no library was selected based on organism, try to find the best match
        if not selected_library:
            # Default to E. coli if no organism was specified
            if self.library_manager.select_library("ecoli"):
                selected_library = self.library_manager.current_library_id
                message = "No specific organism was identified, defaulting to E. coli library."
            else:
                # If we can't even select E. coli, just use the first available library
                if self.library_manager.select_library(available_libraries[0]):
                    selected_library = self.library_manager.current_library_id
                    message = f"No specific organism was identified, using available library: {selected_library}"
                else:
                    return {
                        "success": False,
                        "message": "Could not select any library.",
                        "analysis": analysis,
                        "available_libraries": available_libraries
                    }
        else:
            message = f"Selected library {selected_library} based on identified organism: {', '.join(analysis['organisms'])}"
        
        # Check if the selected library has the required parts, gates, reporters, and inducers
        library_data = self.library_manager.get_library_data()
        missing_features = self._check_library_features(library_data, analysis)
        
        # If there are missing features, include them in the message
        if missing_features:
            message += f"\nWarning: The selected library may not have all the requested features: {', '.join(missing_features)}"
        
        # Find alternative libraries
        alternatives = self._find_alternative_libraries(analysis, selected_library)
        
        return {
            "success": True,
            "library_id": selected_library,
            "message": message,
            "analysis": analysis,
            "alternatives": alternatives,
            "missing_features": missing_features
        }
    
    def _check_library_features(self, library_data: Dict[str, Any], analysis: Dict[str, Any]) -> List[str]:
        """
        Check if a library has all the features requested by the user.
        
        Args:
            library_data: Library data dictionary
            analysis: Analysis of the user request
            
        Returns:
            List of missing features
        """
        missing_features = []
        
        # Skip if no library data is available
        if not library_data:
            return ["library_data_unavailable"]
        
        # Check for reporters
        if analysis["reporters"]:
            for reporter in analysis["reporters"]:
                reporter_found = False
                
                # Handle different library data structures
                parts = []
                if "parts" in library_data:
                    parts_data = library_data["parts"]
                    if isinstance(parts_data, list):
                        parts = parts_data
                    elif isinstance(parts_data, dict) and "parts" in parts_data:
                        parts = parts_data["parts"]
                
                for part in parts:
                    part_id = ""
                    if isinstance(part, dict):
                        part_id = part.get("id", part.get("name", "")).lower()
                    elif isinstance(part, str):
                        part_id = part.lower()
                    
                    if reporter.lower() in part_id:
                        reporter_found = True
                        break
                
                if not reporter_found:
                    missing_features.append(f"{reporter} reporter")
        
        # Check for gates
        if analysis["gates"]:
            for gate_type in analysis["gates"]:
                gate_found = False
                
                # Handle different library data structures
                gates = []
                if "gates" in library_data:
                    gates_data = library_data["gates"]
                    if isinstance(gates_data, list):
                        gates = gates_data
                    elif isinstance(gates_data, dict):
                        gates = [gates_data]  # Single gate as a dictionary
                
                for gate in gates:
                    if isinstance(gate, dict):
                        gate_type_value = gate.get("gate_type", "").lower()
                        if gate_type.lower() == gate_type_value:
                            gate_found = True
                            break
                
                if not gate_found:
                    missing_features.append(f"{gate_type} gate")
        
        # Check for inducers
        if analysis["inducers"]:
            for inducer in analysis["inducers"]:
                inducer_found = False
                
                # Handle different library data structures
                parts = []
                if "parts" in library_data:
                    parts_data = library_data["parts"]
                    if isinstance(parts_data, list):
                        parts = parts_data
                    elif isinstance(parts_data, dict) and "parts" in parts_data:
                        parts = parts_data["parts"]
                
                for part in parts:
                    part_id = ""
                    if isinstance(part, dict):
                        part_id = part.get("id", part.get("name", "")).lower()
                    elif isinstance(part, str):
                        part_id = part.lower()
                    
                    if any(term in part_id for term in self.inducer_terms.get(inducer, [])):
                        inducer_found = True
                        break
                
                if not inducer_found:
                    missing_features.append(f"{inducer} inducer")
        
        return missing_features
    
    def _find_alternative_libraries(self, analysis: Dict[str, Any], current_library: str) -> List[Dict[str, Any]]:
        """
        Find alternative libraries that might match the user's request.
        
        Args:
            analysis: Analysis of the user request
            current_library: ID of the currently selected library
            
        Returns:
            List of alternative libraries with their descriptions
        """
        alternatives = []
        
        # Get all available libraries
        available_libraries = self.library_manager.get_available_libraries()
        
        # Skip the current library
        available_libraries = [lib for lib in available_libraries if lib != current_library]
        
        # Check each library
        for library_id in available_libraries:
            # Try to load this library
            if self.library_manager.select_library(library_id):
                library_data = self.library_manager.get_library_data()
                
                # Check if this library has the features the user wants
                missing_features = self._check_library_features(library_data, analysis)
                
                # Add this library as an alternative
                alternatives.append({
                    "library_id": library_id,
                    "missing_features": missing_features
                })
        
        # Sort alternatives by number of missing features (fewer is better)
        alternatives.sort(key=lambda x: len(x["missing_features"]))
        
        # Limit to top 3 alternatives
        return alternatives[:3]
    
    def get_library_metadata(self, library_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metadata about a library.
        
        Args:
            library_id: ID of the library to get metadata for. If None, uses the current library.
            
        Returns:
            Dict containing metadata about the library
        """
        # If a library ID was provided, try to select it
        if library_id:
            if not self.library_manager.select_library(library_id):
                return {
                    "error": f"Library {library_id} not found"
                }
        
        # Get the current library data
        library_data = self.library_manager.get_library_data()
        
        if not library_data:
            return {
                "error": "No library data available"
            }
        
        # Extract metadata
        metadata = {
            "library_id": self.library_manager.current_library_id,
            "part_count": len(library_data.get("parts", [])),
            "gate_count": len(library_data.get("gates", [])),
            "gate_types": self._extract_gate_types(library_data),
            "has_reporters": self._has_reporters(library_data),
            "has_inducers": self._has_inducers(library_data),
            "organism": self._extract_organism(self.library_manager.current_library_id)
        }
        
        return metadata
    
    def _extract_gate_types(self, library_data: Dict[str, Any]) -> List[str]:
        """
        Extract the types of gates available in a library.
        
        Args:
            library_data: Library data dictionary
            
        Returns:
            List of gate types
        """
        gate_types = set()
        
        # Handle different library data structures
        gates = []
        if "gates" in library_data:
            gates_data = library_data["gates"]
            if isinstance(gates_data, list):
                gates = gates_data
            elif isinstance(gates_data, dict):
                gates = [gates_data]  # Single gate as a dictionary
        
        for gate in gates:
            if isinstance(gate, dict):
                gate_type = gate.get("gate_type", "").lower()
                if gate_type:
                    gate_types.add(gate_type)
        
        return list(gate_types)
    
    def _has_reporters(self, library_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Check if a library has common reporters.
        
        Args:
            library_data: Library data dictionary
            
        Returns:
            Dict mapping reporter types to booleans
        """
        reporters = {
            "gfp": False,
            "rfp": False,
            "yfp": False,
            "cfp": False
        }
        
        # Handle different library data structures
        parts = []
        if "parts" in library_data:
            parts_data = library_data["parts"]
            if isinstance(parts_data, list):
                parts = parts_data
            elif isinstance(parts_data, dict) and "parts" in parts_data:
                parts = parts_data["parts"]
        
        for part in parts:
            part_id = ""
            if isinstance(part, dict):
                part_id = part.get("id", part.get("name", "")).lower()
            elif isinstance(part, str):
                part_id = part.lower()
            
            if "gfp" in part_id:
                reporters["gfp"] = True
            if "rfp" in part_id:
                reporters["rfp"] = True
            if "yfp" in part_id:
                reporters["yfp"] = True
            if "cfp" in part_id:
                reporters["cfp"] = True
        
        return reporters
    
    def _has_inducers(self, library_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Check if a library has common inducers.
        
        Args:
            library_data: Library data dictionary
            
        Returns:
            Dict mapping inducer types to booleans
        """
        inducers = {
            "arabinose": False,
            "iptg": False,
            "atc": False,
            "hsl": False
        }
        
        # Handle different library data structures
        parts = []
        if "parts" in library_data:
            parts_data = library_data["parts"]
            if isinstance(parts_data, list):
                parts = parts_data
            elif isinstance(parts_data, dict) and "parts" in parts_data:
                parts = parts_data["parts"]
        
        for part in parts:
            part_id = ""
            if isinstance(part, dict):
                part_id = part.get("id", part.get("name", "")).lower()
            elif isinstance(part, str):
                part_id = part.lower()
            
            if any(term in part_id for term in ["arabinose", "pbad"]):
                inducers["arabinose"] = True
            if any(term in part_id for term in ["iptg", "ptac", "plac"]):
                inducers["iptg"] = True
            if any(term in part_id for term in ["atc", "ptet"]):
                inducers["atc"] = True
            if any(term in part_id for term in ["hsl", "plux"]):
                inducers["hsl"] = True
        
        return inducers
    
    def _extract_organism(self, library_id: str) -> str:
        """
        Extract the organism from a library ID.
        
        Args:
            library_id: Library ID
            
        Returns:
            Organism name
        """
        if library_id.startswith("Eco"):
            return "E. coli"
        elif library_id.startswith("SC"):
            return "S. cerevisiae (yeast)"
        elif library_id.startswith("Bth"):
            return "B. subtilis"
        else:
            return "Unknown"


class LLMBasedLibrarySelector:
    """
    A class that uses LLM-based reasoning to select appropriate libraries for genetic circuit design.
    This class provides library metadata to an LLM and asks it to reason about which library
    best matches the user's request.
    """
    
    def __init__(self, 
                library_manager: Optional[LibraryManager] = None,
                openai_api_key: Optional[str] = None,
                model: str = "gpt-4"):
        """
        Initialize the LLM-based library selector.
        
        Args:
            library_manager: Library manager instance. If None, a new one will be created.
            openai_api_key: OpenAI API key. If None, will use OPENAI_API_KEY environment variable.
            model: OpenAI model to use for reasoning.
        """
        self.library_manager = library_manager or LibraryManager()
        self.model = model
        
        # Set up OpenAI API
        if openai_api_key:
            openai.api_key = openai_api_key
        elif os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
        else:
            logger.warning("No OpenAI API key provided. LLM-based selection will not work.")
        
        # Cache for library metadata
        self.metadata_cache = {}
    
    def select_library(self, user_request: str) -> Dict[str, Any]:
        """
        Select the most appropriate library for a user request using LLM reasoning.
        
        Args:
            user_request: The user's request as a string
            
        Returns:
            Dict containing:
            - success: Boolean indicating if a library was found
            - library_id: ID of the selected library (if success is True)
            - message: Human-readable message explaining the selection
            - reasoning: The LLM's reasoning for the selection
            - alternatives: List of alternative libraries with reasoning (if available)
        """
        # Get available libraries
        available_libraries = self.library_manager.get_available_libraries()
        
        if not available_libraries:
            return {
                "success": False,
                "message": "No libraries are available in the system.",
                "reasoning": "No libraries are available to select from."
            }
        
        # Get metadata for all libraries
        libraries_metadata = self._get_all_libraries_metadata(available_libraries)
        
        # Construct prompt for LLM
        prompt = self._construct_library_selection_prompt(user_request, libraries_metadata)
        
        try:
            # Call OpenAI API
            response = self._call_openai_api(prompt)
            
            # Parse LLM response
            selection_result = self._parse_library_selection_response(response, available_libraries)
            
            # If successful, try to load the selected library to verify
            if selection_result["success"] and selection_result["library_id"]:
                if not self.library_manager.select_library(selection_result["library_id"]):
                    selection_result["success"] = False
                    selection_result["message"] = f"Selected library {selection_result['library_id']} could not be loaded."
            
            return selection_result
            
        except Exception as e:
            logger.error(f"Error during LLM-based library selection: {e}")
            return {
                "success": False,
                "message": f"Error during library selection: {str(e)}",
                "available_libraries": available_libraries
            }
    
    def _get_all_libraries_metadata(self, library_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all available libraries.
        
        Args:
            library_ids: List of library IDs to get metadata for
            
        Returns:
            Dict mapping library IDs to their metadata
        """
        metadata = {}
        
        for lib_id in library_ids:
            # Check cache first
            if lib_id in self.metadata_cache:
                metadata[lib_id] = self.metadata_cache[lib_id]
                continue
            
            # Try to load the library
            if self.library_manager.select_library(lib_id):
                # Get library info
                library_info = self.library_manager.get_current_library_info()
                
                # Process UCF file to extract detailed metadata
                ucf_path = library_info.get("ucf_path")
                input_path = library_info.get("input_path")
                output_path = library_info.get("output_path")
                
                if ucf_path and os.path.exists(ucf_path):
                    try:
                        # Parse UCF file
                        ucf_data = parse_ecoli_ucf(ucf_path)["structured_data"]
                        
                        # Get parts and gates
                        parts = get_all_parts(ucf_data)
                        gates = get_all_gates(ucf_data)
                        
                        # Categorize parts with more detail
                        promoters = [p for p in parts if p.get("raw_data", {}).get("type") == "promoter"]
                        terminators = [p for p in parts if p.get("raw_data", {}).get("type") == "terminator"]
                        repressors = [p for p in parts if p.get("raw_data", {}).get("type") == "cds" or p.get("raw_data", {}).get("type") == "repressor"]
                        rbs_parts = [p for p in parts if p.get("raw_data", {}).get("type") == "rbs"]
                        reporters = [p for p in parts if any(r in p.get("id", "").lower() for r in ["gfp", "rfp", "yfp", "cfp"])]
                        ribozymes = [p for p in parts if p.get("raw_data", {}).get("type") == "ribozyme"]
                        scars = [p for p in parts if p.get("raw_data", {}).get("type") == "scar"]
                        
                        # Create more detailed part information
                        detailed_parts = []
                        for p in parts:
                            part_detail = {
                                "id": p.get("id", ""),
                                "type": p.get("type", ""),
                                "raw_type": p.get("raw_data", {}).get("type", ""),
                                "description": p.get("raw_data", {}).get("description", ""),
                                "sequence_length": len(p.get("raw_data", {}).get("sequence", "")) if p.get("raw_data", {}).get("sequence") else 0,
                            }
                            detailed_parts.append(part_detail)
                        
                        # Extract input/output related information
                        inputs = []
                        outputs = []
                        input_details = {}
                        output_details = {}
                        
                        # Try to extract input/output info from input file if available
                        if input_path and os.path.exists(input_path):
                            try:
                                with open(input_path, 'r') as f:
                                    input_data = json.load(f)
                                    if isinstance(input_data, dict):
                                        # Extract inputs from input file
                                        if "inputs" in input_data:
                                            inputs = input_data["inputs"]
                                            # Try to extract more details about inputs
                                            if isinstance(inputs, list):
                                                for i, input_item in enumerate(inputs):
                                                    if isinstance(input_item, dict):
                                                        input_name = input_item.get("name", f"input_{i}")
                                                        input_details[input_name] = input_item
                                        
                                        # Extract outputs from input file
                                        if "outputs" in input_data:
                                            outputs = input_data["outputs"]
                                            # Try to extract more details about outputs
                                            if isinstance(outputs, list):
                                                for i, output_item in enumerate(outputs):
                                                    if isinstance(output_item, dict):
                                                        output_name = output_item.get("name", f"output_{i}")
                                                        output_details[output_name] = output_item
                            except Exception as e:
                                logger.error(f"Error parsing input file {input_path}: {e}")
                        
                        # Gate types and information
                        gate_types = set()
                        gate_details = []
                        for gate in gates:
                            gate_type = gate.get("gate_type", "").lower()
                            if gate_type:
                                gate_types.add(gate_type)
                            
                            # Add more detailed gate information
                            gate_detail = {
                                "id": gate.get("id", ""),
                                "type": gate_type,
                                "group_name": gate.get("raw_data", {}).get("group_name", ""),
                                "system": gate.get("raw_data", {}).get("system", ""),
                                "inputs": gate.get("raw_data", {}).get("inputs", []),
                                "outputs": gate.get("raw_data", {}).get("outputs", [])
                            }
                            gate_details.append(gate_detail)
                        
                        # Extract organism from library ID with more detail
                        organism = "Unknown"
                        organism_details = {}
                        if lib_id.startswith("Eco"):
                            organism = "E. coli"
                            organism_details = {
                                "full_name": "Escherichia coli",
                                "type": "bacteria",
                                "gram_stain": "negative",
                                "domains": ["prokaryotic"]
                            }
                        elif lib_id.startswith("SC"):
                            organism = "S. cerevisiae"
                            organism_details = {
                                "full_name": "Saccharomyces cerevisiae",
                                "type": "yeast",
                                "domains": ["eukaryotic", "fungi"]
                            }
                        elif lib_id.startswith("Bth"):
                            organism = "B. subtilis"
                            organism_details = {
                                "full_name": "Bacillus subtilis",
                                "type": "bacteria",
                                "gram_stain": "positive",
                                "domains": ["prokaryotic"]
                            }
                        
                        # Create a more detailed input/output structure
                        io_information = {
                            "inputs": inputs,
                            "outputs": outputs,
                            "input_details": input_details,
                            "output_details": output_details
                        }
                        
                        # Analyze regulated promoters
                        regulated_promoters = {}
                        for promoter in promoters:
                            promoter_id = promoter.get("id", "")
                            # Try to match with a regulator by checking if the promoter name matches the pattern "p<RegulatorName>"
                            if promoter_id.startswith("p"):
                                potential_regulator = promoter_id[1:]  # Remove the 'p' prefix
                                # Check if this regulator exists in the list of repressors
                                if any(r.get("id") == potential_regulator for r in repressors):
                                    regulated_promoters[promoter_id] = potential_regulator
                        
                        # Create metadata
                        lib_metadata = {
                            "library_id": lib_id,
                            "organism": organism,
                            "organism_details": organism_details,
                            "ucf_path": ucf_path,
                            "input_path": input_path,
                            "output_path": output_path,
                            
                            # Counts
                            "parts_count": len(parts),
                            "gates_count": len(gates),
                            "promoters_count": len(promoters),
                            "terminators_count": len(terminators),
                            "reporters_count": len(reporters),
                            "repressors_count": len(repressors),
                            "rbs_count": len(rbs_parts),
                            "ribozymes_count": len(ribozymes),
                            "scars_count": len(scars),
                            
                            # Lists of components
                            "gate_types": list(gate_types),
                            "gates": gate_details,
                            "parts": detailed_parts,  # All parts with details
                            "reporter_types": [r.get("id") for r in reporters],
                            "all_promoters": [p.get("id") for p in promoters],
                            "all_terminators": [t.get("id") for t in terminators],
                            "all_repressors": [r.get("id") for r in repressors],
                            "all_rbs": [r.get("id") for r in rbs_parts],
                            "all_reporters": [r.get("id") for r in reporters],
                            "all_ribozymes": [r.get("id") for r in ribozymes],
                            "all_scars": [s.get("id") for s in scars],
                            
                            # Regulatory relationships
                            "regulated_promoters": regulated_promoters,
                            
                            # Input/Output information
                            "io_info": io_information,
                            
                            # UCF collection statistics
                            "ucf_collections": {
                                collection: len(ucf_data.get(collection, [])) 
                                for collection in ucf_data.keys() 
                                if isinstance(ucf_data.get(collection), list)
                            },
                            
                            # Add sample parts for context (still keeping these for backward compatibility)
                            "sample_promoters": [p.get("id") for p in promoters[:5]],
                            "sample_reporters": [r.get("id") for r in reporters[:5]]
                        }
                        
                        metadata[lib_id] = lib_metadata
                        # Cache metadata
                        self.metadata_cache[lib_id] = lib_metadata
                        
                    except Exception as e:
                        logger.error(f"Error parsing UCF file {ucf_path}: {e}")
                        metadata[lib_id] = {
                            "library_id": lib_id,
                            "error": f"Error parsing metadata: {str(e)}"
                        }
                else:
                    metadata[lib_id] = {
                        "library_id": lib_id,
                        "ucf_path": ucf_path,
                        "input_path": input_path,
                        "output_path": output_path,
                        "error": "UCF file not found"
                    }
            else:
                metadata[lib_id] = {
                    "library_id": lib_id,
                    "error": "Could not load library"
                }
        
        return metadata
    
    def _construct_library_selection_prompt(self, user_request: str, libraries_metadata: Dict[str, Dict[str, Any]]) -> str:
        """
        Construct a prompt for the LLM to select a library.
        
        Args:
            user_request: The user's request
            libraries_metadata: Metadata for all available libraries
            
        Returns:
            Formatted prompt for the LLM
        """
        prompt = f"""
You are a genetic circuit design assistant. Your task is to select the most appropriate library for a user's request.

USER REQUEST:
{user_request}

AVAILABLE LIBRARIES:
"""
        
        # Add library metadata to prompt
        for lib_id, metadata in libraries_metadata.items():
            prompt += f"\n{'='*50}\n"
            prompt += f"LIBRARY: {lib_id}\n"
            prompt += f"{'='*50}\n"
            
            if "error" in metadata:
                prompt += f"Error: {metadata['error']}\n"
                continue  # Skip to next library if there's an error
            
            # Basic organism information
            prompt += f"Organism: {metadata.get('organism', 'Unknown')}"
            organism_details = metadata.get('organism_details', {})
            if organism_details:
                prompt += f" ({organism_details.get('full_name', '')})\n"
                prompt += f"  Type: {organism_details.get('type', 'Unknown')}\n"
                if 'gram_stain' in organism_details:
                    prompt += f"  Gram Stain: {organism_details.get('gram_stain', '')}\n"
                if 'domains' in organism_details:
                    prompt += f"  Domains: {', '.join(organism_details.get('domains', []))}\n"
            else:
                prompt += "\n"
            
            # Component summary
            prompt += "\nCOMPONENT SUMMARY:\n"
            prompt += f"  Total Parts: {metadata.get('parts_count', 0)}\n"
            prompt += f"  Gates: {metadata.get('gates_count', 0)}\n"
            prompt += f"  Promoters: {metadata.get('promoters_count', 0)}\n"
            prompt += f"  Terminators: {metadata.get('terminators_count', 0)}\n"
            prompt += f"  Repressors: {metadata.get('repressors_count', 0)}\n"
            prompt += f"  RBS: {metadata.get('rbs_count', 0)}\n"
            prompt += f"  Reporters: {metadata.get('reporters_count', 0)}\n"
            prompt += f"  Ribozymes: {metadata.get('ribozymes_count', 0)}\n"
            prompt += f"  Scars: {metadata.get('scars_count', 0)}\n"
            
            # Gate information
            gate_types = metadata.get('gate_types', [])
            if gate_types:
                prompt += "\nGATE TYPES:\n"
                for gate_type in gate_types:
                    prompt += f"  - {gate_type}\n"
            
            # Reporter information
            reporter_types = metadata.get('reporter_types', [])
            if reporter_types:
                prompt += "\nREPORTER TYPES:\n"
                for reporter in reporter_types:
                    prompt += f"  - {reporter}\n"
            
            # Regulatory relationships
            regulated_promoters = metadata.get('regulated_promoters', {})
            if regulated_promoters:
                prompt += "\nREGULATORY RELATIONSHIPS:\n"
                for promoter, regulator in regulated_promoters.items():
                    prompt += f"  - {promoter} is regulated by {regulator}\n"
            
            # Gates with details
            gates = metadata.get('gates', [])
            if gates:
                prompt += "\nGATES (Details):\n"
                # Group gates by type
                gates_by_type = {}
                for gate in gates:
                    gate_type = gate.get('type', 'unknown')
                    if gate_type not in gates_by_type:
                        gates_by_type[gate_type] = []
                    gates_by_type[gate_type].append(gate)
                
                # List gates by type
                for gate_type, gate_list in gates_by_type.items():
                    prompt += f"  {gate_type.upper()} Gates:\n"
                    for gate in gate_list[:5]:  # Limit to first 5 of each type
                        prompt += f"    - {gate.get('id', '')} (System: {gate.get('system', 'Unknown')})\n"
                    if len(gate_list) > 5:
                        prompt += f"      ... and {len(gate_list) - 5} more {gate_type} gates\n"
            
            # All promoters
            all_promoters = metadata.get('all_promoters', [])
            if all_promoters:
                prompt += "\nPROMOTERS:\n"
                for promoter in all_promoters[:10]:  # Limit to first 10
                    prompt += f"  - {promoter}\n"
                if len(all_promoters) > 10:
                    prompt += f"  ... and {len(all_promoters) - 10} more promoters\n"
            
            # All reporters
            all_reporters = metadata.get('all_reporters', [])
            if all_reporters:
                prompt += "\nREPORTERS:\n"
                for reporter in all_reporters:
                    prompt += f"  - {reporter}\n"
            
            # All repressors
            all_repressors = metadata.get('all_repressors', [])
            if all_repressors:
                prompt += "\nREPRESSORS:\n"
                for repressor in all_repressors[:10]:  # Limit to first 10
                    prompt += f"  - {repressor}\n"
                if len(all_repressors) > 10:
                    prompt += f"  ... and {len(all_repressors) - 10} more repressors\n"
            
            # Add terminators
            all_terminators = metadata.get('all_terminators', [])
            if all_terminators:
                prompt += "\nTERMINATORS:\n"
                for terminator in all_terminators[:10]:  # Limit to first 10
                    prompt += f"  - {terminator}\n"
                if len(all_terminators) > 10:
                    prompt += f"  ... and {len(all_terminators) - 10} more terminators\n"
            
            # Input/Output information
            io_info = metadata.get('io_info', {})
            inputs = io_info.get('inputs', [])
            if inputs:
                prompt += "\nSUPPORTED INPUTS:\n"
                for input_item in inputs:
                    if isinstance(input_item, dict) and 'name' in input_item:
                        input_name = input_item.get('name', '')
                        input_type = input_item.get('type', '')
                        prompt += f"  - {input_name} (Type: {input_type})\n"
                    else:
                        prompt += f"  - {input_item}\n"
            
            outputs = io_info.get('outputs', [])
            if outputs:
                prompt += "\nSUPPORTED OUTPUTS:\n"
                for output_item in outputs:
                    if isinstance(output_item, dict) and 'name' in output_item:
                        output_name = output_item.get('name', '')
                        output_type = output_item.get('type', '')
                        prompt += f"  - {output_name} (Type: {output_type})\n"
                    else:
                        prompt += f"  - {output_item}\n"
        
        prompt += f"\n{'='*80}\n"
        prompt += """
INSTRUCTIONS:
1. Analyze the user's request carefully to understand what they want to design (type of circuit, organism, inputs, outputs, etc.)
2. Evaluate each available library based on its compatibility with the user's request
3. Select the most appropriate library that best meets the user's needs
4. If no library fully satisfies the request, select the closest match and explain any limitations
5. If multiple libraries could work, recommend the best one with alternatives

Your response must follow this JSON format:
{
  "selected_library_id": "ID of the selected library or null if none is appropriate",
  "reasoning": "Detailed explanation of why this library was selected",
  "alternatives": [
    {
      "library_id": "ID of an alternative library",
      "reasoning": "Why this library is an alternative option"
    }
  ],
  "limitations": "Any limitations of the selected library for this specific request",
  "recommendations": "Additional recommendations for the user"
}
"""
        
        return prompt
    
    def _call_openai_api(self, prompt: str) -> str:
        """
        Call the OpenAI API with a prompt.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            The response from the API
        """
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a genetic circuit design assistant specializing in synthetic biology library selection."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for more consistent results
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise
    
    def _parse_library_selection_response(self, response: str, available_libraries: List[str]) -> Dict[str, Any]:
        """
        Parse the response from the LLM to extract the selected library.
        
        Args:
            response: The response from the LLM
            available_libraries: List of available library IDs
            
        Returns:
            Dict containing the selection result
        """
        try:
            # Try to extract JSON from the response
            response_text = response.strip()
            
            # Find JSON block if not the entire response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}')
            
            if json_start >= 0 and json_end >= 0:
                json_text = response_text[json_start:json_end+1]
                selection_data = json.loads(json_text)
            else:
                # If no JSON block found, try to parse the entire response
                selection_data = json.loads(response_text)
            
            # Extract information
            selected_library_id = selection_data.get("selected_library_id")
            reasoning = selection_data.get("reasoning", "")
            alternatives = selection_data.get("alternatives", [])
            limitations = selection_data.get("limitations", "")
            recommendations = selection_data.get("recommendations", "")
            
            # Validate selected library
            if selected_library_id and selected_library_id not in available_libraries:
                logger.warning(f"LLM selected library {selected_library_id} which is not in available libraries: {available_libraries}")
                selected_library_id = None
                reasoning += "\n\nNote: The originally selected library was not available. Please check available libraries."
            
            # Construct result
            result = {
                "success": selected_library_id is not None,
                "library_id": selected_library_id,
                "reasoning": reasoning,
                "alternatives": alternatives,
                "limitations": limitations,
                "recommendations": recommendations
            }
            
            # Add a user-friendly message
            if selected_library_id:
                result["message"] = f"Selected library {selected_library_id}. "
                if limitations:
                    result["message"] += f"Limitations: {limitations}. "
                if recommendations:
                    result["message"] += f"Recommendations: {recommendations}."
            else:
                result["message"] = "Could not find a suitable library for your request. "
                if recommendations:
                    result["message"] += f"Recommendations: {recommendations}."
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response as JSON: {e}\nResponse: {response}")
            
            # Try to extract library ID using regex
            import re
            library_pattern = r"library[:\s]*([\w\d]+)"
            library_match = re.search(library_pattern, response, re.IGNORECASE)
            
            if library_match:
                potential_library = library_match.group(1)
                if potential_library in available_libraries:
                    return {
                        "success": True,
                        "library_id": potential_library,
                        "message": f"Selected library {potential_library} (extracted from non-JSON response).",
                        "reasoning": response
                    }
            
            return {
                "success": False,
                "message": "Could not parse LLM response.",
                "raw_response": response
            }
        
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}\nResponse: {response}")
            return {
                "success": False,
                "message": f"Error processing LLM response: {str(e)}",
                "raw_response": response
            }
    
    def get_library_metadata(self, library_id: str) -> Dict[str, Any]:
        """
        Get detailed metadata for a specific library.
        
        Args:
            library_id: ID of the library to get metadata for
            
        Returns:
            Dict containing metadata about the library
        """
        # Check cache first
        if library_id in self.metadata_cache:
            return self.metadata_cache[library_id]
        
        # Get metadata for this library
        metadata = self._get_all_libraries_metadata([library_id])
        
        # Return metadata for the requested library
        return metadata.get(library_id, {"error": f"Library {library_id} not found"}) 