# numpy==2.2.4
# scipy==1.15.2
# sympy==1.13.3
# pandas==2.2.3
# rapidfuzz==3.10.1
# scikit-learn==1.6.1
# rouge-score==0.1.2
# deepdiff==8.4.2
# jsonschema==4.23.0
# pydantic==2.10.6
# pyyaml==6.0.2``
# nltk==3.9.1
# sqlparse==0.5.3
# rdkit==2024.9.6
# scikit-bio==0.6.3
# ast-grep-py==0.36.2
from typing import Any
import json
import pandas as pd
import io

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
        "reference_answer": "...",
        "my_key": {...}
    }
    """
    
    output_json = sample.get('output_json', {})
    output_tools = sample.get('output_tools', [])
    output_text = sample.get('output_text', '')
    choices = sample.get('choices', [])
    content = choices[0].get('message', dict()).get('content', '')
    
    messages = [c.get('message', dict()) for c in choices]
    
    # The different criteria that are scored and the points for each
    HAS_3_UNIQUE_PROMOTERS, POINTS_FOR_3_UNIQUE_PROMOTERS = False, 5
    HAS_3_NEW_PROMOTERS, POINTS_FOR_3_NEW_PROMOTERS = False, 5
    HAS_3_NEW_PROMOTER_SEQUENCES, POINTS_FOR_3_NEW_PROMOTER_SEQUENCES = False, 5
    HAS_CORRECT_ORDER, POINTS_FOR_CORRECT_ORDER = False, 2
    NUM_TOOL_FAILURES, POINTS_FOR_NO_TOOL_FAILURES = 0, 2
    HAS_CORRECT_TRUTH_TABLE, POINTS_FOR_CORRECT_TRUTH_TABLE = False, 5
    
    original_promoters_names = [s.lower() for s in ['pAmtR', 'pBM3R1', 'pBetI', 'pAmeR', 'pHlyIIR', 'pIcaRA', 'pLitR', 'pLmrA', 'pPhlF', 'pQacR', 'pPsrA', 'pSrpR']]
    original_promoters_sequences = [s.lower() for s in ['CTTGTCCAACCAAATGATTCGTTACCAATTGACAGTTTCTATCGATCTATAGATAATGCTAGC', 'AATCCGCGTGATAGGTCTGATTCGTTACCAATTGACGGAATGAACGTTCATTCCGATAATGCTAGC', 'AGCGCGGGTGAGAGGGATTCGTTACCAATTGACAATTGATTGGACGTTCAATATAATGCTAGC', 'TCGTCACTAGAGGGCGATAGTGACAAACTTGACAACTCATCACTTCCTAGGTATAATGCTAGC', 'ACCAGGAATCTGAACGATTCGTTACCAATTGACATATTTAAAATTCTTGTTTAAAatgctagc', 'GTCAACTCATAAGATtctgattcgttaccaattgacaaTTCACCTACCTTTCGTTAGgTTAGGTTGT', 'CGAGCGTAGAGCTTAgattcgttaccaatTGACAAATTTATAAATTGTCAgtacagtcctagc', 'CGCTCATTCACTAGGTCTGATTCGTTACCAATTGACAACTGGTGGTCGAATCAAGATAATAGACCAGTCACTATATTT', 'CGACGTACGGTGGAATCTGATTCGTTACCAATTGACATGATACGAAACGTACCGTATCGTTAAGGT', 'GGTATGGAAGCTATACGTTACCAATTGACAGCTAGCTCAGTCCTACTTTAGTATATAGACCGTGCGATCGGTCTATA', 'TGATCGAACGCTTCAAGGAACAAACGTTTGAttgacagctagctcagtcctaggtagagtgctagc', 'TCTATGATTGGTCCAGATTCGTTACCAATTGACAGCTAGCTCAGTCCTAGGTATATACATACATGCTTGTTTGTTTGTAAAC']]

    score = 0
    
    state = item.get('state')
    cello_results = state.get("cello_results")
    if cello_results:
        cello_library = state.get("cello_library")
        if cello_library:
            ucf_data = cello_library.get('user_constraints')
            if ucf_data:
                """
                Check there are three unique promoters in the ucf_data
                """
                promoters = [p for p in ucf_data if p.get('collection') == 'parts' and p.get('type') == 'promoter']
                final_promoter_names = [p.get('name').lower() for p in promoters]
                final_promoter_sequences = [p.get('dnasequence').lower() for p in promoters]
                num_promoters = len(set([p.get('name') for p in promoters]))
                if num_promoters == 3:
                    HAS_3_UNIQUE_PROMOTERS = True
                
                """
                Check that the new promoters are novel in name
                """
                new_promoter_names = set(final_promoter_names) - set(original_promoters_names)
                if len(new_promoter_names) == 3:
                    HAS_3_NEW_PROMOTERS = True

                """
                Check that the sequences are different
                """
                new_promoter_sequences = set(final_promoter_sequences) - set(original_promoters_sequences)
                if len(new_promoter_sequences) == 3:
                    HAS_3_NEW_PROMOTER_SEQUENCES = True
                
        # """
        # Check that the truth table is correct
        # """
        # activity_table = cello_results.get('dna_design', dict()).get('activity_table', '')
        # if activity_table:
        #     # skip the first line
        #     table_lines = activity_table.split('\n')[1:]

        #     # split into the two tables. 
        #     # Table 1 is all lines before the first occurrence of '""'
        #     split_idx = table_lines.index('""')

        #     table_str_scores = '\n'.join(table_lines[:split_idx])
        #     table_str_binary = '\n'.join(table_lines[split_idx + 2:]) # skip the '""' line and the 'Binary' line

        #     df_scores = pd.read_csv(io.StringIO(table_str_scores), index_col=None)
        #     df_binary = pd.read_csv(io.StringIO(table_str_binary), index_col=None)
        #     input_1_col = df_binary.iloc[:, 0]
        #     input_2_col = df_binary.iloc[:, 1]
        #     output_col = df_binary.iloc[:, 2]
        #     for in1, in2, out in zip(input_1_col, input_2_col, output_col):
        #         # check that matches a NOR gate truth table
        #         if in1 == 1 and in2 == 1:
        #             if out != 0:
        #                 HAS_CORRECT_TRUTH_TABLE = False
        #         else: # all other cases should have output 0
        #             if out != 1:
        #                 HAS_CORRECT_TRUTH_TABLE = False

    
    # """
    # ADD POINTS for calling the correct functions
    # """
    # fn_order = ['select_library', 
    #             'list_promoters',
    #             'generate_verilog',
    #             'design_w_cello']
    # assistant_messages = [m for m in messages if m.get('role') == 'assistant']
    # agent_tool_calls = []
    # for message in assistant_messages:
    #     tool_calls = message.get('tool_calls', [])
    #     for tool_call in tool_calls:
    #         tool_name = tool_call.get('function', dict()).get('name', None)
    #         if tool_name in fn_order:
    #             agent_tool_calls.append(tool_name)
                    
    # """
    # CHECK TOOL CALL ORDER
    # Validate that the agent invoked the critical tools in the required *relative* order.
    # We treat the expected list as an *ordered subsequence* of the actual calls list;
    # other calls may appear in-between and are ignored.
    # """
    # expected_idx = 0
    # for tool_name in agent_tool_calls:
    #     if tool_name == fn_order[expected_idx]:
    #         expected_idx += 1
    #         if expected_idx == len(fn_order):
    #             break

    # if expected_idx == len(fn_order):
    #     HAS_CORRECT_ORDER = True
        
    # """
    # COUNT TOOL FAILURES
    # """
    # tool_failures = []
    # tool_results = [m for m in messages if m.get('role') == 'tool']
    # for tr in tool_results:
    #     content = json.loads(tr.get('content', ''))
    #     if isinstance(content, str):
    #         continue
    #     if content.get('success', False) is False:
    #         tool_failures.append(tr)
    # NUM_TOOL_FAILURES = len(tool_failures)
    
    """
    ADD POINTS FOR THE CRITERIA THAT WERE MET
    """
    if HAS_3_UNIQUE_PROMOTERS:
        score += POINTS_FOR_3_UNIQUE_PROMOTERS
    if HAS_3_NEW_PROMOTERS:
        score += POINTS_FOR_3_NEW_PROMOTERS
    if HAS_3_NEW_PROMOTER_SEQUENCES:
        score += POINTS_FOR_3_NEW_PROMOTER_SEQUENCES
    if HAS_CORRECT_ORDER:   
        score += POINTS_FOR_CORRECT_ORDER
    if NUM_TOOL_FAILURES == 0:
        score += POINTS_FOR_NO_TOOL_FAILURES
    if HAS_CORRECT_TRUTH_TABLE:
        score += POINTS_FOR_CORRECT_TRUTH_TABLE

    MAX_SCORE = sum([POINTS_FOR_3_UNIQUE_PROMOTERS, 
                     POINTS_FOR_3_NEW_PROMOTERS, 
                     POINTS_FOR_3_NEW_PROMOTER_SEQUENCES, 
                     POINTS_FOR_CORRECT_ORDER, 
                     POINTS_FOR_NO_TOOL_FAILURES, 
                     POINTS_FOR_CORRECT_TRUTH_TABLE])
    # small penalty based on number of messages
    num_messages = len(messages)
    score -= num_messages * 0.05
    score = float(score) / MAX_SCORE
    return score