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
    
    # Annual Reports (duplicate imports for backward compatibility)
    "AnnualReportParser",
    "AnnualReportData",
    "QuarterlyReportParser",
    "QuarterlyReportData",
    "InvestorPresentationParser",
    "InvestorPresentationData",
]