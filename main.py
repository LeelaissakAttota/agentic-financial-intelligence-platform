"""
Entry point for the AI Financial Research Analyst Agent.

Usage:
    python main.py --company "NVIDIA"

Features:
    - Parses --company arg
    - Instantiates ManagerAgent with all registered workers
    - Calls ManagerAgent.run(company)
    - Writes resulting JSON + rendered markdown to data/reports/<company>_<timestamp>.json
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from agents.manager_agent.manager import ManagerAgent
from agents.manager_agent.schemas import TaskType
from agents.news_agent.news_agent import NewsAgent
from agents.market_agent.market_agent import MarketAgent
from agents.financial_report_agent.agent import FinancialReportAgent
from agents.sentiment_agent.agent import SentimentAgent
from agents.risk_agent.agent import RiskAgent
from agents.competitor_agent.agent import CompetitorAgent
from agents.investment_summary_agent.agent import InvestmentSummaryAgent
from llm.openrouter_client import OpenRouterClient
from config.settings import Settings
from database import persist_pipeline_result, get_session, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run(company: str) -> dict:
    """
    Run the full financial research pipeline for a company.

    Args:
        company: Company name or ticker symbol

    Returns:
        dict: Full pipeline results including all agent outputs
    """
    # Load settings
    settings = Settings()

    # Initialize database
    init_db(settings)

    # Initialize LLM provider
    llm_provider = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )

    # Initialize ManagerAgent
    manager = ManagerAgent(llm_provider=llm_provider)

    # Register all worker agents
    manager.register_worker(TaskType.NEWS_ANALYSIS, NewsAgent(llm_provider=llm_provider))
    manager.register_worker(TaskType.MARKET_DATA, MarketAgent(llm_provider=llm_provider))
    manager.register_worker(TaskType.FINANCIAL_ANALYSIS, FinancialReportAgent(llm_provider=llm_provider))
    manager.register_worker(TaskType.SENTIMENT_ANALYSIS, SentimentAgent(llm_provider=llm_provider))
    manager.register_worker(TaskType.RISK_ANALYSIS, RiskAgent(llm_provider=llm_provider))
    manager.register_worker(TaskType.COMPETITOR_ANALYSIS, CompetitorAgent(llm_provider=llm_provider))
    # InvestmentSummaryAgent is a stub - will be implemented in Phase 2 Step 5
    # manager.register_worker(TaskType.INVESTMENT_SUMMARY, InvestmentSummaryAgent(llm_provider=llm_provider))

    # Run the pipeline
    result = asyncio.run(manager.run(company=company))

    # Persist to database
    session = get_session(settings)
    try:
        persist_pipeline_result(session, result.model_dump())
    finally:
        session.close()

    return result.model_dump()


def save_report(company: str, result: dict) -> str:
    """
    Save the report to data/reports/ directory as JSON and Markdown.

    Args:
        company: Company name
        result: Pipeline result dictionary

    Returns:
        Path to the saved JSON report
    """
    # Sanitize company name for filename
    safe_company = company.replace(" ", "_").replace("/", "_").replace("\\", "_")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename_base = f"{safe_company}_{timestamp}"

    # Ensure reports directory exists
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path = reports_dir / f"{filename_base}.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    logger.info(f"Report saved to {json_path}")
    return str(json_path)


def main():
    parser = argparse.ArgumentParser(description="AI Financial Research Analyst Agent")
    parser.add_argument("--company", required=True, help='Company name or ticker, e.g. "NVIDIA" or "NVDA"')
    args = parser.parse_args()

    logger.info(f"Starting financial research for {args.company}")

    try:
        result = run(args.company)
        json_path = save_report(args.company, result)

        print(f"\n✅ Analysis complete for {args.company}")
        print(f"📄 Report saved to: {json_path}")

        # Print summary
        if result.get("results"):
            print("\n📊 Agent Results:")
            for task_type, task_result in result["results"].items():
                status = task_result.get("status", "unknown")
                print(f"  - {task_type}: {status}")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"\n❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())