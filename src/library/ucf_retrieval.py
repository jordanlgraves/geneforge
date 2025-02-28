import json
import os
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ucf_retrieval")

def load_ecoli_library(json_path):
    """
    Loads a JSON file produced by parse_ecoli_ucf (the 'final_output' structure).
    Returns the 'structured_data' portion containing:
      {
        "metadata": {...},
        "parts": [...],
        "gates": [...],
        "interactions": [...],
        "experimental_data": [...],
        "misc": [...],
        "unrecognized": { "items": [...], "fields": [...] }
      }
    """
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"Could not find library file: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if "structured_data" not in data:
        # This might be a raw UCF file, so let's try to parse it
        try:
            from src.library.parse_ucf import parse_ecoli_ucf
            parsed_data = parse_ecoli_ucf(json_path)
            return parsed_data["structured_data"]
        except Exception as e:
            logger.error(f"Failed to parse JSON file as UCF: {e}")
            raise ValueError("JSON file does not contain 'structured_data' at top-level and could not be parsed as a UCF file.")

    # Return the structured_data portion
    return data["structured_data"]


# ----------------------- Basic Retrieval Functions -----------------------


def get_all_gates(library_data):
    """
    Return the list from library_data["gates"].
    Each gate might be:
      {
        "id": <string>,
        "gate_type": <string>,  # e.g. 'NOR', 'AND'
        "raw_data": <original item>
      }
    or, if parse didn't set gate_type, it might just have 'raw_data'.
    """
    return library_data.get("gates", [])


def get_gate_by_id(library_data, gate_id):
    """
    Returns the first gate whose "id" matches gate_id, or None if not found.
    """
    for g in get_all_gates(library_data):
        if g["id"].lower() == gate_id.lower():
            return g
    return None

def get_gates_by_type(library_data, gate_type):
    """
    Returns all gates whose 'gate_type' matches gate_type (case-insensitive).
    If some gates in the library don't have 'gate_type' set, they'll be skipped.
    """
    gate_type_lower = gate_type.lower()
    results = []
    for g in get_all_gates(library_data):
        gt = g.get("gate_type", "").lower()
        if gt == gate_type_lower:
            results.append(g)
    return results


def get_all_parts(library_data):
    """
    Return the list from library_data["parts"].
    Each part is typically:
      {
        "id": <string>,
        "type": "dna_part",
        "sequence": <string>,
        "raw_data": <original item>
      }
    """
    return library_data.get("parts", [])


def get_part_by_id(library_data, part_id):
    """
    Return the first part whose 'id' matches part_id, or None if not found.
    """
    for p in get_all_parts(library_data):
        if p["id"] == part_id:
            return p
    return None


def get_parts_by_type(library_data, part_type):
    """
    Return all parts whose 'type' matches part_type (exact match).
    For example 'dna_part', or if you introduced 'plasmid', etc.
    """
    results = []
    for p in get_all_parts(library_data):
        if p.get("type") == part_type:
            results.append(p)
    return results


def list_dna_parts_by_keyword(library_data, keyword):
    """
    Return all parts that contain 'keyword' in their 'id'.
    Example usage: list_dna_parts_by_keyword(library_data, "RBS") 
    or "pTet", etc.
    """
    matches = []
    for p in get_all_parts(library_data):
        if keyword.lower() in p["id"].lower():
            matches.append(p)
    return matches

def get_dna_part_by_name(library_data, name):
    """
    Return a single part whose 'id' or raw_data name matches.
    """
    for part in get_all_parts(library_data):
        # match 'id' exactly or with .lower()
        if part["id"].lower() == name.lower():
            return part
        # or check if 'raw_data' has a .get("name") that matches
        raw_name = part["raw_data"].get("name","").lower()
        if raw_name == name.lower():
            return part
    return None


# Example filtering for promoter or repressor:
def list_promoters(library_data):
    """
    Return parts that appear to be promoters.
    If your parse_ecoli_ucf doesn't set 'type'='promoter', you might
    rely on raw_data. Adjust as needed.
    """
    results = []
    for p in get_all_parts(library_data):
        if "promoter" in p["id"].lower():
            results.append(p)
        elif p['raw_data'].get('type','').lower() == 'promoter':
            results.append(p)
    return results

