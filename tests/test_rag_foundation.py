"""
Tests for RAG Foundation Layer.

Tests cover:
- PDF loading and text extraction
- Metadata extraction
- Section-aware chunking
- Embedding generation
- ChromaDB storage and retrieval
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Import RAG components
from rag.ingestion.pdf_processor import PDFProcessor, ExtractedPage, DocumentMetadata
from rag.ingestion.metadata_extractor import MetadataExtractor, FinancialMetadata
from rag.ingestion.document_loader import DocumentLoader, LoadedDocument
from rag.chunking.section_splitter import SectionAwareChunker, Section, Chunk
from rag.embeddings.embedding_service import EmbeddingService, EmbeddingCache
from rag.embeddings.reranker_service import RerankerService
from rag.vector_store.chroma_store import ChromaVectorStore, SearchResult, SearchResponse


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    d = tempfile.mkdtemp()
    yield Path(d)
    # Small delay to allow ChromaDB to release SQLite locks
    time.sleep(0.1)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_pdf_path(temp_dir):
    """Create a minimal test PDF path."""
    pdf_path = temp_dir / "test_10k.pdf"
    pdf_path.write_text("Test PDF content")
    return pdf_path


@pytest.fixture
def sample_financial_text():
    """Sample financial document text for testing."""
    return """
NVIDIA CORPORATION
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the fiscal year ended January 28, 2024

ITEM 1. BUSINESS

NVIDIA Corporation (the "Company" or "NVIDIA") was incorporated in California in April 1993
and reincorporated in Delaware in April 1998. NVIDIA is the pioneer of accelerated computing.

ITEM 1A. RISK FACTORS

Our business faces significant risks including competition, cyclical demand, and supply chain constraints.
These risk factors could materially affect our financial condition.

ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

Revenue for fiscal year 2024 was $60.9 billion, an increase of 126% from fiscal year 2023.
Data Center revenue was $47.5 billion, up 217% year over year.
Gaming revenue was $10.4 billion, down 12% year over year.
Gross margin was 72.7%, up from 56.9% in the prior year.

ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA

Consolidated Balance Sheets
As of January 28, 2024 and January 29, 2023
(In millions)

Assets                          2024        2023
Cash and cash equivalents       $26,030     $13,290
Marketable securities           $19,520     $10,120
Total assets                    $65,728     $41,181

ITEM 15. EXHIBITS AND FINANCIAL STATEMENT SCHEDULES

Note 1: Summary of Significant Accounting Policies
Note 2: Revenue Recognition
"""


# ============================================================================
# PDF Processor Tests
# ============================================================================

class TestPDFProcessor:
    """Tests for PDFProcessor class."""
    
    def test_processor_initialization(self):
        """Test PDFProcessor initializes with correct defaults."""
        processor = PDFProcessor()
        assert processor.extract_tables is True
        assert processor.extract_images is False
    
    def test_processor_custom_config(self):
        """Test PDFProcessor with custom configuration."""
        processor = PDFProcessor(extract_tables=False, extract_images=True)
        assert processor.extract_tables is False
        assert processor.extract_images is True
    
    @patch('fitz.open')
    def test_process_mock_pdf(self, mock_fitz_open, sample_pdf_path):
        """Test processing a PDF with mocked fitz."""
        # Setup mock document
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "title": "NVIDIA 10-K 2024",
            "author": "",
            "subject": "",
            "creator": "",
            "producer": "",
            "creationDate": "D:20240228",
            "modDate": "D:20240228",
        }
        mock_doc.__len__ = Mock(return_value=3)
        mock_doc.close = Mock()
        
        # Mock pages - need to mock get_text for both "text" and "dict" modes
        def mock_get_text(mode="text"):
            if mode == "text":
                return "NVIDIA CORPORATION\nITEM 1. BUSINESS"
            elif mode == "dict":
                return {"blocks": []}
            return ""
        
        mock_page1 = MagicMock()
        mock_page1.get_text.side_effect = mock_get_text
        
        mock_page2 = MagicMock()
        mock_page2.get_text.side_effect = mock_get_text
        
        mock_page3 = MagicMock()
        mock_page3.get_text.side_effect = mock_get_text
        
        mock_doc.__getitem__ = Mock(side_effect=[mock_page1, mock_page2, mock_page3])
        
        mock_fitz_open.return_value = mock_doc
        
        # Test
        processor = PDFProcessor()
        pages, metadata = processor.process(sample_pdf_path)
        
        # Assertions
        assert isinstance(pages, list)
        assert len(pages) == 3
        assert isinstance(metadata, DocumentMetadata)
        assert metadata.page_count == 3
        assert metadata.title == "NVIDIA 10-K 2024"
    
    def test_calculate_hash(self, temp_dir):
        """Test file hash calculation."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello World")
        
        processor = PDFProcessor()
        hash_val = processor._calculate_hash(test_file)
        
        assert len(hash_val) == 64  # SHA256 hex length
        assert isinstance(hash_val, str)
    
    def test_parse_pdf_date(self):
        """Test PDF date parsing."""
        processor = PDFProcessor()
        
        # Standard format
        date = processor._parse_pdf_date("D:20240228120000+00'00'")
        assert date is not None
        assert date.year == 2024
        assert date.month == 2
        assert date.day == 28
        
        # Invalid format
        date = processor._parse_pdf_date("invalid")
        assert date is None
        
        # Empty
        date = processor._parse_pdf_date("")
        assert date is None


