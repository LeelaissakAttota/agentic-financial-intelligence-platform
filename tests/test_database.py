"""
Tests for database integration layer.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from uuid import uuid4

from database.models import Company, Report, AgentRun, Base
from database import (
    get_or_create_company,
    save_report,
    save_agent_run,
    get_company_reports,
    get_report_by_id,
    get_agent_runs_for_report,
    persist_pipeline_result,
    init_db,
)
from sqlalchemy.orm import Session


class MockSession:
    """Mock SQLAlchemy session for testing."""
    
    def __init__(self):
        self.added_objects = []
        self.flushed = False
        self.committed = False
        self.query_results = {}
        
    def add(self, obj):
        self.added_objects.append(obj)
        # Auto-assign id if not set (for models with default uuid)
        if hasattr(obj, 'id') and obj.id is None:
            from uuid import uuid4
            obj.id = str(uuid4())
        
    def flush(self):
        self.flushed = True
        
    def commit(self):
        self.committed = True
        
    def query(self, model):
        class MockQuery:
            def __init__(self, session, model):
                self.session = session
                self.model = model
                self.filters = []
                
            def filter(self, *args):
                self.filters.extend(args)
                return self
                
            def order_by(self, *args):
                return self
                
            def limit(self, *args):
                return self
                
            def first(self):
                key = self.model.__name__
                return self.session.query_results.get(key)
                
            def all(self):
                key = self.model.__name__
                return self.session.query_results.get(key, [])
                
        return MockQuery(self, model)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return MockSession()


class TestCompanyOperations:
    """Tests for company CRUD operations."""
    
    def test_get_or_create_company_creates_new(self, mock_session):
        """Should create new company if none exists."""
        mock_session.query_results = {"Company": None}
        
        company = get_or_create_company(mock_session, "NVIDIA", "NVDA")
        
        assert company.name == "NVIDIA"
        assert company.ticker == "NVDA"
        assert isinstance(company.id, str)
        assert len(mock_session.added_objects) == 1
        assert mock_session.flushed
        
    def test_get_or_create_company_returns_existing(self, mock_session):
        """Should return existing company if found by name."""
        existing = Company(id=str(uuid4()), name="NVIDIA", ticker="NVDA")
        mock_session.query_results = {"Company": existing}
        
        company = get_or_create_company(mock_session, "NVIDIA", "NVDA")
        
        assert company is existing
        assert len(mock_session.added_objects) == 0
        
    def test_get_or_create_company_finds_by_ticker(self, mock_session):
        """Should find existing company by ticker if name differs."""
        existing = Company(id=str(uuid4()), name="NVIDIA Corp", ticker="NVDA")
        mock_session.query_results = {"Company": existing}
        
        company = get_or_create_company(mock_session, "NVIDIA", "NVDA")
        
        assert company is existing


class TestReportOperations:
    """Tests for report saving and retrieval."""
    
    def test_save_report_creates_report(self, mock_session):
        """Should create and save a report."""
        company = Company(id=str(uuid4()), name="NVIDIA", ticker="NVDA")
        pipeline_result = {"company": "NVIDIA", "results": {}}
        
        report = save_report(mock_session, company, pipeline_result)
        
        assert report.company_id == company.id
        assert report.json_payload is not None
        assert "NVIDIA" in report.json_payload
        assert isinstance(report.generated_at, datetime)
        assert len(mock_session.added_objects) == 1
        assert mock_session.flushed
        
    def test_get_company_reports(self, mock_session):
        """Should retrieve reports for a company."""
        report1 = Report(id="1", company_id="comp1", generated_at=datetime(2024, 1, 1))
        report2 = Report(id="2", company_id="comp1", generated_at=datetime(2024, 1, 2))
        mock_session.query_results = {"Report": [report2, report1]}
        
        reports = get_company_reports(mock_session, "comp1")
        
        assert len(reports) == 2
        # Should be ordered by date descending (most recent first)
        
    def test_get_report_by_id(self, mock_session):
        """Should retrieve specific report by ID."""
        report = Report(id="report123", company_id="comp1")
        mock_session.query_results = {"Report": report}
        
        result = get_report_by_id(mock_session, "report123")
        
        assert result is report
        
    def test_get_report_by_id_returns_none(self, mock_session):
        """Should return None if report not found."""
        mock_session.query_results = {"Report": None}
        
        result = get_report_by_id(mock_session, "nonexistent")
        
        assert result is None


class TestAgentRunOperations:
    """Tests for agent run persistence."""
    
    def test_save_agent_run_success(self, mock_session):
        """Should save successful agent run."""
        report_id = str(uuid4())
        output_data = {"status": "success", "data": {"test": "value"}}
        
        run = save_agent_run(
            session=mock_session,
            report_id=report_id,
            agent_name="news_agent",
            input_data={"company": "NVIDIA"},
            output_data=output_data,
            tokens_used=1000,
            cost_usd=0.001,
            status="success"
        )
        
        assert run.report_id == report_id
        assert run.agent_name == "news_agent"
        assert run.status == "success"
        assert run.tokens_used == 1000
        assert run.cost_usd == 0.001
        assert isinstance(run.timestamp, datetime)
        assert len(mock_session.added_objects) == 1
        
    def test_save_agent_run_error(self, mock_session):
        """Should save failed agent run with error."""
        report_id = str(uuid4())
        output_data = {"status": "error", "error": "API timeout"}
        
        run = save_agent_run(
            session=mock_session,
            report_id=report_id,
            agent_name="market_agent",
            input_data={"company": "NVIDIA"},
            output_data=output_data,
            status="error"
        )
        
        assert run.status == "error"
        assert "API timeout" in run.output_payload
        
    def test_get_agent_runs_for_report(self, mock_session):
        """Should retrieve all agent runs for a report."""
        run1 = AgentRun(id="1", report_id="r1", agent_name="news_agent")
        run2 = AgentRun(id="2", report_id="r1", agent_name="market_agent")
        mock_session.query_results = {"AgentRun": [run1, run2]}
        
        runs = get_agent_runs_for_report(mock_session, "r1")
        
        assert len(runs) == 2


class TestPersistPipelineResult:
    """Tests for full pipeline result persistence."""
    
    def test_persist_pipeline_result_complete(self, mock_session):
        """Should persist full pipeline with all agent results."""
        pipeline_result = {
            "company": "NVIDIA",
            "ticker": "NVDA",
            "results": {
                "news_analysis": {
                    "status": "success",
                    "data": {"articles": 5},
                    "usage": {"total_tokens": 1000, "cost_usd": 0.001}
                },
                "market_data": {
                    "status": "success", 
                    "data": {"price": 500},
                    "usage": {"total_tokens": 800, "cost_usd": 0.0008}
                },
                "financial_analysis": {
                    "status": "error",
                    "error": "No documents found",
                    "usage": {}
                }
            }
        }
        
        # Mock company lookup to return new company
        mock_session.query_results = {"Company": None}
        
        result = persist_pipeline_result(mock_session, pipeline_result)
        
        assert "report_id" in result
        assert "company_id" in result
        assert mock_session.committed
        
        # Should have added: 1 company + 1 report + 3 agent runs = 5 objects
        assert len(mock_session.added_objects) >= 5
        
    def test_persist_pipeline_result_reuses_company(self, mock_session):
        """Should reuse existing company if found."""
        existing_company = Company(id="comp1", name="NVIDIA", ticker="NVDA")
        mock_session.query_results = {"Company": existing_company}
        
        pipeline_result = {
            "company": "NVIDIA",
            "ticker": "NVDA", 
            "results": {
                "news_analysis": {"status": "success", "data": {}}
            }
        }
        
        result = persist_pipeline_result(mock_session, pipeline_result)
        
        # Should not add new company
        companies_added = [o for o in mock_session.added_objects if isinstance(o, Company)]
        assert len(companies_added) == 0


class TestInitDB:
    """Tests for database initialization."""
    
    @patch("database.get_engine")
    @patch("database.models.Base.metadata.create_all")
    def test_init_db_creates_tables(self, mock_create_all, mock_get_engine):
        """Should create all tables on init."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        settings = MagicMock()
        settings.postgres_host = "localhost"
        settings.postgres_port = 5432
        settings.postgres_db = "test_db"
        settings.postgres_user = "test_user"
        settings.postgres_password = "test_pass"
        
        init_db(settings)
        
        mock_get_engine.assert_called_once_with(settings)
        mock_create_all.assert_called_once_with(mock_engine)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])