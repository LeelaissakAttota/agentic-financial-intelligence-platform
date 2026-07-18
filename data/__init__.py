"""
Data Package - Financial Data Intelligence

This package contains all data processing modules for the Financial Research Agent:
- news: News intelligence pipeline (Phase 2.2+)
- entity_recognition: Financial entity recognition (Phase 2.3)
- sec: SEC filing downloader (Phase 4)
- filings: Filing processing, caching, incremental updates (Phase 4)
- earnings: Earnings call transcript processing (Phase 4)
- annual_reports: Annual/quarterly report and presentation parsers (Phase 4)
- financial_documents: PDF parsing, table extraction, financial statement parsing (Phase 4)
- portfolio: Portfolio management, orders, positions, risk (Phase 5)
- patterns: Pattern detection, historical patterns (Phase 5)
- alerts: Alert engine, notifications (Phase 5)
- analytics: Advanced analytics, reporting (Phase 5)
- intelligence: Historical intelligence, trend analysis (Phase 5)
- memory: Cross-agent memory sharing (Phase 5)
- knowledge_graph: Knowledge graph persistence (Phase 5)
"""

from data.news import (
    NewsArticle,
    NewsSummary,
    NewsCategory,
    SentimentLabel,
    NewsSource,
    NewsAgentInput,
    NewsAgentOutput,
    WorkerResponse,
    CompanyMention,
    PersonMention,
    EventDetection,
    ArticleSentiment,
)

from data.sec import (
    SECDownloader,
    SECFiling,
    SECCompanyInfo,
    SECRateLimiter,
    SECCache,
    create_sec_downloader,
    SEC_FORM_TYPES,
    SEC_BASE_URL,
    SEC_SEARCH_URL,
    SEC_API_URL,
    SEC_SUBMISSIONS_URL,
)

from data.filings import (
    DocumentCache,
    DocumentCache,
    MemoryCacheBackend,
    SQLiteCacheBackend,
    CacheBackend,
    CacheEntry,
    CacheStats,
    DocumentVersion,
    create_document_cache,
    IncrementalUpdater,
    UpdateConfig,
    UpdateResult,
    UpdateStatus,
    IncrementalRAGUpdater,
    create_incremental_updater,
)

from data.earnings import (
    EarningsCallTranscriptParser,
    EarningsCallProcessor,
    EarningsCallTranscript,
    Speaker,
    TranscriptSection,
    QAExchange,
    GuidanceItem,
    KeyMetric,
)

from data.annual_reports import (
    AnnualReportParser,
    AnnualReportData,
    QuarterlyReportParser,
    QuarterlyReportData,
    InvestorPresentationParser,
    InvestorPresentationData,
)

from data.financial_documents import (
    PDFParser,
    PDFParserBackend,
    PyMuPDFBackend,
    PDFPlumberBackend,
    PDFMinerBackend,
    FinancialDocumentParser,
    PDFParserFactory,
    ParserResult,
    ExtractedPage,
    ExtractedTable,
    DocumentMetadata,
    PDFPLUMBER_AVAILABLE,
    PDFMINER_AVAILABLE,
    parse_pdf,
    parse_financial_pdf,
    extract_tables_from_pdf,
    extract_text_from_pdf,
    
    FinancialTableExtractor,
    TableExtractionResult,
    FinancialTable,
    ChartExtractor,
    FootnoteExtractor,
    FinancialStatementParser,
    IncomeStatementParser,
    BalanceSheetParser,
    CashFlowParser,
    FinancialStatementParserFactory,
    SegmentInformationExtractor,
    ManagementDiscussionExtractor,
    RiskFactorsExtractor,
    BusinessOverviewExtractor,
    EarningsCallTranscriptParser,
    InvestorPresentationParser,
    FinancialDocumentParserFactory,
    
    # Investor Presentation Parser
    InvestorPresentationData,
    InvestorPresentationParser,
)

# Phase 5: Knowledge Persistence & Advanced Analytics
from data.portfolio import (
    OrderSide,
    OrderType,
    OrderStatus,
    PositionSide,
    RebalanceStrategy,
    Order,
    Position,
    Portfolio,
    Transaction,
    PortfolioSnapshot,
    PortfolioBackend,
    PostgresPortfolioBackend,
    PortfolioManager,
    AlertManager,
    create_portfolio_manager,
)

from data.patterns import (
    PatternType,
    PatternConfidence,
    Pattern,
    PatternMatch,
    PatternBackend,
    PostgresPatternBackend,
    PatternDetector,
    PatternAnalytics,
    create_pattern_detector,
)

from data.alerts import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    AlertChannel,
    AlertCondition,
    AlertRule,
    Alert,
    AlertBackend,
    PostgresAlertBackend,
    AlertEvaluator,
    AlertEngine,
    create_alert_engine,
    DEFAULT_ALERT_TEMPLATES,
)

from data.analytics import (
    AnalyticsBackend,
    AnalyticsReport,
    QuantAnalysis,
    FactorAnalysis,
    RiskMetrics,
    AnalyticsEngine,
    create_analytics_engine,
)

from data.intelligence import (
    IntelligenceBackend,
    PostgresIntelligenceBackend,
    HistoricalReport,
    HistoricalNews,
    HistoricalFiling,
    HistoricalSentiment,
    HistoricalIntelligence,
    PostgresIntelligenceBackend,
    create_historical_intelligence,
)