def list_terminators(library_data):
    """
    Return parts that appear to be terminators.
    If parse sets part["type"]='terminator', use that. Otherwise look for name patterns.
    """
    results = []
    for p in get_all_parts(library_data):
        # naive check: if "terminator" in id or raw_data
        # e.g. if p["raw_data"].get("some_field") says 'terminator'
        if "terminator" in p["id"].lower():
            results.append(p)
        elif p['raw_data'].get('type','').lower() == 'terminator':
            results.append(p)
    return results

def list_repressors(library_data):
    """
    Return a list of repressors from the library.
    """
    return choose_repressor(library_data)

def choose_repressor(library_data, family=None):
    """
    Return a list of repressors from the library that match an optional 'family'.
    Common repressor families in E. coli libraries include: SrpR, BetI, PhlF, AmtR
    """
    candidates = []
    for p in get_all_parts(library_data):
        # Check common repressor families
        if any(x in p["id"].lower() for x in ["srpr", "beti", "phlf", "amtr"]):
            candidates.append(p)
        elif p['raw_data'].get('type','').lower() == 'repressor':
            candidates.append(p)

    if family:
        # filter further
        family_lower = family.lower()
        candidates = [c for c in candidates if family_lower in c["id"].lower()]

    return candidates

# New functions for RBS and CDS identification
def list_rbs(library_data):
    """Return parts that appear to be ribosome binding sites (RBS)"""
    results = []
    for p in get_all_parts(library_data):
        if "rbs" in p["id"].lower():
            results.append(p)
        elif p['raw_data'].get('type','').lower() == 'rbs':
            results.append(p)
    return results

def list_cds(library_data):
    """Return parts that appear to be coding sequences (CDS)"""
    results = []
    for p in get_all_parts(library_data):
        if any(x in p["id"].lower() for x in ["cds", "coding", "protein"]):
            results.append(p)
        elif p['raw_data'].get('type','').lower() == 'cds':
            results.append(p)
    return results

def list_reporters(library_data):
    """Return parts that appear to be reporters (GFP, RFP, etc.)"""
    results = []
    for p in get_all_parts(library_data):
        if any(x in p["id"].lower() for x in ["gfp", "rfp", "yfp", "cfp", "reporter"]):
            results.append(p)
        elif p['raw_data'].get('type','').lower() == 'reporter':
            results.append(p)
    return results

def list_inducers(library_data):
    """
    Extract information about inducers from the library.
    Looks at promoter names and metadata for inducers like IPTG, arabinose, etc.
    """
    results = []
    promoters = list_promoters(library_data)
    
    # Common inducers and their associated promoters
    inducer_map = {
        "iptg": ["plac", "ptrc", "ptac", "p_tet", "p_trc"],
        "arabinose": ["para", "pbad"],
        "atc": ["ptet", "p_tet"],
        "rhamnose": ["prha", "prhab"],
        "ahl": ["plux", "luxr"],
    }
    
    found_inducers = set()
    
    # Check promoters for inducer hints
    for promoter in promoters:
        promoter_id = promoter["id"].lower()
        
        for inducer, patterns in inducer_map.items():
            if any(pattern in promoter_id for pattern in patterns):
                inducer_info = {
                    "inducer": inducer,
                    "associated_promoter": promoter["id"],
                    "raw_data": promoter.get("raw_data", {})
                }
                results.append(inducer_info)
                found_inducers.add(inducer)
    
    # Also check metadata if available
    if "inducers" in library_data.get("metadata", {}):
        for inducer in library_data["metadata"]["inducers"]:
            if inducer.lower() not in found_inducers:
                results.append({
                    "inducer": inducer.lower(),
                    "associated_promoter": "unknown",
                    "raw_data": {"note": "From metadata"}
                })
    
    return results

# ----------------------- Experimental Data & Misc -----------------------

def get_experimental_data_for_gate(library_data, gate_id):
    """
    Return a list of experimental data records referencing the gate_id.
    library_data["experimental_data"] might have items like:
      {
        "gate": "AmtR",
        "data_type": "cytometry",
        "raw_data": {...}
      }
    """
    results = []
    exp_data_list = library_data.get("experimental_data", [])
    for rec in exp_data_list:
        if rec.get("gate","").lower() == gate_id.lower():
            results.append(rec)
    return results


