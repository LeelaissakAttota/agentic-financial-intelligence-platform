"""
Table Extractor for Financial Documents.

Specialized table extraction for financial statements, schedules, and tabular data.
Supports multiple backends with financial-table-specific logic.
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF

# Optional imports
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None

logger = logging.getLogger(__name__)


@dataclass
class FinancialTable:
    """A financial table with metadata and classification."""
    page_number: int
    table_index: int
    bbox: tuple[float, float, float, float]
    headers: list[str]
    rows: list[list[str]]
    table_type: str  # income_statement, balance_sheet, cash_flow, segment, other
    statement_period: Optional[str] = None  # e.g., "Twelve Months Ended Dec 31, 2023"
    currency: Optional[str] = None  # USD, EUR, etc.
    unit: Optional[str] = None  # thousands, millions, etc.
    confidence: float = 1.0
    raw_data: list[list[str]] = field(default_factory=list)


@dataclass
class TableExtractionResult:
    """Result of table extraction operation."""
    tables: list[FinancialTable]
    total_tables: int
    financial_statement_tables: int
    extraction_time_seconds: float
    parser_used: str
    warnings: list[str] = field(default_factory=list)
    success: bool = True


class FinancialTableExtractor:
    """
    Specialized table extractor for financial documents.
    
    Features:
    - Financial statement detection (Income Statement, Balance Sheet, Cash Flow)
    - Period detection (annual, quarterly, YTD)
    - Currency and unit detection
    - Header normalization
    - Cross-backend table extraction with quality scoring
    """
    
    def __init__(
        self,
        prefer_backend: str = "pdfplumber",
        min_confidence: float = 0.7,
        extract_period_info: bool = True
    ):
        self.prefer_backend = prefer_backend
        self.min_confidence = min_confidence
        self.extract_period_info = extract_period_info
        
        # Financial table type patterns
        self.table_type_patterns = {
            "income_statement": [
                r"consolidated\s+statements?\s+of\s+(income|operations|earnings)",
                r"statement\s+of\s+(income|operations|earnings)",
                r"income\s+statement",
                r"profit\s+and\s+loss",
                r"p&l",
                r"revenue",
                r"net\s+income",
                r"earnings\s+per\s+share",
            ],
            "balance_sheet": [
                r"consolidated\s+balance\s+sheets?",
                r"balance\s+sheets?",
                r"statement\s+of\s+financial\s+position",
                r"assets",
                r"liabilities\s+and\s+(?:stockholders?\s+)?equity",
                r"shareholders?\s+equity",
            ],
            "cash_flow": [
                r"consolidated\s+statements?\s+of\s+cash\s+flows?",
                r"statement\s+of\s+cash\s+flows?",
                r"cash\s+flow\s+statement",
                r"cash\s+flows?\s+from\s+(?:operating|investing|financing)",
                r"operating\s+activities",
                r"investing\s+activities",
                r"financing\s+activities",
            ],
            "comprehensive_income": [
                r"comprehensive\s+income",
                r"other\s+comprehensive\s+income",
            ],
            "statement_of_changes_in_equity": [
                r"statement\s+of\s+(?:stockholders?\s+)?changes\s+in\s+equity",
                r"changes\s+in\s+equity",
            ],
            "segment_information": [
                r"segment\s+information",
                r"operating\s+segments?",
                r"reportable\s+segments?",
                r"business\s+segments?",
            ],
            "notes_to_financial_statements": [
                r"note\s+\d+",
                r"notes?\s+to\s+(?:consolidated\s+)?financial\s+statements",
                r"footnotes",
            ],
        }
        
        # Period patterns
        self.period_patterns = {
            "annual": [
                r"(?:for\s+the\s+)?(?:fiscal\s+)?year\s+ended",
                r"twelve\s+months\s+ended",
                r"year\s+ended",
            ],
            "quarterly": [
                r"(?:fiscal\s+)?quarter\s+ended",
                r"quarter\s+ended",
                r"three\s+months\s+ended",
            ],
            "ytd": [
                r"year\s+to\s+date",
                r"ytd",
                r"nine\s+months\s+ended",
                r"six\s+months\s+ended",
            ],
        }
        
        # Currency patterns
        self.currency_patterns = {
            "USD": [r"\$", r"usd", r"us\s+dollars?", r"dollars?"],
            "EUR": [r"€", r"eur", r"euros?"],
            "GBP": [r"£", r"gbp", r"pounds?"],
            "CAD": [r"cad", r"canadian\s+dollars?"],
            "JPY": [r"¥", r"jpy", r"yen"],
            "CNY": [r"cny", r"rmb", r"yuan"],
        }
        
        # Unit patterns
        self.unit_patterns = {
            "thousands": [r"\(in\s+thousands?\)", r"in\s+thousands?", r"000\s*omitted", r"thousands?"],
            "millions": [r"\(in\s+millions?\)", r"in\s+millions?", r"millions?"],
            "billions": [r"\(in\s+billions?\)", r"in\s+billions?", r"billions?"],
        }
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self._compiled_table_patterns = {}
        for table_type, patterns in self.table_type_patterns.items():
            self._compiled_table_patterns[table_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._compiled_period_patterns = {}
        for period_type, patterns in self.period_patterns.items():
            self._compiled_period_patterns[period_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._compiled_currency_patterns = {}
        for currency, patterns in self.currency_patterns.items():
            self._compiled_currency_patterns[currency] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._compiled_unit_patterns = {}
        for unit, patterns in self.unit_patterns.items():
            self._compiled_unit_patterns[unit] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    async def extract_tables(self, file_path: str | Path) -> TableExtractionResult:
        """Extract financial tables from a PDF document."""
        start_time = asyncio.get_event_loop().time()
        warnings = []
        
        try:
            # Try primary backend first
            result = await self._extract_with_backend(file_path)
            
            if result.success and result.tables:
                return TableExtractionResult(
                    tables=result.tables,
                    total_tables=len(result.tables),
                    financial_statement_tables=len([t for t in result.tables if t.table_type != "other"]),
                    extraction_time_seconds=asyncio.get_event_loop().time() - start_time,
                    parser_used=result.parser_used,
                    warnings=result.warnings,
                    success=True
                )
            
        except Exception as e:
            logger.error(f"Primary backend failed: {e}")
        
        # Fallback to PyMuPDF if pdfplumber failed
        try:
            warnings.append("Falling back to PyMuPDF")
            result = await self._extract_with_pymupdf(file_path)
            return TableExtractionResult(
                tables=result.tables,
                total_tables=len(result.tables),
                financial_statement_tables=len([t for t in result.tables if t.table_type != "other"]),
                extraction_time_seconds=asyncio.get_event_loop().time() - start_time,
                parser_used="pymupdf",
                warnings=warnings,
                success=result.success
            )
        except Exception as e:
            logger.error(f"All backends failed for table extraction: {e}")
        
        return TableExtractionResult(
            tables=[],
            total_tables=0,
            financial_statement_tables=0,
            extraction_time_seconds=asyncio.get_event_loop().time() - start_time,
            parser_used="none",
            warnings=warnings,
            success=False
        )
    
    async def _extract_with_backend(self, file_path: Path) -> TableExtractionResult:
        """Extract tables using preferred backend."""
        if self.prefer_backend == "pdfplumber":
            return await self._extract_with_pdfplumber(file_path)
        elif self.prefer_backend == "pymupdf":
            return await self._extract_with_pymupdf(file_path)
        else:
            return TableExtractionResult(tables=[], total_tables=0, financial_statement_tables=0,
                                        extraction_time_seconds=0, parser_used="none", success=False)
    
    async def _extract_with_pdfplumber(self, file_path: Path) -> TableExtractionResult:
        """Extract tables using pdfplumber (best for financial tables)."""
        if not PDFPLUMBER_AVAILABLE:
            raise RuntimeError("pdfplumber not available")
        
        import pdfplumber
        start_time = asyncio.get_event_loop().time()
        
        tables = []
        warnings = []
        
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        tables_data = page.extract_tables()
                        
                        for table_idx, table_data in enumerate(tables_data or []):
                            if not table_data:
                                continue
                            
                            financial_table = self._process_table_data(
                                table_data, page_num + 1, table_idx, pdf.pages[page_num]
                            )
                            
                            if financial_table and financial_table.confidence >= self.min_confidence:
                                tables.append(financial_table)
                    
                    except Exception as e:
                        logger.warning(f"Table extraction failed on page {page_num + 1}: {e}")
                        warnings.append(f"Page {page_num + 1} table extraction failed: {e}")
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return TableExtractionResult(
                tables=tables,
                total_tables=len(tables),
                financial_statement_tables=len([t for t in tables if t.table_type != "other"]),
                extraction_time_seconds=processing_time,
                parser_used="pdfplumber",
                warnings=warnings,
                success=True
            )
            
        except Exception as e:
            return TableExtractionResult(
                tables=[],
                total_tables=0,
                financial_statement_tables=0,
                extraction_time_seconds=0,
                parser_used="pdfplumber",
                warnings=[str(e)],
                success=False
            )
    
    async def _extract_with_pymupdf(self, file_path: Path) -> TableExtractionResult:
        """Extract tables using PyMuPDF."""
        import fitz
        start_time = asyncio.get_event_loop().time()
        
        tables = []
        warnings = []
        
        try:
            doc = fitz.open(str(file_path))
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                try:
                    found_tables = page.find_tables()
                    
                    for idx, table in enumerate(found_tables):
                        rows = table.extract()
                        
                        if not rows:
                            continue
                        
                        financial_table = self._process_table_data(
                            rows, page_num + 1, idx, None
                        )
                        
                        if financial_table and financial_table.confidence >= self.min_confidence:
                            tables.append(financial_table)
                
                except Exception as e:
                    logger.warning(f"Table extraction failed on page {page_num + 1}: {e}")
                    warnings.append(f"Page {page_num + 1} table extraction failed: {e}")
            
            doc.close()
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return TableExtractionResult(
                tables=tables,
                total_tables=len(tables),
                financial_statement_tables=len([t for t in tables if t.table_type != "other"]),
                extraction_time_seconds=processing_time,
                parser_used="pymupdf",
                warnings=warnings,
                success=True
            )
            
        except Exception as e:
            return TableExtractionResult(
                tables=[],
                total_tables=0,
                financial_statement_tables=0,
                extraction_time_seconds=0,
                parser_used="pymupdf",
                warnings=[str(e)],
                success=False
            )
    
    def _process_table_data(
        self,
        table_data: list[list[str]],
        page_number: int,
        table_index: int,
        page_obj: Any = None
    ) -> Optional[FinancialTable]:
        """Process raw table data into a FinancialTable."""
        if not table_data or not table_data[0]:
            return None
        
        # Clean rows
        cleaned_rows = []
        for row in table_data:
            cleaned_row = [cell.strip() if cell else "" for cell in row]
            if any(cell for cell in cleaned_row):  # Skip empty rows
                cleaned_rows.append(cleaned_row)
        
        if not cleaned_rows:
            return None
        
        # Detect headers
        headers = []
        data_rows = cleaned_rows
        if cleaned_rows and self._looks_like_header(cleaned_rows[0]):
            headers = cleaned_rows[0]
            data_rows = cleaned_rows[1:]
        else:
            data_rows = cleaned_rows
        
        # Classify table type
        table_type = self._classify_table_type(headers, data_rows)
        
        # Extract period info
        period = self._extract_period(headers, data_rows) if self.extract_period_info else None
        
        # Extract currency
        currency = self._extract_currency(headers, data_rows)
        
        # Extract unit
        unit = self._extract_unit(headers, data_rows)
        
        # Calculate confidence
        confidence = self._calculate_confidence(table_type, headers, data_rows)
        
        if confidence < self.min_confidence:
            return None
        
        # Create bbox approximation for pdfplumber
        bbox = (0, 0, 612, 792)  # Default letter size
        
        return FinancialTable(
            page_number=page_number,
            table_index=table_index,
            bbox=(0, 0, 612, 792),
            headers=headers,
            rows=data_rows,
            table_type=table_type,
            statement_period=period,
            currency=currency,
            unit=unit,
            confidence=confidence,
            raw_data=table_data
        )
    
    def _process_table_data_pymupdf(
        self,
        rows: list[list[str]],
        page_number: int,
        table_index: int,
        page_obj: Any = None
    ) -> Optional[FinancialTable]:
        """Process table data from PyMuPDF."""
        return self._process_table_data(rows, page_number, table_index, page_obj)
    
    def _looks_like_header(self, row: list[str]) -> bool:
        """Check if a row looks like a header row."""
        if not row:
            return False
        
        non_empty = [cell for cell in row if cell and cell.strip()]
        if not non_empty:
            return False
        
        # Header rows typically have more text, fewer numbers
        text_cells = sum(1 for cell in non_empty 
                        if cell and not cell.replace(".", "").replace(",", "").replace("$", "").replace("%", "").replace(",", "").replace("(", "").replace(")", "").isdigit())
        
        return text_cells > len(non_empty) * 0.5
    
    def _classify_table_type(self, headers: list[str], data_rows: list[list[str]]) -> str:
        """Classify table as financial statement type."""
        all_text = " ".join(headers + [cell for row in data_rows for cell in row if cell]).lower()
        
        for table_type, patterns in self._compiled_table_patterns.items():
            for pattern in patterns:
                if pattern.search(all_text):
                    return table_type
        
        return "other"
    
    def _extract_period(self, headers: list[str], data_rows: list[list[str]]) -> Optional[str]:
        """Extract reporting period from headers and data."""
        all_text = " ".join(headers + [cell for row in data_rows for cell in row if cell]).lower()
        
        for period_type, patterns in self._compiled_period_patterns.items():
            for pattern in patterns:
                match = pattern.search(all_text)
                if match:
                    # Try to extract the date
                    context = all_text[max(0, match.start()-50):match.end()+50]
                    return context.strip()
        
        return None
    
    def _extract_currency(self, headers: list[str], data_rows: list[list[str]]) -> Optional[str]:
        """Detect currency from table."""
        all_text = " ".join(headers + [cell for row in data_rows for cell in row if cell]).lower()
        
        for currency, patterns in self._compiled_currency_patterns.items():
            for pattern in patterns:
                if pattern.search(all_text):
                    return currency
        
        return "USD"  # Default
    
    def _extract_unit(self, headers: list[str], data_rows: list[list[str]]) -> Optional[str]:
        """Extract unit (thousands, millions, etc.)."""
        all_text = " ".join(headers + [cell for row in data_rows for cell in row if cell]).lower()
        
        for unit, patterns in self._compiled_unit_patterns.items():
            for pattern in patterns:
                if pattern.search(all_text):
                    return unit
        
        return None
    
    def _calculate_confidence(self, table_type: str, headers: list[str], data_rows: list[list[str]]) -> float:
        """Calculate confidence score for table classification."""
        if table_type == "other":
            return 0.3
        
        confidence = 0.7  # Base confidence for recognized type
        
        # Boost for strong headers
        if headers and len(headers) > 2:
            confidence += 0.1
        
        # Boost for sufficient data rows
        if len(data_rows) > 3:
            confidence += 0.1
        if len(data_rows) > 10:
            confidence += 0.1
        
        # Boost for numeric content
        numeric_cells = sum(1 for row in data_rows for cell in row 
                           if cell and cell.replace(".", "").replace(",", "").replace("$", "").replace("%", "").replace("(", "").replace(")", "").replace("-", "").isdigit())
        total_cells = sum(len(row) for row in data_rows)
        if total_cells > 0 and numeric_cells / total_cells > 0.3:
            confidence += 0.1
        
        return min(confidence, 1.0)


# Chart extractor placeholder
class ChartExtractor:
    """Extract charts and visualizations from financial documents."""
    
    def __init__(self):
        pass
    
    async def extract_charts(self, file_path: Path) -> list[dict]:
        """Extract chart information from a PDF."""
        # This would use image analysis or chart detection
        # For now, return empty list
        return []


# Footnote extractor
class FootnoteExtractor:
    """Extract footnotes from financial documents."""
    
    def __init__(self):
        self.footnote_patterns = [
            re.compile(r"note\s+\d+", re.IGNORECASE),
            re.compile(r"footnote\s+\d+", re.IGNORECASE),
            re.compile(r"\(\d+\)"),  # (1), (2), etc.
            re.compile(r"\[\d+\]"),  # [1], [2], etc.
        ]
    
    async def extract_footnotes(self, file_path: Path) -> list[dict]:
        """Extract footnotes from a document."""
        # Implementation would parse document for footnote references and content
        # For now, return empty list
        return []


# Financial Statement Parsers
class FinancialStatementParser:
    """Base parser for financial statements."""
    
    def __init__(self):
        pass
    
    def parse(self, table: FinancialTable) -> dict:
        """Parse a financial table into structured data."""
        raise NotImplementedError


class IncomeStatementParser(FinancialStatementParser):
    """Parse income statement tables."""
    
    def parse(self, table: FinancialTable) -> dict:
        """Parse income statement into structured format."""
        # Map common line items to standard names
        line_item_mapping = {
            "revenue": ["revenue", "net sales", "net revenue", "total revenue", "sales"],
            "cost_of_revenue": ["cost of revenue", "cost of goods sold", "cogs", "cost of sales"],
            "gross_profit": ["gross profit", "gross margin"],
            "operating_expenses": ["operating expenses", "total operating expenses"],
            "research_development": ["research and development", "r&d", "research & development"],
            "sales_marketing": ["sales and marketing", "selling and marketing", "selling, general and administrative"],
            "general_admin": ["general and administrative", "g&a", "general & administrative"],
            "operating_income": ["operating income", "operating profit", "income from operations"],
            "interest_expense": ["interest expense", "interest income (expense)"],
            "other_income": ["other income", "other income (expense)", "other income, net"],
            "income_before_tax": ["income before tax", "income before income taxes", "pretax income"],
            "income_tax": ["income tax", "provision for income taxes", "income tax expense"],
            "net_income": ["net income", "net earnings", "net profit", "net loss"],
            "eps_basic": ["basic earnings per share", "basic eps", "earnings per share - basic"],
            "eps_diluted": ["diluted earnings per share", "diluted eps", "earnings per share - diluted"],
        }
        
        result = {
            "statement_type": "income_statement",
            "period": None,
            "currency": "USD",
            "unit": None,
            "line_items": {}
        }
        
        # Extract period, currency, unit from table metadata
        # Map rows to standard line items
        for row in table.rows:
            if not row:
                continue
            
            first_cell = row[0].lower() if row[0] else ""
            
            for standard_name, aliases in line_item_mapping.items():
                for alias in aliases:
                    if alias.lower() in first_cell:
                        # Find the numeric value in the row
                        for cell in row[1:]:
                            if cell and self._is_numeric(cell):
                                result["line_items"][standard_name] = cell
                                break
                        break
        
        return result
    
    def _is_numeric(self, text: str) -> bool:
        """Check if text represents a number."""
        if not text:
            return False
        cleaned = text.replace(",", "").replace("$", "").replace("%", "").replace("(", "").replace(")", "").replace("-", "")
        try:
            float(cleaned)
            return True
        except ValueError:
            return False


class BalanceSheetParser(FinancialStatementParser):
    """Parse balance sheet tables."""
    
    def parse(self, table: FinancialTable) -> dict:
        line_item_mapping = {
            # Assets
            "cash": ["cash and cash equivalents", "cash", "cash equivalents"],
            "short_term_investments": ["short-term investments", "marketable securities"],
            "accounts_receivable": ["accounts receivable", "receivables, net"],
            "inventory": ["inventory", "inventories"],
            "prepaid_expenses": ["prepaid expenses", "prepaids"],
            "current_assets": ["total current assets"],
            "property_plant_equipment": ["property, plant and equipment", "pp&e", "property plant equipment"],
            "goodwill": ["goodwill"],
            "intangible_assets": ["intangible assets", "other intangibles"],
            "total_assets": ["total assets"],
            
            # Liabilities
            "accounts_payable": ["accounts payable", "payables"],
            "short_term_debt": ["short-term debt", "current portion of long-term debt"],
            "current_liabilities": ["total current liabilities"],
            "long_term_debt": ["long-term debt", "long term debt"],
            "total_liabilities": ["total liabilities"],
            
            # Equity
            "common_stock": ["common stock"],
            "retained_earnings": ["retained earnings"],
            "total_equity": ["total equity", "total stockholders' equity", "shareholders' equity"],
        }
        
        result = {
            "statement_type": "balance_sheet",
            "period": None,
            "currency": "USD",
            "unit": None,
            "assets": {},
            "liabilities": {},
            "equity": {}
        }
        
        # Similar parsing logic as IncomeStatementParser
        return result


class CashFlowParser(FinancialStatementParser):
    """Parse cash flow statement tables."""
    
    def parse(self, table: FinancialTable) -> dict:
        line_item_mapping = {
            "operating_cash_flow": ["cash provided by operating activities", "net cash provided by operating activities", "operating cash flow"],
            "net_income": ["net income"],
            "depreciation_amortization": ["depreciation and amortization", "depreciation & amortization"],
            "stock_compensation": ["stock-based compensation", "share-based compensation"],
            "working_capital_changes": ["changes in working capital", "changes in operating assets and liabilities"],
            "investing_cash_flow": ["cash used in investing activities", "net cash used in investing activities"],
            "capex": ["capital expenditures", "purchases of property and equipment", "capex"],
            "acquisitions": ["acquisitions", "business acquisitions"],
            "financing_cash_flow": ["cash provided by financing activities", "net cash provided by financing activities"],
            "dividends_paid": ["dividends paid", "dividends"],
            "share_repurchases": ["repurchase of common stock", "share repurchases", "treasury stock"],
            "debt_issued": ["proceeds from debt", "issuance of debt"],
            "debt_repaid": ["repayment of debt", "debt repayment"],
            "free_cash_flow": ["free cash flow", "fcf"],
        }
        
        result = {
            "statement_type": "cash_flow",
            "period": None,
            "currency": "USD",
            "unit": None,
            "line_items": {}
        }
        
        return result


# Parser factory
class FinancialStatementParserFactory:
    """Factory for creating financial statement parsers."""
    
    _parsers = {
        "income_statement": IncomeStatementParser,
        "balance_sheet": BalanceSheetParser,
        "cash_flow": CashFlowParser,
    }
    
    @classmethod
    def get_parser(cls, table_type: str) -> Optional[FinancialStatementParser]:
        parser_class = cls._parsers.get(table_type)
        if parser_class:
            return parser_class()
        return None
    
    @classmethod
    def register_parser(cls, table_type: str, parser_class: type):
        cls._parsers[table_type] = parser_class
    
    @classmethod
    def parse_table(cls, table: FinancialTable) -> Optional[dict]:
        """Parse a financial table using the appropriate parser."""
        parser = cls.get_parser(table.table_type)
        if parser:
            return parser.parse(table)
        return None


# Segment Information Extractor
class SegmentInformationExtractor:
    """Extract segment information from financial tables."""
    
    def __init__(self):
        pass
    
    async def extract(self, tables: list[FinancialTable]) -> list[dict]:
        """Extract segment information from segment tables."""
        segments = []
        
        for table in tables:
            if table.table_type != "segment_information":
                continue
            
            # Parse segment table
            segment_data = self._parse_segment_table(table)
            if segment_data:
                segments.append(segment_data)
        
        return segments
    
    def _parse_segment_table(self, table: FinancialTable) -> Optional[dict]:
        """Parse a segment information table."""
        # Look for segment names in first column
        # Revenue, profit, assets by segment
        pass
        return None


# Management Discussion Extractor
class ManagementDiscussionExtractor:
    """Extract Management's Discussion and Analysis (MD&A) sections."""
    
    def __init__(self):
        self.mdna_patterns = [
            re.compile(r"item\s+7\.?\s*management['\s]?s\s+discussion\s+and\s+analysis", re.IGNORECASE),
            re.compile(r"management['\s]?s\s+discussion\s+and\s+analysis", re.IGNORECASE),
            re.compile(r"md&a", re.IGNORECASE),
        ]
    
    async def extract(self, file_path: Path) -> dict:
        """Extract MD&A section from document."""
        # Use section splitter to find MD&A
        from ..chunking.section_splitter import SectionDetector, create_chunker
        
        # This would use the section detector to find MD&A
        # For now, return empty structure
        return {
            "overview": "",
            "liquidity": "",
            "capital_resources": "",
            "results_of_operations": "",
            "critical_accounting": "",
            "risk_factors_summary": "",
        }


