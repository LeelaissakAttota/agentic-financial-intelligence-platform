"""
Data Financial Documents Package - Financial Document Intelligence

Phase 4: Financial Document Intelligence

Modules:
- parser: Multi-backend PDF parser (PyMuPDF, pdfplumber, pdfminer)
- tables: Financial table extraction and parsing
- parsers: Annual reports, quarterly reports, investor presentations
- investor_presentation_parser: Investor presentation parsing
"""

from data.financial_documents.parser import (
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
)

from data.financial_documents.tables import (
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
)

from data.financial_documents.investor_presentation_parser import (
    InvestorPresentationData,
    InvestorPresentationParser,
)

__all__ = [
    # Parser
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
    
    # Investor Presentation Parser
    "InvestorPresentationData",
    "InvestorPresentationParser",
]