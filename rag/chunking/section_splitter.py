"""
Section-Aware Chunking for Financial Documents.

Splits documents by financial sections (MD&A, Risk Factors, Financial Statements, etc.)
then applies recursive chunking within sections to preserve semantic boundaries.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from ..ingestion.document_loader import LoadedDocument, ExtractedPage

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """A detected section in a financial document."""
    name: str
    section_type: str  # mdna, risk_factors, financial_statements, business, segments, footnotes, other
    start_page: int
    end_page: int
    start_char: int
    end_char: int
    level: int = 1  # Header level (1=main, 2=subsection, etc.)
    parent: Optional[str] = None
    text: str = ""
    confidence: float = 1.0


@dataclass
class Chunk:
    """A text chunk with metadata for vector storage."""
    text: str
    chunk_index: int
    char_start: int
    char_end: int
    
    # Section metadata
    section_name: str = ""
    section_type: str = ""
    section_level: int = 1
    
    # Document metadata
    page_start: int = 1
    page_end: int = 1
    company: str = ""
    document_type: str = ""
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    
    # Chunking metadata
    token_count: int = 0
    overlap_tokens: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "text": self.text,
            "chunk_index": self.chunk_index,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "section_name": self.section_name,
            "section_type": self.section_type,
            "section_level": self.section_level,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "company": self.company,
            "document_type": self.document_type,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "token_count": self.token_count,
            "overlap_tokens": self.overlap_tokens,
        }


class SectionDetector:
    """Detects financial document sections from text and structure."""
    
    # Section type detection patterns (SEC form structure)
    SECTION_PATTERNS = {
        "mdna": [
            r"item\s+7\.?\s*management['\s]?s\s+discussion\s+and\s+analysis",
            r"management['\s]?s\s+discussion\s+and\s+analysis",
            r"md&a",
            r"mda\s*[-:]\s*management",
            r"management\s+discussion",
        ],
        "risk_factors": [
            r"item\s+1a\.?\s*risk\s+factors",
            r"risk\s+factors",
            r"principal\s+risks",
            r"key\s+risks",
        ],
        "financial_statements": [
            r"item\s+8\.?\s*financial\s+statements",
            r"financial\s+statements\s+and\s+supplementary\s+data",
            r"consolidated\s+balance\s+sheets?",
            r"consolidated\s+statements?\s+of\s+(income|operations|comprehensive\s+income|cash\s+flows?)",
            r"balance\s+sheets?",
            r"income\s+statements?",
            r"cash\s+flow\s+statements?",
        ],
        "segments": [
            r"item\s+2\.?\s*properties",
            r"segment\s+information",
            r"reportable\s+segments",
            r"operating\s+segments",
            r"business\s+segments",
        ],
        "business": [
            r"item\s+1\.?\s*business",
            r"business\s+overview",
            r"our\s+business",
            r"company\s+overview",
        ],
        "footnotes": [
            r"notes\s+to\s+(?:consolidated\s+)?financial\s+statements",
            r"note\s+\d+",
            r"footnotes",
        ],
        "controls": [
            r"item\s+9a\.?\s*controls\s+and\s+procedures",
            r"internal\s+control",
            r"disclosure\s+controls",
        ],
        "legal": [
            r"item\s+3\.?\s*legal\s+proceedings",
            r"legal\s+proceedings",
            r"contingencies",
        ],
        "market": [
            r"item\s+5\.?\s*market\s+for",
            r"market\s+for\s+(?:the\s+)?registrant",
            r"stock\s+price",
        ],
    }
    
    def __init__(self):
        self._compiled_patterns = {}
        for section_type, patterns in self.SECTION_PATTERNS.items():
            self._compiled_patterns[section_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def detect_sections(self, document: LoadedDocument) -> list[Section]:
        """Detect sections in a loaded document."""
        full_text = document.full_text
        pages = document.pages
        
        # Strategy 1: SEC Item structure (most reliable for 10-K/10-Q)
        sections = self._detect_sec_structure(full_text, pages)
        
        if not sections:
            # Strategy 2: Header-based detection
            sections = self._detect_by_headers(full_text, pages)
        
        if not sections:
            # Strategy 3: Keyword-based detection
            sections = self._detect_by_keywords(full_text, pages)
        
        if not sections:
            # Fallback: entire document as one section
            sections = [Section(
                name="Full Document",
                section_type="other",
                start_page=1,
                end_page=document.base_metadata.page_count,
                start_char=0,
                end_char=len(full_text),
                level=1,
                text=full_text,
                confidence=0.3,
            )]
        
        # Merge adjacent sections of same type
        sections = self._merge_adjacent(sections)
        
        # Assign text content to sections
        for section in sections:
            section.text = full_text[section.start_char:section.end_char]
        
        logger.debug(f"Detected {len(sections)} sections: {[s.name for s in sections]}")
        return sections
    
    def _detect_sec_structure(self, text: str, pages: list[ExtractedPage]) -> list[Section]:
        """Detect sections using SEC Item numbering (Item 1, 1A, 2, 7, 8, etc.)."""
        sections = []
        
        # Pattern for SEC items: "Item 1.", "Item 1A.", "Item 7.", etc.
        item_pattern = re.compile(
            r"(?i)^\s*item\s+(\d+[a-z]?)\.?\s+(.+?)(?:\n|$)",
            re.MULTILINE
        )
        
        matches = list(item_pattern.finditer(text))
        
        if len(matches) >= 3:  # At least a few items found
            for i, match in enumerate(matches):
                item_num = match.group(1).upper()
                item_title = match.group(2).strip()
                start_pos = match.start()
                end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                
                # Map item number to section type
                section_type = self._item_to_section_type(item_num)
                
                start_page = self._char_to_page(start_pos, pages)
                end_page = self._char_to_page(end_pos, pages)
                
                section = Section(
                    name=f"Item {item_num}: {item_title}",
                    section_type=section_type,
                    start_page=start_page,
                    end_page=end_page,
                    start_char=start_pos,
                    end_char=end_pos,
                    level=1,
                    confidence=0.9,
                )
                sections.append(section)
        
        return sections
    
    def _item_to_section_type(self, item_num: str) -> str:
        """Map SEC item number to section type."""
        item_map = {
            "1": "business",
            "1A": "risk_factors",
            "1B": "risk_factors",
            "2": "properties",
            "3": "legal",
            "4": "other",
            "5": "market",
            "6": "other",
            "7": "mdna",
            "7A": "mdna",
            "8": "financial_statements",
            "9": "controls",
            "9A": "controls",
            "9B": "other",
            "10": "other",
            "11": "executive_comp",
            "12": "security_ownership",
            "13": "relationships",
            "14": "accountant_fees",
            "15": "exhibits",
        }
        return item_map.get(item_num, "other")
    
    def _detect_by_headers(self, text: str, pages: list[ExtractedPage]) -> list[Section]:
        """Detect sections by header patterns (ALL CAPS, numbered, etc.)."""
        sections = []
        
        # Header patterns
        header_patterns = [
            r"^(?:PART\s+[IVX]+\s*\n)?\s*([A-Z][A-Z\s]{5,50})\s*\n",  # ALL CAPS headers
            r"^(\d+\.?\d*\s+[A-Z][A-Za-z\s]{5,50})\s*\n",  # Numbered headers
            r"^(?:ITEM\s+\d+[A-Z]?\.?\s*)?([A-Z][A-Za-z\s]{5,50})\s*\n",  # Item + title
        ]
        
        headers = []
        for pattern in header_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                headers.append((match.start(), match.group(1).strip()))
        
        if headers:
            headers.sort(key=lambda x: x[0])
            
            for i, (pos, title) in enumerate(headers):
                end_pos = headers[i + 1][0] if i + 1 < len(headers) else len(text)
                
                section_type = self._classify_section(title)
                
                start_page = self._char_to_page(pos, pages)
                end_page = self._char_to_page(end_pos, pages)
                
                sections.append(Section(
                    name=title,
                    section_type=section_type,
                    start_page=start_page,
                    end_page=end_page,
                    start_char=pos,
                    end_char=end_pos,
                    level=1,
                    confidence=0.7,
                ))
        
        return sections
    
    def _detect_by_keywords(self, text: str, pages: list[ExtractedPage]) -> list[Section]:
        """Detect sections by keyword occurrence density."""
        sections = []
        
        for section_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Found a section marker, create section around it
                    start_pos = max(0, match.start() - 500)
                    end_pos = min(len(text), match.end() + 10000)
                    
                    start_page = self._char_to_page(start_pos, pages)
                    end_page = self._char_to_page(end_pos, pages)
                    
                    sections.append(Section(
                        name=f"{section_type.replace('_', ' ').title()} (detected)",
                        section_type=section_type,
                        start_page=start_page,
                        end_page=end_page,
                        start_char=start_pos,
                        end_char=end_pos,
                        level=1,
                        confidence=0.5,
                    ))
                    break  # One per section type
        
        return sections
    
    def _classify_section(self, title: str) -> str:
        """Classify a section by its title."""
        title_lower = title.lower()
        
        for section_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(title_lower):
                    return section_type
        return "other"
    
    def _merge_adjacent(self, sections: list[Section]) -> list[Section]:
        """Merge adjacent sections of the same type."""
        if not sections:
            return sections
        
        merged = [sections[0]]
        for section in sections[1:]:
            last = merged[-1]
            
            # Merge if same type and close together
            if (section.section_type == last.section_type and 
                section.start_char - last.end_char < 500):
                last.end_char = section.end_char
                last.end_page = section.end_page
                last.name = f"{last.name} + {section.name}"
            else:
                merged.append(section)
        
        return merged
    
    def _char_to_page(self, char_pos: int, pages: list[ExtractedPage]) -> int:
        """Convert character position to page number."""
        for page in pages:
            if hasattr(page, 'char_start') and hasattr(page, 'char_end'):
                if page.char_start <= char_pos < page.char_end:
                    return page.page_number
        return pages[-1].page_number if pages else 1


class SectionAwareChunker:
    """Chunks documents by section, then recursively within sections."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1024,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        self.section_detector = SectionDetector()
    
    def chunk_document(self, document: LoadedDocument) -> list[Chunk]:
        """Chunk a loaded document preserving section boundaries."""
        # Detect sections
        sections = self.section_detector.detect_sections(document)
        
        # Chunk each section
        all_chunks = []
        chunk_index = 0
        
        for section in sections:
            section_chunks = self._chunk_section(
                section=section,
                document=document,
                start_chunk_index=chunk_index,
            )
            all_chunks.extend(section_chunks)
            chunk_index += len(section_chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(sections)} sections")
        return all_chunks
    
    def _chunk_section(
        self,
        section: Section,
        document: LoadedDocument,
        start_chunk_index: int = 0,
    ) -> list[Chunk]:
        """Chunk a single section recursively."""
        text = section.text
        
        if len(text) <= self.chunk_size:
            # Section fits in one chunk
            return [self._create_chunk(
                text=text,
                chunk_index=start_chunk_index,
                section=section,
                document=document,
                char_start=section.start_char,
            )]
        
        # Recursive splitting
        chunks = self._recursive_split(
            text=text,
            section=section,
            document=document,
            base_char_start=section.start_char,
            start_chunk_index=start_chunk_index,
        )
        
        # Add overlap between chunks
        chunks = self._add_overlap(chunks)
        
        return chunks
    
    def _recursive_split(
        self,
        text: str,
        section: Section,
        document: LoadedDocument,
        base_char_start: int,
        start_chunk_index: int,
    ) -> list[Chunk]:
        """Recursively split text by separators."""
        # Separators in order of preference
        separators = [
            "\n\n\n",  # Paragraph breaks
            "\n\n",    # Double newline
            "\n",      # Single newline
            ". ",      # Sentence
            "? ",
            "! ",
            "; ",
            ", ",
            " ",       # Word
            "",        # Character
        ]
        
        def split_text(text: str, separators: list[str], depth: int = 0) -> list[str]:
            if len(text) <= self.chunk_size or depth >= len(separators):
                return [text]
            
            separator = separators[depth]
            
            if separator == "":
                # Character-level split
                return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size)]
            
            parts = text.split(separator)
            
            if len(parts) == 1:
                # Separator not found, try next level
                return split_text(text, separators, depth + 1)
            
            # Recombine with overlap
            chunks = []
            current = ""
            
            for part in parts:
                test = current + (separator if current else "") + part
                
                if len(test) <= self.chunk_size:
                    current = test
                else:
                    if current:
                        chunks.append(current)
                    current = part
            
            if current:
                chunks.append(current)
            
            # Recursively split oversized chunks
            final_chunks = []
            for chunk in chunks:
                if len(chunk) > self.max_chunk_size:
                    final_chunks.extend(split_text(chunk, separators, depth + 1))
                else:
                    final_chunks.append(chunk)
            
            return final_chunks
        
        # Split the text
        text_chunks = split_text(text, separators)
        
        # Create Chunk objects with proper positions
        chunks = []
        char_pos = base_char_start
        
        for i, chunk_text in enumerate(text_chunks):
            chunks.append(self._create_chunk(
                text=chunk_text,
                chunk_index=start_chunk_index + i,
                section=section,
                document=document,
                char_start=char_pos,
            ))
            char_pos += len(chunk_text)
        
        return chunks
    
    def _create_chunk(
        self,
        text: str,
        chunk_index: int,
        section: Section,
        document: LoadedDocument,
        char_start: int,
    ) -> Chunk:
        """Create a Chunk object with all metadata."""
        char_end = char_start + len(text)
        
        # Estimate token count (rough: 1 token ≈ 4 chars for English)
        token_count = len(text) // 4
        
        # Get page range for this chunk
        page_start = self._char_to_page(char_start, document.pages)
        page_end = self._char_to_page(char_end, document.pages)
        
        # Get company metadata
        company = document.financial_metadata.company_name or ""
        doc_type = document.financial_metadata.document_type or ""
        fiscal_year = document.financial_metadata.fiscal_year
        fiscal_quarter = document.financial_metadata.fiscal_quarter
        
        return Chunk(
            text=text,
            chunk_index=chunk_index,
            char_start=char_start,
            char_end=char_end,
            section_name=section.name,
            section_type=section.section_type,
            section_level=section.level,
            page_start=page_start,
            page_end=page_end,
            company=company,
            document_type=doc_type,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            token_count=token_count,
            overlap_tokens=0,  # Will be updated by _add_overlap
        )
    
    def _add_overlap(self, chunks: list[Chunk]) -> list[Chunk]:
        """Add overlap between adjacent chunks."""
        if len(chunks) <= 1:
            return chunks
        
        for i in range(len(chunks) - 1):
            current = chunks[i]
            next_chunk = chunks[i + 1]
            
            # Add overlap from end of current to start of next
            current_text = current.text
            next_text = next_chunk.text
            
            # Take last N tokens from current (minimum 20% of chunk or overlap amount)
            overlap_chars = min(self.chunk_overlap * 4, len(current_text) // 5)
            if len(current_text) > overlap_chars:
                overlap_text = current_text[-overlap_chars:]
                next_chunk.text = overlap_text + next_text
                next_chunk.overlap_tokens = overlap_chars // 4
        
        return chunks
    
    def _char_to_page(self, char_pos: int, pages: list[ExtractedPage]) -> int:
        """Convert character position to page number."""
        for page in pages:
            if hasattr(page, 'char_start') and hasattr(page, 'char_end'):
                if page.char_start <= char_pos < page.char_end:
                    return page.page_number
        return pages[-1].page_number if pages else 1


def create_chunker(config: Optional[dict] = None) -> SectionAwareChunker:
    """Factory function to create SectionAwareChunker from config."""
    if config is None:
        config = {}
    
    chunking_config = config.get("chunking", {})
    
    return SectionAwareChunker(
        chunk_size=chunking_config.get("chunk_size", 512),
        chunk_overlap=chunking_config.get("chunk_overlap", 50),
        min_chunk_size=chunking_config.get("min_chunk_size", 100),
        max_chunk_size=chunking_config.get("max_chunk_size", 1024),
    )