import json
import sbol2
import tyto
from ols_py.client import Ols4Client

client = Ols4Client()

def parse_sbol(sbol_path):
    """
    Parse an SBOL2 document using pySBOL2, interpret each role by 
    looking it up in a local ontology dictionary (or fallback to OLS/Tyto).
    
    Returns a structured_data dict with:
        {
          "metadata": {...},
          "parts": [...],
          "gates": [...],
          "interactions": [...],
          "experimental_data": [...],
          "misc": [],
          "unrecognized": {
             "roles": [],
             "parts": [],
             "items": []
          }
        }
    """

    # Placeholder for a local ontology dictionary if you want to parse manually:
 
    doc = sbol2.Document()
    doc.read(sbol_path)

    structured_data = {
        "metadata": {
            "source_file": sbol_path,
            "sbol_version": getattr(doc, 'version', 'unknown')
        },
        "parts": [],
        "gates": [],
        "interactions": [],
        "experimental_data": [],
        "misc": [],
        "unrecognized": {
            "roles": [],    # store roles we can't identify
            "parts": [],    # store part records we can't interpret
            "items": []     # if we find entire objects that are unknown
        }
    }

    def lookup_role(role_uri):
        """
        Attempt to interpret the role URI using OLS or Tyto.
        Returns a dict with {uri, label, definition, synonyms} 
        or logs it as unrecognized if we fail.
        """
        role_uri_str = str(role_uri)

        # 2) Try an OLS query (example approach)
        try:
            resp = client.search("0000179", params={"ontology": "sbo"})
            term = resp.response.docs[0]
            if term:
                label = term.label
                synonyms = term.synonyms
                definition = term.description
                return {
                    "uri": role_uri_str,
                    "label": label,
                    "definition": definition,
                    "synonyms": synonyms
                }
        except Exception as e:
            # OLS search failed
            pass

        # 3) Fallback Tyto
        label, definition, synonyms = None, None, []
        try:
            if 'SBO:' in role_uri_str:
                label = tyto.SBO.get_term_by_uri(role_uri_str)
            elif 'SO:' in role_uri_str:
                label = tyto.SO.get_term_by_uri(role_uri_str)
        except Exception:
            label = None

        if not label:
            # Log as unrecognized
            structured_data["unrecognized"]["roles"].append(role_uri_str)
            return {
                "uri": role_uri_str,
                "label": "unrecognized",
                "definition": None,
                "synonyms": []
            }

        return {
            "uri": role_uri_str,
            "label": label,
            "definition": definition,
            "synonyms": synonyms
        }

    # --- PARSING PARTS (ComponentDefinitions) ---
    for cd in doc.componentDefinitions:
        part_id = cd.identity
        display_id = cd.displayId or ""
        name = cd.name if cd.name else display_id

        # roles
        role_data = [lookup_role(r) for r in cd.roles]

        # derive a type from the label, if any
        part_type = "unspecified"
        for rd in role_data:
            lbl_lower = rd["label"].lower()
            if "promoter" in lbl_lower:
                part_type = "promoter"
                break
            elif "cds" in lbl_lower:
                part_type = "CDS"
                break
            elif "enhancer" in lbl_lower:
                part_type = "enhancer"
                break
            # add more heuristics as needed

        seq = ""
        if cd.sequences:
            seq_ref = cd.sequences[0]
            seq_obj = doc.getSequence(seq_ref)
            if seq_obj and seq_obj.elements:
                seq = seq_obj.elements

        part_record = {
            "id": part_id,
            "display_id": display_id,
            "name": name,
            "type": part_type,
            "roles": role_data,
            "sequence": seq
        }
        # If part_type is still 'unspecified' or all roles unrecognized,
        # log it to unrecognized
        if part_type == "unspecified":
            structured_data["unrecognized"]["parts"].append(part_record)

        structured_data["parts"].append(part_record)

    # --- GATES & INTERACTIONS (ModuleDefinitions) ---
    for md in doc.moduleDefinitions:
        md_id = md.identity
        md_name = md.displayId if md.displayId else "unnamed_module"
        md_role_data = [lookup_role(r) for r in md.roles]

        gate_type = "unknown"
        # Optionally do the same logic as part_type if the roles indicate "logicGate"
        # or "inverter" or "AND gate" ...
        gate_record = {
            "id": md_id,
            "display_id": md_name,
            "gate_type": gate_type,
            "roles": md_role_data
        }
        structured_data["gates"].append(gate_record)

        # Interactions
        for interaction in md.interactions:
            interaction_id = interaction.identity
            interaction_type_data = [lookup_role(t) for t in interaction.types]
            
            participation_data = []
            for participation in interaction.participations:
                p_role_data = [lookup_role(pr) for pr in participation.roles]
                part_obj = participation.participant  # => URI of the participant

                participation_data.append({
                    "participant": part_obj,
                    "roles": p_role_data
                })
            
            interaction_record = {
                "id": interaction_id,
                "types": interaction_type_data,
                "participations": participation_data
            }
            structured_data["interactions"].append(interaction_record)

    return structured_data

def main():
    sbol_path = "libs/synbiohub/Eco1C1G1T1_collection.xml"
    ontology_path = "libs/ontology/so.json"  # local or custom ontology


    data = parse_sbol(sbol_path)

    print("=== SBOL Parsed Data with Local Ontology ===")
    print(json.dumps(data, indent=2))

    # Check if anything is unrecognized
    unrec = data["unrecognized"]
    if unrec["roles"] or unrec["parts"] or unrec["items"]:
        print("\n=== Unrecognized Elements in SBOL ===")
        if unrec["roles"]:
            print("Unrecognized role URIs:", unrec["roles"])
        if unrec["parts"]:
            print("Parts with type='unspecified':", [p["display_id"] for p in unrec["parts"]])
        if unrec["items"]:
            print("Items entirely unrecognized:", unrec["items"])
    else:
        print("\nNo unrecognized roles or parts found.")

if __name__ == "__main__":
    main()
