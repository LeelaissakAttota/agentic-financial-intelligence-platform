# Architecture Update - Phase 4 Financial Documents Intelligence

## Overview

Phase 4 extends the Financial Research Agent with comprehensive financial document intelligence capabilities. The architecture follows the existing modular, async-first design with clear separation of concerns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Financial Research Agent                    │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1-3: Core Agents, News Pipeline, Entity Recognition       │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: Financial Documents Intelligence                       │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐   │
│  │    SEC       │   Filings    │   Earnings   │  Reports     │   │
│  │  Downloader  │    Cache     │  Transcripts │   Parsers    │   │
│  └──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘   │
│         │             │             │             │             │
│         └─────────────┴─────────────┴─────────────┘             │
│                           │                                     │
│              ┌────────────▼────────────┐                        │
│              │  Financial Documents    │                        │
│              │  (PDF Parser + Tables)  │                        │
│              └────────────┬────────────┘                        │
│                           │                                     │
│              ┌────────────▼────────────┐                        │
│              │      RAG Pipeline       │                        │
│              │ (Document Loader →      │                        │
│              │  Section Splitter →     │                        │
│              │  Embeddings → Vector)   │                        │
│              └─────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

## New Module Structure

```
data/
├── sec/                    # SEC EDGAR integration
│   ├── __init__.py
│   └── downloader.py       # SECDownloader, rate limiter, cache
│
├── filings/                # Document processing & caching
│   ├── __init__.py
│   ├── cache.py            # Multi-tier cache with versioning
│   └── incremental.py      # Scheduled incremental updates
│
├── earnings/               # Earnings call processing
│   ├── __init__.py
│   └── transcript_parser.py # Speaker, Q&A, guidance extraction
│
├── annual_reports/         # Report-specific parsers
│   ├── __init__.py
│   ├── annual_report_parser.py      # 10-K parser
│   ├── quarterly_report_parser.py   # 10-Q parser
│   └── investor_presentation_parser.py  # PDF/PPTX parser
│
├── financial_documents/    # Core document processing
│   ├── __init__.py
│   ├── parser.py                 # Multi-backend PDF parser
│   ├── tables.py                 # Financial table extraction
│   ├── parsers.py                # Document-type parser bundles
│   └── investor_presentation_parser.py  # Duplicate for direct access
│
└── __init__.py             # Updated with Phase 4 exports
```

## Data Flow

### 1. SEC Filing Download Flow
```
SECDownloader.search_filings()
    │
    ├── Rate limiter (10 req/s)
    ├── Cache check (memory → disk)
    ├── SEC Submissions API
    └── Filing metadata → SECFiling objects
         │
         ▼
SECDownloader.download_filing()
    │
    ├── Download PDF/HTML
    ├── Save to data/filings/{CIK}/{form_type}/
    └── Save metadata JSON
```

### 2. Document Processing Flow
```
parse_financial_pdf() or FinancialDocumentParser.parse()
    │
    ├── Document type detection (filename + metadata)
    ├── Backend selection (pdfplumber → PyMuPDF → pdfminer)
    ├── Parse with fallback
    │
    ├── Extract pages → ExtractedPage (text, blocks, tables, images)
    ├── Extract metadata → DocumentMetadata
    │
    └── ParserResult with pages, metadata, timing
```

### 3. Financial Table Extraction Flow
```
FinancialTableExtractor.extract_tables()
    │
    ├── Try pdfplumber (best tables)
    ├── Fallback to PyMuPDF
    │
    ├── For each table:
    │   ├── Clean rows/cells
    │   ├── Detect headers
    │   ├── Classify type (income_statement, balance_sheet, cash_flow, etc.)
    │   ├── Extract period, currency, units
    │   └── Calculate confidence
    │
    └── TableExtractionResult with FinancialTable[]
```

### 4. Report-Specific Parsing Flow
```
AnnualReportParser.parse()
    │
    ├── parse_financial_pdf() → full text
    ├── Extract metadata (company, ticker, CIK, fiscal year)
    ├── Extract business overview (Item 1)
    ├── Extract financial highlights (regex patterns)
    ├── Extract segments (Item 2)
    ├── Extract MD&A highlights (Item 7)
    ├── Extract risk factors (Item 1A)
    ├── Extract capital allocation (dividends, buybacks, CapEx)
    ├── Extract guidance (forward-looking statements)
    ├── Calculate confidence score
    │
    └── AnnualReportData structured object
```

