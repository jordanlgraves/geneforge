import os
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from src.library.library_manager import LibraryManager

logger = logging.getLogger("llm_file_selector")

class LLMFileSelector:
    """
    A class that helps LLMs select appropriate UCF, input, and output files based on user requests.
    This class provides metadata about available files and processes LLM selections.
    """
    
    def __init__(self, library_manager: Optional[LibraryManager] = None):
        """
        Initialize the file selector with a library manager.
        
        Args:
            library_manager: Library manager instance. If None, a new one will be created.
        """
        self.library_manager = library_manager or LibraryManager()
        
        # Base paths for UCF, input, and output files
        self.ucf_base_path = "ext_repos/Cello-UCF/files/v2/ucf"
        self.input_base_path = "ext_repos/Cello-UCF/files/v2/input"
        self.output_base_path = "ext_repos/Cello-UCF/files/v2/output"
        
        # Organism prefixes for easier selection
        self.organism_prefixes = {
            "ecoli": "Eco",
            "e_coli": "Eco",
            "e.coli": "Eco",
            "eco": "Eco",
            "sc": "SC",
            "yeast": "SC",
            "s.cerevisiae": "SC",
            "bth": "Bth",
            "b.subtilis": "Bth",
            "bacillus": "Bth"
        }
    
    def get_available_files(self) -> Dict[str, Any]:
        """
        Get metadata about all available UCF, input, and output files.
        
        Returns:
            Dict containing metadata about all available files
        """
        # Get all available UCF files
        ucf_files = self._scan_files(self.ucf_base_path)
        
        # Get all available input files
        input_files = self._scan_files(self.input_base_path)
        
        # Get all available output files
        output_files = self._scan_files(self.output_base_path)
        
        # Organize files by organism
        files_by_organism = {}
        
        # Process UCF files
        for file_info in ucf_files:
            organism = self._extract_organism_from_filename(file_info["filename"])
            if organism not in files_by_organism:
                files_by_organism[organism] = {"ucf": [], "input": [], "output": []}
            files_by_organism[organism]["ucf"].append(file_info)
        
        # Process input files
        for file_info in input_files:
            organism = self._extract_organism_from_filename(file_info["filename"])
            if organism not in files_by_organism:
                files_by_organism[organism] = {"ucf": [], "input": [], "output": []}
            files_by_organism[organism]["input"].append(file_info)
        
        # Process output files
        for file_info in output_files:
            organism = self._extract_organism_from_filename(file_info["filename"])
            if organism not in files_by_organism:
                files_by_organism[organism] = {"ucf": [], "input": [], "output": []}
            files_by_organism[organism]["output"].append(file_info)
        
        return {
            "files_by_organism": files_by_organism,
            "ucf_files": ucf_files,
            "input_files": input_files,
            "output_files": output_files
        }
    
    def _scan_files(self, base_path: str) -> List[Dict[str, Any]]:
        """
        Scan a directory for JSON files and extract metadata.
        
        Args:
            base_path: Base path to scan
            
        Returns:
            List of file metadata dictionaries
        """
        files = []
        
        # Check if the base path exists
        if not os.path.exists(base_path):
            logger.warning(f"Base path does not exist: {base_path}")
            return files
        
        # Scan for organism directories
        for organism_dir in os.listdir(base_path):
            organism_path = os.path.join(base_path, organism_dir)
            if not os.path.isdir(organism_path):
                continue
            
            # Scan for JSON files in the organism directory
            for filename in os.listdir(organism_path):
                if not filename.endswith(".json"):
                    continue
                
                file_path = os.path.join(organism_path, filename)
                file_info = self._extract_file_metadata(file_path, filename, organism_dir)
                files.append(file_info)
        
        return files
    
    def _extract_file_metadata(self, file_path: str, filename: str, organism_dir: str) -> Dict[str, Any]:
        """
        Extract metadata from a file.
        
        Args:
            file_path: Path to the file
            filename: Name of the file
            organism_dir: Name of the organism directory
            
        Returns:
            Dict containing file metadata
        """
        # Basic metadata
        metadata = {
            "filename": filename,
            "path": file_path,
            "organism_dir": organism_dir,
            "size": os.path.getsize(file_path),
            "file_type": self._determine_file_type(filename)
        }
        
        # Extract version information from the filename
        version_match = re.search(r'([A-Za-z]{2,3}\d+[A-Za-z]\d+[A-Za-z]\d+[A-Za-z]\d+)', filename)
        if version_match:
            metadata["version"] = version_match.group(1)
        
        # Extract additional metadata from the file content
        try:
            with open(file_path, 'r') as f:
                # Read just the first 10KB to extract header information
                content = f.read(10240)
                
                # Look for specific metadata in the content
                metadata.update(self._extract_content_metadata(content, metadata["file_type"]))
        except Exception as e:
            logger.warning(f"Error extracting metadata from {file_path}: {e}")
        
        return metadata
    
    def _determine_file_type(self, filename: str) -> str:
        """
        Determine the type of file based on its filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            File type (ucf, input, or output)
        """
        if "UCF" in filename:
            return "ucf"
        elif "input" in filename:
            return "input"
        elif "output" in filename:
            return "output"
        else:
            return "unknown"
    
    def _extract_content_metadata(self, content: str, file_type: str) -> Dict[str, Any]:
        """
        Extract metadata from file content.
        
        Args:
            content: File content
            file_type: Type of file
            
        Returns:
            Dict containing extracted metadata
        """
        metadata = {}
        
        # Look for specific metadata based on file type
        if file_type == "ucf":
            # Look for organism information
            organism_match = re.search(r'"organism":\s*"([^"]+)"', content)
            if organism_match:
                metadata["organism"] = organism_match.group(1)
            
            # Look for available gates
            gates_match = re.search(r'"available_gates":\s*\[(.*?)\]', content, re.DOTALL)
            if gates_match:
                gates_content = gates_match.group(1)
                gate_names = re.findall(r'"name":\s*"([^"]+)"', gates_content)
                metadata["available_gates"] = gate_names
            
            # Look for version information
            version_match = re.search(r'"version":\s*"([^"]+)"', content)
            if version_match:
                metadata["version"] = version_match.group(1)
        
        elif file_type == "input":
            # Look for input sensors
            sensors = re.findall(r'"name":\s*"([^"]+_sensor)"', content)
            if sensors:
                metadata["input_sensors"] = sensors
        
        elif file_type == "output":
            # Look for output devices
            devices = re.findall(r'"name":\s*"([^"]+_reporter)"', content)
            if devices:
                metadata["output_devices"] = devices
        
        return metadata
    
    def _extract_organism_from_filename(self, filename: str) -> str:
        """
        Extract the organism prefix from a filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            Organism prefix (e.g., "Eco", "SC", "Bth")
        """
        # Look for common organism prefixes
        for prefix in ["Eco", "SC", "Bth"]:
            if filename.startswith(prefix):
                return prefix
        
        return "Unknown"
    
    def select_files_with_llm(self, user_request: str, llm_reasoning: str) -> Dict[str, Any]:
        """
        Select appropriate UCF, input, and output files based on LLM reasoning.
        
        Args:
            user_request: The user's request
            llm_reasoning: The LLM's reasoning for selecting files
            
        Returns:
            Dict containing selected files and metadata
        """
        # Extract file selections from LLM reasoning
        selections = self._extract_file_selections(llm_reasoning)
        
        # Validate the selections
        validated_selections = self._validate_file_selections(selections)
        
        # If validation failed, try to find alternative files
        if not validated_selections["valid"]:
            alternative_selections = self._find_alternative_files(user_request, selections)
            if alternative_selections["valid"]:
                validated_selections = alternative_selections
        
        # Return the results
        return {
            "success": validated_selections["valid"],
            "message": validated_selections["message"],
            "selections": validated_selections["selections"],
            "llm_reasoning": llm_reasoning
        }
    
    def _extract_file_selections(self, llm_reasoning: str) -> Dict[str, str]:
        """
        Extract file selections from LLM reasoning.
        
        Args:
            llm_reasoning: The LLM's reasoning for selecting files
            
        Returns:
            Dict containing selected files
        """
        selections = {
            "ucf_file": None,
            "input_file": None,
            "output_file": None,
            "organism": None
        }
        
        # Extract UCF file selection
        ucf_match = re.search(r'UCF_FILE:\s*([A-Za-z0-9._]+)', llm_reasoning)
        if ucf_match:
            selections["ucf_file"] = ucf_match.group(1)
        
        # Extract input file selection
        input_match = re.search(r'INPUT_FILE:\s*([A-Za-z0-9._]+)', llm_reasoning)
        if input_match:
            selections["input_file"] = input_match.group(1)
        
        # Extract output file selection
        output_match = re.search(r'OUTPUT_FILE:\s*([A-Za-z0-9._]+)', llm_reasoning)
        if output_match:
            selections["output_file"] = output_match.group(1)
        
        # Extract organism selection
        organism_match = re.search(r'ORGANISM:\s*([A-Za-z0-9._]+)', llm_reasoning)
        if organism_match:
            selections["organism"] = organism_match.group(1)
        
        # If we couldn't extract specific files, try to extract a version
        if not selections["ucf_file"] and not selections["input_file"] and not selections["output_file"]:
            version_match = re.search(r'VERSION:\s*([A-Za-z0-9]+)', llm_reasoning)
            if version_match:
                version = version_match.group(1)
                selections["ucf_file"] = f"{version}.UCF.json"
                selections["input_file"] = f"{version}.input.json"
                selections["output_file"] = f"{version}.output.json"
        
        # If we still don't have files but have an organism, try to find files for that organism
        if (not selections["ucf_file"] or not selections["input_file"] or not selections["output_file"]) and selections["organism"]:
            organism = selections["organism"]
            # Normalize organism name
            normalized_organism = organism.lower().strip()
            if normalized_organism in self.organism_prefixes:
                prefix = self.organism_prefixes[normalized_organism]
                
                # Look for files with this prefix
                available_files = self.get_available_files()
                for file_info in available_files["ucf_files"]:
                    if file_info["filename"].startswith(prefix) and not selections["ucf_file"]:
                        selections["ucf_file"] = file_info["filename"]
                        # If we find a UCF file, look for matching input and output files
                        version = self._extract_version_from_filename(file_info["filename"])
                        if version:
                            selections["input_file"] = f"{version}.input.json"
                            selections["output_file"] = f"{version}.output.json"
                        break
        
        return selections
    
    def _extract_version_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract the version from a filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            Version string or None if not found
        """
        version_match = re.search(r'([A-Za-z]{2,3}\d+[A-Za-z]\d+[A-Za-z]\d+[A-Za-z]\d+)', filename)
        if version_match:
            return version_match.group(1)
        return None
    
    def _validate_file_selections(self, selections: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate file selections to ensure they exist and are compatible.
        
        Args:
            selections: Dict containing selected files
            
        Returns:
            Dict containing validation results
        """
        result = {
            "valid": False,
            "message": "",
            "selections": selections
        }
        
        # Check if we have all required selections
        if not selections["ucf_file"] or not selections["input_file"] or not selections["output_file"]:
            result["message"] = "Missing one or more required file selections"
            return result
        
        # Check if the UCF file exists
        ucf_path = None
        for organism_dir in os.listdir(self.ucf_base_path):
            potential_path = os.path.join(self.ucf_base_path, organism_dir, selections["ucf_file"])
            if os.path.exists(potential_path):
                ucf_path = potential_path
                break
        
        if not ucf_path:
            result["message"] = f"UCF file not found: {selections['ucf_file']}"
            return result
        
        # Check if the input file exists
        input_path = None
        for organism_dir in os.listdir(self.input_base_path):
            potential_path = os.path.join(self.input_base_path, organism_dir, selections["input_file"])
            if os.path.exists(potential_path):
                input_path = potential_path
                break
        
        if not input_path:
            result["message"] = f"Input file not found: {selections['input_file']}"
            return result
        
        # Check if the output file exists
        output_path = None
        for organism_dir in os.listdir(self.output_base_path):
            potential_path = os.path.join(self.output_base_path, organism_dir, selections["output_file"])
            if os.path.exists(potential_path):
                output_path = potential_path
                break
        
        if not output_path:
            result["message"] = f"Output file not found: {selections['output_file']}"
            return result
        
        # Check if the files are compatible (same version)
        ucf_version = self._extract_version_from_filename(selections["ucf_file"])
        input_version = self._extract_version_from_filename(selections["input_file"])
        output_version = self._extract_version_from_filename(selections["output_file"])
        
        if ucf_version != input_version or ucf_version != output_version:
            result["message"] = f"Incompatible file versions: UCF={ucf_version}, input={input_version}, output={output_version}"
            return result
        
        # All checks passed
        result["valid"] = True
        result["message"] = "File selections are valid"
        result["selections"]["ucf_path"] = ucf_path
        result["selections"]["input_path"] = input_path
        result["selections"]["output_path"] = output_path
        result["selections"]["version"] = ucf_version
        
        return result
    
    def _find_alternative_files(self, user_request: str, selections: Dict[str, str]) -> Dict[str, Any]:
        """
        Find alternative files if the selected files are not valid.
        
        Args:
            user_request: The user's request
            selections: Dict containing selected files
            
        Returns:
            Dict containing alternative file selections
        """
        result = {
            "valid": False,
            "message": "",
            "selections": selections.copy()
        }
        
        # Extract organism from user request or selections
        organism = selections["organism"]
        if not organism:
            # Try to extract organism from user request
            for org_name, prefix in self.organism_prefixes.items():
                if org_name in user_request.lower():
                    organism = org_name
                    break
        
        if not organism:
            result["message"] = "Could not determine organism from request or selections"
            return result
        
        # Normalize organism name
        normalized_organism = organism.lower().strip()
        if normalized_organism not in self.organism_prefixes:
            result["message"] = f"Unsupported organism: {organism}"
            return result
        
        prefix = self.organism_prefixes[normalized_organism]
        
        # Find UCF files for this organism
        available_files = self.get_available_files()
        ucf_files = [f for f in available_files["ucf_files"] if f["filename"].startswith(prefix)]
        
        if not ucf_files:
            result["message"] = f"No UCF files found for organism: {organism}"
            return result
        
        # Select the first UCF file
        ucf_file = ucf_files[0]["filename"]
        result["selections"]["ucf_file"] = ucf_file
        
        # Extract version from UCF file
        version = self._extract_version_from_filename(ucf_file)
        if not version:
            result["message"] = f"Could not extract version from UCF file: {ucf_file}"
            return result
        
        # Find matching input and output files
        input_file = f"{version}.input.json"
        output_file = f"{version}.output.json"
        
        # Validate that these files exist
        input_path = None
        for organism_dir in os.listdir(self.input_base_path):
            potential_path = os.path.join(self.input_base_path, organism_dir, input_file)
            if os.path.exists(potential_path):
                input_path = potential_path
                break
        
        if not input_path:
            result["message"] = f"Input file not found: {input_file}"
            return result
        
        output_path = None
        for organism_dir in os.listdir(self.output_base_path):
            potential_path = os.path.join(self.output_base_path, organism_dir, output_file)
            if os.path.exists(potential_path):
                output_path = potential_path
                break
        
        if not output_path:
            result["message"] = f"Output file not found: {output_file}"
            return result
        
        # All checks passed
        result["valid"] = True
        result["message"] = f"Found alternative files for organism: {organism}"
        result["selections"]["input_file"] = input_file
        result["selections"]["output_file"] = output_file
        result["selections"]["ucf_path"] = os.path.join(self.ucf_base_path, prefix, ucf_file)
        result["selections"]["input_path"] = input_path
        result["selections"]["output_path"] = output_path
        result["selections"]["version"] = version
        result["selections"]["organism"] = organism
        
        return result 