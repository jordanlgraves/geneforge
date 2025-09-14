# src/utils/answer_parsing.py
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple, Union

__all__ = [
    "coerce_answer_object",
    "clean_math",
    "clean_math_in_object",
]

# --------------------------------------------------------------------------------------
# Utilities for robustly parsing "answer" payloads and normalizing math/LaTeX strings.
#
# Public API:
#   - coerce_answer_object(answer_like) -> (dict|None, List[str])
#       Best-effort conversion of the inner "answer" into a Python dict, handling:
#         * double-encoded JSON
#         * unicode escapes
#         * extra junk around the JSON
#         * fenced code blocks (``` ... ``` / ```latex ... ```) in values (recursively stripped)
#
#   - clean_math(val) -> str
#       Backwards-compatible helper to normalize a single LaTeX string:
#         * strips code fences and markdown/LaTeX wrappers ($...$, $$...$$, \(...\), \[...\])
#         * trims surrounding whitespace
#
#   - clean_math_in_object(obj) -> obj
#       Recursively applies clean_math to all string values inside dict/list structures.
# --------------------------------------------------------------------------------------

# -------- Code fence handling ----------------------------------------------------------

CODE_FENCE_RE = re.compile(
    r"^\s*```(?:[a-zA-Z0-9_-]+)?\s*([\s\S]*?)\s*```\s*$",
    re.MULTILINE,
)

def _strip_code_fences_once(s: str) -> str:
    if not isinstance(s, str):
        return s  # type: ignore[return-value]
    m = CODE_FENCE_RE.match(s)
    return m.group(1).strip() if m else s.strip()