def list_misc_items(library_data):
    """
    Return all items in 'misc'.
    """
    return library_data.get("misc", [])


def list_unrecognized_items(library_data):
    """
    Return all items in 'unrecognized' that didn't match known categories.
    """
    return library_data.get("unrecognized", {}).get("items", [])


# ----------------------- Library Metadata Extraction -----------------------

def extract_library_metadata(library_data, library_id=None):
    """
    Extract comprehensive metadata about a library for the LLM-based selector.
    
    Args:
        library_data: The structured library data
        library_id: Optional ID of the library
        
    Returns:
        Dictionary with metadata about the library
    """
    metadata = {
        "library_id": library_id or library_data.get("metadata", {}).get("name", "unknown_library"),
        "organism": detect_organism(library_data),
        "part_count": len(get_all_parts(library_data)),
        "gate_count": len(get_all_gates(library_data)),
        "gate_types": get_gate_types(library_data),
        "reporters": get_reporter_types(library_data),
        "inducers": get_inducer_types(library_data),
        "promoter_count": len(list_promoters(library_data)),
        "terminator_count": len(list_terminators(library_data)),
        "repressor_count": len(list_repressors(library_data)),
        "rbs_count": len(list_rbs(library_data)),
        "cds_count": len(list_cds(library_data)),
        "misc_count": len(list_misc_items(library_data)),
    }
    
    # Add experimental data summary if available
    exp_data = library_data.get("experimental_data", [])
    if exp_data:
        metadata["experimental_data_count"] = len(exp_data)
        exp_types = Counter([data.get("data_type", "unknown") for data in exp_data])
        metadata["experimental_data_types"] = dict(exp_types)
    
    # Extract additional metadata from the raw metadata
    raw_metadata = library_data.get("metadata", {})
    for key in ["version", "author", "organism", "organism_class", "description"]:
        if key in raw_metadata:
            metadata[key] = raw_metadata[key]
    
    # Add genetic circuit capabilities
    metadata["circuit_capabilities"] = analyze_circuit_capabilities(library_data)
    
    return metadata

def detect_organism(library_data):
    """
    Detect the organism this library is for based on patterns in parts and metadata.
    """
    # First check metadata
    metadata = library_data.get("metadata", {})
    if "organism" in metadata:
        return metadata["organism"]
    
    # Check library ID pattern if available
    library_id = metadata.get("name", "")
    if library_id.startswith("Eco"):
        return "Escherichia coli"
    elif library_id.startswith("SC"):
        return "Saccharomyces cerevisiae"
    elif library_id.startswith("BS"):
        return "Bacillus subtilis"
    
    # Check part names and sequences for hints
    ecoli_markers = ["ecoli", "e. coli", "escherichia"]
    yeast_markers = ["yeast", "cerevisiae", "saccharomyces"]
    bacillus_markers = ["bacillus", "subtilis"]
    
    # Count occurrences in part names
    organism_counts = defaultdict(int)
    
    for part in get_all_parts(library_data):
        part_id = part.get("id", "").lower()
        part_desc = part.get("raw_data", {}).get("description", "").lower()
        
        # Check for organism markers
        for marker in ecoli_markers:
            if marker in part_id or marker in part_desc:
                organism_counts["Escherichia coli"] += 1
                
        for marker in yeast_markers:
            if marker in part_id or marker in part_desc:
                organism_counts["Saccharomyces cerevisiae"] += 1
                
        for marker in bacillus_markers:
            if marker in part_id or marker in part_desc:
                organism_counts["Bacillus subtilis"] += 1
    
    # Return the most likely organism based on counts
    if organism_counts:
        return max(organism_counts.items(), key=lambda x: x[1])[0]
    
    # Default to E. coli if no other information is available
    return "Escherichia coli"

def get_gate_types(library_data):
    """
    Get all unique gate types in the library.
    """
    gate_types = set()
    for gate in get_all_gates(library_data):
        gate_type = gate.get("gate_type", "")
        if gate_type:
            gate_types.add(gate_type.upper())
        
        # Check raw data for gate type information
        raw_data = gate.get("raw_data", {})
        if "gate_type" in raw_data:
            gate_types.add(raw_data["gate_type"].upper())
    
    return list(gate_types)

