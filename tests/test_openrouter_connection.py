import pytest
import os
from config.settings import Settings
from llm.openrouter_client import OpenRouterClient
from llm.model_registry import resolve_model, Complexity

# Skip this test if no API key is available - requires live credentials
requires_openrouter_key = pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="Requires OPENROUTER_API_KEY"
)

@requires_openrouter_key
def test_openrouter_connection():
    """
    Integration test to verify OpenRouter connection, JSON parsing and usage tracking.
    """
    settings = Settings()
    
    if not settings.openrouter_api_key:
        pytest.skip("OPENROUTER_API_KEY not found in .env")

    # 1. Initialize Client
    client = OpenRouterClient(
        api_key=settings.openrouter_api_key, 
        base_url=settings.openrouter_base_url
    )
    
    # 2. Test JSON Generation (Simple Task -> Fast Model)
    system_prompt = "You are a project status bot. Respond only in JSON."
    user_message = "Return a JSON object with field 'status' as 'active' and 'version' as '1.0'"
    
    try:
        print("\nTesting OpenRouter JSON generation...")
        # Resolve fast model from registry
        resolution = resolve_model("news_agent", Complexity.SIMPLE)
        model = resolution.model
        
        response = client.generate_json(
            system_prompt=system_prompt,
            user_message=user_message,
            response_schema={"status": "string", "version": "string"},
            model=model
        )
        
        content = response["content"]
        usage = response["usage"]
        
        # Validate JSON structure
        assert "status" in content
        assert content["status"] == "active"
        
        print(f"✅ Connection Successful!")
        print(f"Model Used: {usage.model}")
        print(f"Tokens: {usage.total_tokens} (Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens})")
        print(f"Estimated Cost: ${usage.cost}")
        
    except Exception as e:
        pytest.fail(f"OpenRouter connection test failed: {str(e)}")

if __name__ == "__main__":
    test_openrouter_connection()