# ============================================================================
# Metadata Extractor Tests
# ============================================================================

class TestMetadataExtractor:
    """Tests for MetadataExtractor class."""
    
    def test_extractor_initialization(self):
        """Test MetadataExtractor initializes correctly."""
        extractor = MetadataExtractor()
        assert extractor.config == {}
    
    def test_extract_company_name(self, sample_financial_text):
        """Test company name extraction."""
        extractor = MetadataExtractor()
        
        pages = [ExtractedPage(page_number=1, text=sample_financial_text, blocks=[])]
        
        base_meta = DocumentMetadata(
            file_path="test.pdf",
            file_hash="abc123",
            file_size=1000,
            page_count=1,
        )
        
        metadata = extractor.extract(pages, base_meta)
        
        assert metadata.company_name is not None
        assert "NVIDIA" in metadata.company_name.upper()
    
    def test_extract_document_type(self, sample_financial_text):
        """Test document type classification."""
        extractor = MetadataExtractor()
        
        pages = [ExtractedPage(page_number=1, text=sample_financial_text, blocks=[])]
        
        base_meta = DocumentMetadata(
            file_path="test.pdf",
            file_hash="abc123",
            file_size=1000,
            page_count=1,
        )
        
        metadata = extractor.extract(pages, base_meta)
        
        assert metadata.document_type == "10k"
    
    def test_extract_sec_identifiers(self, sample_financial_text):
        """Test SEC identifier extraction."""
        extractor = MetadataExtractor()
        
        # Add CIK and accession to text
        text = sample_financial_text + "\nCIK: 0001045810\nAccession Number: 0001045810-24-000012"
        
        pages = [ExtractedPage(page_number=1, text=text, blocks=[])]
        
        base_meta = DocumentMetadata(
            file_path="test.pdf",
            file_hash="abc123",
            file_size=1000,
            page_count=1,
        )
        
        metadata = extractor.extract(pages, base_meta)
        
        assert metadata.cik == "0001045810"
        assert metadata.accession_number == "0001045810-24-000012"
    
    def test_extract_fiscal_period(self, sample_financial_text):
        """Test fiscal year/quarter extraction."""
        extractor = MetadataExtractor()
        
        pages = [ExtractedPage(page_number=1, text=sample_financial_text, blocks=[])]
        
        base_meta = DocumentMetadata(
            file_path="test.pdf",
            file_hash="abc123",
            file_size=1000,
            page_count=1,
        )
        
        metadata = extractor.extract(pages, base_meta)
        
        assert metadata.fiscal_year == 2024
    
    def test_detect_content_sections(self, sample_financial_text):
        """Test detection of key financial sections."""
        extractor = MetadataExtractor()
        
        pages = [ExtractedPage(page_number=1, text=sample_financial_text, blocks=[])]
        
        base_meta = DocumentMetadata(
            file_path="test.pdf",
            file_hash="abc123",
            file_size=1000,
            page_count=1,
        )
        
        metadata = extractor.extract(pages, base_meta)
        
        assert metadata.has_mdna is True
        assert metadata.has_risk_factors is True
        assert metadata.has_financial_statements is True
        assert metadata.has_footnotes is True


