import os
import sys
import time
import threading
import importlib
import inspect
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Type
from dotenv import load_dotenv
import streamlit as st
from src.scenarios.scenario import Scenario

load_dotenv()
# Ensure the project root is on the PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

@dataclass
class ScenarioSpec:
    module: str
    class_name: str
    name: str


def discover_scenarios(package: str) -> List[ScenarioSpec]:
    """Discover Scenario subclasses in a given package (e.g., 'src.scenarios.intro_to_sys_eng').
    Only modules directly inside the package are considered; subpackages like 'no_solutions' or 'to_review'
    are ignored by default.
    """
    specs: List[ScenarioSpec] = []

    pkg = importlib.import_module(package)
    # Files in the same directory as the package module
    pkg_dir = os.path.dirname(pkg.__file__)  # type: ignore[attr-defined]

    for filename in os.listdir(pkg_dir):
        if not filename.endswith(".py"):
            continue
        if filename.startswith("_"):
            continue
        module_name = filename[:-3]
        full_module = f"{package}.{module_name}"
        try:
            mod = importlib.import_module(full_module)
        except Exception:
            continue

        # Find first class that subclasses Scenario
        scenario_class: Optional[Type[Scenario]] = None
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, Scenario) and obj is not Scenario:
                scenario_class = obj
                break
        if scenario_class is None:
            continue

        specs.append(ScenarioSpec(full_module, scenario_class.__name__, scenario_class.__name__))

    return specs


def load_scenario(spec: ScenarioSpec, *, model: str | None) -> Scenario:
    mod = importlib.import_module(spec.module)
    cls = getattr(mod, spec.class_name)
    prompt = getattr(mod, "PROMPT", None)
    scenario = cls(
        scenario_name=spec.name,
        prompt=prompt,
        model_name=model,
    )
    return scenario



def _format_message_line(msg: Dict[str, Any]) -> str:
    role = msg.get("role")
    content = msg.get("content", "")
    if role == "assistant" and msg.get("tool_calls"):
        # Summarize tool calls
        calls = []
        for tc in msg["tool_calls"]:
            fn = tc.get("function", {}).get("name", "")
            args = tc.get("function", {}).get("arguments", "")
            calls.append(f"{fn}({args})")
        return f"assistant: [tool_calls] " + "; ".join(calls)
    return f"{role}: {content}"


class RunRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}

    def ensure(self, model: str) -> None:
        with self._lock:
            if model not in self._runs:
                self._runs[model] = {"status": "idle", "log": [], "events": [], "current": None, "thread": None}

    def set_status(self, model: str, status: str) -> None:
        with self._lock:
            self._runs[model]["status"] = status

    def set_current(self, model: str, current: str | None) -> None:
        with self._lock:
            self._runs[model]["current"] = current

    def append_log(self, model: str, line: str) -> None:
        with self._lock:
            self._runs[model]["log"].append(line)

    def clear_log(self, model: str) -> None:
        with self._lock:
            self._runs[model]["log"] = []
            self._runs[model]["events"] = []

    def append_event(self, model: str, event: Dict[str, Any]) -> None:
        with self._lock:
            self._runs[model]["events"].append(event)

    def set_thread(self, model: str, th: threading.Thread | None) -> None:
        with self._lock:
            self._runs[model]["thread"] = th

    def snapshot(self, models: List[str]) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            snap: Dict[str, Dict[str, Any]] = {}
            for m in models:
                run = self._runs.get(m, {"status": "idle", "log": [], "events": [], "current": None, "thread": None})
                snap[m] = {
                    "status": run.get("status"),
                    "current": run.get("current"),
                    "log": list(run.get("log", [])),
                    "events": list(run.get("events", [])),
                    "thread": run.get("thread"),
                }
            return snap


@st.cache_resource
def get_registry() -> RunRegistry:
    return RunRegistry()


