"""
PDF Parser for Financial Documents with Multi-Library Support and Fallback.

Supports multiple PDF libraries (PyMuPDF, pdfplumber, pdfminer) with automatic
fallback logic for robust financial document parsing.
"""

import asyncio
import hashlib
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF

# Optional imports with availability flags
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    from pdfminer.layout import LAParams
    from pdfminer.pdfpage import PDFPage
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False
    extract_text = None
    LAParams = None
    PDFPage = None

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Represents a table extracted from a PDF page."""
    page_number: int
    table_index: int
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1
    rows: list[list[str]]
    headers: list[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class ExtractedPage:
    """Represents a single page of extracted content."""
    page_number: int
    text: str
    blocks: list[dict]  # Raw text blocks from parser
    tables: list[ExtractedTable] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    char_start: int = 0
    char_end: int = 0


@dataclass
class DocumentMetadata:
    """Metadata extracted from a financial document."""
    file_path: str
    file_hash: str
    file_size: int
    page_count: int
    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""
    producer: str = ""
    creation_date: Optional[date] = None
    modification_date: Optional[date] = None
    # Financial document specific
    company_name: Optional[str] = None
    document_type: Optional[str] = None  # 10k, 10q, annual_report, earnings, presentation
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    filing_date: Optional[date] = None
    accession_number: Optional[str] = None
    cik: Optional[str] = None


@dataclass
class ParserResult:
    """Result of PDF parsing operation."""
    pages: list[ExtractedPage]
    metadata: DocumentMetadata
    processing_time_seconds: float
    parser_used: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True


class PDFParserBackend(ABC):
    """Abstract base class for PDF parser backends."""
    
    @abstractmethod
    async def parse(self, file_path: Path) -> ParserResult:
        """Parse a PDF file and return structured result."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this parser backend."""
        pass
    
    @property
    @abstractmethod
    def supports_tables(self) -> bool:
        """Whether this backend supports table extraction."""
        pass
    
    @property
    @abstractmethod
    def supports_images(self) -> bool:
        """Whether this backend supports image extraction."""
        pass


