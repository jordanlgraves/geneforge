# Download the definitions from the SBOL/SO defitions and write them to a file

import requests
import json
import os
import sys
from tqdm import tqdm


identifiers_base_url = 'http://identifiers.org/so/'

from ontology import *

for role in VALID_ROLES.keys():
    role_url = identifiers_base_url + role

    response = requests.get(role_url)
    if response.status_code == 200:
        data = json.loads(response.text)
        description = data['description']
        print(f'"{role}": "{description}"')
    
