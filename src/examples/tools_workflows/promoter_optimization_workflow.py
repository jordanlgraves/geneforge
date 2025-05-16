import os
import copy
from pathlib import Path
import logging

from src.tools.cello_integration import CelloIntegration
from src.tools.promoter_calculator_integration import PromoterCalculatorIntegration
from src.library.part_library_customizer import filter_parts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("promoter_opt_workflow")


def run_workflow(
    library_id: str = "Eco1C1G1T1",
    verilog_code: str | None = None,
    promoter_gain: float = 1.25,
    n_iterations: int = 200,
):
    """Full optimisation round-trip.

    1. Compile initial design with Cello.
    2. Parse part-usage to find the promoter actually placed.
    3. Mutate that promoter to achieve ~promoter_gain× Tx_rate.
    4. Write a **minimal** custom UCF that keeps only the chosen promoter (and
       dependencies) and patches its DNA + model ymax.
    5. Re-compile and report the score improvement.
    """

    # ---------------------------------------------------------------------
    # 0. Boiler-plate
    # ---------------------------------------------------------------------
    if verilog_code is None:
        verilog_code = """module main(input a, output y); assign y = ~a; endmodule"""

    cello = CelloIntegration(library_id=library_id)
    lm = cello.library_manager  # convenience handle

    # ---------------------------------------------------------------------
    # 1.  Initial compile
    # ---------------------------------------------------------------------
    res1 = cello.run_cello(run_name="round1", verilog_code=verilog_code)
    if not res1["success"]:
        raise RuntimeError("Initial Cello run failed: " + res1.get("error", "unknown"))

    out_dir1 = Path(res1["results"]["output_path"])
    metrics1 = cello.evaluate_circuit_performance(out_dir1.as_posix())
    score1 = metrics1.get("overall_score", 0.0)
    promoters_used = metrics1.get("part_usage", {}).get("promoters", [])
    if not promoters_used:
        raise RuntimeError("Cello did not report any promoter in part usage list.")

    # Choose the first promoter that actually exists in the UCF `parts` collection
    ucf_promoter_ids = {item["name"] for item in lm.get_ucf_data() if item.get("collection") == "parts"}
    promoter_id = next((p for p in promoters_used if p in ucf_promoter_ids), None)
    if promoter_id is None:
        raise RuntimeError("None of the promoters used by Cello are present in the UCF parts list.")

    logger.info("Cello placed promoter %s (validated in UCF)", promoter_id)

    # ---------------------------------------------------------------------
    # 2.  Fetch promoter DNA + optimise
    # ---------------------------------------------------------------------
    ucf_data = lm.get_ucf_data()
    input_sensors_data = lm.get_input_sensor_data()
    promoter_part = next(
        item for item in ucf_data if item.get("collection") == "parts" and item.get("name") == promoter_id
    )
    seq_old = promoter_part["dnasequence"]

    pc = PromoterCalculatorIntegration()
    opt = pc.optimize_promoter(seq_old, iterations=n_iterations)
    seq_new = opt["optimized_sequence"]
    tx_new = opt["optimized_strength"]
    logger.info("Promoter strength improved from %.2f to %.2f", opt["original_strength"], tx_new)

    # ---------------------------------------------------------------------
    # 3.  Build modified parts & minimal UCF
    # ---------------------------------------------------------------------
    # 3a. patch promoter DNA
    prom_mod = copy.deepcopy(promoter_part)
    prom_mod["dnasequence"] = seq_new

    # 3b. find dependent models & patch ymax
    deps_ucf = filter_parts(ucf_data, [promoter_part])
    model_mods = []
    for item in deps_ucf:
        if item.get("collection") == "models":
            # copy & patch parameters
            model_cpy = copy.deepcopy(item)
            for param in model_cpy.get("parameters", []):
                if param.get("name") == "ymax":
                    param["value"] = tx_new
            model_mods.append(model_cpy)

    modified_parts = [prom_mod] + model_mods

    # create custom UCF (library_manager handles dependency filtering)
    new_ucf_path = lm.create_custom_ucf(
        selected_parts=[promoter_id],
        modified_parts=modified_parts,
        ucf_name="custom_opt_promoter.UCF.json",
    )
    logger.info("Wrote custom UCF → %s", new_ucf_path)

    # ---------------------------------------------------------------------
    # 4.  Re-compile with patched UCF
    # ---------------------------------------------------------------------
    res2 = cello.run_cello(run_name="round2", verilog_code=verilog_code)
    if not res2["success"]:
        raise RuntimeError("Second Cello run failed: " + res2.get("error", "unknown"))

    out_dir2 = Path(res2["results"]["output_path"]).parent
    metrics2 = cello.evaluate_circuit_performance(out_dir2.as_posix())
    score2 = metrics2.get("overall_score", 0.0)

    # ---------------------------------------------------------------------
    # 5.  Report
    # ---------------------------------------------------------------------
    print("Initial score :", score1)
    print("Optimised score:", score2)
    print("Δscore        :", score2 - score1)


if __name__ == "__main__":
    run_workflow()