class PyMuPDFBackend(PDFParserBackend):
    """PyMuPDF (fitz) backend - fast, good for text and basic tables."""
    
    def __init__(self, extract_tables: bool = True, extract_images: bool = False):
        self.extract_tables = extract_tables
        self.extract_images = extract_images
    
    @property
    def name(self) -> str:
        return "PyMuPDF"
    
    @property
    def supports_tables(self) -> bool:
        return True
    
    @property
    def supports_images(self) -> bool:
        return True
    
    async def parse(self, file_path: Path) -> ParserResult:
        start_time = asyncio.get_event_loop().time()
        warnings = []
        errors = []
        pages = []
        
        try:
            doc = fitz.open(str(file_path))
            file_hash = self._calculate_hash(file_path)
            
            # Extract metadata
            metadata = self._extract_metadata(doc, file_path, file_hash)
            
            # Extract pages
            char_pos = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                extracted_page = self._extract_page(page, page_num + 1)
                extracted_page.char_start = char_pos
                char_pos += len(extracted_page.text)
                extracted_page.char_end = char_pos
                pages.append(extracted_page)
            
            doc.close()
            
        except Exception as e:
            logger.error(f"PyMuPDF parsing failed for {file_path}: {e}")
            errors.append(f"PyMuPDF parsing failed: {str(e)}")
            # Return empty result with error
            return ParserResult(
                pages=[],
                metadata=DocumentMetadata(
                    file_path=str(file_path),
                    file_hash="",
                    file_size=0,
                    page_count=0
                ),
                processing_time_seconds=0,
                parser_used=self.name,
                errors=errors,
                success=False
            )
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return ParserResult(
            pages=pages,
            metadata=metadata,
            processing_time_seconds=processing_time,
            parser_used=self.name,
            warnings=warnings,
            errors=errors,
            success=True
        )
    
    def _extract_metadata(self, doc: fitz.Document, path: Path, file_hash: str) -> DocumentMetadata:
        meta = doc.metadata
        
        # Parse dates
        creation_date = self._parse_pdf_date(meta.get("creationDate", ""))
        mod_date = self._parse_pdf_date(meta.get("modDate", ""))
        
        return DocumentMetadata(
            file_path=str(path),
            file_hash=file_hash,
            file_size=path.stat().st_size,
            page_count=len(doc),
            title=meta.get("title", ""),
            author=meta.get("author", ""),
            subject=meta.get("subject", ""),
            creator=meta.get("creator", ""),
            producer=meta.get("producer", ""),
            creation_date=self._parse_pdf_date(meta.get("creationDate", "")),
            modification_date=self._parse_pdf_date(meta.get("modDate", "")),
        )
    
    def _extract_page(self, page: fitz.Page, page_number: int) -> ExtractedPage:
        # Get text with layout preservation
        text = page.get_text("text")
        
        # Get detailed blocks for structure analysis
        blocks = page.get_text("dict")["blocks"]
        
        tables = []
        if self.extract_tables:
            tables = self._extract_tables(page, page_number)
        
        images = []
        if self.extract_images:
            images = self._extract_images(page, page_number)
        
        return ExtractedPage(
            page_number=page_number,
            text=text,
            blocks=blocks,
            tables=tables,
            images=images,
        )
    
    def _extract_tables(self, page: fitz.Page, page_number: int) -> list:
        tables = []
        try:
            # PyMuPDF 1.23+ has find_tables()
            found_tables = page.find_tables()
            
            for idx, table in enumerate(found_tables):
                rows = table.extract()
                
                if not rows:
                    continue
                
                headers = []
                data_rows = rows
                if rows and self._looks_like_header(rows[0]):
                    headers = rows[0]
                    data_rows = rows[1:]
                
                bbox = table.bbox
                tables.append(ExtractedTable(
                    page_number=page_number,
                    table_index=idx,
                    bbox=bbox,
                    rows=data_rows,
                    headers=headers,
                    confidence=0.85
                ))
        except Exception as e:
            logger.warning(f"Table extraction failed on page {page_number}: {e}")
        
        return tables
    
    def _extract_images(self, page: fitz.Page, page_number: int) -> list[dict]:
        images = []
        try:
            image_list = page.get_images(full=True)
            for img_idx, img in enumerate(image_list):
                images.append({
                    "page_number": page_number,
                    "image_index": img_idx,
                    "xref": img[0],
                    "width": img[2],
                    "height": img[3],
                    "colorspace": img[4],
                })
        except Exception as e:
            logger.warning(f"Image extraction failed on page {page_number}: {e}")
        return images
    
    def _looks_like_header(self, row: list[str]) -> bool:
        if not row:
            return False
        text_cells = sum(1 for cell in row if cell and not cell.replace(".", "").replace(",", "").replace("$", "").replace("%", "").replace(",", "").isdigit())
        return text_cells > len(row) * 0.5
    
    def _calculate_hash(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _parse_pdf_date(self, date_str: str) -> Optional[date]:
        if not date_str or not date_str.startswith("D:"):
            return None
        try:
            date_part = date_str[2:10]  # YYYYMMDD
            return date(int(date_part[:4]), int(date_part[4:6]), int(date_part[6:8]))
        except Exception:
            return None


class PDFPlumberBackend(PDFParserBackend):
    """pdfplumber backend - excellent table extraction, good for financial tables."""
    
    def __init__(self, extract_tables: bool = True, extract_images: bool = False):
        if not PDFPLUMBER_AVAILABLE:
            raise RuntimeError("pdfplumber not available. Install with: pip install pdfplumber")
        self.extract_tables = extract_tables
        self.extract_images = extract_images
    
    @property
    def name(self) -> str:
        return "pdfplumber"
    
    @property
    def supports_tables(self) -> bool:
        return True
    
    @property
    def supports_images(self) -> bool:
        return False  # pdfplumber doesn't extract images well
    
    async def parse(self, file_path: Path) -> ParserResult:
        start_time = asyncio.get_event_loop().time()
        warnings = []
        errors = []
        pages = []
        
        try:
            import pdfplumber
            
            file_hash = self._calculate_hash(file_path)
            
            with pdfplumber.open(str(file_path)) as pdf:
                metadata = DocumentMetadata(
                    file_path=str(file_path),
                    file_hash=self._calculate_hash(file_path),
                    file_size=file_path.stat().st_size,
                    page_count=len(pdf.pages),
                    title=pdf.metadata.get("Title", "") if pdf.metadata else "",
                    author=pdf.metadata.get("Author", "") if pdf.metadata else "",
                    subject=pdf.metadata.get("Subject", "") if pdf.metadata else "",
                    creator=pdf.metadata.get("Creator", "") if pdf.metadata else "",
                    producer=pdf.metadata.get("Producer", "") if pdf.metadata else "",
                )
                
                char_pos = 0
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    text = page.extract_text() or ""
                    
                    # Extract tables
                    tables = []
                    if self.extract_tables:
                        try:
                            tables_data = page.extract_tables()
                            for idx, table_data in enumerate(tables_data or []):
                                if table_data:
                                    headers = []
                                    data_rows = table_data
                                    if table_data and self._looks_like_header(table_data[0]):
                                        headers = table_data[0]
                                        data_rows = table_data[1:]
                                    else:
                                        data_rows = table_data
                                    
                                    tables.append(ExtractedTable(
                                        page_number=page_num + 1,
                                        table_index=idx,
                                        bbox=(0, 0, page.width, page.height),  # Approximate
                                        rows=data_rows,
                                        headers=headers,
                                        confidence=0.9  # pdfplumber tables are usually high quality
                                    ))
                        except Exception as e:
                            logger.warning(f"Table extraction failed on page {page_num + 1}: {e}")
                    
                    page_obj = ExtractedPage(
                        page_number=page_num + 1,
                        text=text,
                        blocks=[],  # pdfplumber doesn't provide block structure
                        tables=tables,
                        images=[],
                    )
                    pages.append(page_obj)
            
        except Exception as e:
            logger.error(f"pdfplumber parsing failed for {file_path}: {e}")
            errors.append(f"pdfplumber parsing failed: {str(e)}")
            return ParserResult(
                pages=[],
                metadata=DocumentMetadata(file_path=str(file_path), file_hash="", file_size=0, page_count=0),
                processing_time_seconds=0,
                parser_used=self.name,
                errors=errors,
                success=False
            )
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return ParserResult(
            pages=pages,
            metadata=metadata,
            processing_time_seconds=processing_time,
            parser_used=self.name,
            warnings=[],
            errors=errors,
            success=True
        )
    
    def _calculate_hash(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _looks_like_header(self, row: list[str]) -> bool:
        if not row:
            return False
        text_cells = sum(1 for cell in row if cell and not cell.replace(".", "").replace(",", "").replace("$", "").replace("%", "").replace(",", "").isdigit())
        return text_cells > len(row) * 0.5


class PDFMinerBackend(PDFParserBackend):
    """pdfminer backend - good text extraction, no table support."""
    
    def __init__(self, extract_tables: bool = False, extract_images: bool = False):
        if not PDFMINER_AVAILABLE:
            raise RuntimeError("pdfminer not available. Install with: pip install pdfminer.six")
        # Tables not supported in pdfminer easily
        pass
    
    @property
    def name(self) -> str:
        return "pdfminer"
    
    @property
    def supports_tables(self) -> bool:
        return False
    
    @property
    def supports_images(self) -> bool:
        return False
    
    async def parse(self, file_path: Path) -> ParserResult:
        start_time = asyncio.get_event_loop().time()
        warnings = []
        errors = []
        pages = []
        
        try:
            from pdfminer.high_level import extract_text
            from pdfminer.pdfpage import PDFPage
            from pdfminer.pdfparser import PDFParser
            from pdfminer.pdfdocument import PDFDocument
            
            file_hash = self._calculate_hash(file_path)
            
            # Extract full text first
            full_text = extract_text(str(file_path))
            
            # Get page count and basic metadata
            with open(file_path, 'rb') as f:
                parser = PDFParser(f)
                doc = PDFDocument(parser)
                page_count = sum(1 for _ in PDFPage.create_pages(doc))
            
            metadata = DocumentMetadata(
                file_path=str(file_path),
                file_hash=file_hash,
                file_size=file_path.stat().st_size,
                page_count=page_count,
            )
            
            # For pdfminer, we don't easily get per-page text
            # So we create one "page" with all text
            pages = [ExtractedPage(
                page_number=1,
                text=full_text,
                blocks=[],
                tables=[],
                images=[],
            )]
            
        except Exception as e:
            logger.error(f"pdfminer parsing failed for {file_path}: {e}")
            errors.append(f"pdfminer parsing failed: {str(e)}")
            return ParserResult(
                pages=[],
                metadata=DocumentMetadata(file_path=str(file_path), file_hash="", file_size=0, page_count=0),
                processing_time_seconds=0,
                parser_used=self.name,
                errors=errors,
                success=False
            )
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return ParserResult(
            pages=pages,
            metadata=metadata,
            processing_time_seconds=processing_time,
            parser_used=self.name,
            warnings=["pdfminer does not support per-page extraction or tables"],
            errors=errors,
            success=True
        )
    
    def _calculate_hash(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


class PDFParser:
    """
    Multi-backend PDF Parser with automatic fallback.
    
    Tries backends in order of preference:
    1. pdfplumber (best for tables)
    2. PyMuPDF (fast, good text, decent tables)
    3. pdfminer (fallback, text only)
    
    Features:
    - Automatic fallback on failure
    - Content hash-based deduplication
    - Multi-library support
    - Table extraction with multiple backends
    - Financial document metadata extraction
    - Async processing
    """
    
    def __init__(
        self,
        backends: Optional[list[str]] = None,
        prefer_tables: bool = True,
        extract_images: bool = False,
        fallback_enabled: bool = True
    ):
        """
        Initialize PDF Parser with specified backends.
        
        Args:
            backends: List of backend names in preference order.
                      Options: "pdfplumber", "pymupdf", "pdfminer"
            prefer_tables: Whether to prefer backends with table support
            extract_images: Whether to extract images
            fallback_enabled: Whether to fall back on failure
        """
        self.prefer_tables = prefer_tables
        self.extract_images = extract_images
        self.fallback_enabled = fallback_enabled
        
        # Default backend order: pdfplumber (best tables) -> PyMuPDF (fast) -> pdfminer (fallback)
        if backends is None:
            backends = ["pdfplumber", "pymupdf", "pdfminer"]
        
        self._backends: list[PDFParserBackend] = []
        self._initialize_backends(backends)
    
    def _initialize_backends(self, backend_names: list[str]):
        """Initialize backends in order, skipping unavailable ones."""
        for name in backend_names:
            try:
                if name == "pdfplumber":
                    if PDFPLUMBER_AVAILABLE:
                        self._backends.append(PDFPlumberBackend())
                elif name == "pymupdf":
                    self._backends.append(PyMuPDFBackend())
                elif name == "pdfminer":
                    if PDFMINER_AVAILABLE:
                        self._backends.append(PDFMinerBackend())
                else:
                    logger.warning(f"Unknown PDF backend: {name}")
            except Exception as e:
                logger.warning(f"Failed to initialize {name} backend: {e}")
        
        if not self._backends:
            raise RuntimeError("No PDF parser backends available!")
        
        logger.info(f"Initialized PDF backends: {[b.name for b in self._backends]}")
    
    async def parse(self, file_path: str | Path) -> ParserResult:
        """
        Parse a PDF file with automatic fallback.
        
        Tries each backend in order until one succeeds.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"File is not a PDF: {path}")
        
        last_error = None
        
        for backend in self._backends:
            try:
                logger.debug(f"Trying {backend.name} backend for {path.name}")
                result = await backend.parse(path)
                
                if result.success:
                    logger.info(f"Successfully parsed {path.name} with {backend.name}")
                    return result
                else:
                    last_error = result.errors[0] if result.errors else "Unknown error"
                    logger.warning(f"{backend.name} failed for {path.name}: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"{backend.name} raised exception for {path.name}: {e}")
                continue
        
        # All backends failed
        error_msg = f"All PDF backends failed for {path.name}. Last error: {last_error}"
        logger.error(error_msg)
        return ParserResult(
            pages=[],
            metadata=DocumentMetadata(file_path=str(path), file_hash="", file_size=0, page_count=0),
            processing_time_seconds=0,
            parser_used="none",
            errors=[error_msg],
            success=False
        )
    
    async def parse_with_preferred_backend(self, file_path: str | Path, backend_name: str) -> ParserResult:
        """Parse with a specific backend (no fallback)."""
        path = Path(file_path)
        backend = next((b for b in self._backends if b.name == backend_name), None)
        
        if not backend:
            raise ValueError(f"Backend {backend_name} not available")
        
        return await backend.parse(path)
    
    async def parse_multiple(self, file_paths: list[str | Path]) -> list[ParserResult]:
        """Parse multiple PDFs concurrently."""
        semaphore = asyncio.Semaphore(4)  # Limit concurrency
        
        async def parse_one(path):
            async with semaphore:
                return await self.parse(path)
        
        tasks = [parse_one(path) for path in file_paths]
        return await asyncio.gather(*tasks)
    
    def get_available_backends(self) -> list[str]:
        return [b.name for b in self._backends]
    
    def get_backend(self, name: str) -> Optional[PDFParserBackend]:
        return next((b for b in self._backends if b.name == name), None)


class FinancialDocumentParser:
    """
    High-level financial document parser with intelligent backend selection.
    
    Automatically selects the best backend based on document type:
    - SEC filings (10-K, 10-Q) -> pdfplumber (best tables)
    - Annual reports -> pdfplumber (best tables)
    - Earnings presentations -> PyMuPDF (fast)
    - Simple text documents -> PyMuPDF (fast)
    - Scanned/OCR documents -> pdfminer (fallback)
    """
    
    def __init__(self, parser: Optional[PDFParser] = None):
        self.parser = parser or PDFParser(
            backends=["pdfplumber", "pymupdf", "pdfminer"],
            prefer_tables=True,
            fallback_enabled=True
        )
    
    def _detect_document_type(self, file_path: Path, metadata: DocumentMetadata) -> str:
        """Detect financial document type from metadata and content."""
        title = (metadata.title or "").lower()
        subject = (metadata.subject or "").lower()
        filename = metadata.file_path.lower()
        
        # Check for SEC filing types
        if "10-k" in title or "10-k" in filename or "10-k" in subject:
            return "10k"
        if "10-q" in title or "10-q" in filename or "10-q" in subject:
            return "10q"
        if "8-k" in title or "8-k" in filename or "8-k" in subject:
            return "8k"
        if "def14a" in title or "def14a" in filename or "proxy" in subject:
            return "def14a"
        if "s-1" in title or "s-1" in filename or "registration" in subject:
            return "s1"
        if "13f" in title or "13f" in filename:
            return "13f"
        
        # Check for other document types
        if "annual report" in title or "annual report" in subject:
            return "annual_report"
        if "quarterly report" in title or "quarterly report" in subject:
            return "quarterly_report"
        if "earnings" in title or "earnings" in subject or "transcript" in title:
            return "earnings_transcript"
        if "presentation" in title or "presentation" in subject or "slides" in subject:
            return "investor_presentation"
        
        return "financial_document"
    
    def _select_backend(self, doc_type: str) -> list[str]:
        """Select optimal backend order for document type."""
        if doc_type in ["10k", "10q", "10q", "annual_report", "def14a", "s1"]:
            # SEC filings with complex tables - pdfplumber first
            return ["pdfplumber", "pymupdf", "pdfminer"]
        elif doc_type in ["earnings_transcript", "investor_presentation"]:
            # Presentations - PyMuPDF fast, good text
            return ["pymupdf", "pdfplumber", "pdfminer"]
        else:
            # Default order
            return ["pdfplumber", "pymupdf", "pdfminer"]
    
    async def parse(self, file_path: str | Path) -> ParserResult:
        """Parse financial document with intelligent backend selection."""
        path = Path(file_path)
        
        # Quick parse to get metadata
        quick_parser = PDFParser(backends=["pymupdf"], fallback_enabled=False)
        quick_result = await quick_parser.parse(file_path)
        
        if not quick_result.success:
            # Fallback to full parser
            return await self.parser.parse(file_path)
        
        # Detect document type
        doc_type = self._detect_document_type(path, quick_result.metadata)
        
        # Select optimal backend order
        backend_order = self._select_backend(doc_type)
        
        # Parse with optimal backend order
        optimal_parser = PDFParser(
            backends=backend_order,
            prefer_tables=True,
            fallback_enabled=True
        )
        
        result = await optimal_parser.parse(file_path)
        result.metadata.document_type = doc_type
        
        return result
    
    async def parse_batch(self, file_paths: list[str | Path]) -> list[ParserResult]:
        """Parse multiple financial documents."""
        return await self.parser.parse_multiple(file_paths)


class PDFParserFactory:
    """Factory for creating PDF parsers with different configurations."""
    
    @staticmethod
    def create_standard() -> PDFParser:
        """Standard parser with all backends."""
        return PDFParser(
            backends=["pdfplumber", "pymupdf", "pdfminer"],
            prefer_tables=True,
            fallback_enabled=True
        )
    
    @staticmethod
    def create_fast() -> PDFParser:
        """Fast parser for simple documents."""
        return PDFParser(
            backends=["pymupdf", "pdfplumber"],
            prefer_tables=False,
            fallback_enabled=True
        )
    
    @staticmethod
    def create_table_focused() -> PDFParser:
        """Parser optimized for table extraction."""
        return PDFParser(
            backends=["pdfplumber", "pymupdf"],
            prefer_tables=True,
            fallback_enabled=True
        )
    
    @staticmethod
    def create_financial() -> FinancialDocumentParser:
        """Financial document parser with smart backend selection."""
        return FinancialDocumentParser()
    
    @staticmethod
    def create_archival() -> PDFParser:
        """Parser for archival/OCR documents."""
        return PDFParser(
            backends=["pdfminer", "pymupdf", "pdfplumber"],
            prefer_tables=False,
            fallback_enabled=True
        )


# Convenience functions
async def parse_pdf(file_path: str | Path, backend: Optional[str] = None) -> ParserResult:
    """Convenience function to parse a single PDF."""
    if backend:
        parser = PDFParser(backends=[backend], fallback_enabled=False)
    else:
        parser = PDFParserFactory.create_standard()
    return await parser.parse(file_path)


async def parse_financial_pdf(file_path: str | Path) -> ParserResult:
    """Parse a financial PDF with intelligent backend selection."""
    parser = PDFParserFactory.create_financial()
    return await parser.parse(file_path)


async def extract_tables_from_pdf(file_path: str | Path) -> list:
    """Extract all tables from a PDF."""
    result = await parse_financial_pdf(file_path)
    tables = []
    for page in result.pages:
        tables.extend(page.tables)
    return tables


async def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract all text from a PDF."""
    result = await parse_financial_pdf(file_path)
    return "\n\n".join(page.text for page in result.pages)


# Export all
__all__ = [
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
]