# ============================================================================
# Document Loader Tests
# ============================================================================

class TestDocumentLoader:
    """Tests for DocumentLoader class."""
    
    def test_loader_initialization(self):
        """Test DocumentLoader initializes correctly."""
        loader = DocumentLoader()
        assert loader.pdf_processor is not None
        assert loader.metadata_extractor is not None
    
    def test_supported_extensions(self):
        """Test supported file extensions."""
        loader = DocumentLoader()
        assert ".pdf" in loader.supported_extensions
    
    @patch('rag.ingestion.document_loader.PDFProcessor.process')
    @patch('rag.ingestion.document_loader.MetadataExtractor.extract')
    def test_load_mock_document(self, mock_extract, mock_process, sample_pdf_path):
        """Test loading a document with mocked components."""
        # Setup mocks
        mock_pages = [
            ExtractedPage(page_number=1, text="Test content", blocks=[]),
        ]
        mock_process.return_value = (mock_pages, DocumentMetadata(
            file_path=str(sample_pdf_path),
            file_hash="abc123",
            file_size=1000,
            page_count=1,
        ))
        
        mock_extract.return_value = FinancialMetadata(
            file_path=str(sample_pdf_path),
            file_hash="abc123",
            page_count=1,
            company_name="NVIDIA",
            document_type="10k",
            fiscal_year=2024,
        )
        
        # Test
        loader = DocumentLoader()
        doc = loader.load(sample_pdf_path)
        
        # Assertions
        assert isinstance(doc, LoadedDocument)
        assert doc.processing_status == "success"
        assert len(doc.pages) == 1
        assert doc.company_name == "NVIDIA"
        assert doc.document_type == "10k"
        assert doc.fiscal_year == 2024
    
    def test_validate_document(self):
        """Test document validation."""
        loader = DocumentLoader()
        
        # Valid document
        doc = LoadedDocument(
            pages=[ExtractedPage(page_number=1, text="x" * 2000, blocks=[])],
            base_metadata=DocumentMetadata(
                file_path="test.pdf",
                file_hash="abc123",
                file_size=1000,
                page_count=1,
            ),
            financial_metadata=FinancialMetadata(
                file_path="test.pdf",
                file_hash="abc123",
                page_count=1,
                company_name="NVIDIA",
                document_type="10k",
                has_financial_statements=True,
                has_mdna=True,
            ),
            processing_status="success",
        )
        
        is_valid, issues = loader.validate_document(doc)
        assert is_valid is True
        assert len(issues) == 0
        
        # Invalid document (no company)
        doc.financial_metadata.company_name = None
        is_valid, issues = loader.validate_document(doc)
        assert is_valid is False
        assert any("company" in issue.lower() for issue in issues)


# ============================================================================
# Section Splitter / Chunker Tests
# ============================================================================