def get_reporter_types(library_data):
    """
    Get all reporter types in the library (GFP, RFP, etc.)
    """
    reporters = []
    reporter_parts = list_reporters(library_data)
    
    for part in reporter_parts:
        part_id = part.get("id", "").lower()
        reporter_type = None
        
        # Detect reporter type from part ID
        if "gfp" in part_id:
            reporter_type = "GFP"
        elif "rfp" in part_id:
            reporter_type = "RFP"
        elif "yfp" in part_id:
            reporter_type = "YFP"
        elif "cfp" in part_id:
            reporter_type = "CFP"
        elif "lux" in part_id:
            reporter_type = "Lux"
        
        if reporter_type and reporter_type not in reporters:
            reporters.append(reporter_type)
    
    return reporters

def get_inducer_types(library_data):
    """
    Get all inducer types in the library (IPTG, arabinose, etc.)
    """
    inducers = []
    inducer_data = list_inducers(library_data)
    
    for item in inducer_data:
        inducer = item.get("inducer", "").lower()
        if inducer and inducer not in inducers:
            inducers.append(inducer)
    
    return inducers

def analyze_circuit_capabilities(library_data):
    """
    Analyze the genetic circuit capabilities of this library.
    
    Returns:
        Dictionary with circuit capability analysis
    """
    capabilities = {
        "logic_gates": get_gate_types(library_data),
        "input_sensors": [],
        "output_reporters": get_reporter_types(library_data),
    }
    
    # Analyze input sensors (based on inducers and promoters)
    inducers = get_inducer_types(library_data)
    if inducers:
        capabilities["input_sensors"] = inducers
    
    # Analyze potential circuit complexity
    gate_count = len(get_all_gates(library_data))
    if gate_count >= 10:
        capabilities["max_complexity"] = "High"
    elif gate_count >= 5:
        capabilities["max_complexity"] = "Medium"
    else:
        capabilities["max_complexity"] = "Low"
    
    return capabilities


# ----------------------- Example Usage / Test Script -----------------------

def main():
    """Example usage of the UCF retrieval functions"""
    lib_path = "libs/cello-ucf/Eco1C1G1T0.UCF.json"

    # 1) Load the library
    try:
        library_data = load_ecoli_library(lib_path)
    except FileNotFoundError:
        # Try with ext_repos path
        alt_path = "ext_repos/Cello-UCF/files/v2/ucf/Eco/Eco1C1G1T0.UCF.json"
        library_data = load_ecoli_library(alt_path)
    
    # 2) Extract library metadata
    metadata = extract_library_metadata(library_data, "Eco1C1G1T0")
    print("Library Metadata:")
    print(json.dumps(metadata, indent=2))
    
    # 3) Retrieve gates
    all_gates = get_all_gates(library_data)
    print(f"\nFound {len(all_gates)} gates in the library.")
    if all_gates:
        example_gate_id = all_gates[0]["id"]
        print("Example gate 0 ID:", all_gates[0]["id"])
        print("Example gate 0 gate_type:", all_gates[0].get("gate_type"))

    # 4) Retrieve parts
    all_parts = get_all_parts(library_data)
    print(f"\nFound {len(all_parts)} parts in the library.")
    if all_parts:
        print("Example part 0 ID:", all_parts[0]["id"])
        print("First 40 bases of part 0 sequence:", all_parts[0].get("sequence","")[:40])
    
    # 5) Check for inducers
    inducers = list_inducers(library_data)
    print(f"\nDetected {len(inducers)} potential inducers:")
    for inducer in inducers:
        print(f"- {inducer['inducer']} (associated with {inducer['associated_promoter']})")
    
    # 6) Check for reporters
    reporters = list_reporters(library_data)
    print(f"\nFound {len(reporters)} reporter parts:")
    for i, reporter in enumerate(reporters[:3]):  # Show first 3
        print(f"- {reporter['id']}")
    if len(reporters) > 3:
        print(f"  ... and {len(reporters) - 3} more")

if __name__ == "__main__":
    main()
