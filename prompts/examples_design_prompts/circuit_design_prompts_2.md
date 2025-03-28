# Circuit Design Prompts

## 1. Simple Sensor/Reporter Circuit in E. coli

**Prompt:**

Design a genetic circuit in E. coli that senses the presence of a specific small molecule (e.g., arabinose) and produces a fluorescent readout (e.g., GFP). The circuit should be plasmid-based and minimal, using commonly available parts from a standard parts library.

**What this tests:**

- Basic sensor output.
- Ability of your AI system to search part databases for known inducible promoters and reporters.
- Familiarization with standard molecular cloning techniques.

## 2. Threshold-Based Switch in E. coli

**Prompt:**

Design a circuit in E. coli that remains "off" unless the concentration of an inducer (e.g., IPTG) passes a certain threshold. Once this threshold is surpassed, the circuit should switch "on" to produce a colorimetric enzyme (e.g., LacZ for a blue-white readout). Include a feedback mechanism to sharpen the threshold response.

**What this tests:**

- Nonlinear response design (cooperative or ultrasensitive responses).
- Incorporation of feedback loops (positive or negative feedback).
- Parameter optimization (promoter strength, ribosome binding site strength, plasmid copy number).

## 3. Multi-Input Logic Gate in E. coli

**Prompt:**

Develop a multi-input logic gate in E. coli that only expresses a fluorescent protein when two different chemical signals (e.g., arabinose and IPTG) are both present. Propose how to arrange promoters, transcription factors, and regulatory elements to achieve an AND logic.

**What this tests:**

- Skills in designing more complex genetic circuits (logic gate behavior).
- Ability of the AI agent to integrate multiple regulatory elements.
- Handling of combinatorial permutations of part usage and arrangement.

## 4. Oscillatory Circuit (Repressilator) in E. coli

**Prompt:**

Design an oscillatory genetic circuit (e.g., a repressilator) in E. coli with a period of approximately 3 hours. Identify key transcriptional repressors or other regulatory parts, and propose a design that would yield stable oscillations.

**What this tests:**

- Dynamic circuit design (tuning parameters for oscillations).
- The ability to model gene expression delays, degradation rates, and other kinetic factors.
- Potential integration of computational modeling within the design loop.

## 5. Circuit to Optimize Recombinant Protein Production

**Prompt:**

Create a genetic design that maximizes the yield of recombinant protein X in E. coli. Provide one design that balances metabolic load (to maintain cell viability) and production rate, and another that disregards metabolic burden but aims for the highest possible yield.

**What this tests:**

- Trade-off management between growth rate and protein production.
- Use of dynamic promoters or tunable expression systems.
- Potential incorporation of feedback to maintain or boost cell health during production.

## 6. RNA-Seq-Driven Target Expression Shift (E. coli → Mammalian "Bridge")

**Prompt:**

Given an RNA-seq profile indicating low expression of a desired metabolic gene, design a genetic circuit that compensates by overexpressing this gene in E. coli. As a second phase, propose how you would adapt the circuit for mammalian cells. Specify which regulatory elements and promoters might be changed, and how you would ensure stable expression in a mammalian system.

**What this tests:**

- The AI's capacity to interpret omics data (RNA-seq).
- Translational strategy from prokaryotic to eukaryotic expression systems.
- Use of species-specific regulatory elements (bacterial vs. mammalian promoters, terminators, enhancers, etc.).

## 7. Synthetic CRISPR Control in E. coli

**Prompt:**

Design a CRISPR-based circuit in E. coli that uses a dCas9 (dead Cas9) system to repress or activate specific endogenous genes. The goal is to regulate multiple genes simultaneously for enhanced bio-production of a target small molecule (e.g., a precursor for a pharmaceutical).

**What this tests:**

- Incorporating CRISPR/dCas9 modules for transcriptional regulation.
- Target selection based on knowledge of E. coli metabolic pathways.
- Multi-gene modulation strategies (parallel or sequential targeting).

## 8. Programmed Cell Death in Mammalian Cells

**Prompt:**

Propose a mammalian synthetic circuit that selectively induces apoptosis in cells exhibiting a specific cancer-related marker (e.g., expression of a known oncogene). The circuit should remain inert in healthy cells but trigger a kill switch once a threshold of the oncogene is detected. Outline the regulatory elements, detection mechanism, and safety safeguards (e.g., additional kill switch if misfired).

**What this tests:**

- Knowledge of mammalian gene regulation, including promoters responsive to cancer-specific transcription factors.
- Safety and regulatory considerations (failsafes).
- Potential for layering multiple detection steps (AND gate logic, threshold detection).

## 9. Cellular Rejuvenation Circuit

**Prompt:**

Design a genetic circuit in mammalian cells to transiently express Yamanaka factors (or similar reprogramming genes) under tight temporal control, aiming to push cells toward a more youthful state without permanently converting them to pluripotent stem cells. Propose how you would integrate external control signals (e.g., a small molecule or temperature shift) to turn the circuit off after partial reprogramming is achieved.

**What this tests:**

- Complex eukaryotic gene regulation (inducible systems, tight spatiotemporal control).
- Balancing partial vs. full reprogramming (avoiding tumorigenicity).
- Conditional or transient expression strategies.

## 10. Multi-Omics Optimization for Product Synthesis

**Prompt:**

Take in transcriptomic and proteomic data for a mammalian cell line to identify bottlenecks in a specific biosynthetic pathway (e.g., production of a therapeutic monoclonal antibody). Design a synthetic circuit that upregulates or downregulates target genes to optimize yield, while minimizing toxic byproducts. Summarize how the AI arrives at the final design using a knowledge graph and parts library.

**What this tests:**

- Ability to handle multi-omics data integration (transcriptomics, proteomics, metabolomics).
- Systems-level approach to metabolic engineering.
- Knowledge graph-driven part selection and design rationale.
