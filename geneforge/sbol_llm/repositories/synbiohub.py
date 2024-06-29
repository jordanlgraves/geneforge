
import requests
import sbol2

def fetch_sequence(part_id):
    url = f'https://synbiohub.org/public/igem/{part_id}/1/sbol'
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception('Failed to fetch part sequence')
    
def create_component(doc, name, part_id, role):
    uri = f'https://synbiohub.org/public/igem/{part_id}/1'
    if uri in doc.componentDefinitions:
        return doc.componentDefinitions[uri]
    else:
        sbol_string = fetch_sequence(part_id)
        temp_doc = sbol2.Document()
        temp_doc.readString(sbol_string)
        component = temp_doc.componentDefinitions[0]
        component.name = name
        component.roles = [role]
        doc.addComponentDefinition(component)
        return component
    