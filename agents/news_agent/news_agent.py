"""News Intelligence Agent - Fetches and analyzes financial news for a company."""

import json
from datetime import datetime
from typing import Optional, Dict, Any

from .schemas import NewsAgentInput, NewsAgentOutput, NewsArticle
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from .exceptions import NewsAgentError, NewsAgentInputError, NewsAgentLLMError, NewsAgentParseError
from llm.llm_provider import LLMProvider
from agents.manager_agent.schemas import WorkerResponse
from agents.manager_agent.manager import BaseWorkerAgent


class NewsAgent(BaseWorkerAgent):
    """Agent that collects and analyzes recent financial news for a company."""
    
    def __init__(self, llm_provider: LLMProvider, model: str = "openrouter/auto"):
        """
        Initialize the News Agent.
        
        Args:
            llm_provider: LLM provider for generating analysis
            model: Model to use for analysis
        """
        super().__init__(agent_name="news_agent")
        self.llm_provider = llm_provider
        self.model = model
    
    async def run(self, company: str, context: Dict[str, Any] = None) -> WorkerResponse:
        """
        Execute the news analysis workflow.
        
        Args:
            company: Company name to analyze
            context: Optional context from other agents (e.g., query)
            
        Returns:
            WorkerResponse with analysis results
        """
        query = context.get("query") if context else None
        
        try:
            # Validate input
            input_data = NewsAgentInput(company=company, query=query)
        except Exception as e:
            return WorkerResponse(
                status="error",
                error=f"Invalid input: {str(e)}",
                data=None,
                usage=None
            )
        
        try:
            # Build prompt and call LLM
            user_prompt = self._build_user_prompt(input_data, context)
            
            # Define response schema for structured output
            response_schema = {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "articles": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "impact": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                            },
                            "required": ["title", "impact", "confidence"]
                        }
                    }
                },
                "required": ["company", "articles"]
            }
            
            # Use generate_json for structured output
            llm_result = self.llm_provider.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_prompt,
                response_schema=response_schema,
                model=self.model
            )
            
            # Parse and validate output
            content = llm_result.get("content", {})
            usage = llm_result.get("usage")
            
            if not content or "articles" not in content:
                return WorkerResponse(
                    status="error",
                    error="Invalid LLM response: missing articles",
                    data=None,
                    usage=usage.to_dict() if usage and hasattr(usage, 'to_dict') else usage
                )
            
            # Validate output schema
            try:
                output = NewsAgentOutput(**content)
            except Exception as e:
                return WorkerResponse(
                    status="error",
                    error=f"Output validation failed: {str(e)}",
                    data=None,
                    usage=usage.to_dict() if usage and hasattr(usage, 'to_dict') else usage
                )
            
            # Return in WorkerResponse format
            return WorkerResponse(
                status="success",
                data=output.model_dump(),
                usage=usage.to_dict() if usage and hasattr(usage, 'to_dict') else usage
            )
            
        except NewsAgentError:
            raise
        except Exception as e:
            return WorkerResponse(
                status="error",
                error=f"News agent failed: {str(e)}",
                data=None,
                usage=None
            )
    
    def _build_user_prompt(self, input_data: NewsAgentInput, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the user prompt for the LLM."""
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        prompt = USER_PROMPT_TEMPLATE.format(
            company=input_data.company,
            current_date=current_date
        )
        
        if input_data.query:
            prompt += f"\n\nAdditional focus: {input_data.query}"
        
        if context and context.get("query"):
            prompt += f"\n\nManager query: {context['query']}"
        
        return prompt


# Synchronous wrapper for testing
def run_news_agent_sync(llm_provider: LLMProvider, company: str, query: Optional[str] = None) -> dict:
    """Synchronous wrapper for the NewsAgent.run method for testing."""
    agent = NewsAgent(llm_provider)
    import asyncio
    result = asyncio.run(agent.run(company, {"query": query} if query else {}))
    return result.model_dump()


# Legacy interface for backwards compatibility
def run(payload: dict) -> dict:
    """Legacy sync interface - raises NotImplementedError."""
    raise NotImplementedError("Use NewsAgent class with async run() method")
