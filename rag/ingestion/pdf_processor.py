"""
PDF Document Processor for Financial Reports.

Uses PyMuPDF (fitz) for high-quality text extraction, table detection,
and metadata preservation from financial documents (10-K, 10-Q, Annual Reports).
"""

import fitz  # PyMuPDF
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Represents a table extracted from a PDF page."""
    page_number: int
    table_index: int
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1
    rows: list[list[str]]
    headers: list[str] = field(default_factory=list)


@dataclass
class ExtractedPage:
    """Represents a single page of extracted content."""
    page_number: int
    text: str
    blocks: list[dict]  # Raw text blocks from PyMuPDF
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


class PDFProcessor:
    """Processes PDF financial documents with high-quality extraction."""
    
    def __init__(self, extract_tables: bool = True, extract_images: bool = False):
        self.extract_tables = extract_tables
        self.extract_images = extract_images
    
    def process(self, file_path: str | Path) -> tuple[list[ExtractedPage], DocumentMetadata]:
        """
        Process a PDF file and extract all content.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted pages, document metadata)
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"File is not a PDF: {path}")
        
        logger.info(f"Processing PDF: {path}")
        
        # Open document
        doc = fitz.open(str(path))
        
        try:
            # Extract metadata
            metadata = self._extract_metadata(doc, path)
            
            # Extract pages
            pages = []
            char_pos = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                extracted_page = self._extract_page(page, page_num + 1)
                extracted_page.char_start = char_pos
                char_pos += len(extracted_page.text)
                extracted_page.char_end = char_pos
                pages.append(extracted_page)
            
            logger.info(f"Extracted {len(pages)} pages from {path.name}")
            return pages, metadata
            
        finally:
            doc.close()
    
    def _extract_metadata(self, doc: fitz.Document, path: Path) -> DocumentMetadata:
        """Extract document metadata."""
        meta = doc.metadata
        
        # Calculate file hash
        file_hash = self._calculate_hash(path)
        
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
            creation_date=creation_date,
            modification_date=mod_date,
        )
    
    def _extract_page(self, page: fitz.Page, page_number: int) -> ExtractedPage:
        """Extract text, tables, and images from a single page."""
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
    
    def _extract_tables(self, page: fitz.Page, page_number: int) -> list[ExtractedTable]:
        """Extract tables from a page using PyMuPDF's table detection."""
        tables = []
        
        try:
            # PyMuPDF 1.23+ has find_tables()
            found_tables = page.find_tables()
            
            for idx, table in enumerate(found_tables):
                # Extract table data
                rows = table.extract()
                
                if not rows:
                    continue
                
                # First row as headers if it looks like headers
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
                ))
                
        except Exception as e:
            logger.warning(f"Table extraction failed on page {page_number}: {e}")
        
        return tables
    
    def _looks_like_header(self, row: list[str]) -> bool:
        """Heuristic to detect if a row is a header row."""
        if not row:
            return False
        # Header rows often have fewer numbers, more text
        text_cells = sum(1 for cell in row if cell and not cell.replace(".", "").replace(",", "").replace("$", "").replace("%", "").isdigit())
        return text_cells > len(row) * 0.5
    
    def _extract_images(self, page: fitz.Page, page_number: int) -> list[dict]:
        """Extract image information from a page."""
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
    
    def _calculate_hash(self, path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _parse_pdf_date(self, date_str: str) -> Optional[date]:
        """Parse PDF date format (D:YYYYMMDDHHmmSSOHH'mm')."""
        if not date_str or not date_str.startswith("D:"):
            return None
        try:
            # D:20240115120000+00'00'
            date_part = date_str[2:10]  # YYYYMMDD
            return date(int(date_part[:4]), int(date_part[4:6]), int(date_part[6:8]))
        except Exception:
            return None
    
    def extract_full_text(self, file_path: str | Path) -> str:
        """Convenience method to extract all text from a PDF."""
        pages, _ = self.process(file_path)
        return "\n\n".join(page.text for page in pages)
    
    def get_page_text(self, file_path: str | Path, page_number: int) -> str:
        """Extract text from a specific page (1-indexed)."""
        path = Path(file_path)
        doc = fitz.open(str(path))
        try:
            if 1 <= page_number <= len(doc):
                page = doc[page_number - 1]
                return page.get_text("text")
            return ""
        finally:
            doc.close()


def create_pdf_processor(config: Optional[dict] = None) -> PDFProcessor:
    """Factory function to create PDFProcessor from config."""
    config = config or {}
    return PDFProcessor(
        extract_tables=config.get("extract_tables", True),
        extract_images=config.get("extract_images", False),
    )