# Migration Notes - Phase 4 Financial Documents Intelligence

## Breaking Changes

None. Phase 4 is purely additive - no existing APIs modified.

## New Dependencies

Add to `requirements.txt` or `pyproject.toml`:

```toml
# PDF Processing
pdfplumber >= 0.10.0
pymupdf >= 1.23.0
pdfminer.six >= 20221105

# Async Database
aiosqlite >= 0.19.0

# Optional: PowerPoint parsing
python-pptx >= 0.6.21
```

Install with:
```bash
pip install pdfplumber pymupdf pdfminer.six aiosqlite python-pptx
```

## New Imports

All Phase 4 modules are available via `data` package:

```python
# SEC Filings
from data.sec import (
    SECDownloader,
    SECFiling,
    SECCompanyInfo,
    create_sec_downloader,
    SEC_FORM_TYPES,
)

# Document Cache & Incremental Updates
from data.filings import (
    DocumentCache,
    VersionedDocumentCache,
    MemoryCacheBackend,
    SQLiteCacheBackend,
    IncrementalUpdater,
    UpdateConfig,
    create_document_cache,
    create_incremental_updater,
)

# Earnings Transcripts
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

# Annual/Quarterly Reports & Presentations
from data.annual_reports import (
    AnnualReportParser,
    AnnualReportData,
    QuarterlyReportParser,
    QuarterlyReportData,
    InvestorPresentationParser,
    InvestorPresentationData,
)

# Core Financial Document Processing
from data.financial_documents import (
    # PDF Parser
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
    parse_pdf,
    parse_financial_pdf,
    extract_tables_from_pdf,
    extract_text_from_pdf,
    
    # Tables
    FinancialTableExtractor,
    TableExtractionResult,
    FinancialTable,
    FinancialStatementParser,
    IncomeStatementParser,
    BalanceSheetParser,
    CashFlowParser,
    FinancialStatementParserFactory,
    SegmentInformationExtractor,
    ManagementDiscussionExtractor,
    RiskFactorsExtractor,
    BusinessOverviewExtractor,
)
```

## Configuration Updates

No required configuration changes. Optional configurations:

### SEC Downloader
```python
from data.sec import create_sec_downloader

# Custom configuration
downloader = await create_sec_downloader(
    cache_dir=Path("./custom/cache"),
    cache_ttl_days=60,
    rate_limit=5.0,  # More conservative
    output_dir=Path("./custom/filings")
)
```

### Document Cache
```python
from data.filings import create_document_cache

cache = await create_document_cache(
    cache_dir=Path("./custom/cache"),
    version_dir=Path("./custom/versions"),
    company_mapping_file=Path("./custom/company_mapping.json")
)
```

### Incremental Updater
```python
from data.filings import IncrementalUpdater, UpdateConfig
from data.sec import create_sec_downloader

async with create_sec_downloader() as downloader:
    cache = await create_document_cache()
    
    config = UpdateConfig(
        check_interval_hours=12,      # Twice daily
        lookback_days=3,              # Only last 3 days
        form_types=["10-K", "10-Q", "8-K", "DEF14A"],
        max_filings_per_run=50,
        download_documents=True,
        process_documents=True,
        update_rag_index=True,
    )
    
    updater = IncrementalUpdater(
        config=config,
        sec_downloader=downloader,
        document_cache=cache,
        rag_update_callback=my_rag_update_function,
    )
```

## Integration with Existing Agents

### FinancialReportAgent Enhancement

The `FinancialReportAgent` can now use real document parsers instead of relying on news summaries:

```python
# In agents/financial_report_agent/agent.py
from data.annual_reports import AnnualReportParser, QuarterlyReportParser
from data.financial_documents import FinancialDocumentParser

class FinancialReportAgent:
    def __init__(self, ...):
        self.annual_parser = AnnualReportParser()
        self.quarterly_parser = QuarterlyReportParser()
        self.general_parser = FinancialDocumentParser()
    
    async def analyze_company(self, company: str, ...):
        # Download and parse latest 10-K
        # Download and parse latest 10-Q
        # Download and parse investor presentations
        # Cross-reference with news and market data
```

