#!/usr/bin/env python3

import json
import os
from pprint import pprint

def main():
    """Check the TetRLacI library for relevant components."""
    library_path = 'libs/cello-ucf/TetRLacI.UCF.json'
    
    print(f"Analyzing library: {os.path.basename(library_path)}")
    print("=" * 50)
    
    try:
        with open(library_path, 'r') as f:
            data = json.load(f)
        
        # Check header information
        print("\nHEADER INFORMATION:")
        for item in data:
            if item.get('collection') == 'header':
                pprint(item)
        
        # Check gates information
        print("\nGATES:")
        for item in data:
            if item.get('collection') == 'gates':
                print(f"Gate: {item.get('gate_name')}")
                print(f"  Regulator: {item.get('regulator')}")
                print(f"  Inducer: {item.get('inducer')}")
                print(f"  Type: {item.get('gate_type')}")
                print(f"  System: {item.get('system')}")
                print("-" * 30)
        
        # Check response functions
        print("\nRESPONSE FUNCTIONS:")
        for item in data:
            if item.get('collection') == 'response_functions':
                print(f"Gate: {item.get('gate_name')}")
                print(f"  Equation: {item.get('equation')}")
                print("-" * 30)
        
        # Check for parts
        print("\nPARTS:")
        parts_found = False
        for item in data:
            if item.get('collection') == 'parts':
                parts_found = True
                print(f"Part: {item.get('name')}")
                print(f"  Type: {item.get('type')}")
                print(f"  Sequence: {item.get('dnasequence')[:50]}..." if item.get('dnasequence') else "  Sequence: None")
                print("-" * 30)
        
        if not parts_found:
            print("No parts found in this library.")
        
        # Check for LacI and IPTG
        print("\nCHECKING FOR LacI AND IPTG:")
        lacI_found = False
        iptg_found = False
        
        for item in data:
            if 'lac' in str(item).lower() or 'laci' in str(item).lower():
                lacI_found = True
                print("LacI reference found in:")
                pprint(item)
                print("-" * 30)
            
            if 'iptg' in str(item).lower():
                iptg_found = True
                print("IPTG reference found in:")
                pprint(item)
                print("-" * 30)
        
        if not lacI_found:
            print("No LacI references found.")
        if not iptg_found:
            print("No IPTG references found.")
        
        # Check for pBAD and arabinose
        print("\nCHECKING FOR pBAD AND ARABINOSE:")
        pbad_found = False
        arabinose_found = False
        
        for item in data:
            if 'pbad' in str(item).lower() or 'para' in str(item).lower():
                pbad_found = True
                print("pBAD reference found in:")
                pprint(item)
                print("-" * 30)
            
            if 'arabinose' in str(item).lower():
                arabinose_found = True
                print("Arabinose reference found in:")
                pprint(item)
                print("-" * 30)
        
        if not pbad_found:
            print("No pBAD references found.")
        if not arabinose_found:
            print("No arabinose references found.")
        
        # Check for GFP
        print("\nCHECKING FOR GFP:")
        gfp_found = False
        
        for item in data:
            if 'gfp' in str(item).lower():
                gfp_found = True
                print("GFP reference found in:")
                pprint(item)
                print("-" * 30)
        
        if not gfp_found:
            print("No GFP references found.")
        
    except Exception as e:
        print(f"Error processing library: {str(e)}")

if __name__ == "__main__":
    main() 