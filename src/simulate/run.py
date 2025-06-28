import tellurium as te
import libsbml
from typing import List, Dict

def run_kinetic_model_tellurium(sbml_doc: libsbml.SBMLDocument, 
                                parameters: dict,
                                initial_concentrations: dict,
                                events: List[Dict] | Dict | None = None,
                                start = 0.0,
                                end = 100.0,
                                steps = 100):
    """

    'initial_concentrations': {
            'P': {
                {
                'value': None,
                'unit': 'uM_litre',
                'source': None
            }
        }
    }
    'events': {
        # Legacy dict style (still supported for backward-compatibility):
        'P': {
            'time': None,
            'value': None
        }
    }
    OR
    'events': [
        {
            'time': None,
            'species': 'P',
            'value': None
        }
    }
    'parameters':  {
        'kdeg_P': { 
            'value': 1.0, 
            'unit': 'dimensionless',
            'source': 'from SBML'
        }
    }
    """
    sbml_str = libsbml.writeSBMLToString(sbml_doc)
    rr = te.loadSBMLModel(sbml_str)

    # Set the parameters
    print(parameters)
    for param_name, param_spec in parameters.items():
        if param_spec['value'] is not None:
            rr[param_name] = param_spec['value']
        

    # Set the initial concentrations
    print(initial_concentrations)
    for species_name, species_spec in initial_concentrations.items():
        if species_spec['value'] is not None:
            rr[species_name] = species_spec['value']
        
    if events is not None:
        # Support both legacy dict format and new list-of-dicts format
        if isinstance(events, dict):
            for event_species, event_spec in events.items():
                event_time = event_spec['time']
                event_value = event_spec['value']
                _event_name = f"set_{event_species}_at_{event_time}".replace('.', '_')
                rr.addEvent(_event_name, True, f"time >= {event_time}")
                rr.addEventAssignment(_event_name, event_species, str(event_value))
        elif isinstance(events, list):
            for ev in events:
                try:
                    event_species = ev['species']
                    event_time = ev['time']
                    event_value = ev['value']
                except KeyError as exc:
                    raise ValueError(f"Event entries must contain 'species', 'time', and 'value' keys. E.g. '{{'species': 'P', 'time': 50, 'value': 10}}` Missing {exc} in {ev}")

                _event_name = f"set_{event_species}_at_{event_time}".replace('.', '_')
                rr.addEvent(_event_name, True, f"time >= {event_time}")
                rr.addEventAssignment(_event_name, event_species, str(event_value))
        else:
            raise TypeError("'events' must be a dict or a list of dicts.")
    

    result = rr.simulate(start=start, end=end, steps=int(steps))
    print(result)
    return result