# Simple Single-Input “Pass Gate”
When Input A is present, turn on GFP in E. coli. If Input A is absent, GFP should remain off.

# Two-Input AND Gate
Design a 2-input AND gate that expresses GFP only if both Input A (arabinose) and Input B (aTc) are present. If either input is absent, GFP must be off.

# Simple Sensor/Reporter Circuit in E. coli
Design a genetic circuit in E. coli that senses the presence of a specific small molecule (e.g., arabinose) and produces a fluorescent readout (e.g., GFP). The circuit should be plasmid-based and minimal, using commonly available parts from a standard parts library.

# NOT Gate with User-Specified Threshold (Inverting Logic)
Design a NOT gate in E. coli that turns OFF GFP expression whenever Input A is high, but expresses GFP at a measurable level otherwise. We want a low leak in the OFF state (<10% of the ON fluorescence).

# Threshold-Based Switch in E. coli
Design a circuit in E. coli that remains “off” unless the concentration of an inducer (e.g., IPTG) passes a certain threshold. Once this threshold is surpassed, the circuit should switch “on” to produce a colorimetric enzyme (e.g., LacZ for a blue-white readout). Include a feedback mechanism to sharpen the threshold response.

# Two-Layer Cascade (Sequential Logic)
Build a circuit in E. coli with an intermediate transcription factor. If Input A is present, then produce a repressor X, which in turn should repress GFP unless Input B is also present to inactivate that repressor. In effect, the output should be ON only if A=1 and B=1. Use at least two transcriptional layers.

# Multi-Input Logic Gate in E. coli
Develop a multi-input logic gate in E. coli that only expresses a fluorescent protein when two different chemical signals (e.g., arabinose and IPTG) are both present. Propose how to arrange promoters, transcription factors, and regulatory elements to achieve an AND logic.

# Oscillatory Circuit (Repressilator) in E. coli
Design an oscillatory genetic circuit (e.g., a repressilator) in E. coli with a period of approximately 3 hours. Identify key transcriptional repressors or other regulatory parts, and propose a design that would yield stable oscillations.

# Time-Delay Circuit (Feed-Forward Loop or Decay-Based Delay)
Construct a circuit that, when Input A (arabinose) is turned on at time 0, waits ~30 minutes before expressing GFP. If the input is turned off before 30 minutes, GFP should not appear.

# Toggle Switch (Bistable Memory Element)
Design a toggle switch in E. coli using two mutually repressing genes. The circuit has two stable states: one that expresses GFP, another that expresses RFP. A brief input pulse should flip the circuit from RFP to GFP, and another input pulse should flip it back.

# Circuit to Optimize Recombinant Protein Production
Create a genetic design that maximizes the yield of recombinant protein X in E. coli. Provide one design that balances metabolic load (to maintain cell viability) and production rate, and another that disregards metabolic burden but aims for the highest possible yield.

# RNA-Seq-Driven Target Expression Shift (E. coli → Mammalian “Bridge”)
Given an RNA-seq profile indicating low expression of a desired metabolic gene, design a genetic circuit that compensates by overexpressing this gene in E. coli. As a second phase, propose how you would adapt the circuit for mammalian cells. Specify which regulatory elements and promoters might be changed, and how you would ensure stable expression in a mammalian system.

# Multi-Output Logic
Create a circuit with two fluorescent outputs in E. coli. Output1 (RFP) should be ON if A or B is present. Output2 (GFP) should be ON only if both A and B are present.

# Synthetic CRISPR Control in E. coli
Design a CRISPR-based circuit in E. coli that uses a dCas9 (dead Cas9) system to repress or activate specific endogenous genes. The goal is to regulate multiple genes simultaneously for enhanced bio-production of a target small molecule (e.g., a precursor for a pharmaceutical).

#  Programmed Cell Death in Mammalian Cells
Propose a mammalian synthetic circuit that selectively induces apoptosis in cells exhibiting a specific cancer-related marker (e.g., expression of a known oncogene). The circuit should remain inert in healthy cells but trigger a kill switch once a threshold of the oncogene is detected. Outline the regulatory elements, detection mechanism, and safety safeguards (e.g., additional kill switch if misfired).

# Cellular Rejuvenation Circuit
Design a genetic circuit in mammalian cells to transiently express Yamanaka factors (or similar reprogramming genes) under tight temporal control, aiming to push cells toward a more youthful state without permanently converting them to pluripotent stem cells. Propose how you would integrate external control signals (e.g., a small molecule or temperature shift) to turn the circuit off after partial reprogramming is achieved.

# Multi-Omics Optimization for Product Synthesis
Take in transcriptomic and proteomic data for a mammalian cell line to identify bottlenecks in a specific biosynthetic pathway (e.g., production of a therapeutic monoclonal antibody). Design a synthetic circuit that upregulates or downregulates target genes to optimize yield, while minimizing toxic byproducts. Summarize how the AI arrives at the final design using a knowledge graph and parts library.

