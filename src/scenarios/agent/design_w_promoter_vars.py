#!/usr/bin/env python3
import logging
import json
import os
from src.scenarios.agent.workflows import WorkflowRunner
from src.prompt_manager import get_system_prompt
import src.library.cello_utils as cello_utils
from glob import glob
import pandas as pd
import io

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DesignWithPromoterVarsExample")

PROMPT = """Your task is to design a simple genetic circuit, a NOR gate, for E. coli. 

However, you must use custom promoters. 
Please start by selecting the 'Eco1C1G1T1' library. 
Then, take a random promoter from the library and generate three new promoter variants that are stronger than the original. 
Then, create a new, minimal genetic library that contains *only* these three new variants and their necessary dependencies. 
Finally, use this new custom library to design the NOR gate with Cello. 
Report the name of the final DNA sequence design if successful."""

SYSTEM_PROMPT = get_system_prompt()


class DesignWithPromoterVarsWorkflow(WorkflowRunner):
    """
    Extension of ExampleRunner to check for a custom UCF file where the original
    promoter has been replaced by variants, and Cello results are present.
    """
    def check_finished(self) -> bool:
        """
        Check if:
        1. A custom UCF file was created.
        2. Cello results were obtained.
        3. The custom UCF contains the new variants and not the original.
        """
        has_cello_results = self.session_state.cello_results is not None

        return has_cello_results

    def _process_prompt(self, prompt):
        """
        Get the prompt for the example.
        """
        return PROMPT
    
    def _process_system_prompt(self, system_prompt):
        """
        Get the system prompt for the example.
        """
        return SYSTEM_PROMPT

    def score_run(self, messages, session_state_history):
        # The different criteria that are scored and the points for each
        HAS_3_UNIQUE_PROMOTERS, POINTS_FOR_3_UNIQUE_PROMOTERS = False, 5
        HAS_3_NEW_PROMOTERS, POINTS_FOR_3_NEW_PROMOTERS = False, 5
        HAS_3_NEW_PROMOTER_SEQUENCES, POINTS_FOR_3_NEW_PROMOTER_SEQUENCES = False, 5
        HAS_CORRECT_ORDER, POINTS_FOR_CORRECT_ORDER = False, 2
        NUM_TOOL_FAILURES, POINTS_FOR_NO_TOOL_FAILURES = 0, 2
        HAS_CORRECT_TRUTH_TABLE, POINTS_FOR_CORRECT_TRUTH_TABLE = False, 5
        
        user_constraints_path = "ext_repos/Cello-UCF/files/v2/ucf/Eco/Eco1C1G1T1.UCF.json"
        with open(user_constraints_path, 'r') as f:
            ucf_data = json.load(f)
        original_promoters = [p for p in ucf_data if p.get('collection') == 'parts' and p.get('type') == 'promoter']
        original_promoters_names = [p.get('name') for p in original_promoters]
        original_promoters_sequences = [p.get('sequence') for p in original_promoters]

        score = 0
        
        last_session_state = session_state_history[-1]['state']
        cello_results = last_session_state.get("cello_results")
        if cello_results:
            cello_library = last_session_state.get("cello_library")
            if cello_library:
                ucf_data = cello_library.get('user_constraints')
                if ucf_data:
                    """
                    Check there are three unique promoters in the ucf_data
                    """
                    promoters = [p for p in ucf_data if p.get('collection') == 'parts' and p.get('type') == 'promoter']
                    final_promoter_names = [p.get('name') for p in promoters]
                    final_promoter_sequences = [p.get('dnasequence') for p in promoters]
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
                    
            """
            Check that the truth table is correct
            """
            activity_table = cello_results.get('dna_design', dict()).get('activity_table', '')
            if activity_table:
                # skip the first line
                table_lines = activity_table.split('\n')[1:]

                # split into the two tables. 
                # Table 1 is all lines before the first occurrence of '""'
                split_idx = table_lines.index('""')

                table_str_scores = '\n'.join(table_lines[:split_idx])
                table_str_binary = '\n'.join(table_lines[split_idx + 2:]) # skip the '""' line and the 'Binary' line

                df_scores = pd.read_csv(io.StringIO(table_str_scores), index_col=None)
                df_binary = pd.read_csv(io.StringIO(table_str_binary), index_col=None)

        
                input_1_col = df_binary.iloc[:, 0]
                input_2_col = df_binary.iloc[:, 1]
                output_col = df_binary.iloc[:, 2]
                for in1, in2, out in zip(input_1_col, input_2_col, output_col):
                    # check that matches a NOR gate truth table
                    if in1 == 1 and in2 == 1:
                        if out != 0:
                            HAS_CORRECT_TRUTH_TABLE = False
                    else: # all other cases should have output 0
                        if out != 1:
                            HAS_CORRECT_TRUTH_TABLE = False
                                
        """
        ADD POINTS for calling the correct functions
        """
        fn_order = ['select_library', 
                    'list_promoters',
                    'generate_verilog',
                    'design_w_cello']
        assistant_messages = [m for m in messages if m.get('role') == 'assistant']
        agent_tool_calls = []
        for message in assistant_messages:
            tool_calls = message.get('tool_calls', [])
            for tool_call in tool_calls:
                tool_name = tool_call.get('function', dict()).get('name', None)
                if tool_name in fn_order:
                    agent_tool_calls.append(tool_name)
                        
        """
        CHECK TOOL CALL ORDER
        Validate that the agent invoked the critical tools in the required *relative* order.
        We treat the expected list as an *ordered subsequence* of the actual calls list;
        other calls may appear in-between and are ignored.
        """
        expected_idx = 0
        for tool_name in agent_tool_calls:
            if tool_name == fn_order[expected_idx]:
                expected_idx += 1
                if expected_idx == len(fn_order):
                    break

        if expected_idx == len(fn_order):
            HAS_CORRECT_ORDER = True
            
        """
        COUNT TOOL FAILURES
        """
        tool_failures = []
        tool_results = [m for m in messages if m.get('role') == 'tool']
        for tr in tool_results:
            content = json.loads(tr.get('content', ''))
            if isinstance(content, str):
                continue
            if content.get('success', False) is False:
                tool_failures.append(tr)
        NUM_TOOL_FAILURES = len(tool_failures)
        
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

        # small penalty based on number of messages
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

        return {'score': score, 
                'num_tool_failures': NUM_TOOL_FAILURES, 
                'num_messages': num_messages,
                'num_tool_calls': len(agent_tool_calls),
                'num_agent_messages': len(assistant_messages),
                'has_3_unique_promoters': HAS_3_UNIQUE_PROMOTERS,
                'has_3_new_promoters': HAS_3_NEW_PROMOTERS,
                'has_3_new_promoter_sequences': HAS_3_NEW_PROMOTER_SEQUENCES,
                'has_correct_order': HAS_CORRECT_ORDER,
                'has_correct_truth_table': HAS_CORRECT_TRUTH_TABLE}


def run_example():
    """
    Uses the LLM modules with session state to execute a design workflow
    that involves creating and using promoter variants.
    """
    # Create and run the example using the customized runner
    runner = DesignWithPromoterVarsWorkflow(
        example_name="DesignWithPromoterVars",
        prompt=PROMPT,
        system_prompt=SYSTEM_PROMPT,
        max_rounds=25,
        max_attempts=3
    )
    
    final_result = runner.run()
    runner.log_results(final_result)
    
    return runner

if __name__ == "__main__":
    run_example()
