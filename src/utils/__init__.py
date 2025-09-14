# src/utils/answer_parsing.py
from __future__ import annotations
import json, re
from typing import Any, Dict, List, Optional, Tuple

# Matches a full fenced block like ```latex\n ... \n``` (greedy body, DOTALL)
_CODEBLOCK_FULL_RE = re.compile(
    r"""^```[ \t]*[a-zA-Z0-9_-]*[ \t]*\n    # opening fence with optional lang/whitespace
        (?P<body>.*?)                      # body (non-greedy, DOTALL)
        \n[ \t]*```[ \t]*$                 # closing fence, allow indentation/trailing space
    """,
    re.DOTALL | re.VERBOSE,
)
# Matches any inline triple-backtick run to strip leftovers
_CODEBLOCK_ANY_OPEN_OR_CLOSE_RE = re.compile(r"```[ \t]*[a-zA-Z0-9_-]*[ \t]*|[ \t]*```")

def strip_code_fences(text: str) -> str:
    if not isinstance(text, str):
        return text
    t = text.strip()

    m = _CODEBLOCK_FULL_RE.match(t)
    if m:
        t = m.group("body").strip()

    # Remove any leftover opening/closing ticks anywhere in the string
    t = _CODEBLOCK_ANY_OPEN_OR_CLOSE_RE.sub("", t).strip()
    return t

def strip_math_delimiters(text: str) -> str:
    """Remove $...$, $$...$$, \(...\), \[...\] wrappers if present."""
    if not isinstance(text, str):
        return text
    t = text.strip()
    # $$ ... $$
    if t.startswith("$$") and t.endswith("$"):
        # Handle $$...$$ safely
        if t.endswith("$$"):
            t = t[2:-2].strip()
    # $ ... $
    if t.startswith("$") and t.endswith("$") and len(t) >= 2:
        t = t[1:-1].strip()
    # \( ... \)
    if t.startswith(r"\(") and t.endswith(r"\)"):
        t = t[2:-2].strip()
    # \[ ... \]
    if t.startswith(r"\[") and t.endswith(r"\]"):
        t = t[2:-2].strip()
    return t

def clean_math(text: str) -> str:
    """Strip fences and math delimiters; return a plain LaTeX expression."""
    return strip_math_delimiters(strip_code_fences(text or ""))

def _brace_extract(text: str) -> Optional[str]:
    """Extract the largest top-level {...} substring for loose JSON text."""
    if not isinstance(text, str):
        return None
    start = text.find("{")
    end = text.rfind("}")
    if 0 <= start < end:
        return text[start:end+1]
    return None

def _post_clean_object_str_values(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Clean string values (strip code fences & math delimiters)."""
    for k, v in list(obj.items()):
        if isinstance(v, str):
            obj[k] = strip_code_fences(v)
            obj[k] = strip_math_delimiters(obj[k])
    return obj

def coerce_answer_object(
    value: Any,
    required_keys: Optional[List[str]] = None,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Try multiple strategies to obtain a dict from `value`:
      1) If dict -> return
      2) json.loads(value)
      3) Remove code fences globally, then brace-extract and json.loads
      4) Regex extract `"key": "value"` for required_keys only

    Returns (obj_or_None, warnings) where warnings are parse steps taken.
    """
    warnings: List[str] = []

    # 1) Already dict
    if isinstance(value, dict):
        return _post_clean_object_str_values(value), warnings

    if not isinstance(value, str):
        warnings.append("answer_not_str_or_dict")
        return None, warnings

    # 2) Direct JSON load
    try:
        obj = json.loads(value)
        if isinstance(obj, dict):
            warnings.append("loaded_direct_json")
            return _post_clean_object_str_values(obj), warnings
    except Exception as e:
        warnings.append(f"json_loads_failed:{type(e).__name__}")

    # 3) Global fence removal + brace extract
    cleaned = strip_code_fences(value)
    brace = _brace_extract(cleaned)
    if brace:
        try:
            obj = json.loads(brace)
            if isinstance(obj, dict):
                warnings.append("brace_extracted_json")
                return _post_clean_object_str_values(obj), warnings
        except Exception as e:
            warnings.append(f"brace_json_failed:{type(e).__name__}")

    # 4) Minimal regex extraction for required keys
    obj: Dict[str, Any] = {}
    if required_keys:
        for k in required_keys:
            # Capture string value across newlines until next unescaped quote
            # Values in your tasks don't contain embedded quotes → safe non-greedy
            pat = re.compile(rf'"{re.escape(k)}"\s*:\s*"(.*?)"', re.DOTALL)
            m = pat.search(value)
            if m:
                obj[k] = clean_math(m.group(1))
    if obj:
        warnings.append("regex_key_extract")
        return obj, warnings

    return None, warnings
