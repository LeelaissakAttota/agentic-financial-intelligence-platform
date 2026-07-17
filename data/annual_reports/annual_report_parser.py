"""
Annual Report Parser for Financial Document Intelligence.

Parses company annual reports (10-K, Annual Reports) to extract:
- Business overview
- Financial highlights
- Segment information
- Risk factors
- MD&A highlights
- Capital allocation
- Guidance
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from ..financial_documents.parser import parse_financial_pdf

logger = logging.getLogger(__name__)


@dataclass
class AnnualReportData:
    """Structured data extracted from an annual report."""
    company_name: str
    ticker: Optional[str] = None
    fiscal_year: Optional[int] = None
    filing_date: Optional[date] = None
    cik: Optional[str] = None
    
    # Business overview
    business_description: str = ""
    products_services: list[str] = field(default_factory=list)
    markets: list[str] = field(default_factory=list)
    competitive_position: str = ""
    
    # Financial highlights
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    free_cash_flow: Optional[float] = None
    
    # Key metrics
    key_metrics: dict[str, Any] = field(default_factory=dict)
    
    # Business segments
    segments: list[dict] = field(default_factory=list)
    
    # Risk factors
    risk_factors: list[str] = field(default_factory=list)
    
    # MD&A highlights
    mda_highlights: dict[str, str] = field(default_factory=dict)
    
    # Capital allocation
    dividends: Optional[float] = None
    buybacks: Optional[float] = None
    capex: Optional[float] = None
    
    # Guidance
    guidance: dict[str, Any] = field(default_factory=dict)
    
    # ESG
    esg_highlights: dict[str, Any] = field(default_factory=dict)
    
    # Source
    source_file: Optional[str] = None
    pages_processed: int = 0
    extraction_confidence: float = 0.0


class AnnualReportParser:
    """
    Parse company annual reports (10-K, Annual Reports).
    
    Extracts:
    - Business overview
    - Financial highlights
    - Segment information
    - Risk factors
    - MD&A key points
    - Capital allocation
    - Guidance
    """
    
    def __init__(self):
        from rag.chunking.section_splitter import create_chunker
        self.chunker = create_chunker()
    
    async def parse(self, file_path: Path) -> AnnualReportData:
        """Parse annual report PDF or HTML."""
        # Parse document
        result = await parse_financial_pdf(file_path)
        
        if not result.success:
            raise ValueError(f"Failed to parse {file_path}: {result.errors}")
        
        # Combine text
        full_text = "\n\n".join(page.text for page in result.pages)
        
        # Create base data
        data = AnnualReportData(
            source_file=str(file_path),
            pages_processed=len(result.pages)
        )
        
        # Extract metadata from first pages
        await self._extract_metadata(full_text, data, result)
        
        # Extract business overview
        await self._extract_business_overview(full_text, data)
        
        # Extract financial highlights
        await self._extract_financial_highlights(full_text, data)
        
        # Extract segments
        await self._extract_segments(full_text, data)
        
        # Extract MD&A highlights
        await self._extract_mda_highlights(full_text, data)
        
        # Extract risk factors
        await self._extract_risk_factors(full_text, data)
        
        # Extract capital allocation
        await self._extract_capital_allocation(full_text, data)
        
        # Extract guidance
        await self._extract_guidance(full_text, data)
        
        # Calculate confidence
        data.extraction_confidence = self._calculate_confidence(data)
        
        return data
    
    async def _extract_metadata(self, text: str, data: AnnualReportData, result):
        """Extract company metadata from document."""
        # Try to find company name
        lines = text.split('\n')[:50]
        for line in lines:
            if any(keyword in line.lower() for keyword in ['corporation', 'inc.', 'inc', 'company', 'ltd', 'llc']):
                data.company_name = line.strip()
                break
        
        # Try to find ticker
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', text[:5000])
        if ticker_match:
            data.ticker = ticker_match.group(1)
        
        # Try to find CIK
        cik_match = re.search(r'cik[:\\s]*(\d{10})', text, re.IGNORECASE)
        if cik_match:
            data.cik = cik_match.group(1)
        
        # Find fiscal year
        year_matches = re.findall(r'(?:fiscal\s+year|year\s+ended)\s+(?:20\d{2})', text, re.IGNORECASE)
        if year_matches:
            year_match = re.search(r'(20\d{2})', year_matches[0])
            if year_match:
                data.fiscal_year = int(year_match.group(1))
        
        # Filing date
        date_match = re.search(r'filed\s+(?:on\s+)?(\w+\s+\d{1,2},?\s+20\d{2})', text, re.IGNORECASE)
        if date_match:
            try:
                data.filing_date = datetime.strptime(date_match.group(1), "%B %d, %Y").date()
            except:
                pass
    
    async def _extract_business_overview(self, text: str, data: AnnualReportData):
        """Extract business description and overview."""
        # Find business section
        patterns = [
            r'(?i)(?:item\s+1\.?\s*business|business\s+overview|our\s+business)',
            r'(?i)(?:who\s+we\s+are|company\s+overview)',
        ]
        
        business_text = self._extract_section(text, patterns, max_chars=10000)
        
        if business_text:
            data.business_description = business_text[:5000]
            
            # Extract products/services
            product_matches = re.findall(
                r'(?:products?|services?|solutions?|offerings?)[:\\s]+([^\n]{20,200})',
                business_text, re.IGNORECASE
            )
            data.products_services = [p.strip() for p in product_matches[:10]]
            
            # Extract markets
            market_matches = re.findall(
                r'(?:markets?|customers?|industries?|sectors?)[:\\s]+([^\n]{20,200})',
                business_text, re.IGNORECASE
            )
            data.markets = [m.strip() for m in market_matches[:10]]
    
    async def _extract_financial_highlights(self, text: str, data: AnnualReportData):
        """Extract key financial highlights."""
        # Revenue
        rev_match = re.search(
            r'(?:total\s+)?revenue\s+(?:of|was|is|amounted to)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)\s*(?:million|billion|b|m|mm)?',
            text, re.IGNORECASE
        )
        if rev_match:
            value = float(rev_match.group(1).replace(',', ''))
            if 'billion' in rev_match.group(0).lower() or 'b ' in rev_match.group(0).lower():
                value *= 1e9
            elif 'million' in rev_match.group(0).lower() or 'm ' in rev_match.group(0).lower():
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
            text, re.IGNORECASE
        )
        if eps_match:
            data.eps = float(eps_match.group(1).replace(',', ''))
        
        # Margins
        gm_match = re.search(r'gross margin\s+(?:of|was|is)\s*([\d,\.]+)\s*%', text, re.IGNORECASE)
        if gm_match:
            data.gross_margin = float(gm_match.group(1))
        
        om_match = re.search(r'operating margin\s+(?:of|was|is)\s*([\d,\.]+)\s*%', text, re.IGNORECASE)
        if om_match:
            data.operating_margin = float(om_match.group(1))
        
        # Free cash flow
        fcf_match = re.search(
            r'free cash flow\s+(?:of|was|is)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)\s*(?:million|billion|b|m|mm)?',
            text, re.IGNORECASE
        )
        if fcf_match:
            value = float(fcf_match.group(1).replace(',', ''))
            if 'billion' in fcf_match.group(0).lower():
                value *= 1e9
            elif 'million' in fcf_match.group(0).lower():
                value *= 1e6
            data.free_cash_flow = value
    
    async def _extract_segments(self, text: str, data: AnnualReportData):
        """Extract business segment information."""
        # Look for segment reporting section
        segment_patterns = [
            r'(?i)(?:segment\s+information|reportable\s+segments?|operating\s+segments?)',
            r'(?i)item\s+2\.?\s*properties',  # Sometimes segments in Item 2
        ]
        
        segment_text = self._extract_section(text, segment_patterns, max_chars=15000)
        
        if segment_text:
            # Look for segment names and metrics
            segment_pattern = re.compile(
                r'([A-Z][A-Za-z\s]{3,30})\s*(?:segment|division)?[:\\s]+.*?(?:revenue|sales|income).*?[\$£€]?\s*([\d,\.]+)',
                re.IGNORECASE | re.DOTALL
            )
            
            for match in re.finditer(segment_pattern, segment_text):
                segment_name = match.group(1).strip()
                revenue_str = match.group(2).replace(',', '')
                try:
                    revenue = float(revenue_str)
                    data.segments.append({
                        'name': segment_name,
                        'revenue': revenue,
                        'type': 'operating_segment'
                    })
                except:
                    pass
    
    async def _extract_mda_highlights(self, text: str, data: AnnualReportData):
        """Extract key MD&A highlights."""
        # Find MD&A section
        mda_patterns = [
            r'(?i)(?:item\s+7\.?\s*management\'?s\s+discussion\s+and\s+analysis|md&a|management\'s\s+discussion)',
        ]
        
        mda_text = self._extract_section(text, mda_patterns, max_chars=20000)
        
        if mda_text:
            # Extract key topics
            highlights = {}
            
            # Liquidity and capital resources
            liquidity_text = self._extract_subsection(mda_text, [
                r'(?i)(?:liquidity\s+and\s+capital\s+resources|capital\s+resources\s+and\s+liquidity)'
            ])
            if liquidity_text:
                highlights['liquidity'] = liquidity_text[:2000]
            
            # Results of operations
            results_text = self._extract_subsection(mda_text, [
                r'(?i)(?:results\s+of\s+operations|operating\s+results)'
            ])
            if results_text:
                highlights['results_of_operations'] = results_text[:2000]
            
            # Critical accounting estimates
            critical_text = self._extract_subsection(mda_text, [
                r'(?i)(?:critical\s+accounting\s+(?:estimates|policies))'
            ])
            if critical_text:
                highlights['critical_accounting'] = critical_text[:2000]
            
            # Contractual obligations
            contract_text = self._extract_subsection(mda_text, [
                r'(?i)(?:contractual\s+obligations|off-balance\s+sheet)'
            ])
            if contract_text:
                highlights['contractual_obligations'] = contract_text[:2000]
            
            data.mda_highlights = highlights
    
    async def _extract_risk_factors(self, text: str, data: AnnualReportData):
        """Extract risk factors."""
        risk_patterns = [
            r'(?i)(?:item\s+1a\.?\s*risk\s+factors|risk\s+factors)',
        ]
        
        risk_text = self._extract_section(text, risk_patterns, max_chars=30000)
        
        if risk_text:
            # Extract individual risk factors (often numbered or bulleted)
            risk_factors = re.findall(
                r'(?:^|\n)\s*(?:\d+\.|-\s+|\*\s+)([^\n]{50,500})',
                risk_text
            )
            data.risk_factors = [r.strip() for r in risk_factors[:50]]
    
    async def _extract_capital_allocation(self, text: str, data: AnnualReportData):
        """Extract capital allocation information."""
        # Dividends
        div_match = re.search(
            r'(?:dividend|dividends)\s+(?:of|was|is|declared|paid)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)\s*(?:per\s+share|per share)?',
            text, re.IGNORECASE
        )
        if div_match:
            data.dividends = float(div_match.group(1).replace(',', ''))
        
        # Share buybacks
        buyback_match = re.search(
            r'(?:repurchase|buyback|treasury\s+stock)\s+(?:of|was|is|amounted\s+to)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)\s*(?:million|billion|b|m|mm)?',
            text, re.IGNORECASE
        )
        if buyback_match:
            value = float(buyback_match.group(1).replace(',', ''))
            if 'billion' in buyback_match.group(0).lower():
                value *= 1e9
            elif 'million' in buyback_match.group(0).lower():
                value *= 1e6
            data.buybacks = value
        
        # CapEx
        capex_match = re.search(
            r'(?:capital\s+expenditures?|capex)\s+(?:of|was|is|amounted\s+to)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)\s*(?:million|billion|b|m|mm)?',
            text, re.IGNORECASE
        )
        if capex_match:
            value = float(capex_match.group(1).replace(',', ''))
            if 'billion' in capex_match.group(0).lower():
                value *= 1e9
            elif 'million' in capex_match.group(0).lower():
                value *= 1e6
            data.capex = value
    
    async def _extract_guidance(self, text: str, data: AnnualReportData):
        """Extract forward-looking guidance."""
        guidance_patterns = [
            r'(?i)(?:guidance|outlook|expects?|anticipates?|projects?|targets?)\s+(?:for\s+)?(?:20\d{2}|fiscal\s+20\d{2}|next\s+year|next\s+quarter)',
        ]
        
        guidance_text = self._extract_section(text, guidance_patterns, max_chars=10000)
        
        if guidance_text:
            # Extract specific guidance metrics
            guidance = {}
            
            # Revenue guidance
            rev_guidance = re.search(
                r'(?:revenue|sales)\s+(?:guidance|outlook|expected|expected\s+to\s+be)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)\s*(?:million|billion|b|m|mm)?',
                guidance_text, re.IGNORECASE
            )
            if rev_guidance:
                guidance['revenue'] = rev_guidance.group(0)
            
            # EPS guidance
            eps_guidance = re.search(
                r'(?:eps|earnings\s+per\s+share)\s+(?:guidance|outlook|expected\s+to\s+be)\s*[:\\-]?\s*[\$£€]?\s*([\d,\.]+)',
                guidance_text, re.IGNORECASE
            )
            if eps_guidance:
                guidance['eps'] = eps_guidance.group(0)
            
            # Margin guidance
            margin_guidance = re.search(
                r'(?:gross|operating)\s+margin\s+(?:guidance|outlook|expected\s+to\s+be)\s*[:\\-]?\s*([\d,\.]+)\s*%',
                guidance_text, re.IGNORECASE
            )
            if margin_guidance:
                guidance[f'{margin_guidance.group(0).split()[0]}_margin'] = margin_guidance.group(0)
            
            data.guidance = guidance
    
    def _extract_section(self, text: str, patterns: list[str], max_chars: int = 5000) -> str:
        """Extract a section based on patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start = match.start()
                end = min(start + max_chars, len(text))
                return text[start:end]
        return ""
    
    def _extract_subsection(self, text: str, patterns: list[str]) -> str:
        """Extract a subsection within a larger section."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start = match.start()
                end = min(start + 5000, len(text))
                return text[start:end]
        return ""
    
    def _calculate_confidence(self, data: AnnualReportData) -> float:
        """Calculate extraction confidence score."""
        score = 0.0
        total = 0
        
        # Check each field
        fields = [
            ('company_name', data.company_name),
            ('ticker', data.ticker),
            ('fiscal_year', data.fiscal_year),
            ('revenue', data.revenue),
            ('net_income', data.net_income),
            ('eps', data.eps),
            ('business_description', data.business_description),
            ('segments', data.segments),
            ('risk_factors', data.risk_factors),
            ('mda_highlights', data.mda_highlights),
        ]
        
        for name, value in fields:
            total += 1
            if value:
                score += 1
        
        return score / total if total > 0 else 0.0


# Export
__all__ = [
    "AnnualReportData",
    "AnnualReportParser",
]