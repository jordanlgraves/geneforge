import json
import os
import logging
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parse_ucf")

def parse_ucf(ucf_path: str, organism_type: str = None) -> Dict:
    """
    Parse a UCF library JSON file. This is a wrapper around organism-specific parsers.
    
    Args:
        ucf_path: Path to the UCF JSON file
        organism_type: Optional organism type to force a specific parser
        
    Returns:
        Dictionary containing the parsed UCF data
    """
    # Determine organism type from filename if not provided
    if not organism_type:
        filename = os.path.basename(ucf_path)
        if filename.startswith("Eco"):
            organism_type = "ecoli"
        elif filename.startswith("SC"):
            organism_type = "yeast"
        elif filename.startswith("BS"):
            organism_type = "bacillus"
        else:
            # Default to E. coli parser
            organism_type = "ecoli"
            logger.warning(f"Could not determine organism type from filename '{filename}'. Using E. coli parser.")
    
    # Call the appropriate parser
    organism_type = organism_type.lower()
    if organism_type in ["ecoli", "e.coli", "e. coli", "escherichia coli"]:
        return parse_ecoli_ucf(ucf_path)
    elif organism_type in ["yeast", "saccharomyces", "s. cerevisiae", "saccharomyces cerevisiae"]:
        return parse_yeast_ucf(ucf_path)
    else:
        logger.warning(f"No specific parser for organism type '{organism_type}'. Using E. coli parser.")
        return parse_ecoli_ucf(ucf_path)

def parse_ecoli_ucf(ucf_path: str) -> Dict:
    """
    Parse the UCF library JSON (e.g. Eco1C1G1T0.UCF.json).
    Returns:
      {
        'summary': {...},      # Summarized stats
        'report': {...},       # Human-readable classification
        'structured_data': {   # Data for merging
           'metadata': {...},
           'parts': [...],
           'gates': [...],
           'interactions': [...],
           'experimental_data': [...],
           'misc': [...],
           'unrecognized': {...}  # <-- newly added
        }
      }
    """
    if not os.path.exists(ucf_path):
        raise FileNotFoundError(f"UCF file not found: {ucf_path}")

    with open(ucf_path, 'r', encoding='utf-8') as f:
        try:
            lib = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in UCF file: {e}")

    # Verify we have a list/array
    if not isinstance(lib, list):
        raise ValueError(f"UCF file does not contain a JSON array as expected. Found {type(lib)} instead.")

    # This is the final structure we'll return
    structured_data = {
        "metadata": {},
        "parts": [],
        "gates": [],
        "interactions": [],
        "experimental_data": [],
        "misc": [],
        "unrecognized": {
            "items": [],       # raw items we can't categorize
            "fields": []       # fields within recognized items that we can't interpret
        }
    }

    # We'll also build a 'report' dict for summarizing
    report = {
        'metadata': {},
        'circuit_components': [],
        'gate_definitions': [],
        'dna_parts': [],
        'experimental_data': [],
        'miscellaneous': []
    }

    total_entries = len(lib)

    for i, item in enumerate(lib):
        # Skip non-dict items
        if not isinstance(item, dict):
            logger.warning(f"Skipping non-dict item at index {i}: {item}")
            continue
        # If i == 0, assume library-level metadata
        if i == 0:
            metadata = {k: v for k, v in item.items() if k != 'collection'}
            structured_data['metadata'] = metadata
            report['metadata'] = metadata
            continue  # Skip the rest of the checks for item 0

        # 1) circuit component if it has outputs, inputs, netlist
        if all(k in item for k in ['outputs','inputs','netlist']):
            # We log in 'report'
            desc = {
                'type': 'circuit_component',
                'structure': list(item.keys()),
                'example_inputs': item.get('inputs', []),
                'example_outputs': item.get('outputs', [])
            }
            report['circuit_components'].append(desc)

            # We'll store the entire raw item in "misc" for now
            structured_data["misc"].append({
                "category": "circuit_component",
                "raw": item
            })

        # 2) gate definition if 'regulator' in item
        elif 'regulator' in item:
            desc = {
                'type': 'gate_definition',
                'properties': list(item.keys()),
                'example_regulator': item.get('regulator'),
                'example_gate_type': item.get('gate_type')
            }
            report['gate_definitions'].append(desc)

            # minimal gate object
            gate_obj = {
                "id": item.get('regulator', f"gate_{i}"),
                "gate_type": item.get('gate_type','unknown'),
                "raw_data": item
            }
            structured_data["gates"].append(gate_obj)

        # 3) If 'equation' in item => gate model
        elif 'equation' in item:
            # add it to gate_definitions in the summary
            desc = {
                'type': 'gate_model',
                'equation_variables': item.get('variables',[]),
                'parameters': item.get('parameters',[])
            }
            report['gate_definitions'].append(desc)

            # store raw in "misc"
            structured_data["misc"].append({
                "category": "gate_model_equation",
                "raw_data": item
            })

        # 4) DNA part if 'dnasequence' in item
        elif 'dnasequence' in item:
            seq = item.get('dnasequence','')
            name = item.get('name', f"unnamed_part_{i}")
            part_desc = {
                'type': 'dna_part',
                'name': name,
                'sequence_length': len(seq)
            }
            report['dna_parts'].append(part_desc)

            part_obj = {
                "id": name,
                "type": "dna_part",
                "sequence": seq,
                "raw_data": item
            }
            structured_data["parts"].append(part_obj)

        # 5) experimental data if 'cytometry_data' in item
        elif 'cytometry_data' in item:
            gate_name = item.get('gate_name', f"gate_{i}")
            report['experimental_data'].append({
                'gate': gate_name,
                'data_type': 'cytometry'
            })

            structured_data["experimental_data"].append({
                "gate": gate_name,
                "data_type": "cytometry",
                "raw_data": item
            })

        elif 'gate_name' in item:
            if 'growth' in item and 'input' in item:
                # Maybe these are specialized experimental conditions
                structured_data["experimental_data"].append({
                    "gate": item['gate_name'],
                    "type": "growth_input_data",
                    "raw_data": item
                })
            else:
                # This is likely a gate definition or gate data from Cello
                # We can parse them as gate definitions, or store them in "gates".
                gate_id = item.get('gate_name', f"gate_{i}")
                # Maybe we look for 'expression_cassettes', 'promoter', 'input', 'growth' etc.
                gate_obj = {
                    "id": gate_id,
                    "raw_data": item
                }
                # Possibly parse out the promoter name from item['promoter']
                # or note the 'input' field for special usage

                structured_data["gates"].append(gate_obj)

                # We may want to treat them separately from 'regulator' gates,
                # We can add a new subcategory.

        elif 'plasmid_sequence' in item:
            plasmid_obj = {
            "type": "plasmid",
            "description": item.get('plasmid_description', 'N/A'),
            "sequence": item.get('plasmid_sequence', ''),
            "raw_data": item
            }
            structured_data["misc"].append(plasmid_obj)

        elif 'eugene_part_rules' in item or 'eugene_gate_rules' in item:
            # This is your design-time composition constraints
            structured_data["misc"].append({
            "category": "eugene_rules",
            "raw_data": item
            })

        elif 'locations' in item:
            # Possibly store as module layout info
            structured_data["misc"].append({
            "category": "module_locations",
            "raw_data": item
            })

        # 6) Otherwise, unrecognized
        else:
            report['miscellaneous'].append({
                'index': i,
                'keys': list(item.keys())
            })
            # store entire item in unrecognized
            structured_data["unrecognized"]["items"].append({
                "index": i,
                "keys": list(item.keys()),
                "raw": item
            })

    # Summarize
    summary = {
        'total_entries': total_entries,
        'metadata_fields': list(report['metadata'].keys()),
        'num_circuit_components': len(report['circuit_components']),
        'num_gate_definitions': len(report['gate_definitions']),
        'num_dna_parts': len(report['dna_parts']),
        'num_experimental_datasets': len(report['experimental_data']),
        'unique_component_types': len({tuple(c['structure']) for c in report['circuit_components']})
    }
    summary["num_plasmids"] = len([x for x in structured_data["misc"] if x.get("type") == "plasmid"])
    summary["num_eugene_rules"] = len([x for x in structured_data["misc"] if x.get("category") == "eugene_rules"])
    summary["num_module_locations"] = len([x for x in structured_data["misc"] if x.get("category") == "module_locations"])  

    # Add organism identifier
    filename = os.path.basename(ucf_path)
    if filename.startswith("Eco"):
        summary["organism"] = "Escherichia coli"
    elif filename.startswith("SC"):
        summary["organism"] = "Saccharomyces cerevisiae"
    elif filename.startswith("BS"):
        summary["organism"] = "Bacillus subtilis"
    else:
        summary["organism"] = "Unknown"

    final_output = {
        "summary": summary,
        "report": report,
        "structured_data": structured_data
    }
    return final_output

