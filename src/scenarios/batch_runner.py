#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.scenarios.retrieval.synbiohub_part import SynBioHubPartScenario
from src.scenarios.intro_to_sys_eng.p1p1 import IntroToSysEng1p1
from src.scenarios.intro_to_sys_eng.p1p2 import IntroToSysEng1p2
from src.scenarios.intro_to_sys_eng.p1p3 import IntroToSysEng1p3
from src.scenarios.intro_to_sys_eng.p2p3 import IntroToSysEng2p3
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


# ---------------------------
# Utility helpers
# ---------------------------

def now_run_id() -> str:
    # e.g., run-2025-09-01_14-22-33
    return "run-" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def sanitize_filename(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in s)


def failure_trace_markdown(model: str, scen_name: str, class_name: str, metrics: Dict[str, Any]) -> str:
    fr = metrics.get("failure_report") or {}
    primary = fr.get("primary") or {}
    tail = fr.get("tail_transcript") or []
    tool_usage = fr.get("tool_usage") or {}

    lines = []
    lines.append(f"# Failure Trace — {model} / {scen_name} ({class_name})")
    lines.append("")
    lines.append(f"**Primary code:** `{primary.get('code')}`")
    lines.append("")
    if primary.get("message"):
        lines.append(f"**Message:** {primary.get('message')}")
        lines.append("")
    if primary.get("details"):
        lines.append("**Details (JSON):**")
        lines.append("```json")
        lines.append(json.dumps(primary.get("details"), indent=2))
        lines.append("```")
        lines.append("")
    if tool_usage:
        lines.append("**Tool Usage:**")
        lines.append("```json")
        lines.append(json.dumps(tool_usage, indent=2))
        lines.append("```")
        lines.append("")
    if tail:
        lines.append("**Tail Transcript (last few messages):**")
        lines.append("")
        for i, m in enumerate(tail, 1):
            role = m.get("role", "?")
            content = m.get("content", "")
            name = m.get("name")
            hdr = f"{i}. **{role.upper()}**" + (f" (tool: `{name}`)" if name else "")
            lines.append(hdr)
            lines.append("")
            lines.append("```")
            if isinstance(content, str) and len(content) > 4000:
                content = content[:4000] + "\n... [truncated]"
            lines.append(content if isinstance(content, str) else json.dumps(content, indent=2))
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


def aggregate_metrics(results: Dict[str, Any]) -> Dict[str, Any]:
    out = {'correct': 0, 'answered': 0, 'total': len(results)}
    for _, r in results.items():
        m = r.get("metrics", {})
        out['correct'] += int(bool(m.get("correct")))
        out['answered'] += int(bool(m.get("gave_answer")))

    return {
        "total": out['total'],
        "answered": out['answered'],
        "correct": out['correct'],
        "total_accuracy": out['correct'] / out['total'] if out['total'] else 0.0,
        "perc_answered": (out['answered'] / out['total'] * 100) if out['total'] else 0.0,
        "acc_answered": (out['correct'] / out['answered']) if out['answered'] else 0.0,
    }


def run_scenarios(scenarios: List[Scenario], *, max_rounds: int, num_retries: int) -> List[Scenario]:
    for scenario in scenarios:
        scenario.run(max_rounds=max_rounds, num_retries=num_retries)
    return scenarios


def git_commit() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def ensure_latest_symlink(root: str, run_dir: str):
    latest = os.path.join(root, "latest")
    try:
        if os.path.islink(latest) or os.path.exists(latest):
            if os.path.islink(latest):
                os.unlink(latest)
            else:
                # if it's a dir/file, remove it (careful)
                if os.path.isdir(latest):
                    shutil.rmtree(latest)
                else:
                    os.remove(latest)
        # Symlink when supported; else copy summaries for convenience
        if platform.system().lower().startswith("win"):
            # Windows: create a small copy of summaries instead of a symlink
            os.makedirs(latest, exist_ok=True)
            for fname in ["batch_results.json", "summary_rows.json", "summary_rows.csv",
                          "_failures_summary.json"]:
                src = os.path.join(run_dir, fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(latest, fname))
        else:
            os.symlink(os.path.relpath(run_dir, root), latest)
    except Exception as e:
        print(f"[warn] Could not create 'latest' pointer: {e}")


def prune_old_runs(root: str, keep: int):
    # Keep the newest 'keep' run directories (run-YYYY-... format), remove older ones.
    if keep <= 0:
        return
    entries = [d for d in os.listdir(root) if d.startswith("run-") and os.path.isdir(os.path.join(root, d))]
    if not entries:
        return
    # Sort by dir mtime desc
    entries.sort(key=lambda d: os.path.getmtime(os.path.join(root, d)), reverse=True)
    for d in entries[keep:]:
        path = os.path.join(root, d)
        try:
            shutil.rmtree(path)
            print(f"[prune] removed old run dir: {path}")
        except Exception as e:
            print(f"[warn] could not remove {path}: {e}")


