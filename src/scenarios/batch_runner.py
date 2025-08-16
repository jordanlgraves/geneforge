#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Type

from src.scenarios.retrieval.synbiohub_part import SynBioHubPartScenario
from src.scenarios.intro_to_sys_eng.p1p1 import IntroToSysEng1p1
from src.scenarios.intro_to_sys_eng.p1p2 import IntroToSysEng1p2
from src.scenarios.intro_to_sys_eng.p1p3 import IntroToSysEng1p3
from src.scenarios.intro_to_sys_eng.p3p1 import IntroToSysEng3p1
from src.scenarios.intro_to_sys_eng.p3p7 import IntroToSysEng3p7
from src.scenarios.intro_to_sys_eng.p3p13 import IntroToSysEng3p13

from src.scenarios.eng_gene_circuits.egc_1p1 import EGCProblem1p1Scenario
from src.scenarios.eng_gene_circuits.egc_3p1p1 import EGCProblem3p1p1Scenario
from src.scenarios.eng_gene_circuits.egc_3p1p2 import EGCProblem3p1p2Scenario
from src.scenarios.eng_gene_circuits.egc_3p1p3 import EGCProblem3p1p3Scenario
from src.scenarios.eng_gene_circuits.egc_5p1p1 import EGCProblem5p1p1Scenario

from src.scenarios.design.design_minimal_input_sensors import MinimalInputSensorsScenario
from src.scenarios.design.design_w_promoter_vars import DesignWithPromoterVarsScenario
from src.scenarios.design.design_and_sim_genetic_toggle import GeneticToggleSwitchScenario

from src.scenarios.scenario import Scenario




def run_scenarios(scenarios: List[Scenario], *, max_rounds: int, num_retries: int) -> List[Scenario]:
    for scenario in scenarios:
        scenario.run(max_rounds=max_rounds, num_retries=num_retries)
    return scenarios


def aggregate_metrics(results: Dict[str, Any]) -> Dict[str, Any]:
    score_results = {'correct': 0, 'gave_answer': 0, 'total_accuracy': 0, 'perc_answered': 0, 'acc_answered': 0}
    for scenario_name, result in results.items():
        print(f"{scenario_name}: {result}")
        score_results['correct'] += result.get("metrics", {}).get("correct", 0)
        score_results['gave_answer'] += result.get("metrics", {}).get("gave_answer", 0)
    
    if score_results['gave_answer'] == 0:
        score_results['total_accuracy'] = 0
        score_results['perc_answered'] = 0
        score_results['acc_answered'] = 0
    else:
        score_results['total_accuracy'] = score_results['correct'] / score_results['gave_answer']
        score_results['perc_answered'] = score_results['gave_answer'] / len(results) * 100
        score_results['acc_answered'] = score_results['correct'] / score_results['gave_answer']
    
    print(f"Total accuracy: {score_results['total_accuracy']}")
    print(f"Percentage answered: {score_results['perc_answered']}")
    print(f"Accuracy answered: {score_results['acc_answered']}")
    return score_results

if __name__ == "__main__":
    models = [
        "gemini/gemini-2.5-pro", 
        "gemini/gemini-2.5-flash",
        "gpt-4o-mini",
        "gpt-5-nano-2025-08-07",
        "o3",
        "deepseek-chat",
        # "deepseek-reasoner"
        ]
    all_results = {}
    output_dir = "outputs/benchmarks"
    for model in models:
        args = {
            "model_name": model,
            "system_prompt": None
        }
            
        scenarios = [
            SynBioHubPartScenario(scenario_name="SynBioHubPart", **args),
            IntroToSysEng1p1(scenario_name="IntroToSysEng1p1", **args),
            IntroToSysEng1p2(scenario_name="IntroToSysEng1p2", **args),
            IntroToSysEng1p3(scenario_name="IntroToSysEng1p3", **args),
            IntroToSysEng3p1(scenario_name="IntroToSysEng3p1", **args),
            IntroToSysEng3p7(scenario_name="IntroToSysEng3p7", **args),
            IntroToSysEng3p13(scenario_name="IntroToSysEng3p13", **args),
            EGCProblem1p1Scenario(scenario_name="EGCProblem1p1", **args),
            EGCProblem3p1p1Scenario(scenario_name="EGCProblem3p1p1", **args),
            EGCProblem3p1p2Scenario(scenario_name="EGCProblem3p1p2", **args),
            EGCProblem3p1p3Scenario(scenario_name="EGCProblem3p1p3", **args),
            EGCProblem5p1p1Scenario(scenario_name="EGCProblem5p1p1", **args),
            DesignWithPromoterVarsScenario(scenario_name="DesignWithPromoterVars", **args),
            MinimalInputSensorsScenario(scenario_name="MinimalInputSensors", **args),
            GeneticToggleSwitchScenario(scenario_name="GeneticToggleSwitch", **args),
        ]

        finished_scenarios = run_scenarios(
            scenarios=scenarios,
            max_rounds=15,
            num_retries=1,
        )
        model_results = {}
        for scenario in finished_scenarios:
            model_results[scenario.scenario_name] = {"metrics": scenario.get_metrics(), "messages": scenario.messages}
            
        if '/' in model:
            model = model.split('/')[-1]
        all_results[model] = model_results
        
        # Aggregate metrics for the model
        all_results[model]['aggregated_results'] = aggregate_metrics(model_results)
        
        # Output results for the model
        os.makedirs(output_dir, exist_ok=True)
        for scenario, result in zip(scenarios, model_results.values()):
            json.dump(result['metrics'], 
                      open(f"{output_dir}/{model}_{scenario.__class__.__name__}_metrics.json", "w"), 
                      indent=2)
            json.dump(result['messages'], 
                      open(f"{output_dir}/{model}_{scenario.__class__.__name__}_messages.json", "w"), 
                      indent=2)
    
    # Output aggregated results for all models
    with open(f"{output_dir}/batch_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(json.dumps(all_results, indent=2))

    from matplotlib import pyplot as plt
    plt.figure(figsize=(12, 12))
    ax = plt.subplot(3, 1, 1)
    ax.bar(all_results.keys(), [results['aggregated_results']['total_accuracy'] for results in all_results.values()])
    ax.set_ylabel('Total Accuracy')
    ax = plt.subplot(3, 1, 2)
    ax.bar(all_results.keys(), [results['aggregated_results']['perc_answered'] for results in all_results.values()])
    ax.set_ylabel('Percentage Answered')
    ax = plt.subplot(3, 1, 3)
    ax.bar(all_results.keys(), [results['aggregated_results']['acc_answered'] for results in all_results.values()])
    ax.set_ylabel('Accuracy Answered')
    
    plt.savefig(f"{output_dir}/batch_results_aggregated.png")
    
    
    # Model-wise comparison
    model_results = {}
    for model, results in all_results.items():
        model_results[model] = results['aggregated_results']
    
    # Plot model-wise comparison
    plt.figure(figsize=(12, 12))
    ax = plt.subplot(3, 1, 1)
    ax.bar(model_results.keys(), [results['total_accuracy'] for results in model_results.values()])
    ax.set_ylabel('Total Accuracy')
    ax = plt.subplot(3, 1, 2)
    ax.bar(model_results.keys(), [results['perc_answered'] for results in model_results.values()])
    ax.set_ylabel('Percentage Answered')
    ax = plt.subplot(3, 1, 3)
    ax.bar(model_results.keys(), [results['acc_answered'] for results in model_results.values()])
    ax.set_ylabel('Accuracy Answered')
    
    plt.savefig(f"{output_dir}/batch_results_model_comparison.png")
    