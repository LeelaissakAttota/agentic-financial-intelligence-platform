"""
Metadata Extractor for Financial Documents.

Extracts structured metadata from financial documents including company identification,
document type, fiscal periods, and SEC filing information.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .pdf_processor import DocumentMetadata, ExtractedPage

logger = logging.getLogger(__name__)


@dataclass
class FinancialMetadata:
    """Enhanced financial document metadata."""
    # Base document info
    file_path: str
    file_hash: str
    page_count: int
    
    # Company identification
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    cik: Optional[str] = None
    
    # Document classification
    document_type: Optional[str] = None  # 10k, 10q, 8k, annual_report, earnings, presentation
    filing_type: Optional[str] = None    # SEC form type
    
    # Fiscal period
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    period_end_date: Optional[date] = None
    filing_date: Optional[date] = None
    
    # SEC identifiers
    accession_number: Optional[str] = None
    file_number: Optional[str] = None
    
    # Content indicators
    has_financial_statements: bool = False
    has_mdna: bool = False  # Management Discussion & Analysis
    has_risk_factors: bool = False
    has_segment_info: bool = False
    has_footnotes: bool = False
    
    # Processing metadata
    extraction_date: date = field(default_factory=date.today)
    confidence_scores: dict[str, float] = field(default_factory=dict)
    
    # Raw extraction for debugging
    raw_indicators: dict[str, list[str]] = field(default_factory=dict)


class MetadataExtractor:
    """Extracts structured metadata from financial documents."""
    
    # Company name patterns (common formats in 10-K/10-Q)
    COMPANY_PATTERNS = [
        r"(?i)^\s*([A-Z][A-Za-z0-9\s&.'\-]+(?:Inc|Corp|Corporation|Company|Co|LLC|Ltd|Limited|Holdings|Group|Systems|Technologies|Pharmaceuticals|Biotechnology|Therapeutics))\s*$",
        r"(?i)exact\s+name\s+of\s+registrant\s+as\s+specified\s+in\s+its\s+charter[:\s]+([^\n]+)",
        r"(?i)registrant[:\s]+([^\n]+)",
    ]
    
    # Document type patterns
    DOC_TYPE_PATTERNS = {
        "10k": [
            r"(?i)form\s+10[- ]?k",
            r"(?i)annual\s+report\s+pursuant\s+to\s+section\s+13\s+or\s+15\(d\)",
        ],
        "10q": [
            r"(?i)form\s+10[- ]?q",
            r"(?i)quarterly\s+report\s+pursuant\s+to\s+section\s+13\s+or\s+15\(d\)",
        ],
        "8k": [
            r"(?i)form\s+8[- ]?k",
            r"(?i)current\s+report",
        ],
        "annual_report": [
            r"(?i)annual\s+report\s+(?:to\s+shareholders|for\s+the\s+fiscal\s+year)",
            r"(?i)year\s+ended\s+\w+\s+\d{4}",
        ],
        "earnings": [
            r"(?i)earnings\s+(?:release|report|announcement)",
            r"(?i)quarterly\s+earnings",
            r"(?i)q[1-4]\s+\d{4}\s+earnings",
        ],
        "presentation": [
            r"(?i)investor\s+presentation",
            r"(?i)earnings\s+presentation",
            r"(?i)company\s+presentation",
        ],
    }
    
    # CIK patterns
    CIK_PATTERNS = [
        r"(?i)cik\s*[:\-]?\s*(\d{10})",
        r"(?i)central\s+index\s+key\s*[:\-]?\s*(\d{10})",
        r"(?i)commission\s+file\s+number\s*[:\-]?\s*(\d{10})",
    ]
    
    # Accession number pattern
    ACCESSION_PATTERN = r"(?i)accession\s+number\s*[:\-]?\s*(\d{10}-\d{2}-\d{6})"
    
    # Fiscal year/quarter patterns
    FISCAL_PATTERNS = {
        "year": [
            r"(?i)fiscal\s+year\s+(?:ended|ending)?\s*:?\s*(\d{4})",
            r"(?i)for\s+the\s+fiscal\s+year\s+ended\s+\w+\s+\d{1,2},\s*(\d{4})",
            r"(?i)year\s+ended\s+\w+\s+\d{1,2},\s*(\d{4})",
        ],
        "quarter": [
            r"(?i)fiscal\s+quarter\s+([1-4])\s+(?:ended|ending)?\s*:?\s*\d{4}",
            r"(?i)quarter\s+ended\s+\w+\s+\d{1,2},\s*\d{4}",
            r"(?i)q([1-4])\s+\d{4}",
        ],
        "period_end": [
            r"(?i)period\s+ended\s*[:\-]?\s*(\w+\s+\d{1,2},\s*\d{4})",
            r"(?i)as\s+of\s+(\w+\s+\d{1,2},\s*\d{4})",
        ],
    }
    
    # Section detection keywords
    SECTION_KEYWORDS = {
        "financial_statements": [
            "consolidated balance sheet", "consolidated statement of operations",
            "consolidated statement of income", "consolidated statement of cash flows",
            "consolidated statement of comprehensive income", "balance sheet",
            "income statement", "statement of cash flows", "statement of earnings",
        ],
        "mdna": [
            "management's discussion and analysis", "md&a", "mda",
            "discussion and analysis of financial condition",
        ],
        "risk_factors": [
            "risk factors", "item 1a", "item 1.a",
        ],
        "segments": [
            "segment information", "operating segments", "reportable segments",
            "business segments", "segment reporting",
        ],
        "footnotes": [
            "notes to consolidated financial statements", "notes to financial statements",
            "footnotes", "note 1", "note 2",
        ],
    }
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
    
    def extract(self, pages: list[ExtractedPage], base_metadata: DocumentMetadata) -> FinancialMetadata:
        """
        Extract financial metadata from processed document pages.
        
        Args:
            pages: List of extracted pages from PDFProcessor
            base_metadata: Base metadata from PDFProcessor
            
        Returns:
            FinancialMetadata with all extracted information
        """
        # Combine all text for analysis
        full_text = "\n\n".join(page.text for page in pages)
        
        # Start with base metadata
        metadata = FinancialMetadata(
            file_path=base_metadata.file_path,
            file_hash=base_metadata.file_hash,
            page_count=base_metadata.page_count,
            company_name=base_metadata.company_name,
            document_type=base_metadata.document_type,
            fiscal_year=base_metadata.fiscal_year,
            fiscal_quarter=base_metadata.fiscal_quarter,
            filing_date=base_metadata.filing_date,
            accession_number=base_metadata.accession_number,
            cik=base_metadata.cik,
        )
        
        # Extract from text content
        self._extract_company_info(full_text, metadata)
        self._extract_document_type(full_text, metadata)
        self._extract_sec_identifiers(full_text, metadata)
        self._extract_fiscal_period(full_text, metadata)
        self._detect_content_sections(full_text, metadata)
        
        # Calculate confidence scores
        self._calculate_confidence(metadata)
        
        return metadata
    
    def _extract_company_info(self, text: str, metadata: FinancialMetadata):
        """Extract company name and ticker from document text."""
        # Look in first few pages for company name
        first_pages_text = text[:10000]
        
        for pattern in self.COMPANY_PATTERNS:
            match = re.search(pattern, first_pages_text, re.MULTILINE)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) > 5 and len(candidate) < 200:
                    metadata.company_name = candidate
                    metadata.raw_indicators.setdefault("company_name", []).append(candidate)
                    break
        
        # Extract ticker if present (usually in header/footer or first page)
        ticker_match = re.search(r"(?i)(?:nasdaq|nyse|ticker)\s*[:\(]\s*([A-Z]{1,5})\s*[\)]", first_pages_text)
        if ticker_match:
            metadata.ticker = ticker_match.group(1).upper()
    
    def _extract_document_type(self, text: str, metadata: FinancialMetadata):
        """Classify document type from content."""
        first_pages = text[:15000].lower()
        
        scores = {}
        for doc_type, patterns in self.DOC_TYPE_PATTERNS.items():
            score = 0
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, first_pages)
                if found:
                    score += len(found)
                    matches.extend(found)
            if score > 0:
                scores[doc_type] = score
                metadata.raw_indicators.setdefault("document_type", []).extend(matches)
        
        if scores:
            # Pick highest scoring type
            metadata.document_type = max(scores, key=scores.get)
            metadata.confidence_scores["document_type"] = min(scores[metadata.document_type] / 10.0, 1.0)
    
    def _extract_sec_identifiers(self, text: str, metadata: FinancialMetadata):
        """Extract SEC filing identifiers (CIK, accession number)."""
        # CIK
        for pattern in self.CIK_PATTERNS:
            match = re.search(pattern, text)
            if match:
                cik = match.group(1).zfill(10)
                metadata.cik = cik
                metadata.raw_indicators.setdefault("cik", []).append(cik)
                break
        
        # Accession number
        match = re.search(self.ACCESSION_PATTERN, text)
        if match:
            metadata.accession_number = match.group(1)
            metadata.raw_indicators.setdefault("accession_number", []).append(match.group(1))
    
    def _extract_fiscal_period(self, text: str, metadata: FinancialMetadata):
        """Extract fiscal year, quarter, and period end date."""
        # Fiscal year
        for pattern in self.FISCAL_PATTERNS["year"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    year = int(match.group(1))
                    if 1990 <= year <= 2030:
                        metadata.fiscal_year = year
                        metadata.raw_indicators.setdefault("fiscal_year", []).append(str(year))
                        break
                except ValueError:
                    pass
        
        # Fiscal quarter
        for pattern in self.FISCAL_PATTERNS["quarter"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    quarter = int(match.group(1))
                    if 1 <= quarter <= 4:
                        metadata.fiscal_quarter = quarter
                        metadata.raw_indicators.setdefault("fiscal_quarter", []).append(str(quarter))
                        break
                except ValueError:
                    pass
        
        # Period end date
        for pattern in self.FISCAL_PATTERNS["period_end"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    parsed_date = self._parse_date(date_str)
                    if parsed_date:
                        metadata.period_end_date = parsed_date
                        metadata.raw_indicators.setdefault("period_end_date", []).append(date_str)
                        break
                except Exception:
                    pass
    
    def _detect_content_sections(self, text: str, metadata: FinancialMetadata):
        """Detect presence of key financial document sections."""
        text_lower = text.lower()
        
        for section, keywords in self.SECTION_KEYWORDS.items():
            found = []
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    found.append(keyword)
            
            if found:
                setattr(metadata, f"has_{section}", True)
                metadata.raw_indicators.setdefault(f"has_{section}", []).extend(found)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse various date formats."""
        formats = [
            "%B %d, %Y",      # January 15, 2024
            "%b %d, %Y",      # Jan 15, 2024
            "%Y-%m-%d",       # 2024-01-15
            "%m/%d/%Y",       # 01/15/2024
            "%d %B %Y",       # 15 January 2024
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
    
    def _calculate_confidence(self, metadata: FinancialMetadata):
        """Calculate confidence scores for extracted metadata."""
        # Company name confidence
        if metadata.company_name:
            # Higher confidence if found in multiple places
            count = len(metadata.raw_indicators.get("company_name", []))
            metadata.confidence_scores["company_name"] = min(0.5 + count * 0.2, 1.0)
        
        # Document type confidence
        if metadata.document_type:
            count = len(metadata.raw_indicators.get("document_type", []))
            metadata.confidence_scores["document_type"] = min(count * 0.15, 1.0)
        
        # CIK confidence
        if metadata.cik:
            metadata.confidence_scores["cik"] = 0.9
        
        # Fiscal year/quarter confidence
        if metadata.fiscal_year:
            metadata.confidence_scores["fiscal_year"] = 0.85
        if metadata.fiscal_quarter:
            metadata.confidence_scores["fiscal_quarter"] = 0.85
        
        # Section detection confidence
        for section in ["financial_statements", "mdna", "risk_factors", "segments", "footnotes"]:
            if getattr(metadata, f"has_{section}", False):
                count = len(metadata.raw_indicators.get(f"has_{section}", []))
                metadata.confidence_scores[f"has_{section}"] = min(count * 0.2, 1.0)


def create_metadata_extractor(config: Optional[dict] = None) -> MetadataExtractor:
    """Factory function to create MetadataExtractor from config."""
    return MetadataExtractor(config)