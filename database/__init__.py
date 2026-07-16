"""Database integration layer for the Financial Research Agent."""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from database.models import Company, Report, AgentRun
from database.connection import get_engine, get_session_factory


def init_db(settings) -> None:
    """Initialize database by creating all tables.
    
    Args:
        settings: Application settings with database configuration
    """
    from database.models import Base
    
    engine = get_engine(settings)
    Base.metadata.create_all(engine)


def get_session(settings) -> Session:
    """Create a new database session.
    
    Args:
        settings: Application settings
        
    Returns:
        SQLAlchemy session
    """
    engine = get_engine(settings)
    factory = get_session_factory(engine)
    return factory()


def get_or_create_company(session: Session, name: str, ticker: str = "") -> Company:
    """Get existing company or create new one.
    
    Args:
        session: Database session
        name: Company name
        ticker: Optional ticker symbol
        
    Returns:
        Company instance
    """
    # Try to find by name first
    company = session.query(Company).filter(Company.name == name).first()
    
    if company:
        return company
    
    # Try to find by ticker if provided
    if ticker:
        company = session.query(Company).filter(Company.ticker == ticker).first()
        if company:
            return company
    
    # Create new company
    company = Company(
        name=name,
        ticker=ticker,
        created_at=datetime.utcnow()
    )
    session.add(company)
    session.flush()
    
    return company


def save_report(
    session: Session, 
    company: Company, 
    pipeline_result: Dict[str, Any]
) -> Report:
    """Save a research report to the database.
    
    Args:
        session: Database session
        company: Company instance
        pipeline_result: Full pipeline result dictionary
        
    Returns:
        Report instance
    """
    report = Report(
        company_id=company.id,
        json_payload=json.dumps(pipeline_result, default=str),
        generated_at=datetime.utcnow()
    )
    session.add(report)
    session.flush()
    
    return report


def save_agent_run(
    session: Session,
    report_id: str,
    agent_name: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    tokens_used: Optional[int] = None,
    cost_usd: Optional[float] = None,
    status: str = "success"
) -> AgentRun:
    """Save an agent run record.
    
    Args:
        session: Database session
        report_id: ID of the parent report
        agent_name: Name of the agent (e.g., "news_agent")
        input_data: Input payload to the agent
        output_data: Output payload from the agent
        tokens_used: Optional token count
        cost_usd: Optional cost in USD
        status: "success" or "error"
        
    Returns:
        AgentRun instance
    """
    agent_run = AgentRun(
        report_id=report_id,
        agent_name=agent_name,
        input_payload=json.dumps(input_data, default=str),
        output_payload=json.dumps(output_data, default=str),
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        status=status,
        timestamp=datetime.utcnow()
    )
    session.add(agent_run)
    session.flush()
    
    return agent_run


def get_company_reports(
    session: Session, 
    company_id: str,
    limit: int = 50
) -> List[Report]:
    """Get all reports for a company, most recent first.
    
    Args:
        session: Database session
        company_id: Company ID
        limit: Maximum number of reports to return
        
    Returns:
        List of Report instances
    """
    return (
        session.query(Report)
        .filter(Report.company_id == company_id)
        .order_by(Report.generated_at.desc())
        .limit(limit)
        .all()
    )


def get_report_by_id(session: Session, report_id: str) -> Optional[Report]:
    """Get a report by its ID.
    
    Args:
        session: Database session
        report_id: Report ID
        
    Returns:
        Report instance or None
    """
    return (
        session.query(Report)
        .filter(Report.id == report_id)
        .first()
    )


def get_agent_runs_for_report(session: Session, report_id: str) -> List[AgentRun]:
    """Get all agent runs for a specific report.
    
    Args:
        session: Database session
        report_id: Report ID
        
    Returns:
        List of AgentRun instances
    """
    return (
        session.query(AgentRun)
        .filter(AgentRun.report_id == report_id)
        .order_by(AgentRun.timestamp.asc())
        .all()
    )


def persist_pipeline_result(
    session: Session,
    pipeline_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Persist a complete pipeline result including all agent runs.
    
    Args:
        session: Database session
        pipeline_result: Full pipeline result from ManagerAgent
        
    Returns:
        Dictionary with report_id and company_id
    """
    company_name = pipeline_result.get("company", "Unknown")
    ticker = pipeline_result.get("ticker", "")
    
    # Get or create company
    company = get_or_create_company(session, company_name, ticker)
    
    # Save the full pipeline result as a report
    report = save_report(session, company, pipeline_result)
    
    # Save each agent run
    results = pipeline_result.get("results", {})
    for task_type, task_result in results.items():
        usage = task_result.get("usage") or {}
        
        save_agent_run(
            session=session,
            report_id=report.id,
            agent_name=task_type,
            input_data={"company": company_name, "ticker": ticker},
            output_data=task_result,
            tokens_used=usage.get("total_tokens"),
            cost_usd=usage.get("cost_usd"),
            status=task_result.get("status", "unknown")
        )
    
    # Commit all changes
    session.commit()
    
    return {
        "report_id": report.id,
        "company_id": company.id
    }


__all__ = [
    "init_db",
    "get_session",
    "get_or_create_company",
    "save_report",
    "save_agent_run",
    "get_company_reports",
    "get_report_by_id",
    "get_agent_runs_for_report",
    "persist_pipeline_result",
]