def _strip_code_fences_recursive(val: Any) -> Any:
    """
    Recursively strip code fences from strings. If val is not a string, pass-through (or map).
    """
    if isinstance(val, dict):
        return {k: _strip_code_fences_recursive(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_strip_code_fences_recursive(v) for v in val]
    if isinstance(val, str):
        prev = None
        cur = val
        # Repeat to handle nested / repeated fences
        while prev != cur:
            prev = cur
            cur = _strip_code_fences_once(cur)
        return cur
    return val

# -------- Math wrapper handling --------------------------------------------------------

MATH_WRAPPERS: List[re.Pattern] = [
    re.compile(r"^\s*\$\$\s*([\s\S]*?)\s*\$\$\s*$"),     # $$ ... $$
    re.compile(r"^\s*\$\s*([\s\S]*?)\s*\$\s*$"),         # $ ... $
    re.compile(r"^\s*\\\(\s*([\s\S]*?)\s*\\\)\s*$"),     # \( ... \)
    re.compile(r"^\s*\\\[\s*([\s\S]*?)\s*\\\]\s*$"),     # \[ ... \]
]

def _strip_math_wrappers_once(s: str) -> str:
    for pat in MATH_WRAPPERS:
        m = pat.match(s)
        if m:
            return m.group(1).strip()
    return s.strip()

def _strip_math_wrappers_recursive(s: str) -> str:
    prev = None
    cur = s
    while prev != cur:
        prev = cur
        cur = _strip_math_wrappers_once(cur)
    return cur

# -------- JSON parsing helpers ---------------------------------------------------------

def _json_loads_object(s: str) -> Dict[str, Any]:
    obj = json.loads(s)
    if not isinstance(obj, dict):
        raise ValueError("JSON is not an object")
    return obj

def _decode_unicode_escapes(s: str) -> str:
    """
    Safely interpret typical backslash escapes. Prefers JSON semantics to avoid
    edge cases of codecs.decode('unicode_escape').
    """
    try:
        return json.loads(s)  # works if s is a JSON string literal like '"x\\n"'
    except Exception:
        try:
            return json.loads(f"\"{s}\"")  # wrap raw text in quotes, then decode
        except Exception:
            return s  # fallback

def _extract_braced_substring(s: str) -> str | None:
    """
    Pragmatic "largest object" capture: first '{' to last '}'.
    Works well for typical model outputs with junk before/after.
    """
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return s[start:end+1]

def _coerce_from_string(s: str, warnings: List[str]) -> Dict[str, Any] | None:
    # 1) direct parse
    try:
        obj = _json_loads_object(s)
        warnings.append("json_ok")
        return obj
    except Exception:
        warnings.append("json_fail")

    # 2) unicode unescape then parse
    try:
        s2 = _decode_unicode_escapes(s)
        if s2 != s:
            obj = _json_loads_object(s2)
            warnings.append("unicode_json_ok")
            return obj
        warnings.append("unicode_json_noop")
    except Exception:
        warnings.append("unicode_json_fail")

    # 3) extract {...} region
    try:
        sub = _extract_braced_substring(s)
        if sub:
            obj = _json_loads_object(sub)
            warnings.append("brace_json_ok")
            return obj
        warnings.append("brace_json_none")
    except Exception:
        warnings.append("brace_json_fail")

    # 4) one more pass: unescape THEN extract
    try:
        s3 = _decode_unicode_escapes(s)
        sub = _extract_braced_substring(s3)
        if sub:
            obj = _json_loads_object(sub)
            warnings.append("unescape_brace_json_ok")
            return obj
        warnings.append("unescape_brace_json_none")
    except Exception:
        warnings.append("unescape_brace_json_fail")

    return None

# -------- Public: coerce_answer_object -------------------------------------------------

def coerce_answer_object(answer_like: Any) -> Tuple[Dict[str, Any] | None, List[str]]:
    """
    Attempt to coerce 'answer_like' into a dict, stripping code fences recursively
    from all string values.

    Returns:
        (obj_or_none, warnings)
    """
    warnings: List[str] = []

    # Already a dict
    if isinstance(answer_like, dict):
        cleaned = _strip_code_fences_recursive(answer_like)
        return cleaned, warnings

    # Bytes -> str
    if isinstance(answer_like, (bytes, bytearray)):
        try:
            answer_like = answer_like.decode("utf-8", errors="replace")
            warnings.append("bytes_decoded_utf8")
        except Exception:
            answer_like = str(answer_like)
            warnings.append("bytes_str_fallback")

    # Anything else -> str
    if not isinstance(answer_like, str):
        answer_like = str(answer_like)
        warnings.append("nonstring_coerced_to_str")

    # Try multiple ways to parse JSON object from string
    obj = _coerce_from_string(answer_like, warnings)
    if obj is None:
        # If it's a quoted JSON blob, remove outer quotes and try again
        s = answer_like.strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s2 = s[1:-1]
            obj = _coerce_from_string(s2, warnings)

    if obj is None:
        return None, warnings

    # Deep-clean all strings: remove code fences
    cleaned = _strip_code_fences_recursive(obj)
    return cleaned, warnings

# -------- Public: clean_math + recursive variant --------------------------------------

def clean_math(val: Any) -> str:
    """
    Backwards-compatible helper that normalizes a single LaTeX/math string.

    Operations:
      1) convert non-strings to string (pass-through for None -> "")
      2) strip fenced code blocks (```...``` / ```latex ...```)
      3) strip surrounding math wrappers repeatedly:
           $$ ... $$, $ ... $, \( ... \), \[ ... \]
      4) trim leading/trailing whitespace

    NOTE: The function does NOT alter internal LaTeX syntax; it only strips
    external wrappers and obvious formatting noise.
    """
    if val is None:
        return ""
    if not isinstance(val, str):
        val = str(val)

    # Remove code fences if present
    s = _strip_code_fences_recursive(val)
    if isinstance(s, (dict, list)):
        # In the unlikely event fences produced structured data, stringify
        s = str(s)

    # Remove common math wrappers repeatedly
    s = _strip_math_wrappers_recursive(s)

    # Final trim
    return s.strip()

def clean_math_in_object(obj: Any) -> Any:
    """
    Recursively apply clean_math to every string value inside a dict/list structure.
    Non-container values are returned unchanged (except strings -> cleaned).
    """
    if isinstance(obj, dict):
        return {k: clean_math_in_object(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_math_in_object(v) for v in obj]
    if isinstance(obj, str):
        return clean_math(obj)
    return obj
