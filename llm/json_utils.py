"""
JSON extraction utility for LLM responses.

Provides robust JSON parsing from LLM outputs that may include:
- Plain JSON
- Markdown code fences (```json ... ```)
- Extra text before/after JSON
- Multiple JSON objects (returns first valid)
"""
import json
import re
from typing import Any


def extract_json(text: str) -> Any:
    """
    Extract and parse the first valid JSON object/array from text.

    Handles:
    - Plain JSON: {"key": "value"}
    - Markdown fenced: ```json\n{"key": "value"}\n```
    - Generic fenced: ```\n{"key": "value"}\n```
    - JSON embedded in text: "Result: {\"key\": \"value\"} done"
    - Multiple JSON objects: returns first valid one

    Args:
        text: Raw text potentially containing JSON

    Returns:
        Parsed JSON (dict, list, or primitive)

    Raises:
        ValueError: If no valid JSON found
    """
    if not text or not text.strip():
        raise ValueError("No valid JSON found in empty input")

    # Strategy 1: Try to find JSON in markdown code fences
    # Pattern: ```json ... ``` or ``` ... ``` (must have closing fence)
    fence_pattern = r'```(?:json)?\s*\n(.*?)\n```'
    matches = list(re.finditer(fence_pattern, text, re.DOTALL | re.IGNORECASE))

    for match in matches:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # Strategy 1b: Check for unclosed fence (```json\n... but no closing ```)
    # This should NOT be treated as valid - fall through to other strategies

    # Strategy 2: Try to find JSON-like structures in the text
    # Look for {...} or [...] patterns
    # We need to handle nested braces/brackets properly

    # First, try to find {...} objects
    brace_stack = []
    in_string = False
    escape_next = False
    start_pos = None

    for i, char in enumerate(text):
        if not in_string and char == '{':
            if not brace_stack:
                start_pos = i
            brace_stack.append('{')
        elif not in_string and char == '}':
            if brace_stack:
                brace_stack.pop()
                if not brace_stack and start_pos is not None:
                    candidate = text[start_pos:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        # Continue searching
                        start_pos = None
        elif char == '"' and not escape_next:
            in_string = not in_string
        escape_next = (char == '\\' and not escape_next)

    # Strategy 3: Try to find [...] arrays
    bracket_stack = []
    in_string = False
    escape_next = False
    start_pos = None

    for i, char in enumerate(text):
        if not in_string and char == '[':
            if not bracket_stack:
                start_pos = i
            bracket_stack.append('[')
        elif not in_string and char == ']':
            if bracket_stack:
                bracket_stack.pop()
                if not bracket_stack and start_pos is not None:
                    candidate = text[start_pos:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        start_pos = None
        elif char == '"' and not escape_next:
            in_string = not in_string
        escape_next = (char == '\\' and not escape_next)

    # Strategy 4: Fallback - try to parse the entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # No valid JSON found
    raise ValueError("No valid JSON found in input text")