### NewsAgent Enhancement

```python
# In agents/news_agent/agent.py
from data.sec import SECDownloader
from data.filings import IncrementalUpdater

class NewsAgent:
    def __init__(self, ...):
        self.sec_downloader = SECDownloader()
        self.incremental_updater = IncrementalUpdater(...)
    
    async def monitor_filings(self):
        # Check for new SEC filings
        # Trigger analysis on material events (8-K)
        # Update RAG index with new filings
```

## Usage Examples

### Basic SEC Filing Download
```python
from data.sec import create_sec_downloader

async with create_sec_downloader() as downloader:
    # Get Apple's latest 10-K and 10-Q
    filings = await downloader.search_filings(
        cik="0000320193",
        form_types=["10-K", "10-Q"],
        count=10
    )
    
    for filing in filings:
        print(f"{filing.form_type} - {filing.filing_date}")
        path = await downloader.download_filing(filing, Path("./data/apple"))
        print(f"  Downloaded: {path}")
```

### Parse Annual Report
```python
from data.annual_reports import AnnualReportParser
from pathlib import Path

parser = AnnualReportParser()
data = await parser.parse(Path("./data/apple/AAPL_10-K_2023-11-03_0000320193-23-000106.htm"))

print(f"Company: {data.company_name}")
print(f"Revenue: ${data.revenue:,.0f}" if data.revenue else "Revenue: N/A")
print(f"Net Income: ${data.net_income:,.0f}" if data.net_income else "Net Income: N/A")
print(f"Segments: {[s['name'] for s in data.segments]}")
print(f"Risk Factors: {len(data.risk_factors)} found")
print(f"Guidance: {data.guidance}")
print(f"Confidence: {data.extraction_confidence:.1%}")
```

### Extract Financial Tables
```python
from data.financial_documents import FinancialTableExtractor, FinancialStatementParserFactory

extractor = FinancialTableExtractor()
result = await extractor.extract_tables(Path("10k.pdf"))

for table in result.tables:
    if table.table_type in ["income_statement", "balance_sheet", "cash_flow"]:
        parser = FinancialStatementParserFactory.get_parser(table.table_type)
        if parser:
            parsed = parser.parse(table)
            print(f"{table.table_type}: {parsed}")
```

### Parse Earnings Transcript
```python
from data.earnings import EarningsCallTranscriptParser

parser = EarningsCallTranscriptParser()
transcript = await parser.parse(Path("earnings_Q3_2024.txt"))

print(f"Company: {transcript.company} ({transcript.ticker})")
print(f"Quarter: {transcript.quarter} {transcript.year}")
print(f"Speakers: {transcript.speakers}")
print(f"Q&A Exchanges: {len(transcript.qa_exchanges)}")

for guidance in transcript.guidance:
    print(f"Guidance - {guidance.metric}: {guidance.direction} ({guidance.confidence})")
    print(f"  Value: {guidance.value}")
    print(f"  Period: {guidance.period}")
    print(f"  Speaker: {guidance.speaker}")

for metric in transcript.key_metrics:
    print(f"Metric - {metric.metric}: {metric.value} ({metric.sentiment})")
```

### Process Investor Presentation
```python
from data.annual_reports import InvestorPresentationParser

parser = InvestorPresentationParser()
data = await parser.parse(Path("investor_presentation.pdf"))

print(f"Title: {data.presentation_title}")
print(f"Slides: {data.total_slides}")
print(f"Key Highlights: {data.key_highlights}")
print(f"Strategic Initiatives: {data.strategic_initiatives}")
print(f"Growth Drivers: {data.growth_drivers}")
print(f"Key Metrics: {data.key_metrics}")
print(f"Guidance: {data.guidance}")
print(f"Capital Allocation: {data.capital_allocation}")
```