class TestSectionSplitter:
    """Tests for SectionAwareChunker and SectionDetector."""
    
    def test_chunker_initialization(self):
        """Test SectionAwareChunker initializes correctly."""
        chunker = SectionAwareChunker(chunk_size=512, chunk_overlap=50)
        assert chunker.section_detector is not None
        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 50
    
    def test_sec_structure_detection(self, sample_financial_text):
        """Test detection of SEC item structure."""
        pages = [ExtractedPage(page_number=1, text=sample_financial_text, blocks=[])]
        
        from rag.ingestion.document_loader import LoadedDocument
        doc = LoadedDocument(
            pages=pages,
            base_metadata=DocumentMetadata(
                file_path="test.pdf",
                file_hash="abc123",
                file_size=1000,
                page_count=1,
            ),
            financial_metadata=FinancialMetadata(
                file_path="test.pdf",
                file_hash="abc123",
                page_count=1,
                company_name="NVIDIA",
                document_type="10k",
            ),
        )
        
        chunker = SectionAwareChunker(chunk_size=512, chunk_overlap=50)
        chunks = chunker.chunk_document(doc)
        
        # Should have created chunks
        assert len(chunks) > 0
        
        # Check chunk metadata
        for chunk in chunks:
            assert isinstance(chunk, Chunk)
            assert chunk.company == "NVIDIA"
            assert chunk.document_type == "10k"
            assert chunk.token_count > 0
            assert chunk.section_type in ["business", "risk_factors", "mdna", "financial_statements", "exhibits", "other"]
    
    def test_chunk_size_limit(self, sample_financial_text):
        """Test that chunks respect size limits."""
        pages = [ExtractedPage(page_number=1, text=sample_financial_text, blocks=[])]
        
        from rag.ingestion.document_loader import LoadedDocument
        doc = LoadedDocument(
            pages=pages,
            base_metadata=DocumentMetadata(
                file_path="test.pdf",
                file_hash="abc123",
                file_size=1000,
                page_count=1,
            ),
            financial_metadata=FinancialMetadata(
                file_path="test.pdf",
                file_hash="abc123",
                page_count=1,
                company_name="NVIDIA",
                document_type="10k",
            ),
        )
        
        # Small chunk size
        chunker = SectionAwareChunker(chunk_size=200, chunk_overlap=20)
        chunks = chunker.chunk_document(doc)
        
        # All chunks should be within reasonable size
        for chunk in chunks:
            assert chunk.token_count <= 100  # 200 chars / 4 ≈ 50 tokens, with margin
    
    def test_overlap_between_chunks(self, sample_financial_text):
        """Test that chunks have overlap when a single section is split."""
        # Create a document with a very long MD&A section that will be split into multiple chunks
        long_mdna = "ITEM 7. MD&A\n\n" + "Revenue grew significantly this quarter. " * 200
        
        pages = [ExtractedPage(page_number=1, text=long_mdna, blocks=[])]
        
        from rag.ingestion.document_loader import LoadedDocument
        doc = LoadedDocument(
            pages=pages,
            base_metadata=DocumentMetadata(
                file_path="test.pdf",
                file_hash="abc123",
                file_size=1000,
                page_count=1,
            ),
            financial_metadata=FinancialMetadata(
                file_path="test.pdf",
                file_hash="abc123",
                page_count=1,
                company_name="NVIDIA",
                document_type="10k",
            ),
        )
        
        chunker = SectionAwareChunker(chunk_size=200, chunk_overlap=50)
        chunks = chunker.chunk_document(doc)
        
        # Check overlap exists - when a single section is split into multiple chunks
        if len(chunks) > 1:
            has_overlap = any(c.overlap_tokens > 0 for c in chunks)
            assert has_overlap, f"Expected overlap in chunks but got {[c.overlap_tokens for c in chunks]}"
        else:
            # If only one chunk, skip overlap check
            pass


# ============================================================================
# Embedding Service Tests
# ============================================================================

