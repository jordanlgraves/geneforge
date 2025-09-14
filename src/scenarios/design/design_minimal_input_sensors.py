from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from src.scenarios.scenario import Scenario, FailureCode
from src.utils.answer_parsing import coerce_answer_object  # not strictly needed here, but available
# ^ kept for parity with other scenarios; we parse files here rather than tool payloads.


PROMPT = """Design with minimal input sensors:

1) Select a Cello library appropriate for the organism (or any valid library).
2) List available input sensors.
3) Create a **custom input sensors** file that contains **exactly one** sensor (your choice).
4) Run Cello on any simple verilog design (your choice) using that custom input sensors file.
5) (Optional) Report circuit performance.

Use the tools. You do **not** need to call `report_answer`. The run will be graded from tool effects."""


def _safe_json_load(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def _read_json_file(session_state, path_or_rel: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Robust file reader that looks in absolute path first, then inside the
    SessionState.output_directory (if provided).
    """
    try:
        p = Path(path_or_rel)
        if not p.exists():
            # Try relative to session output dir
            if getattr(session_state, "output_directory", None):
                p = Path(session_state.output_directory) / path_or_rel
        if not p.exists():
            return None, f"File not found: {path_or_rel}"
        data = _safe_json_load(p.read_text())
        if data is None:
            return None, f"JSON parse failed for: {str(p)}"
        return data, None
    except Exception as e:
        return None, str(e)


def _extract_sensor_names(obj: Any) -> List[str]:
    """
    Heuristic, schema-tolerant extraction of sensor names from a Cello
    "input sensors" JSON. We support several plausible layouts:

    - {"input_sensors": [ { "name": "...", ... }, ... ]}
    - {"sensors": [ { "name": "...", ... }, ... ]}
    - nested dicts/lists where any dict with a "name" and other sensor-ish
      keys appears (we look for dicts with "name" and at least one of:
      "models", "structure", "type", "family", "sensor").

    We never fail hard here; an empty list means "could not detect sensors".
    """
    names: List[str] = []

    def collect_from_list(lst: List[Any]):
        for el in lst:
            if isinstance(el, dict):
                # Common case: dicts with "name"
                nm = el.get("name")
                if isinstance(nm, str) and nm.strip():
                    names.append(nm.strip())

    def walk(node: Any):
        if isinstance(node, dict):
            # Explicit top-level keys
            if "input_sensors" in node and isinstance(node["input_sensors"], list):
                collect_from_list(node["input_sensors"])
            if "sensors" in node and isinstance(node["sensors"], list):
                collect_from_list(node["sensors"])

            # Heuristic: any dict with a "name" and sensor-ish signal
            nm = node.get("name")
            if isinstance(nm, str) and nm.strip():
                sensorish = any(k in node for k in ("models", "structure", "type", "family", "sensor"))
                if sensorish and nm.strip() not in names:
                    names.append(nm.strip())

            # Recurse
            for v in node.values():
                walk(v)

        elif isinstance(node, list):
            for v in node:
                walk(v)
        # primitives ignored

    walk(obj)
    # De-duplicate while preserving order
    dedup: List[str] = []
    for n in names:
        if n not in dedup:
            dedup.append(n)
    return dedup


class MinimalInputSensorsScenario(Scenario):
    """
    Verification focuses on:
      - A library was selected.
      - A custom input sensors file was created.
      - That custom file contains **exactly one** sensor (any valid sensor).
      - Cello was run (cello_results present & success == True).

    We do NOT require a `report_answer` tool call; grading is from tool side-effects.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prompt", PROMPT)
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        # Let the normal runner stop; we don't force tool usage here.
        return super().check_finished()

    def get_metrics(self) -> Dict[str, Any]:
        base = super().get_metrics()

        # 1) Library selection
        lib_id = getattr(self.session_state.cello_library, "current_library_id", None)
        library_selected = bool(lib_id)

        if not library_selected:
            self.record_failure(
                FailureCode.NO_TOOL_USE,
                "No library selected",
                details={"hint": "Use the select_library tool before creating a custom input sensors file."},
            )

        # 2) Custom input sensors file
        custom_input_path = getattr(self.session_state, "custom_input_path", None)
        custom_file_ok = False
        sensors_in_custom: List[str] = []
        custom_file_error: Optional[str] = None

        if not custom_input_path:
            self.record_failure(
                FailureCode.ANSWER_NOT_PROVIDED,
                "Custom input sensors file was not created",
                details={"hint": "Use create_custom_input_sensors_file(selected_sensors=[...])."},
            )
        else:
            data, err = _read_json_file(self.session_state, custom_input_path)
            if err:
                custom_file_error = err
                self.record_failure(
                    FailureCode.BAD_JSON,
                    "Could not load/parse custom input sensors JSON",
                    details={"path": custom_input_path, "error": err},
                )
            else:
                custom_file_ok = True
                sensors_in_custom = _extract_sensor_names(data)

        # 3) Enforce exactly one sensor
        exactly_one_sensor = len(sensors_in_custom) == 1
        if custom_file_ok and not exactly_one_sensor:
            self.record_failure(
                FailureCode.WRONG_ANSWER,
                "Custom input sensors file must contain exactly one sensor",
                details={"sensor_count": len(sensors_in_custom), "sensors_detected": sensors_in_custom[:10]},
            )

        # 4) Cello results
        cello_results = getattr(self.session_state, "cello_results", None)
        cello_success = bool(cello_results and cello_results.get("success"))
        cello_output_dir = cello_results.get("output_dir") if isinstance(cello_results, dict) else None

        if custom_file_ok and not cello_success:
            self.record_failure(
                FailureCode.TOOL_RUNTIME_ERROR,
                "Cello did not complete successfully",
                details={"output_dir": cello_output_dir, "results_keys": list(cello_results.keys()) if isinstance(cello_results, dict) else None},
            )

        # Overall judgement for this scenario:
        # We consider it "correct" iff:
        #   - library_selected
        #   - custom_file_ok and exactly_one_sensor
        #   - cello_success
        is_correct = library_selected and custom_file_ok and exactly_one_sensor and cello_success

        # We mark "gave_answer" True because this scenario grades by tool effects,
        # not by a `report_answer` payload.
        base.update({
            "gave_answer": True,
            "correct": is_correct,
            "library_selected": library_selected,
            "library_id": lib_id,
            "custom_input_path": custom_input_path,
            "custom_input_loaded": custom_file_ok,
            "custom_input_error": custom_file_error,
            "sensor_count": len(sensors_in_custom),
            "selected_sensor": (sensors_in_custom[0] if exactly_one_sensor else None),
            "cello_success": cello_success,
            "cello_output_dir": cello_output_dir,
            "failure_report": self.get_failure_report(),
        })

        # Keep batch-runner compatibility
        base["status"] = "success" if is_correct else "failed"
        return base


if __name__ == "__main__":
    # Lightweight smoke test (won't exercise tools here)
    s = MinimalInputSensorsScenario(scenario_name="MinimalInputSensorsScenario")
    s.run()
    print("Metrics (empty run):", s.get_metrics())