def _worker(model: str, scenario_specs, run_cfg):
    reg = get_registry()
    reg.set_status(model, "running")
    reg.clear_log(model)
    reg.set_current(model, None)

    for spec in scenario_specs:
        # Build scenario for this model
        scenario = load_scenario(spec, model=model)
        reg.set_current(model, spec.name)
        reg.append_log(model, f"\n- \"{spec.name}\"")
        reg.append_event(model, {"type": "header", "label": spec.name})

        # Run scenario in a thread, poll messages for streaming UI
        finished_flag = {"done": False}

        def _run():
            try:
                scenario.run(max_rounds=run_cfg.get("max_rounds", 15), num_retries=run_cfg.get("num_retries", 1))
            finally:
                finished_flag["done"] = True

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        last_idx = 0
        while not finished_flag["done"]:
            # stream newly added messages
            # skip the system message
            msgs = list(scenario.messages)
            if last_idx < len(msgs):
                new_msgs = msgs[last_idx:]
                for m in new_msgs:
                    if m["role"] == "system":  # skip the system message
                        continue
                    # Record rich event
                    if m.get("role") == "assistant" and m.get("tool_calls"):
                        if m.get("content"):
                            reg.append_event(model, {"role": "assistant", "content": m.get("content", "")})
                        for tc in m.get("tool_calls", []):
                            reg.append_event(model, {
                                "role": "assistant_tool_call",
                                "function": tc.get("function", {}).get("name", ""),
                                "arguments": tc.get("function", {}).get("arguments", ""),
                            })
                    elif m.get("role") == "tool":
                        reg.append_event(model, {"role": "tool", "name": m.get("name"), "content": m.get("content", "")})
                    else:
                        reg.append_event(model, {"role": m.get("role"), "content": m.get("content", "")})

                    # Keep simple log as well
                    reg.append_log(model, "- " + _format_message_line(m))
                last_idx = len(msgs)
            time.sleep(0.2)

        # catch any final messages after completion
        msgs = list(scenario.messages)
        if last_idx < len(msgs):
            new_msgs = msgs[last_idx:]
            for m in new_msgs:
                if m["role"] == "system":
                    continue
                if m.get("role") == "assistant" and m.get("tool_calls"):
                    if m.get("content"):
                        reg.append_event(model, {"role": "assistant", "content": m.get("content", "")})
                    for tc in m.get("tool_calls", []):
                        reg.append_event(model, {
                            "role": "assistant_tool_call",
                            "function": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", ""),
                        })
                elif m.get("role") == "tool":
                    reg.append_event(model, {"role": "tool", "name": m.get("name"), "content": m.get("content", "")})
                else:
                    reg.append_event(model, {"role": m.get("role"), "content": m.get("content", "")})

                reg.append_log(model, "- " + _format_message_line(m))

        reg.append_log(model, f'- {{"FINISHED {spec.name}"}}')
        reg.append_log(model, f'- {{"METRICS: {scenario.get_metrics()}"}}')
        reg.append_log(model, f'--------------------------------')
        reg.append_event(model, {"type": "finished", "metrics": scenario.get_metrics()})

    reg.set_status(model, "finished")
    reg.set_current(model, None)


def _ensure_model_state(model: str) -> None:
    get_registry().ensure(model)


def main():
    st.set_page_config(page_title="Multi-Model Scenario Runner", layout="wide")
    st.title("Multi-Model Scenario Runner")

    # Model selection
    st.caption("Enter comma-separated model names. Examples: gpt-4o, gemini-pro, deepseek-reasoner")
    default_models = "gemini/gemini-1.5-pro, gemini/gemini-2.5-flash, gpt-4o-mini, gpt-5-nano-2025-08-07"
    models_csv = st.text_input("Models", value=default_models)
    models = [m.strip() for m in models_csv.split(",") if m.strip()]

    # Scenario package
    pkg = st.text_input("Scenario package", value="src.scenarios.intro_to_sys_eng")
    discovered = discover_scenarios(pkg)
    options = [s.class_name for s in discovered]
    selected = st.multiselect("Scenarios", options=options, default=options)
    scenario_specs = [s for s in discovered if s.class_name in set(selected)]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        max_rounds = st.number_input("Max rounds", min_value=1, max_value=50, value=15)
    with col_b:
        num_retries = st.number_input("Num retries", min_value=0, max_value=5, value=1)
    with col_c:
        reasoning = st.checkbox("Use reasoning defaults", value=True)

    # Controls
    run_cfg = {"max_rounds": int(max_rounds), "num_retries": int(num_retries), "reasoning": reasoning}
    auto_refresh = st.checkbox("Auto-refresh", value=True, help="Refresh the dashboard periodically while runs are active")
    if st.button("Start All", type="primary"):
        reg = get_registry()
        for model in models:
            reg.ensure(model)
            snap = reg.snapshot([model])[model]
            if snap["status"] in ("idle", "finished"):
                reg.clear_log(model)
                th = threading.Thread(target=_worker, args=(model, scenario_specs, run_cfg), daemon=True)
                reg.set_thread(model, th)
                th.start()

    # Grid rendering – one column per model
    if not models:
        st.info("Add at least one model to begin.")
        return

    cols = st.columns(len(models))
    reg = get_registry()
    snapshot = reg.snapshot(models)
    for i, model in enumerate(models):
        run = snapshot.get(model, {"status": "idle", "log": [], "events": [], "current": None})
        with cols[i]:
            st.subheader(model)
            status = run["status"]
            current = run["current"]
            st.caption(f"Status: {status}" + (f" – Running: {current}" if current else ""))

            events = run.get("events", [])
            if not events:
                st.caption("No output yet.")
            else:
                for ev in events:
                    etype = ev.get("type")
                    if etype == "header":
                        st.markdown(f"**\"{ev.get('label','')}\"**")
                        continue
                    if etype == "finished":
                        st.success("FINISHED")
                        st.json(ev.get("metrics", {}))
                        st.markdown("---")
                        continue

                    role = ev.get("role")
                    if role == "user":
                        with st.chat_message("user"):
                            st.markdown(ev.get("content", ""))
                    elif role == "assistant":
                        with st.chat_message("assistant"):
                            st.markdown(ev.get("content", ""))
                    elif role == "assistant_tool_call":
                        with st.expander(f"🛠️ Tool Call: {ev.get('function','')}", expanded=False):
                            args = ev.get("arguments", "")
                            st.code(args, language="json")
                    elif role == "tool":
                        with st.expander(f"📤 Tool Response: {ev.get('name') or 'tool'}", expanded=False):
                            payload = ev.get("content", "")
                            try:
                                import json as _json
                                st.json(_json.loads(payload))
                            except Exception:
                                st.code(payload, language="json")

    # Lightweight auto-refresh while anything is running
    if auto_refresh and any(snapshot.get(m, {}).get("status") == "running" for m in models):
        time.sleep(0.5)
        st.rerun()


if __name__ == "__main__":
    main()