# Risk Factors Extractor
class RiskFactorsExtractor:
    """Extract risk factors from financial documents."""
    
    def __init__(self):
        self.risk_patterns = [
            re.compile(r"item\s+1a\.?\s*risk\s+factors", re.IGNORECASE),
            re.compile(r"risk\s+factors", re.IGNORECASE),
            re.compile(r"principal\s+risks", re.IGNORECASE),
        ]
    
    async def extract(self, file_path: Path) -> list[dict]:
        """Extract risk factors from document."""
        # Use section splitter to find risk factors section
        # Return structured risk factors
        return []


# Business Overview Extractor
class BusinessOverviewExtractor:
    """Extract business overview from financial documents."""
    
    def __init__(self):
        self.business_patterns = [
            re.compile(r"item\s+1\.?\s*business", re.IGNORECASE),
            re.compile(r"business\s+overview", re.IGNORECASE),
            re.compile(r"our\s+business", re.IGNORECASE),
        ]
    
    async def extract(self, file_path: Path) -> dict:
        """Extract business overview."""
        return {
            "description": "",
            "products_services": [],
            "markets": [],
            "competition": "",
            "regulation": "",
        }


# Earnings Call Transcript Parser
class EarningsCallTranscriptParser:
    """Parse earnings call transcripts."""
    
    def __init__(self):
        self.speaker_patterns = [
            re.compile(r"^([A-Z][a-z]+ [A-Z][a-z]+):\s*(.+)$"),  # "John Smith: Hello"
            re.compile(r"^([A-Z]+):\s*(.+)$"),  # "OPERATOR: Hello"
        ]
        self.section_patterns = [
            re.compile(r"(presentation|prepared remarks|remarks)", re.IGNORECASE),
            re.compile(r"(q&a|question and answer|questions and answers)", re.IGNORECASE),
        ]
    
    async def parse(self, file_path: Path) -> dict:
        """Parse earnings call transcript."""
        # Extract speakers, sections, Q&A
        return {
            "company": "",
            "quarter": "",
            "year": 0,
            "date": None,
            "participants": [],
            "presentation": "",
            "qa": [],
        }
    
    def _parse_speakers(self, text: str) -> list[dict]:
        speakers = []
        for pattern in self.speaker_patterns:
            for match in pattern.finditer(text):
                speakers.append({
                    "speaker": match.group(1),
                    "text": match.group(2)
                })
        return speakers


