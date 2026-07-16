# Manager Agent Prompts

# In a full implementation, these would contain the prompts used by the Manager Agent
# for task planning and potentially for generating the final summary.
# For the foundation phase, we are using rule-based planning, so these are placeholders.

TASK_PLANNING_PROMPT = """
You are an expert financial analyst tasked with creating an analysis plan for a company.
Given the company name and any additional query, determine which analyses are needed
and in what order they should be executed.

Available analysis types:
- news_analysis: Recent news and sentiment
- market_data: Current stock metrics and financial ratios
- financial_analysis: Deep dive into financial statements (requires RAG)
- sentiment_analysis: Aggregated sentiment from news and other sources
- competitor_analysis: Comparison with industry peers
- risk_analysis: Identification and assessment of risks
- investment_summary: Final synthesis and recommendation

Return your plan as a JSON array of analysis types in execution order.
"""

SUMMARY_PROMPT = """
You are an expert financial analyst creating an investment summary.
Based on the following analysis results, create a coherent investment thesis
with a clear recommendation (buy, hold, or sell).

Analysis results:
{results}

Provide your response in JSON format with the following structure:
{{
  "recommendation": "buy|hold|sell",
  "confidence": 0.0-1.0,
  "investment_thesis": "string",
  "key_catalysts": ["string"],
  "key_risks": ["string"],
  "time_horizon": "short|medium|long",
  "disclaimer": "string"
}}
"""