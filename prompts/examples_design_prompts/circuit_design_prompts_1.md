# Circuit Design Prompts

## 1. Simple Single-Input "Pass Gate"

**Goal**  
Test the absolute basics: converting a single input signal into a single output reporter (e.g., GFP) in *E. coli*.

**Specification (Natural Language Example)**  
"When Input A is present, turn on GFP in *E. coli*. If Input A is absent, GFP should remain off."

**Logic Representation**  
Output = A

**Key Points**  
- **LLM Parsing**: Very straightforward prompt → single Boolean expression (GFP = A).
- **Cello**: Assigns an inducible promoter responsive to Input A (e.g., pTet for aTc or pBAD for arabinose) to drive GFP.
- **iBioSim Simulation**: Verify that with Input A = 1, GFP is high; with Input A = 0, GFP is ~0.
- **RL Optimization (Optional here)**: Likely trivial—there's minimal space to optimize, but you can confirm the RL loop runs.

This circuit ensures each pipeline component is functioning at the simplest possible level.

## 2. Two-Input AND Gate

**Goal**  
Demonstrate classic combinational logic in *E. coli* with two distinct inducers (e.g., arabinose & aTc).

**Specification (Natural Language Example)**  
"Design a 2-input AND gate that expresses GFP only if both Input A (arabinose) and Input B (aTc) are present. If either input is absent, GFP must be off."

**Logic Representation**  
GFP = A AND B

**Truth table:**

| A | B | GFP |
|---|---|-----|
| 0 | 0 | 0   |
| 0 | 1 | 0   |
| 1 | 0 | 0   |
| 1 | 1 | 1   |

**Key Points**  
- **LLM Parsing**: Should produce a formal logic expression (Verilog or truth table).
- **Cello**: Finds or assembles a circuit (e.g., cascaded repressors) to implement AND using pBAD, pTet, repressor genes, and GFP.
- **iBioSim**: Simulate all four input combinations, confirm the correct ON/OFF pattern for GFP.
- **RL Optimization**: Potentially needed if the initial design shows leaky expression (e.g., GFP partially ON in undesired states). The RL agent can try swapping different promoters or adjusting RBS strengths for better performance.

This scenario demonstrates multi-input logic and ensures the pipeline handles combinational gating.

## 3. NOT Gate with User-Specified Threshold (Inverting Logic)

**Goal**  
Show the system can implement inversion and also quantitative specifications (e.g., "strong OFF, moderate ON").

**Specification (Natural Language Example)**  
"Design a NOT gate in *E. coli* that turns OFF GFP expression whenever Input A is high, but expresses GFP at a measurable level otherwise. We want a low leak in the OFF state (<10% of the ON fluorescence).

**Logic Representation**  
GFP = NOT(A)

**Additional Quantitative Target**  
OFF leakage < 10% of ON level (when A=0).

**Key Points**  
- **LLM Parsing**: Must recognize the user wants an inverter, plus a quantitative performance requirement.
- **Cello**: Generate a circuit using a repressor under the control of input A, repressing GFP. Possibly pTet -> repressor -> pX -> GFP.
- **iBioSim**: Perform quantitative simulation to measure GFP levels at A=0 vs. A=1, ensuring OFF < 10% of ON.
- **RL Optimization**: If the circuit's initial OFF leakage is 20%, RL can swap out repressor/promoter variants or tweak RBS strengths to reduce leakage below 10%.

This example tests analog performance goals (low leakage) rather than just a strict logic table.

## 4. Two-Layer Cascade (Sequential Logic)

**Goal**  
Demonstrate that the system can handle multi-layer regulatory cascades—e.g., an input controlling an intermediate regulator, which then controls the final output.

**Specification (Natural Language Example)**  
"Build a circuit in *E. coli* with an intermediate transcription factor. If Input A is present, then produce a repressor X, which in turn should repress GFP unless Input B is also present to inactivate that repressor. In effect, the output should be ON only if A=1 and B=1. Use at least two transcriptional layers."

**Logic Representation**  
This is effectively an AND, but specifically requests a two-layer design. For instance: pBAD -> repressorX and pTet -> GFP, with interplay where repressorX is inactivated by aTc.

**Key Points**  
- **LLM Parsing**: Must interpret "two-layer cascade" or "multi-step regulation" as a design constraint.
- **Cello**: Instead of building a single-step AND gate, it must generate a 2-step arrangement.
- **iBioSim**: Simulate the stepwise expression. Possibly observe a delay as repressor X accumulates or is inactivated.
- **RL Optimization**: If the user wants minimal delay or minimal basal expression, the RL agent can pick from alternative repressor families or promoter strengths.

This validates that the pipeline can handle layered logic (not purely direct connections from input to output).

## 5. Time-Delay Circuit (Feed-Forward Loop or Decay-Based Delay)

**Goal**  
Demonstrate the system's ability to handle dynamic (temporal) specifications. For instance, GFP should only appear after some time delay once an input is applied.

