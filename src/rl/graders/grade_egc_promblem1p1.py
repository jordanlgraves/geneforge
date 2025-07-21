from typing import Any
import json

def grade(sample: dict[str, Any], item: dict[str, Any]) -> float:
    """
    The `sample` argument supplied to the grading function will be a dictionary populated with the 
    model's output during training for you to grade. `output_json` will only be populated if the 
    output uses `response_format`.
    
    sample:
    {
        "choices": [...],
        "output_text": "...",
        "output_json": {},
        "output_tools": [...]
    }
    
    The `item` argument supplied is a dictionary populated with input grading context. 
    For evals, this will include keys from the data source.
    For fine-tuning this will include keys from each training data row.
    
    item:
    {
        "reference_answer": {
            "dG": -1.16,
            "reaction_favored": "forward",
            "explanation": "We use the standard thermodynamic equation: \\Delta G = RT \\ln\\left(\\frac{k_{-1} [ES]}{k_1 [E][S]}\\right). Substituting values: \\Delta G = 0.5961 \\cdot \\ln\\left(\\frac{0.1 \\cdot 50}{0.01 \\cdot 35 \\cdot 100}\\right). \\Delta G = 0.5961 \\cdot \\ln\\left(\\frac{5}{35}\\right) = 0.5961 \\cdot \\ln(0.142857). \\Delta G \\approx 0.5961 \\cdot (-1.9459) = -1.16 \\,\\text{kcal/mol}. Since \\Delta G < 0, the forward reaction is favored. At steady state (\\Delta G = 0), trial-and-error shows that: \\\\[ES] = 75 \\,\\text{nM}\\\\ [S] = 75 \\,\\text{nM}\\\\ [E] = 10 \\,\\text{nM}\\\\ This satisfies the condition that the total amount of enzyme and substrate is conserved, and results in \\Delta G = 0.",
            "ES": 75,
            "S": 75,
            "E": 10
        }
    }
    """

    output_json = sample.get('output_json', {})
    output_tools = sample.get('output_tools', [])
    output_text = sample.get('output_text', '')

    reference_answer = json.loads(item.get('reference_answer', '{}'))
    
    # Extract the final answer from the output
    final_answer = json.loads(output_tools[-1].get('content', {})).get('answer', '')
    if final_answer:
        final_answer = json.loads(final_answer)
    else:
        final_answer = output_text
    
    score = 0
    max_score = 6
    tolerance = 0.01
    if abs(final_answer.get('dG') - reference_answer.get('dG')) < tolerance:
        score += 1
    if final_answer.get('reaction_favored') == reference_answer.get('reaction_favored'):
        score += 1
    if final_answer.get('explanation') == reference_answer.get('explanation'):
        score += 1
    if abs(final_answer.get('ES') - reference_answer.get('ES')) < tolerance:
        score += 1
    if abs(final_answer.get('S') - reference_answer.get('S')) < tolerance:
        score += 1
    if abs(final_answer.get('E') - reference_answer.get('E')) < tolerance:
        score += 1
    return score / max_score