def parse_yeast_ucf(ucf_path: str) -> Dict:
    """
    Parse a UCF file for Saccharomyces cerevisiae (yeast).
    This is currently a stub that calls the E. coli parser, but could be 
    expanded for yeast-specific parsing logic in the future.
    
    Args:
        ucf_path: Path to the UCF JSON file
        
    Returns:
        Dictionary containing the parsed UCF data
    """
    # Currently, we use the same parsing logic as E. coli
    # but override the organism in the summary
    parsed_data = parse_ecoli_ucf(ucf_path)
    parsed_data["summary"]["organism"] = "Saccharomyces cerevisiae"
    
    # Add any yeast-specific parsing logic here in the future
    
    return parsed_data

def main():
    """
    Example usage of the UCF parser.
    """
    # Try different paths to locate the UCF file
    potential_paths = [
        "libs/cello-ucf/Eco1C1G1T0.UCF.json",
        "ext_repos/Cello-UCF/files/v2/ucf/Eco/Eco1C1G1T0.UCF.json"
    ]
    
    ucf_path = None
    for path in potential_paths:
        if os.path.exists(path):
            ucf_path = path
            break
    
    if not ucf_path:
        print("Could not find UCF file in expected locations.")
        return
    
    # Parse the UCF file
    parsed = parse_ucf(ucf_path)

    # Print summary
    print("=== UCF Summary ===")
    print(json.dumps(parsed['summary'], indent=2))

    # Show if we have unrecognized items
    unrec = parsed['structured_data']['unrecognized']
    if unrec["items"]:
        print("\nUnrecognized items found:")
        for i,u in enumerate(unrec["items"]):
            print(f"  {i}: index={u['index']}, keys={u['keys']}")
    else:
        print("\nNo unrecognized items.")

    # Count part types
    part_types = {}
    for part in parsed['structured_data']['parts']:
        part_type = part.get('type', 'unknown')
        if part_type in part_types:
            part_types[part_type] += 1
        else:
            part_types[part_type] = 1
    
    print("\nPart types:")
    for t, count in part_types.items():
        print(f"  {t}: {count}")

    # Save the parsed data to a JSON file
    output_dir = "outputs/parsed_ucf"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.basename(ucf_path)
    output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_parsed.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(parsed, f, indent=2)
    print(f"\nParsed data saved to {output_path}")

if __name__ == "__main__":
    main()