**Specification (Natural Language Example)**  
"Construct a circuit that, when Input A (arabinose) is turned on at time 0, waits ~30 minutes before expressing GFP. If the input is turned off before 30 minutes, GFP should not appear."

**Desired Behavior**  
GFP remains OFF for about 30 minutes after input is applied, then transitions to ON.

**Possible Implementations**  
- A feed-forward loop that has a direct path activating GFP and an indirect path that temporarily represses it until a certain concentration threshold is reached.
- A decay-based delay where a key repressor is constitutively present, and Input A halts production of that repressor, leading to a slow decrease in repressor concentration before GFP can turn ON.

**Key Points**  
- **LLM Parsing**: Must recognize "time delay" and produce a design requirement that iBioSim can evaluate over a time course (not just final states).
- **Cello or Manual**: Cello is typically digital, but can produce a multi-layer design. If needed, a partial manual design with stored param values can still be used to test iBioSim.
- **iBioSim**: Must run dynamic simulations (time-series) to confirm the delay.
- **RL Optimization**: If the user wants exactly ~30 minutes of delay, RL might tune promoter strengths or repressor half-lives to dial in the desired kinetics.

This tests temporal logic and simulates how well the pipeline handles dynamic conditions.

## 6. Toggle Switch (Bistable Memory Element)

**Goal**  
Explore a classic bistable circuit that can store state, demonstrating that the system can tackle design specs beyond simple gating or linear time-delay.

**Specification (Natural Language Example)**  
"Design a toggle switch in *E. coli* using two mutually repressing genes. The circuit has two stable states: one that expresses GFP, another that expresses RFP. A brief input pulse should flip the circuit from RFP to GFP, and another input pulse should flip it back."

**Desired Behavior**  
Two stable states:
- State 1: GFP = High, RFP = Low
- State 2: GFP = Low, RFP = High

A short induction (e.g., IPTG or aTc) pushes the circuit from one state to the other.

**Key Points**  
- **LLM Parsing**: Must parse a more complex description of stable states, flipping, etc.
- **Cello**: In principle, can design a mutual repressor circuit. Might require specifying that the user wants two outputs (GFP, RFP) with mutual negative regulation.
- **iBioSim**: Evaluate the stability of the two states and confirm that each input pulse toggles the system. Possibly run a time-series simulation with transient pulses of inducer.
- **RL Optimization**: Might tune repressor strengths or promoter leakiness to ensure distinct stable states and reduce spontaneous switching.

This tests bistability and memory behavior, pushing beyond purely combinational logic.

## 7. (Optional Stretch) Multi-Output Logic

**Goal**  
Demonstrate a scenario where the circuit produces two outputs with different logic or timing rules. For example, "Output1 is an OR gate of A,B; Output2 is an AND gate of A,B."

**Specification (Natural Language Example)**  
"Create a circuit with two fluorescent outputs in *E. coli*. Output1 (RFP) should be ON if A or B is present. Output2 (GFP) should be ON only if both A and B are present."

**Logic Representation**  
- RFP = A OR B
- GFP = A AND B

**Key Points**  
- **LLM Parsing**: Must recognize two separate outputs with different logic.
- **Cello**: Attempt to build a 2-output circuit within the constraints of the chosen part library.
- **iBioSim**: Verify the combined truth table across all input combinations.
- **RL Optimization**: Possibly optimize to minimize crosstalk or avoid fluorescent bleed-through.

This final scenario ensures the pipeline can handle multiple outputs simultaneously, which is common in more elaborate genetic programs.

## Summary of the Example Circuits

| Circuit | Complexity | Key Testing Aspect |
|---------|------------|---------------------|
| 1. Single-Input Pass Gate | Very Low | Basic pipeline validation (LLM → Cello → iBioSim). |
| 2. Two-Input AND Gate | Low-Med | Classic combinational logic, tests multi-input design. |
| 3. NOT Gate + Quantitative Leakage Spec | Med | Introduces performance constraints (OFF < 10% of ON). |
| 4. Two-Layer Cascade | Med-High | Layered logic, tests multi-step regulation. |
| 5. Time-Delay Circuit | High (temporal) | Demonstrates dynamic (time-series) specs. |
| 6. Toggle Switch (Bistability) | High (nonlinear) | Tests memory behavior & stability analysis. |
| 7. Multi-Output Logic (Optional Stretch) | High (multi-output) | Tests parallel logic for two different outputs. |

Circuits 1–2 are the minimal baseline: they confirm that the LLM can parse straightforward specs, that Cello can produce working designs, and that iBioSim can simulate simple truth tables. Circuits 3–4 add slightly more complexity: leakage constraints (quantitative specs) and multi-layer gating. Circuits 5–6 bring in dynamic or nonlinear behavior: time delays and toggle switches. This ensures the pipeline can handle advanced design tasks. Circuit 7 is a multi-output scenario—useful for a more complex test if time allows.