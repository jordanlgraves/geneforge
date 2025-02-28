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
                        
                        # Categorize parts
                        promoters = [p for p in parts if p.get("raw_data", {}).get("type") == "promoter"]
                        terminators = [p for p in parts if p.get("raw_data", {}).get("type") == "terminator"]
                        reporters = [p for p in parts if any(r in p.get("id", "").lower() for r in ["gfp", "rfp", "yfp", "cfp"])]
                        
                        # Gate types
                        gate_types = set()
                        for gate in gates:
                            gate_type = gate.get("gate_type", "").lower()
                            if gate_type:
                                gate_types.add(gate_type)
                        
                        # Extract organism from library ID
                        organism = "Unknown"
                        if lib_id.startswith("Eco"):
                            organism = "E. coli"
                        elif lib_id.startswith("SC"):
                            organism = "S. cerevisiae (yeast)"
                        elif lib_id.startswith("Bth"):
                            organism = "B. subtilis"
                        
                        # Create metadata
                        lib_metadata = {
                            "library_id": lib_id,
                            "organism": organism,
                            "ucf_path": ucf_path,
                            "input_path": input_path,
                            "output_path": output_path,
                            "parts_count": len(parts),
                            "gates_count": len(gates),
                            "promoters_count": len(promoters),
                            "terminators_count": len(terminators),
                            "reporters_count": len(reporters),
                            "reporter_types": [r.get("id") for r in reporters],
                            "gate_types": list(gate_types),
                            # Add sample parts for context
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
            prompt += f"\n--- LIBRARY: {lib_id} ---\n"
            
            if "error" in metadata:
                prompt += f"Error: {metadata['error']}\n"
                continue
            
            # Basic information
            prompt += f"Organism: {metadata.get('organism', 'Unknown')}\n"
            prompt += f"Parts: {metadata.get('parts_count', 0)}\n"
            prompt += f"Gates: {metadata.get('gates_count', 0)}\n"
            
            # Gate types
            gate_types = metadata.get('gate_types', [])
            if gate_types:
                prompt += f"Gate Types: {', '.join(gate_types)}\n"
            
            # Reporter information
            reporter_types = metadata.get('reporter_types', [])
            if reporter_types:
                prompt += f"Reporter Types: {', '.join(reporter_types)}\n"
            
            # Sample promoters
            sample_promoters = metadata.get('sample_promoters', [])
            if sample_promoters:
                prompt += f"Sample Promoters: {', '.join(sample_promoters)}\n"
        
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