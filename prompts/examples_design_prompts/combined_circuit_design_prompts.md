**Test 1: Single-Input Pass Gate**
**Goal**  
Test the absolute basics: converting the arabinose input via a pBAD promoter into a GFP output in *E. coli*.

"When 0.2% arabinose is present, the pBAD promoter drives GFP expression in *E. coli*. If arabinose is absent, GFP remains off."

**What this tests:**
- Basic sensor output  
- Ability to select appropriate library (*E. coli*)
- Ability to select specific part (pBAD promoter) from library  
- Ability to search part database for inducible promoters and reporters  
- End-to-end pipeline validation (LLM → Cello → simulation)

**Verifiable output:**
- truth_table.csv (Cello output)
- other cello output files
---

**Test 2: Two-Input AND Gate**
**Goal**  
Implement multi-input logic: express GFP only when both arabinose (A) and aTc (B) are present.

"GFP = A AND B in *E. coli*. If either input is missing, GFP must be off."

**What this tests:**
- Complex logic design (combinatorial gating)  
- Correct input sensors uses (aTc/arabinose)
- Integration of multiple regulatory elements (promoters, repressors)  


**Verifiable output:**
- truth_table.csv  
- circuit_score.txt

---

**Test 3: Feedback-Enhanced Threshold Switch**
**Goal**  
Design a threshold-based switch in *E. coli* with positive feedback to sharpen the response, minimizing leakage.

"GFP remains off until IPTG exceeds threshold T, then switches on sharply, with <10% leakage in the off state."

**What this tests:**
- Nonlinear response design (ultrasensitivity)  
- Incorporation of feedback loops (positive feedback)  
- Quantitative performance constraints (leakage <10% of ON)

**Verifiable output:**
- circuit_score.txt (response curve and leakage metrics)

