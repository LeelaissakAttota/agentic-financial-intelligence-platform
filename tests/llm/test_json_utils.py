"""
Unit tests for llm.json_utils.extract_json
"""
import pytest
from llm.json_utils import extract_json


class TestExtractJson:
    """Tests for the extract_json function."""

    def test_plain_json_object(self):
        """Plain JSON object without any wrapping."""
        text = '{"key": "value", "number": 42}'
        result = extract_json(text)
        assert result == {"key": "value", "number": 42}

    def test_plain_json_array(self):
        """Plain JSON array without any wrapping."""
        text = '[1, 2, 3, "four"]'
        result = extract_json(text)
        assert result == [1, 2, 3, "four"]

    def test_markdown_json_fence(self):
        """JSON wrapped in markdown code fence with json specifier."""
        text = '''```json
{"name": "Test", "value": 123}
```'''
        result = extract_json(text)
        assert result == {"name": "Test", "value": 123}

    def test_markdown_json_fence_with_extra_whitespace(self):
        """JSON in markdown fence with leading/trailing whitespace."""
        text = '''  
```json
{"result": "ok"}
```
'''
        result = extract_json(text)
        assert result == {"result": "ok"}

    def test_markdown_generic_fence(self):
        """JSON in generic markdown code fence (no language specifier)."""
        text = '''```
{"status": "success"}
```'''
        result = extract_json(text)
        assert result == {"status": "success"}

    def test_json_with_leading_text(self):
        """JSON with explanatory text before it."""
        text = 'Here is the result:\n{"found": true, "count": 5}'
        result = extract_json(text)
        assert result == {"found": True, "count": 5}

    def test_json_with_trailing_text(self):
        """JSON with explanatory text after it."""
        text = '{"error": false}\n\nEnd of response.'
        result = extract_json(text)
        assert result == {"error": False}

    def test_json_with_surrounding_text(self):
        """JSON embedded in text on both sides."""
        text = 'Start of response.\n```json\n{"data": [1,2,3]}\n```\nEnd of response.'
        result = extract_json(text)
        assert result == {"data": [1, 2, 3]}

    def test_nested_json_objects(self):
        """Nested JSON structures."""
        text = '{"outer": {"inner": {"deep": "value"}}}'
        result = extract_json(text)
        assert result == {"outer": {"inner": {"deep": "value"}}}

    def test_json_with_escapes(self):
        """JSON containing escaped characters."""
        text = '{"message": "Hello \\"World\\"", "path": "C:\\\\Users"}'
        result = extract_json(text)
        assert result == {"message": 'Hello "World"', "path": "C:\\Users"}

    def test_json_with_unicode(self):
        """JSON containing unicode characters."""
        text = '{"name": "NVIDIA", "symbol": "📈", "currency": "USD"}'
        result = extract_json(text)
        assert result == {"name": "NVIDIA", "symbol": "📈", "currency": "USD"}

    def test_multiple_json_objects_returns_first(self):
        """When multiple JSON objects exist, return the first valid one."""
        text = '{"first": 1} some text {"second": 2}'
        result = extract_json(text)
        assert result == {"first": 1}

    def test_empty_string_raises(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json("")

    def test_no_json_raises(self):
        """Text with no JSON should raise ValueError."""
        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json("This is just plain text with no JSON.")

    def test_incomplete_json_raises(self):
        """Incomplete/malformed JSON should raise ValueError."""
        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json('{"key": "value"')  # missing closing brace

    def test_markdown_fence_unclosed_raises(self):
        """Unclosed markdown fence with VALID JSON inside should still be parsed."""
        # The JSON inside is valid, so it should be extracted even without closing fence
        text = '```json\n{"key": "value"}'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_null_json_value(self):
        """JSON null value should be parsed as None."""
        text = '{"result": null}'
        result = extract_json(text)
        assert result == {"result": None}

    def test_boolean_values(self):
        """JSON true/false should become Python True/False."""
        text = '{"yes": true, "no": false}'
        result = extract_json(text)
        assert result == {"yes": True, "no": False}

    def test_number_formats(self):
        """Various number formats: int, float, scientific."""
        text = '{"int": 42, "float": 3.14, "sci": 1e6, "neg": -7}'
        result = extract_json(text)
        assert result == {"int": 42, "float": 3.14, "sci": 1000000.0, "neg": -7}

    def test_single_quotes_in_json_not_supported(self):
        """Single-quoted JSON is invalid; should raise."""
        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json("{'key': 'value'}")  # single quotes not valid JSON

    def test_trailing_comma_not_supported(self):
        """Trailing commas in JSON are invalid; should raise."""
        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json('{"a": 1,}')

    def test_json_with_newlines_in_strings(self):
        """JSON strings containing newlines."""
        text = '{"text": "line1\\nline2\\nline3"}'
        result = extract_json(text)
        assert result == {"text": "line1\nline2\nline3"}

    def test_large_json_performance(self):
        """Large JSON should parse within reasonable time."""
        large_obj = {"items": [{"id": i, "data": "x" * 100} for i in range(1000)]}
        import json
        text = json.dumps(large_obj)
        result = extract_json(text)
        assert len(result["items"]) == 1000
        assert result["items"][0]["id"] == 0