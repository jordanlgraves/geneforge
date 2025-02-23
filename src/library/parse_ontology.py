import json

def parse_local_ontology(ontology_json_path):
    """
    Reads a local ontology JSON file (in OBO Graphs format) and returns a dictionary:
      {
        "http://purl.obolibrary.org/obo/SO_0000165": {
          "label": "enhancer",
          "definition": "A cis-acting sequence that ... ",
          "synonyms": ["INSDC_qualifier:enhancer", ...],
          "comments": [...],
          ...
        },
        ...
      }
    """
    with open(ontology_json_path, 'r', encoding='utf-8') as f:
        ontology_data = json.load(f)

    # The JSON typically has: { "graphs": [ { "nodes": [...], ... } ] }
    # We’ll assume the first item in "graphs" has the relevant "nodes"
    graphs = ontology_data.get("graphs", [])
    if not graphs:
        raise ValueError("No 'graphs' found in ontology JSON")

    nodes = graphs[0].get("nodes", [])
    if not nodes:
        raise ValueError("No 'nodes' found in first graph of ontology JSON")

    # Build a dictionary: id -> details
    ontology_dict = {}

    for node in nodes:
        node_id = node.get("id")
        node_lbl = node.get("lbl", "")
        node_meta = node.get("meta", {})

        # definition text (if present)
        definition_val = ""
        definition_obj = node_meta.get("definition")
        if definition_obj and "val" in definition_obj:
            definition_val = definition_obj["val"]

        # synonyms (some might be "exact", "broad", etc.)
        # We'll gather them in a single list
        synonyms_list = []
        for syn in node_meta.get("synonyms", []):
            synonyms_list.append(syn.get("val", ""))

        # Comments
        comments_list = node_meta.get("comments", [])

        # Put it all into a dictionary for this URI
        ontology_dict[node_id] = {
            "label": node_lbl,
            "definition": definition_val,
            "synonyms": synonyms_list,
            "comments": comments_list,
            # You can store more (e.g. xrefs, basicPropertyValues, etc.)
        }

    return ontology_dict

def main():
    onto_path = "libs/ontology/so.json"
    so_dict = parse_local_ontology(onto_path)

    # Show an example lookup
    example_uri = "http://purl.obolibrary.org/obo/SO_0000165"  # "enhancer"
    if example_uri in so_dict:
        print("Found URI:", example_uri)
        print("Label:", so_dict[example_uri]["label"])
        print("Synonyms:", so_dict[example_uri]["synonyms"])
        print("Definition:", so_dict[example_uri]["definition"])
    else:
        print("URI not found:", example_uri)

if __name__ == "__main__":
    main()