### 5. Incremental Update Flow
```
IncrementalUpdater.run_update()
    │
    ├── Get companies to update (config or cache)
    ├── For each company:
    │   ├── Search recent filings (lookback window)
    │   ├── For each filing:
    │   │   ├── Check cache by content hash
    │   │   ├── If new/changed: download & process
    │   │   ├── Store in VersionedDocumentCache
    │   │   └── Update filing metadata cache
    │   └── Aggregate results
    ├── Trigger RAG index update (callback)
    ├── Save state (last_run, next_run, results)
    │
    └── UpdateResult with counts
```

## Integration with Existing Systems

### RAG Pipeline Integration
```python
# Existing: rag.ingestion.document_loader.DocumentLoader
# Now enhanced with:
from data.financial_documents import parse_financial_pdf

# DocumentLoader.process() can now handle SEC filings, 
# earnings transcripts, investor presentations
```

### Agent Integration Points

#### FinancialReportAgent
```python
from data.annual_reports import AnnualReportParser, QuarterlyReportParser
from data.financial_documents import FinancialDocumentParser

# Can now parse 10-K, 10-Q, investor presentations directly
# Instead of relying solely on news/summaries
```

#### NewsAgent
```python
from data.sec import SECDownloader
from data.filings import IncrementalUpdater

# Can monitor SEC filings in real-time
# Trigger analysis on new 8-K, 10-K, 10-Q
```

#### ManagerAgent
```python
# Can orchestrate multi-document analysis:
# - SEC filings + earnings transcripts + investor presentations
# - Cross-reference guidance across documents
```

## Configuration

All components use configuration-driven design:

```python
# SEC Downloader
config = {
    "rate_limit": 10,          # req/s
    "cache_ttl_days": 30,
    "cache_dir": "./data/sec/cache",
    "output_dir": "./data/filings"
}

# Document Cache
config = {
    "memory_cache_mb": 200,
    "disk_cache_mb": 5000,
    "default_ttl_days": 90,
    "enable_dedup": True
}

# Incremental Updater
config = {
    "check_interval_hours": 6,
    "lookback_days": 7,
    "form_types": ["10-K", "10-Q", "8-K"],
    "max_filings_per_run": 100,
    "download_documents": True,
    "process_documents": True,
    "update_rag_index": True
}
```

## Performance Considerations

### Concurrency
- `PDFParser.parse_multiple()` uses semaphore (4 concurrent)
- `SECDownloader` uses aiohttp connection pool (10 connections)
- `IncrementalUpdater` processes companies sequentially but filings can be parallelized

### Caching Strategy
- **Memory**: Hot documents, LRU eviction at 200MB
- **Disk**: All documents, SQLite with pickle serialization
- **Deduplication**: Content hash prevents re-processing identical documents

### Incremental Processing
- Only downloads new/changed filings (hash comparison)
- Lookback window limits scope (default 7 days)
- Checkpoint/resume via state file

## Error Handling

All components follow consistent error handling:
- Structured logging with component names
- Graceful degradation (fallback parsers)
- Partial results returned on non-critical failures
- Detailed error context in `ParserResult.errors`

## Testing Strategy

Each parser/extractor is independently testable:
- Unit tests with sample PDFs/fixtures
- Mock SEC API responses
- Integration tests with real documents
- Async/await throughout for testability

## Future Extensibility

### Planned Phase 5 Extensions
1. **XBRL Parser** - Structured financial data from SEC XBRL
2. **Chart/Image Analysis** - OCR and chart data extraction
3. **Multi-language** - International filings (20-F, 40-F, 6-K)
4. **Streaming Updates** - Webhook/Server-Sent Events for real-time
5. **LLM-Enhanced Extraction** - Complex narrative parsing

### Extension Points
- New `PDFParserBackend` implementations
- New `FinancialStatementParser` for specialized statements
- New document types in `FinancialDocumentParser.type_patterns`
- Custom `UpdateConfig` filters for specialized workflows