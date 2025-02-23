import json
import os

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
        raise ValueError("JSON file does not contain 'structured_data' at top-level. "
                         "Make sure it's the output from parse_ecoli_ucf().")

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


# ----------------------- Example Usage / Test Script -----------------------

def main():
    """Example usage of the UCF retrieval functions"""
    lib_path = "libs/cello-ucf/Eco1C1G1T0.UCF.json"

    # 1) Load the library
    import parse_ucf
    library_data = parse_ucf.parse_ecoli_ucf(lib_path)['structured_data']
    
    # 2) Retrieve gates
    all_gates = get_all_gates(library_data)
    print(f"Found {len(all_gates)} gates in the library.")
    if all_gates:
        example_gate_id = all_gates[0]["id"]
        print("Example gate 0 ID:", all_gates[0]["id"])
        print("Example gate 0 gate_type:", all_gates[0].get("gate_type"))

    # 3) Retrieve gates by type
    nor_gates = get_gates_by_type(library_data, "nor")
    print(f"Found {len(nor_gates)} NOR gates in the library.")

    # 4) Retrieve parts
    all_parts = get_all_parts(library_data)
    print(f"Found {len(all_parts)} parts in the library.")
    if all_parts:
        print("Example part 0 ID:", all_parts[0]["id"])
        print("First 40 bases of part 0 sequence:", all_parts[0].get("sequence","")[:40])

    # 5) Retrieve a specific gate by ID
    gate_amtr = get_gate_by_id(library_data, "AmtR")
    if gate_amtr:
        print(f"Gate AmtR found. gate_type:", gate_amtr.get("gate_type"))
    else:
        print("Gate AmtR not found in library.")

    # 6) Check experimental data for AmtR gate
    amtr_experiments = get_experimental_data_for_gate(library_data, "AmtR")
    print(f"Found {len(amtr_experiments)} experimental data items for gate AmtR.")

    # 7) List unrecognized items
    unrec_items = list_unrecognized_items(library_data)
    print(f"\nThere are {len(unrec_items)} unrecognized items in the library.")

    # 8) Misc items
    misc_entries = list_misc_items(library_data)
    print(f"There are {len(misc_entries)} items in 'misc' category.")

    # 9) List promoters
    promoters = list_promoters(library_data)
    print(f"Found {len(promoters)} promoters in the library.")

    # 10) List terminators
    terminators = list_terminators(library_data)
    print(f"Found {len(terminators)} terminators in the library.")

    # 11) Choose repressors
    repressors = choose_repressor(library_data)
    print(f"Found {len(repressors)} repressors in the library.")

    # 12) Get DNA part by name - use a part we know exists
    dna_part = get_dna_part_by_name(library_data, "AmtR")
    if dna_part:
        print(f"Found DNA part {dna_part['id']} in the library.")
    else:
        print("DNA part AmtR not found in library.")

if __name__ == "__main__":
    main()