from data.memory import (
    MemoryType,
    MemorySource,
    MemoryScope,
    MemoryEntry,
    MemoryBackend,
    PostgresMemoryBackend,
    CrossAgentMemory,
    create_cross_agent_memory,
)

from data.knowledge_graph import (
    NodeType,
    RelationshipType,
    GraphNode,
    GraphEdge,
    GraphBackend,
    PostgresGraphBackend,
    KnowledgeGraph,
)

__all__ = [
    # News
    "NewsArticle",
    "NewsSummary",
    "NewsCategory",
    "SentimentLabel",
    "NewsSource",
    "NewsAgentInput",
    "NewsAgentOutput",
    "WorkerResponse",
    "CompanyMention",
    "PersonMention",
    "EventDetection",
    "ArticleSentiment",
    
    # SEC
    "SECDownloader",
    "SECFiling",
    "SECCompanyInfo",
    "SECRateLimiter",
    "SECCache",
    "create_sec_downloader",
    "SEC_FORM_TYPES",
    "SEC_BASE_URL",
    "SEC_SEARCH_URL",
    "SEC_API_URL",
    "SEC_SUBMISSIONS_URL",
    
    # Filings
    "DocumentCache",
    "DocumentCache",
    "MemoryCacheBackend",
    "SQLiteCacheBackend",
    "CacheBackend",
    "CacheEntry",
    "CacheStats",
    "DocumentVersion",
    "create_document_cache",
    "IncrementalUpdater",
    "UpdateConfig",
    "UpdateResult",
    "UpdateStatus",
    "IncrementalRAGUpdater",
    "create_incremental_updater",
    
    # Earnings
    "EarningsCallTranscriptParser",
    "EarningsCallProcessor",
    "EarningsCallTranscript",
    "Speaker",
    "TranscriptSection",
    "QAExchange",
    "GuidanceItem",
    "KeyMetric",
    
    # Annual Reports
    "AnnualReportParser",
    "AnnualReportData",
    "QuarterlyReportParser",
    "QuarterlyReportData",
    "InvestorPresentationParser",
    "InvestorPresentationData",
    
    # Financial Documents
    "PDFParser",
    "PDFParserBackend",
    "PyMuPDFBackend",
    "PDFPlumberBackend",
    "PDFMinerBackend",
    "FinancialDocumentParser",
    "PDFParserFactory",
    "ParserResult",
    "ExtractedPage",
    "ExtractedTable",
    "DocumentMetadata",
    "PDFPLUMBER_AVAILABLE",
    "PDFMINER_AVAILABLE",
    "parse_pdf",
    "parse_financial_pdf",
    "extract_tables_from_pdf",
    "extract_text_from_pdf",
    
    # Tables
    "FinancialTableExtractor",
    "TableExtractionResult",
    "FinancialTable",
    "ChartExtractor",
    "FootnoteExtractor",
    "FinancialStatementParser",
    "IncomeStatementParser",
    "BalanceSheetParser",
    "CashFlowParser",
    "FinancialStatementParserFactory",
    "SegmentInformationExtractor",
    "ManagementDiscussionExtractor",
    "RiskFactorsExtractor",
    "BusinessOverviewExtractor",
    "EarningsCallTranscriptParser",
    "InvestorPresentationParser",
    "FinancialDocumentParserFactory",
    
    # Phase 5: Portfolio
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "PositionSide",
    "RebalanceStrategy",
    "Order",
    "Position",
    "Portfolio",
    "Transaction",
    "PortfolioSnapshot",
    "PortfolioBackend",
    "PostgresPortfolioBackend",
    "PortfolioManager",
    "AlertManager",
    "create_portfolio_manager",
    
    # Phase 5: Patterns
    "PatternType",
    "PatternConfidence",
    "Pattern",
    "PatternMatch",
    "PatternBackend",
    "PostgresPatternBackend",
    "PatternDetector",
    "PatternAnalytics",
    "create_pattern_detector",
    
    # Phase 5: Alerts
    "AlertSeverity",
    "AlertStatus",
    "AlertType",
    "AlertChannel",
    "AlertCondition",
    "AlertRule",
    "Alert",
    "AlertBackend",
    "PostgresAlertBackend",
    "AlertEvaluator",
    "AlertEngine",
    "create_alert_engine",
    "DEFAULT_ALERT_TEMPLATES",
    
    # Phase 5: Analytics
    "AnalyticsBackend",
    "AnalyticsReport",
    "QuantAnalysis",
    "FactorAnalysis",
    "RiskMetrics",
    "AnalyticsEngine",
    "create_analytics_engine",
    
    # Phase 5: Intelligence
    "IntelligenceBackend",
    "PostgresIntelligenceBackend",
    "HistoricalReport",
    "HistoricalNews",
    "HistoricalFiling",
    "HistoricalSentiment",
    "HistoricalIntelligence",
    "PostgresIntelligenceBackend",
    "create_historical_intelligence",
    
    # Phase 5: Cross-Agent Memory
    "MemoryType",
    "MemorySource",
    "MemoryScope",
    "MemoryEntry",
    "MemoryBackend",
    "PostgresMemoryBackend",
    "CrossAgentMemory",
    "create_cross_agent_memory",
    
    # Phase 5: Knowledge Graph
    "NodeType",
    "RelationshipType",
    "GraphNode",
    "GraphEdge",
    "GraphBackend",
    "PostgresGraphBackend",
    "KnowledgeGraph",
]