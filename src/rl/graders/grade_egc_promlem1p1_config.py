import importlib
import inspect

_explanation_grader_prompt = """You are an expert grader. Compare the reference answer and the model answer. 
If the steps and explanation in the model answer are exact matches to the reference answer, output a score of 1. 
If they are somewhat similar in meaning, output a score in 0.5. Otherwise, give a score of 0.
"""
explanation_grader_config = {
   "type": "score_model",
   "name": "my_score_model",
   "input": [
        {
            "role": "system",
            "content": _explanation_grader_prompt
        },
        {
            "role": "user",
            "content": "Reference: {{ item.reference_answer }}. Model answer: {{ sample.output_text }}"
        }
   ],
   "pass_threshold": 0.5,
   "model": "o3-mini-2024-01-31",
   "range": [0, 1],
   "sampling_params": {
       "max_tokens": 32768,
       "top_p": 1,
       "reasoning_effort": "medium"
   },
}
    
_grader_module = importlib.import_module("src.rl.graders.grade_egc_promblem1p1")
correctness_grader_config = {
    "type": "python",
    "source": inspect.getsource(_grader_module.grade)
}


multi_grader_config = {
  "type": "multi",
  "graders": {
    "explanation": explanation_grader_config,
    "correct": correctness_grader_config
  },
  "calculate_output": "0.5 * correct + 0.5 * explanation"
}
