#!/usr/bin/env python3

import os
import json
from typing import Dict, List, Any

def load_ecoli_library(json_path):
    """Load a UCF JSON file and return the structured data."""
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"Could not find library file: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # If this is a raw UCF file (list of dictionaries)
    if isinstance(data, list) and len(data) > 0 and "collection" in data[0]:
        return data
    
    # If this is already processed
    if "structured_data" in data:
        return data["structured_data"]
    
    return data

def get_all_parts(library_data):
    """Get all parts from the library."""
    if isinstance(library_data, list):
        # For raw UCF files
        return [item for item in library_data if item.get("collection") == "parts"]
    
    # For processed libraries
    return library_data.get("parts", [])

def list_promoters(library_data):
    """Find promoters in the library."""
    results = []
    parts = get_all_parts(library_data)
    
    for part in parts:
        if isinstance(library_data, list):
            # For raw UCF files
            if part.get("type") == "promoter":
                results.append(part)
        else:
            # For processed libraries
            if "promoter" in part.get("id", "").lower():
                results.append(part)
            elif part.get('raw_data', {}).get('type', '').lower() == 'promoter':
                results.append(part)
    
    return results

def list_reporters(library_data):
    """Find reporter genes like GFP, RFP, etc."""
    results = []
    parts = get_all_parts(library_data)
    
    for part in parts:
        part_id = part.get("id", "") if isinstance(library_data, list) else part.get("id", "")
        if any(x in part_id.lower() for x in ["gfp", "rfp", "yfp", "cfp", "reporter"]):
            results.append(part)
    
    return results

def find_inducers(library_data):
    """Find information about inducers like IPTG and arabinose."""
    # Look for headers that mention inducers
    if isinstance(library_data, list):
        for item in library_data:
            if item.get("collection") == "header":
                media = item.get("media", "").lower()
                if "arabinose" in media or "iptg" in media:
                    return f"Header mentions inducers: {media}"
    
    # Look for gates that use inducers
    for item in library_data if isinstance(library_data, list) else []:
        if item.get("collection") == "gates":
            inducer = item.get("inducer")
            if inducer:
                return f"Found inducer: {inducer}"
    
    # Look for promoters typically used with inducers
    inducers = []
    for promoter in list_promoters(library_data):
        promoter_id = promoter.get("id", "").lower() if isinstance(library_data, list) else promoter.get("id", "").lower()
        if "pbad" in promoter_id or "para" in promoter_id:
            inducers.append("arabinose")
        if "plac" in promoter_id or "ptrc" in promoter_id or "ptac" in promoter_id:
            inducers.append("IPTG")
    
    return f"Inferred inducers: {list(set(inducers))}"

def main():
    """Check all UCF files in the cello-ucf directory."""
    libs_dir = 'libs/cello-ucf'
    
    for lib_file in os.listdir(libs_dir):
        if lib_file.endswith('.UCF.json'):
            print(f"\n{'='*50}")
            print(f"Library: {lib_file}")
            print(f"{'='*50}")
            
            try:
                data = load_ecoli_library(os.path.join(libs_dir, lib_file))
                
                print(f"Inducers: {find_inducers(data)}")
                
                print("\nPromoters:")
                promoters = list_promoters(data)
                for i, p in enumerate(promoters[:5]):
                    p_id = p.get("id", "") if isinstance(data, list) else p.get("id", "")
                    p_name = p.get("name", "") if isinstance(data, list) else p.get("name", "")
                    print(f"  {i+1}. {p_id or p_name}")
                if len(promoters) > 5:
                    print(f"  ... and {len(promoters)-5} more")
                
                print("\nReporters:")
                reporters = list_reporters(data)
                for i, r in enumerate(reporters):
                    r_id = r.get("id", "") if isinstance(data, list) else r.get("id", "")
                    r_name = r.get("name", "") if isinstance(data, list) else r.get("name", "")
                    print(f"  {i+1}. {r_id or r_name}")
                if not reporters:
                    print("  None found")
                
                print("\nSearching for pLac and pBAD:")
                found = False
                for part in get_all_parts(data):
                    part_id = part.get("id", "") if isinstance(data, list) else part.get("id", "")
                    part_name = part.get("name", "") if isinstance(data, list) else part.get("name", "")
                    identifier = part_id or part_name
                    if 'lac' in identifier.lower() or 'pbad' in identifier.lower():
                        print(f"  Found: {identifier}")
                        found = True
                if not found:
                    print("  None found")
                
            except Exception as e:
                print(f"Error processing {lib_file}: {str(e)}")

if __name__ == "__main__":
    main() 