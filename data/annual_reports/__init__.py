"""
Data Annual Reports Package - Annual and Quarterly Report Parsers

Phase 4: Real Financial Documents Intelligence
"""

from data.annual_reports.annual_report_parser import (
    AnnualReportParser,
    AnnualReportData,
)

from data.annual_reports.quarterly_report_parser import (
    QuarterlyReportParser,
    QuarterlyReportData,
)

from data.annual_reports.investor_presentation_parser import (
    InvestorPresentationParser,
    InvestorPresentationData,
)

__all__ = [
    "AnnualReportParser",
    "AnnualReportData",
    "QuarterlyReportParser",
    "QuarterlyReportData",
    "InvestorPresentationParser",
    "InvestorPresentationData",
]