# Investor Presentation Parser
class InvestorPresentationParser:
    """Parse investor presentations."""
    
    def __init__(self):
        self.slide_patterns = [
            re.compile(r"slide\s+\d+", re.IGNORECASE),
            re.compile(r"page\s+\d+", re.IGNORECASE),
        ]
    
    async def parse(self, file_path: Path) -> dict:
        """Parse investor presentation."""
        # Extract slides, key metrics, guidance
        return {
            "slides": [],
            "key_metrics": {},
            "guidance": {},
        }


# Factory for creating document parsers
class FinancialDocumentParserFactory:
    """Factory for creating document-specific parsers."""
    
    @staticmethod
    def create_parser(document_type: str):
        parsers = {
            "10k": {
                "table_extractor": FinancialTableExtractor(),
                "income_statement": IncomeStatementParser(),
                "balance_sheet": BalanceSheetParser(),
                "cash_flow": CashFlowParser(),
                "mdna": ManagementDiscussionExtractor(),
                "risk_factors": RiskFactorsExtractor(),
                "business": BusinessOverviewExtractor(),
                "segments": SegmentInformationExtractor(),
            },
            "10q": {
                "table_extractor": FinancialTableExtractor(),
                "income_statement": IncomeStatementParser(),
                "balance_sheet": BalanceSheetParser(),
                "cash_flow": CashFlowParser(),
                "mdna": ManagementDiscussionExtractor(),
                "risk_factors": RiskFactorsExtractor(),
            },
            "earnings_transcript": {
                "parser": EarningsCallTranscriptParser(),
            },
            "investor_presentation": {
                "parser": InvestorPresentationParser(),
            },
            "annual_report": {
                "table_extractor": FinancialTableExtractor(),
                "income_statement": IncomeStatementParser(),
                "balance_sheet": BalanceSheetParser(),
                "cash_flow": CashFlowParser(),
                "business": BusinessOverviewExtractor(),
            },
        }
        
        return parsers.get(document_type, parsers["10k"])


# Export
__all__ = [
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
]