"""
Quarterly Report Parser (10-Q).

Parses quarterly reports (10-Q) to extract financial results and key highlights.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from data.financial_documents.parser import parse_financial_pdf, ParserResult

logger = logging.getLogger(__name__)


@dataclass
class QuarterlyReportData:
    """Structured data extracted from a quarterly report (10-Q)."""
    company_name: str
    ticker: Optional[str] = None
    quarter: Optional[str] = None  # Q1, Q2, Q3, Q4
    fiscal_year: Optional[int] = None
    filing_date: Optional[date] = None
    
    # Financial results
    revenue: Optional[float] = None
    revenue_yoy_change: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    eps_yoy_change: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    
    # Guidance
    guidance: dict[str, Any] = field(default_factory=dict)
    
    # Key highlights
    highlights: list[str] = field(default_factory=list)
    
    # Segment performance
    segment_performance: list[dict] = field(default_factory=list)
    
    # MD&A highlights
    mda_summary: str = ""


class QuarterlyReportParser:
    """Parse quarterly reports (10-Q)."""
    
    async def parse(self, file_path: Path) -> QuarterlyReportData:
        result = await parse_financial_pdf(file_path)
        
        if not result.success:
            raise ValueError(f"Failed to parse {file_path}: {result.errors}")
        
        full_text = "\n\n".join(page.text for page in result.pages)
        
        data = QuarterlyReportData(
            company_name="",
            filing_date=None
        )
        
        # Extract quarter and year
        quarter_match = re.search(r'(?:q[1-4]|quarter\s+[1-4])\s+(?:20\d{2})', result.pages[0].text, re.IGNORECASE)
        if quarter_match:
            q_text = quarter_match.group(0).upper()
            q_match = re.search(r'Q([1-4])', q_text)
            y_match = re.search(r'(20\d{2})', q_text)
            if q_match:
                data.quarter = f"Q{q_match.group(1)}"
            if y_match:
                data.fiscal_year = int(y_match.group(1))
        
        # Extract financials
        text = "\n\n".join(page.text for page in result.pages)
        
        # Revenue
        rev_match = re.search(
            r'total\s+revenue\s+(?:of|was|is)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)\s*(?:million|billion|b|m|mm)?',
            full_text, re.IGNORECASE
        )
        if rev_match:
            value = float(rev_match.group(1).replace(',', ''))
            if 'billion' in rev_match.group(0).lower():
                value *= 1e9
            elif 'million' in rev_match.group(0).lower():
                value *= 1e6
            data.revenue = value
        
        # Net income
        ni_match = re.search(
            r'net income\s+(?:of|was|is)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)\s*(?:million|billion|b|m|mm)?',
            text, re.IGNORECASE
        )
        if ni_match:
            value = float(ni_match.group(1).replace(',', ''))
            if 'billion' in ni_match.group(0).lower():
                value *= 1e9
            elif 'million' in ni_match.group(0).lower():
                value *= 1e6
            data.net_income = value
        
        # EPS
        eps_match = re.search(
            r'(?:eps|earnings per share)\s+(?:of|was|is)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)',
            full_text, re.IGNORECASE
        )
        if eps_match:
            data.eps = float(eps_match.group(1).replace(',', ''))
        
        return data


# Export
__all__ = [
    "QuarterlyReportData",
    "QuarterlyReportParser",
]