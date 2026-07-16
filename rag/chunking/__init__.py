"""
RAG Chunking Package - Section-aware chunking for financial documents.
"""

from .section_splitter import SectionAwareChunker, SectionDetector, Section, Chunk, create_chunker

__all__ = [
    "SectionAwareChunker",
    "SectionDetector", 
    "Section",
    "Chunk",
    "create_chunker",
]