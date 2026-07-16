import pytest
from llm.claude_client import ClaudeClient

def test_claude_connection():
    """
    Verifies that the ClaudeClient can successfully make a request 
    and receive a parsed JSON response.
    """
    client = ClaudeClient()
    
    # A simple prompt designed to force a JSON response
    system_prompt = "You are a helpful assistant. You must ONLY respond in JSON format."
    user_payload = {"task": "Say hello", "format": "json"}
    
    try:
        result = client.generate(system_prompt, user_payload)
        
        # Assert that we got a dictionary back (parsed JSON)
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        
        print("\n✅ Claude Connection Verified: Received valid JSON response.")
        
    except Exception as e:
        pytest.fail(f"Claude connection failed: {str(e)}")

if __name__ == "__main__":
    # Allow running the test directly via 'python tests/test_claude_connection.py'
    test_claude_connection()