### Incremental Updates
```python
from data.filings import create_incremental_updater
from data.sec import create_sec_downloader
from data.filings import create_document_cache

async def my_rag_update(new_doc_keys):
    """Callback to update RAG index with new documents."""
    # Implementation depends on your vector store
    pass

async with create_sec_downloader() as downloader:
    cache = await create_document_cache()
    updater = await create_incremental_updater(
        sec_downloader=downloader,
        document_cache=cache,
        rag_update_callback=my_rag_update,
        config=UpdateConfig(
            check_interval_hours=6,
            lookback_days=7,
            form_types=["10-K", "10-Q", "8-K", "DEF14A", "S-1"],
        )
    )
    
    # Run once
    result = await updater.run_update(force=True)
    print(f"Added: {result.items_added}, Updated: {result.items_updated}, Failed: {result.items_failed}")
    
    # Or run scheduled
    # await updater.run_scheduled()
```

## Directory Structure

Ensure these directories exist (created automatically):
```
data/
├── sec/
│   └── cache/           # SEC API response cache
├── filings/
│   ├── cache/           # Document cache (SQLite)
│   ├── versions/        # Versioned document storage
│   └── update_state.json # Incremental updater state
├── rag/
│   └── update_state.json # RAG index updater state
└── company_mapping.json  # Ticker -> Company name mapping
```

## Testing

Run existing tests to verify compatibility:
```bash
# All 319 existing tests should pass
pytest tests/ --ignore=tests/test_claude_connection.py --ignore=tests/test_openrouter_connection.py -v

# Quick smoke test
python -c "
from data.sec import SECDownloader
from data.filings import DocumentCache
from data.earnings import EarningsCallTranscriptParser
from data.annual_reports import AnnualReportParser
from data.financial_documents import PDFParser
print('All Phase 4 imports work!')
"
```

## Troubleshooting

### PDF Parser Issues
- **No backends available**: Install `pdfplumber`, `pymupdf`, or `pdfminer.six`
- **Table extraction fails**: Ensure `pdfplumber` is installed (best for tables)
- **Memory errors**: Reduce concurrency in `parse_multiple()` or process files sequentially

### SEC Downloader Issues
- **Rate limit errors**: Increase `rate_limit` delay or reduce concurrency
- **403/429 errors**: Check `User-Agent` header is set correctly
- **Missing filings**: Verify CIK is correct (10-digit, zero-padded)

### Cache Issues
- **Disk space**: Configure `max_size_mb` in `SQLiteCacheBackend`
- **Permission errors**: Ensure write access to cache directories
- **Stale data**: Run `cache.clear_expired()` or adjust TTL

### Incremental Updater Issues
- **State file corruption**: Delete `data/filings/update_state.json` to reset
- **Duplicate processing**: Check `content_hash` deduplication is working
- **RAG callback failures**: Wrap callback in try/except, log errors

## Performance Tuning

### For Large-Scale Processing
```python
# Increase connection pool for SEC downloads
connector = aiohttp.TCPConnector(limit=20)

# Process multiple PDFs concurrently
results = await parser.parse_multiple(file_paths)  # Uses semaphore(4)

# Use fast parser for simple documents
fast_parser = PDFParserFactory.create_fast()
```

### For Memory-Constrained Environments
```python
# Reduce memory cache
memory_cache = MemoryCacheBackend(max_size_mb=50)

# Disable image extraction
parser = PDFParser(extract_images=False)
```

## Future Considerations

Phase 5 will add:
1. **XBRL Parser** - For structured SEC financial data
2. **Chart/Image Analysis** - OCR and chart data extraction
3. **Multi-language Support** - 20-F, 40-F, 6-K parsers
4. **Streaming Updates** - Real-time filing notifications
5. **LLM-Enhanced Extraction** - Complex narrative parsing with LLMs