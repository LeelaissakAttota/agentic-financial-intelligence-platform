"""
Document Loader for Financial Reports.

Orchestrates the document ingestion pipeline: loading PDFs, extracting content,
extracting metadata, and preparing for chunking.
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from .pdf_processor import PDFProcessor, ExtractedPage, DocumentMetadata
from .metadata_extractor import MetadataExtractor, FinancialMetadata

logger = logging.getLogger(__name__)


@dataclass
class LoadedDocument:
    """A fully loaded and processed financial document."""
    # Core content
    pages: list[ExtractedPage]
    
    # Metadata
    base_metadata: DocumentMetadata
    financial_metadata: FinancialMetadata
    
    # Processing info
    processing_status: str = "success"
    processing_errors: list[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    
    @property
    def full_text(self) -> str:
        """Get full document text."""
        return "\n\n".join(page.text for page in self.pages)
    
    @property
    def company_name(self) -> Optional[str]:
        """Get company name from financial metadata."""
        return self.financial_metadata.company_name
    
    @property
    def document_type(self) -> Optional[str]:
        """Get document type."""
        return self.financial_metadata.document_type
    
    @property
    def fiscal_year(self) -> Optional[int]:
        """Get fiscal year."""
        return self.financial_metadata.fiscal_year
    
    @property
    def fiscal_quarter(self) -> Optional[int]:
        """Get fiscal quarter."""
        return self.financial_metadata.fiscal_quarter


class DocumentLoader:
    """High-level document loading and processing pipeline."""
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        
        # Initialize sub-components
        pdf_config = self.config.get("pdf_processor", {})
        self.pdf_processor = PDFProcessor(
            extract_tables=pdf_config.get("extract_tables", True),
            extract_images=pdf_config.get("extract_images", False),
        )
        
        meta_config = self.config.get("metadata_extractor", {})
        self.metadata_extractor = MetadataExtractor(meta_config)
        
        # Supported file types
        self.supported_extensions = {".pdf"}
    
    def load(self, file_path: str | Path) -> LoadedDocument:
        """
        Load and process a financial document.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            LoadedDocument with extracted content and metadata
        """
        import time
        start_time = time.time()
        
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")
        
        if path.suffix.lower() not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {path.suffix}. Supported: {self.supported_extensions}")
        
        logger.info(f"Loading document: {path.name}")
        
        errors = []
        pages = []
        base_metadata = None
        financial_metadata = None
        
        try:
            # Step 1: Extract content from PDF
            pages, base_metadata = self.pdf_processor.process(path)
            logger.debug(f"Extracted {len(pages)} pages")
            
            # Step 2: Extract financial metadata
            financial_metadata = self.metadata_extractor.extract(pages, base_metadata)
            logger.debug(f"Extracted metadata: company={financial_metadata.company_name}, type={financial_metadata.document_type}")
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        processing_time = time.time() - start_time
        
        # Determine overall status
        if errors:
            status = "partial" if pages else "failed"
        else:
            status = "success"
        
        return LoadedDocument(
            pages=pages,
            base_metadata=base_metadata or DocumentMetadata(
                file_path=str(path),
                file_hash="",
                file_size=path.stat().st_size,
                page_count=0,
            ),
            financial_metadata=financial_metadata or FinancialMetadata(
                file_path=str(path),
                file_hash="",
                page_count=0,
            ),
            processing_status=status,
            processing_errors=errors,
            processing_time_seconds=processing_time,
        )
    
    def load_multiple(self, file_paths: list[str | Path]) -> list[LoadedDocument]:
        """Load multiple documents."""
        return [self.load(path) for path in file_paths]
    
    def load_directory(self, directory: str | Path, pattern: str = "*.pdf") -> list[LoadedDocument]:
        """Load all matching documents from a directory."""
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        files = list(path.glob(pattern))
        logger.info(f"Found {len(files)} documents in {path}")
        return self.load_multiple(files)
    
    def validate_document(self, loaded_doc: LoadedDocument) -> tuple[bool, list[str]]:
        """
        Validate a loaded document meets minimum requirements.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        if loaded_doc.processing_status == "failed":
            issues.append("Document processing failed")
            return False, issues
        
        if not loaded_doc.pages:
            issues.append("No pages extracted")
            return False, issues
        
        if loaded_doc.base_metadata.page_count == 0:
            issues.append("Page count is zero")
        
        if not loaded_doc.financial_metadata.company_name:
            issues.append("Company name not detected")
        
        if not loaded_doc.financial_metadata.document_type:
            issues.append("Document type not detected")
        
        # Check for minimum content
        total_chars = sum(len(p.text) for p in loaded_doc.pages)
        if total_chars < 1000:
            issues.append(f"Very little text extracted ({total_chars} chars)")
        
        # Check for key sections
        if not loaded_doc.financial_metadata.has_financial_statements:
            issues.append("No financial statements detected")
        
        if not loaded_doc.financial_metadata.has_mdna:
            issues.append("No MD&A section detected")
        
        # Critical issues that make document invalid
        critical_issues = [
            i for i in issues 
            if any(keyword in i.lower() for keyword in ["company name", "document type", "no pages", "processing failed"])
        ]
        
        is_valid = len(critical_issues) == 0
        return is_valid, issues


def create_document_loader(config: Optional[dict] = None) -> DocumentLoader:
    """Factory function to create DocumentLoader from config."""
    return DocumentLoader(config)