# ---------------------------
# CLI
# ---------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Run genetic design model benchmarks")
    p.add_argument("--output-root", default="outputs/benchmarks", help="Root folder for benchmark outputs")
    p.add_argument("--run-id", default=None, help="Optional run id (default: timestamped)")
    p.add_argument("--clean-run", action="store_true", help="If the run dir exists, remove it before writing")
    p.add_argument("--keep-runs", type=int, default=0, help="If >0, prune older run dirs to keep only N most recent")
    p.add_argument("--max-rounds", type=int, default=15)
    p.add_argument("--num-retries", type=int, default=1)
    return p.parse_args()


# ---------------------------
# Main
# ---------------------------

if __name__ == "__main__":
    args = parse_args()

    output_root = args.output_root
    os.makedirs(output_root, exist_ok=True)

    run_id = args.run_id or now_run_id()
    run_dir = os.path.join(output_root, run_id)
    traces_dir = os.path.join(run_dir, "_traces")
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(traces_dir, exist_ok=True)

    if args.clean_run and os.listdir(run_dir):
        print(f"[clean] removing existing run dir: {run_dir}")
        shutil.rmtree(run_dir)
        os.makedirs(run_dir, exist_ok=True)
        os.makedirs(traces_dir, exist_ok=True)

    # models list (editable)
    models = [
        # "gemini/gemini-2.5-pro", 
        "gemini/gemini-2.5-flash",
        # "gpt-4o-mini",
        "gpt-5-nano-2025-08-07",
        "o3",
        "deepseek-chat",
        "claude-opus-4-1-20250805"
        # "deepseek-reasoner"
    ]

    # scenario set (keep commented lines to quickly enable later)
    def build_scenarios(model_name: str):
        args_local = {"model_name": model_name, "system_prompt": None}
        return [
            # SynBioHubPartScenario(scenario_name="SynBioHubPart", **args_local),
            
            # KNOWLEDGE
            IntroToSysEng1p1(scenario_name="IntroToSysEng1p1", **args_local),
            IntroToSysEng1p2(scenario_name="IntroToSysEng1p2", **args_local),
            IntroToSysEng1p3(scenario_name="IntroToSysEng1p3", **args_local),
            IntroToSysEng2p3(scenario_name="IntroToSysEng2p3", **args_local),
            IntroToSysEng3p1(scenario_name="IntroToSysEng3p1", **args_local),
            IntroToSysEng3p7(scenario_name="IntroToSysEng3p7", **args_local),
            IntroToSysEng3p13(scenario_name="IntroToSysEng3p13", **args_local),
            EGCProblem1p1Scenario(scenario_name="EGCProblem1p1", **args_local),
            EGCProblem3p1p1Scenario(scenario_name="EGCProblem3p1p1", **args_local),
            EGCProblem3p1p2Scenario(scenario_name="EGCProblem3p1p2", **args_local),
            EGCProblem3p1p3Scenario(scenario_name="EGCProblem3p1p3", **args_local),
            EGCProblem5p1p1Scenario(scenario_name="EGCProblem5p1p1", **args_local),
            # DesignWithPromoterVarsScenario(scenario_name="DesignWithPromoterVars", **args_local),
            # MinimalInputSensorsScenario(scenario_name="MinimalInputSensors", **args_local),
            # GeneticToggleSwitchScenario(scenario_name="GeneticToggleSwitch", **args_local),
        ]

    all_results: Dict[str, Any] = {}
    summary_rows: List[Dict[str, Any]] = []
    failures_index: Dict[str, Dict[str, Any]] = {}

    # Optional metadata
    meta = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "models": [m.split('/')[-1] if '/' in m else m for m in models],
    }
    with open(os.path.join(run_dir, "meta.json"), "w") as mf:
        json.dump(meta, mf, indent=2)

    # ---------------- Run benchmarks ----------------
    for model in models:
        scenarios = build_scenarios(model)
        finished_scenarios = run_scenarios(scenarios=scenarios, max_rounds=args.max_rounds, num_retries=args.num_retries)

        model_results: Dict[str, Any] = {}
        for scenario in finished_scenarios:
            model_results[scenario.scenario_name] = {
                "metrics": scenario.get_metrics(),
                "messages": scenario.messages
            }

        save_model = model.split('/')[-1] if '/' in model else model
        all_results[save_model] = model_results
        all_results[save_model]['aggregated_results'] = aggregate_metrics(model_results)

        # Per-scenario artifacts into run_dir
        for scenario in finished_scenarios:
            class_name = scenario.__class__.__name__
            scen_name = scenario.scenario_name
            res = model_results[scen_name]
            metrics = res['metrics']

            with open(os.path.join(run_dir, f"{save_model}_{class_name}_metrics.json"), "w") as f:
                json.dump(metrics, f, indent=2)
            with open(os.path.join(run_dir, f"{save_model}_{class_name}_messages.json"), "w") as f:
                json.dump(res['messages'], f, indent=2)

            fr = metrics.get('failure_report')
            if fr:
                with open(os.path.join(run_dir, f"{save_model}_{class_name}_failure.json"), "w") as f:
                    json.dump(fr, f, indent=2)

                md = failure_trace_markdown(save_model, scen_name, class_name, metrics)
                trace_name = f"{sanitize_filename(save_model)}__{sanitize_filename(scen_name)}.md"
                with open(os.path.join(traces_dir, trace_name), "w") as tf:
                    tf.write(md)

            primary = (fr or {}).get("primary") or {}
            summary_rows.append({
                "model": save_model,
                "scenario": scen_name,
                "class_name": class_name,
                "status": metrics.get("status"),
                "correct": bool(metrics.get("correct")),
                "answered": bool(metrics.get("gave_answer")),
                "tool_calls": int(metrics.get("tool_calls", 0)),
                "tool_call_failures": int(metrics.get("tool_call_failures", 0)),
                "tool_call_successes": int(metrics.get("tool_call_successes", 0)),
                "primary_failure_code": primary.get("code"),
                "primary_failure_message": primary.get("message"),
                "primary_failure_at_round": primary.get("at_round"),
                "parse_warnings": metrics.get("parse_warnings"),
            })

            if fr:
                failures_index.setdefault(save_model, {})[scen_name] = {
                    "code": primary.get("code"),
                    "message": primary.get("message"),
                    "at_round": primary.get("at_round"),
                }

    # ---------------- Save run-level summaries ----------------
    with open(os.path.join(run_dir, "batch_results.json"), "w") as f:
        json.dump(all_results, f, indent=2)
    print(json.dumps(all_results, indent=2))

    with open(os.path.join(run_dir, "summary_rows.json"), "w") as f:
        json.dump(summary_rows, f, indent=2)

    if summary_rows:
        csv_path = os.path.join(run_dir, "summary_rows.csv")
        fieldnames = list(summary_rows[0].keys())
        with open(csv_path, "w", newline="") as cf:
            writer = csv.DictWriter(cf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)

    with open(os.path.join(run_dir, "_failures_summary.json"), "w") as ff:
        json.dump(failures_index, ff, indent=2)

    # ---------------- Plots into run_dir ----------------
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
    plt.tight_layout()
    plt.savefig(os.path.join(run_dir, "batch_results_aggregated.png"))

    model_results = {}
    for model_key, results in all_results.items():
        model_results[model_key] = results['aggregated_results']

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
    plt.tight_layout()
    plt.savefig(os.path.join(run_dir, "batch_results_model_comparison.png"))

    # ---------------- Root-level conveniences ----------------
    # Maintain root-level runs index
    runs_index_path = os.path.join(output_root, "runs_index.json")
    try:
        if os.path.exists(runs_index_path):
            with open(runs_index_path, "r") as rf:
                runs_index = json.load(rf)
        else:
            runs_index = []

        runs_index.append({
            "run_id": run_id,
            "timestamp": meta["timestamp"],
            "git_commit": meta["git_commit"],
            "path": os.path.relpath(run_dir, output_root),
            "models": meta["models"],
        })
        with open(runs_index_path, "w") as rf:
            json.dump(runs_index, rf, indent=2)
    except Exception as e:
        print(f"[warn] could not update runs_index.json: {e}")

    # Point 'latest' to this run (symlink or copy fallback)
    ensure_latest_symlink(output_root, run_dir)

    # Prune old runs if requested
    if args.keep_runs and args.keep_runs > 0:
        prune_old_runs(output_root, args.keep_runs)

    # Optional: print quick failure index
    if failures_index:
        print("\n=== Failures Summary ===")
        for m, scenemap in failures_index.items():
            print(f"\n[{m}]")
            for sn, v in scenemap.items():
                print(f"  - {sn}: {v.get('code')} @ round {v.get('at_round')} — {v.get('message')}")
    else:
        print("\nNo failures recorded across evaluated scenarios.")