class TestEmbeddingService:
    """Tests for EmbeddingService and EmbeddingCache."""
    
    def test_cache_initialization(self, temp_dir):
        """Test EmbeddingCache initializes correctly."""
        cache = EmbeddingCache(cache_dir=str(temp_dir / "cache"))
        assert cache.cache_dir.exists()
        assert cache.cache_dir.is_dir()
    
    def test_cache_get_miss(self, temp_dir):
        """Test cache miss returns None."""
        cache = EmbeddingCache(cache_dir=str(temp_dir / "cache"))
        result = cache.get("test text", "test-model")
        assert result is None
        assert cache.get_stats()["misses"] == 1
    
    def test_cache_set_and_get(self, temp_dir):
        """Test cache set and get roundtrip."""
        cache = EmbeddingCache(cache_dir=str(temp_dir / "cache"))
        
        embedding = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        cache.set("test text", "test-model", embedding)
        
        retrieved = cache.get("test text", "test-model")
        
        assert retrieved is not None
        np.testing.assert_array_equal(retrieved, embedding)
        assert cache.get_stats()["hits"] == 1
    
    def test_cache_different_models(self, temp_dir):
        """Test cache separates by model name."""
        cache = EmbeddingCache(cache_dir=str(temp_dir / "cache"))
        
        emb1 = np.array([0.1, 0.2], dtype=np.float32)
        emb2 = np.array([0.3, 0.4], dtype=np.float32)
        
        cache.set("same text", "model-a", emb1)
        cache.set("same text", "model-b", emb2)
        
        retrieved_a = cache.get("same text", "model-a")
        retrieved_b = cache.get("same text", "model-b")
        
        np.testing.assert_array_equal(retrieved_a, emb1)
        np.testing.assert_array_equal(retrieved_b, emb2)
    
    def test_cache_clear(self, temp_dir):
        """Test cache clearing."""
        cache = EmbeddingCache(cache_dir=str(temp_dir / "cache"))
        
        cache.set("text", "model", np.array([0.1]))
        assert cache.get_stats()["memory_entries"] == 1
        
        cache.clear()
        assert cache.get_stats()["memory_entries"] == 0
        assert cache.get_stats()["hits"] == 0
        assert cache.get_stats()["misses"] == 0
    
    @patch('rag.embeddings.embedding_service.ContainerONNXEmbeddingFunction')
    def test_embedding_service_mock(self, mock_embedding_fn):
        """Test EmbeddingService with mocked embedding function."""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], dtype=np.float32)
        mock_embedding_fn.return_value = mock_instance
        
        service = EmbeddingService(
            model_name="test-model",
            device="cpu",
            cache_enabled=False,
        )
        
        # Test single text
        result = service.embed("Test text")
        assert result.shape == (3,)
        
        # Test multiple texts
        results = service.embed(["Text 1", "Text 2"])
        assert results.shape == (2, 3)
        
        # Verify model was called
        assert mock_instance.called
    
    def test_embedding_service_stats(self):
        """Test embedding service statistics."""
        with patch('sentence_transformers.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([[0.1, 0.2]], dtype=np.float32)
            mock_model.get_sentence_embedding_dimension.return_value = 2
            mock_st.return_value = mock_model
            
            service = EmbeddingService(cache_enabled=False)
            service.embed("test")
            
            stats = service.get_stats()
            assert stats["total_embeddings"] >= 1
            assert "avg_time_ms" in stats


# ============================================================================
# Reranker Service Tests
# ============================================================================

class TestRerankerService:
    """Tests for RerankerService."""
    
    @patch('sentence_transformers.CrossEncoder')
    def test_rerank_mock(self, mock_ce):
        """Test reranker with mocked model."""
        # Setup mock
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.9, 0.3, 0.7])
        mock_ce.return_value = mock_model
        
        reranker = RerankerService(model_name="test-model", device="cpu")
        
        query = "NVIDIA revenue growth"
        docs = [
            "Revenue was $60.9B in FY2024",
            "Risk factors include competition",
            "Data Center revenue grew 217%",
        ]
        
        results = reranker.rerank(query, docs, top_k=2)
        
        # Should return top 2 by score
        assert len(results) == 2
        assert results[0][0] == 0  # First doc (0.9)
        assert results[1][0] == 2  # Third doc (0.7)
    
    @patch('sentence_transformers.CrossEncoder')
    def test_rerank_with_scores(self, mock_ce):
        """Test rerank_with_scores method."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.8, 0.4, 0.6])
        mock_ce.return_value = mock_model
        
        reranker = RerankerService(device="cpu")
        
        query = "test query"
        docs = [
            {"text": "Doc 1", "source": "10k"},
            {"text": "Doc 2", "source": "10q"},
            {"text": "Doc 3", "source": "10k"},
        ]
        
        results = reranker.rerank_with_scores(query, docs, top_k=2, score_threshold=0.5)
        
        assert len(results) == 2
        assert "rerank_score" in results[0]
        assert results[0]["rerank_score"] == 0.8
        assert results[1]["rerank_score"] == 0.6


# ============================================================================
# ChromaDB Vector Store Tests
# ============================================================================

class TestChromaVectorStore:
    """Tests for ChromaVectorStore."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self._stores = []
    
    def teardown_method(self):
        """Clean up stores after each test."""
        for store in self._stores:
            try:
                store.close()
            except Exception:
                pass
    
    def _make_store(self, persist_dir):
        """Create a store and track it for cleanup."""
        store = ChromaVectorStore(persist_dir=str(persist_dir))
        self._stores.append(store)
        return store
    
    def test_store_initialization(self, temp_dir):
        """Test ChromaVectorStore initializes correctly."""
        persist_dir = temp_dir / "chroma"
        store = self._make_store(persist_dir)
        
        assert store.collection is not None
        assert store.collection_name == "financial_reports"
        assert store.embedding_dim == 1024
    
    def test_add_documents(self, temp_dir):
        """Test adding documents to store."""
        persist_dir = temp_dir / "chroma"
        store = self._make_store(persist_dir)
        
        documents = ["Document 1", "Document 2"]
        embeddings = np.array([[0.1]*1024, [0.2]*1024], dtype=np.float32)
        metadatas = [
            {"company": "NVIDIA", "doc_type": "10k"},
            {"company": "AMD", "doc_type": "10k"},
        ]
        
        ids = store.add(documents, embeddings, metadatas)
        
        assert len(ids) == 2
        assert all(isinstance(id_, str) for id_ in ids)
    
    def test_add_chunks(self, temp_dir):
        """Test adding chunks with standardized metadata."""
        persist_dir = temp_dir / "chroma"
        store = self._make_store(persist_dir)
        
        chunks = [
            {
                "text": "NVIDIA revenue grew 126%",
                "company": "NVIDIA",
                "document_type": "10k",
                "fiscal_year": 2024,
                "section": "Item 7 - MD&A",
                "section_type": "mdna",
                "page_start": 42,
                "page_end": 45,
                "chunk_index": 0,
                "token_count": 150,
                "source_document": "nvidia_10k_2024.pdf",
            }
        ]
        embeddings = np.array([[0.1]*1024], dtype=np.float32)
        
        ids = store.add_chunks(chunks, embeddings)
        
        assert len(ids) == 1
    
    def test_search(self, temp_dir):
        """Test vector search."""
        persist_dir = temp_dir / "chroma"
        store = self._make_store(persist_dir)
        
        # Add test documents
        documents = ["NVIDIA revenue 2024", "AMD revenue 2024", "NVIDIA risk factors"]
        embeddings = np.array([[0.1]*1024, [0.2]*1024, [0.3]*1024], dtype=np.float32)
        metadatas = [
            {"company": "NVIDIA", "section_type": "mdna"},
            {"company": "AMD", "section_type": "mdna"},
            {"company": "NVIDIA", "section_type": "risk_factors"},
        ]
        store.add(documents, embeddings, metadatas)
        
        # Search
        query_embedding = np.array([0.15]*1024, dtype=np.float32)
        response = store.search(query_embedding, n_results=2)
        
        assert isinstance(response, SearchResponse)
        assert len(response.results) <= 2
        assert response.search_time_ms > 0
    
    def test_search_with_filter(self, temp_dir):
        """Test search with metadata filter."""
        persist_dir = temp_dir / "chroma"
        store = self._make_store(persist_dir)
        
        # Add documents
        documents = ["NVIDIA revenue", "AMD revenue"]
        embeddings = np.array([[0.1]*1024, [0.2]*1024], dtype=np.float32)
        metadatas = [
            {"company": "NVIDIA"},
            {"company": "AMD"},
        ]
        store.add(documents, embeddings, metadatas)
        
        # Search with company filter
        query_embedding = np.array([0.15]*1024, dtype=np.float32)
        response = store.search(query_embedding, n_results=10, where={"company": "NVIDIA"})
        
        assert len(response.results) == 1
        assert response.results[0].metadata["company"] == "NVIDIA"
    
    def test_get_by_company(self, temp_dir):
        """Test retrieving all chunks for a company."""
        persist_dir = temp_dir / "chroma"
        store = self._make_store(persist_dir)
        
        # Add documents
        documents = ["NVIDIA doc 1", "NVIDIA doc 2", "AMD doc 1"]
        embeddings = np.array([[0.1]*1024]*3, dtype=np.float32)
        metadatas = [
            {"company": "NVIDIA"},
            {"company": "NVIDIA"},
            {"company": "AMD"},
        ]
        store.add(documents, embeddings, metadatas)
        
        # Get by company
        results = store.get_by_company("NVIDIA")
        
        assert len(results) == 2
        assert all(r.metadata["company"] == "NVIDIA" for r in results)
    
    def test_count(self, temp_dir):
        """Test document counting."""
        persist_dir = temp_dir / "chroma"
        store = self._make_store(persist_dir)
        
        # Empty count
        assert store.count() == 0
        
        # Add documents
        store.add(["doc1"], np.array([[0.1]*1024], dtype=np.float32), [{"company": "NVIDIA"}])
        assert store.count() == 1
        
        # Count with filter
        store.add(["doc2"], np.array([[0.2]*1024], dtype=np.float32), [{"company": "AMD"}])
        assert store.count({"company": "NVIDIA"}) == 1
        assert store.count() == 2
    
    def test_get_stats(self, temp_dir):
        """Test getting store statistics."""
        persist_dir = temp_dir / "chroma"
        store = self._make_store(persist_dir)
        
        # Add test data
        docs = ["NVIDIA 10k", "NVIDIA 10q", "AMD 10k"]
        embeddings = np.array([[0.1]*1024]*3, dtype=np.float32)
        metadatas = [
            {"company": "NVIDIA", "document_type": "10k"},
            {"company": "NVIDIA", "document_type": "10q"},
            {"company": "AMD", "document_type": "10k"},
        ]
        store.add(docs, embeddings, metadatas)
        
        stats = store.get_stats()
        
        assert stats["total_chunks"] == 3
        assert stats["unique_companies"] == 2
        assert "NVIDIA" in stats["companies"]
        assert "AMD" in stats["companies"]
        assert "10k" in stats["document_types"]
        assert "10q" in stats["document_types"]
    
    def test_reset(self, temp_dir):
        """Test store reset."""
        persist_dir = temp_dir / "chroma"
        store = self._make_store(persist_dir)
        
        # Add document with valid metadata
        store.add(["doc1"], np.array([[0.1]*1024], dtype=np.float32), [{"source": "test"}])
        assert store.count() == 1
        
        # Reset
        store.reset()
        assert store.count() == 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestRAGIntegration:
    """Integration tests for the full RAG pipeline."""
    
    @patch('rag.ingestion.document_loader.PDFProcessor.process')
    @patch('rag.ingestion.document_loader.MetadataExtractor.extract')
    @patch('sentence_transformers.SentenceTransformer')
    def test_full_pipeline_mock(self, mock_st, mock_extract, mock_process, temp_dir, sample_pdf_path):
        """Test the full pipeline with all components mocked."""
        # Setup mocks
        sample_text = "NVIDIA revenue grew 126% to $60.9 billion in FY2024. Data Center segment led growth."
        
        mock_pages = [ExtractedPage(page_number=1, text=sample_text, blocks=[])]
        mock_process.return_value = (mock_pages, DocumentMetadata(
            file_path="test.pdf",
            file_hash="abc123",
            file_size=1000,
            page_count=1,
        ))
        
        mock_extract.return_value = FinancialMetadata(
            file_path="test.pdf",
            file_hash="abc123",
            page_count=1,
            company_name="NVIDIA",
            document_type="10k",
            fiscal_year=2024,
            has_mdna=True,
            has_financial_statements=True,
        )
        
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1]*1024], dtype=np.float32)
        mock_model.get_sentence_embedding_dimension.return_value = 1024
        mock_st.return_value = mock_model
        
        # Run pipeline
        from rag.ingestion.document_loader import DocumentLoader
        from rag.chunking.section_splitter import SectionAwareChunker
        from rag.embeddings.embedding_service import EmbeddingService
        from rag.vector_store.chroma_store import ChromaVectorStore
        
        # 1. Load document
        loader = DocumentLoader()
        doc = loader.load(sample_pdf_path)
        
        assert doc.company_name == "NVIDIA"
        assert doc.processing_status == "success"
        
        # 2. Chunk document
        chunker = SectionAwareChunker(chunk_size=256, chunk_overlap=20)
        chunks = chunker.chunk_document(doc)
        
        assert len(chunks) > 0
        assert all(c.company == "NVIDIA" for c in chunks)
        
        # 3. Generate embeddings
        embedding_service = EmbeddingService(device="cpu", cache_enabled=False)
        texts = [c.text for c in chunks]
        embeddings = embedding_service.embed(texts)
        
        assert embeddings.shape[0] == len(chunks)
        assert embeddings.shape