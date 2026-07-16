# RAG Foundation Layer Documentation

## Overview

The RAG (Retrieval-Augmented Generation) Foundation Layer provides the core infrastructure for processing financial documents and enabling semantic search over their content. This layer is used by the Financial Report Agent to extract insights from SEC filings (10-K, 10-Q), annual reports, earnings releases, and investor presentations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAG FOUNDATION LAYER                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────────┐
│   Ingestion  │───▶│     Chunking     │───▶│   Embeddings    │───▶│  Vector DB   │
│   Pipeline   │    │  (Section-Aware) │    │   (BGE-M3)      │    │  (ChromaDB)  │
└──────────────┘    └──────────────────┘    └─────────────────┘    └──────────────┘
       │                    │                     │                    │
       ▼                    ▼                     ▼                    ▼
  PDFProcessor        SectionDetector        EmbeddingService      ChromaVectorStore
  MetadataExtractor   SectionAwareChunker    EmbeddingCache        SearchResult
  DocumentLoader      Chunk                  RerankerService       
                                               
Key Components:
- rag.ingestion: Document loading, PDF processing, metadata extraction
- rag.chunking: Section detection and semantic chunking
- rag.embeddings: Embedding generation with caching, cross-encoder reranking
- rag.vector_store: ChromaDB persistence, hybrid search, metadata filtering
```

## Data Flow

```
1. DOCUMENT INGESTION
   PDF File
      │
      ▼
   PDFProcessor (PyMuPDF)
      ├── Extract text per page
      ├── Extract tables
      ├── Extract metadata (title, author, dates)
      └── Calculate SHA256 hash
      │
      ▼
   MetadataExtractor
      ├── Company name detection
      ├── Document type classification (10-K, 10-Q, 8-K, etc.)
      ├── SEC identifiers (CIK, accession number)
      ├── Fiscal period (year, quarter)
      └── Section detection (MD&A, Risk Factors, Financial Statements)
      │
      ▼
   LoadedDocument (full text + structured metadata)

2. CHUNKING
   LoadedDocument
      │
      ▼
   SectionDetector
      ├── Strategy 1: SEC Item structure (Item 1, 1A, 7, 8, etc.)
      ├── Strategy 2: Header patterns (ALL CAPS, numbered)
      └── Strategy 3: Keyword density
      │
      ▼
   SectionAwareChunker
      ├── Chunk each section recursively
      ├── Separators: \n\n\n, \n\n, \n, ., ?, !, ;, ,
      ├── Target: 512 tokens, overlap: 50 tokens
      └── Preserve section metadata in each chunk
      │
      ▼
   List[Chunk] with: text, section_type, page_range, company, fiscal_year

3. EMBEDDING GENERATION
   Chunks
      │
      ▼
   EmbeddingService (BGE-M3)
      ├── Check cache (SHA256 of text + model)
      ├── Add instruction prefix: "Represent this financial document for retrieval:"
      ├── Batch encode (batch_size=32)
      ├── L2 normalize
      └── Store in cache (disk + memory)
      │
      ▼
   Embeddings (1024-dim vectors)

4. VECTOR STORAGE
   Chunks + Embeddings
      │
      ▼
   ChromaVectorStore
      ├── Persistent ChromaDB (HNSW index)
      ├── Collection per deployment (default: "financial_reports")
      ├── Metadata: company, doc_type, fiscal_year, section_type, page_range
      └── Distance metric: cosine
      │
      ▼
   Stored vectors ready for retrieval

5. RETRIEVAL
   Query
      │
      ▼
   EmbeddingService.embed_query()
      │
      ▼
   ChromaVectorStore.search() / hybrid_search()
      ├── Vector similarity (cosine)
      ├── BM25 keyword (via where_document)
      ├── Metadata filters (company, doc_type, date range, section_type)
      └── Cross-encoder rerank (BGE-Reranker-v2-M3)
      │
      ▼
   SearchResponse with ranked results + citations
```

## Components

### 1. Ingestion (`rag/ingestion/`)

#### `pdf_processor.py` - PDFProcessor
- **Purpose**: High-quality PDF text extraction using PyMuPDF
- **Features**:
  - Page-by-page text extraction with layout preservation
  - Table detection and extraction
  - Image metadata extraction
  - SHA256 content hashing for deduplication
  - PDF metadata parsing (title, author, dates)
- **Configuration**: `extract_tables`, `extract_images`

#### `metadata_extractor.py` - MetadataExtractor
- **Purpose**: Extract structured financial metadata from document text
- **Capabilities**:
  - Company name identification (regex patterns)
  - Document type classification (10-K, 10-Q, 8-K, annual_report, earnings, presentation)
  - SEC identifiers: CIK, accession number, file number
  - Fiscal period: year, quarter, period end date
  - Section presence flags: MD&A, Risk Factors, Financial Statements, Segments, Footnotes
- **Confidence scoring**: Each extraction has a confidence score (0.0-1.0)

#### `document_loader.py` - DocumentLoader
- **Purpose**: High-level orchestration of ingestion pipeline
- **Methods**:
  - `load(file_path)` → LoadedDocument
  - `load_multiple(file_paths)` → List[LoadedDocument]
  - `load_directory(directory, pattern)` → List[LoadedDocument]
  - `validate_document(doc)` → (is_valid, issues)

### 2. Chunking (`rag/chunking/`)

#### `section_splitter.py` - SectionDetector
- **Purpose**: Detect financial document sections using multiple strategies
- **Strategies** (in order):
  1. **SEC Item Structure**: Matches "Item 1.", "Item 1A.", "Item 7.", etc. (highest confidence: 0.9)
  2. **Header Patterns**: ALL CAPS headers, numbered sections (confidence: 0.7)
  3. **Keyword Density**: Section-type keywords (confidence: 0.5)
  4. **Fallback**: Entire document as one section (confidence: 0.3)
- **Section Types**: `business`, `risk_factors`, `mdna`, `financial_statements`, `segments`, `footnotes`, `controls`, `legal`, `market`, `other`

#### `section_splitter.py` - SectionAwareChunker
- **Purpose**: Chunk documents preserving section boundaries
- **Algorithm**:
  1. Detect sections
  2. For each section, if text ≤ chunk_size: single chunk
  3. Else: recursive splitting by separators (`\n\n\n`, `\n\n`, `\n`, `. `, `? `, `! `, `; `, `, `, ` `, ``)
  4. Add overlap between adjacent chunks
  5. Attach full metadata to each chunk
- **Configuration**:
  - `chunk_size`: 512 tokens (default)
  - `chunk_overlap`: 50 tokens (default)
  - `min_chunk_size`: 100 tokens
  - `max_chunk_size`: 1024 tokens

#### `Chunk` dataclass
```python
Chunk(
    text: str,
    chunk_index: int,
    char_start: int,
    char_end: int,
    section_name: str,
    section_type: str,
    section_level: int,
    page_start: int,
    page_end: int,
    company: str,
    document_type: str,
    fiscal_year: int,
    fiscal_quarter: int,
    token_count: int,
    overlap_tokens: int,
)
```

### 3. Embeddings (`rag/embeddings/`)

#### `embedding_service.py` - EmbeddingService
- **Model**: BGE-M3 (BAAI/bge-m3) - 1024 dimensions, 8192 token context
- **Features**:
  - Instruction-aware: "Represent this financial document for retrieval:"
  - Batch processing (default: 32)
  - Device selection: cuda, cpu, mps
  - L2 normalization for cosine similarity
- **Caching** (EmbeddingCache):
  - Key: SHA256(model_name + text)
  - Storage: Disk (`.npy` files) + memory LRU
  - Subdirectory sharding for filesystem performance
  - Statistics: hits, misses, hit_rate
- **Methods**:
  - `embed(texts)` → np.ndarray
  - `embed_documents(texts)` → np.ndarray
  - `embed_query(text)` → np.ndarray
  - `get_dimension()` → int
  - `get_stats()` → dict
  - `warmup(sample_texts)` → None

#### `reranker_service.py` - RerankerService
- **Model**: BGE-Reranker-v2-M3 (cross-encoder)
- **Purpose**: Re-rank retrieval results for higher precision
- **Input**: (query, document) pairs
- **Output**: Relevance scores (0-1)
- **Features**:
  - Batch processing (default: 16)
  - Max length: 512 tokens
  - Threshold filtering
  - Statistics tracking

### 4. Vector Store (`rag/vector_store/`)

#### `chroma_store.py` - ChromaVectorStore
- **Backend**: ChromaDB persistent client
- **Collection**: "financial_reports" (configurable)
- **Index**: HNSW (space=cosine, M=16, ef_construction=200)
- **Metadata Schema**:
  ```json
  {
    "company": "NVIDIA",
    "document_type": "10k",
    "fiscal_year": 2024,
    "fiscal_quarter": null,
    "section": "Item 7 - MD&A",
    "section_type": "mdna",
    "page_start": 42,
    "page_end": 45,
    "chunk_index": 0,
    "token_count": 450,
    "source_document": "nvidia_10k_2024.pdf"
  }
  ```
- **Methods**:
  - `add(documents, embeddings, metadatas, ids)` → List[str]
  - `add_chunks(chunks, embeddings)` → List[str]
  - `search(query_embedding, n_results, where, where_document)` → SearchResponse
  - `hybrid_search(query_embedding, query_text, n_results, where, alpha)` → SearchResponse
  - `get_by_ids(ids)` → List[SearchResult]
  - `get_by_company(company, limit, document_type)` → List[SearchResult]
  - `delete_by_company(company)` → int
  - `delete_by_document(source_document)` → int
  - `count(where)` → int
  - `get_stats()` → dict
  - `reset()` → None

#### `SearchResult` dataclass
```python
SearchResult(
    id: str,
    document: str,
    metadata: dict,
    distance: float,
    score: float,  # 1 - distance for cosine
    rerank_score: Optional[float]
)
```

#### `SearchResponse` dataclass
```python
SearchResponse(
    results: List[SearchResult],
    query: str,
    total_found: int,
    search_time_ms: float,
    metadata_filter: Optional[dict]
)
```

## Configuration

All settings in `config/settings.py`:

```python
# ChromaDB Vector Store
chroma_persist_dir: str = "./data/processed/chroma"
chroma_collection_name: str = "financial_reports"

# RAG Configuration
# Embedding Model
embedding_model: str = "BAAI/bge-m3"
embedding_device: str = "cuda"  # cuda, cpu, mps
embedding_batch_size: int = 32
embedding_instruction: str = "Represent this financial document for retrieval:"

# Chunking
chunk_size: int = 512
chunk_overlap: int = 50
min_chunk_size: int = 100

# Retrieval
retrieval_top_k: int = 20
retrieval_rerank_top_k: int = 10
retrieval_score_threshold: float = 0.5

# Reranker
reranker_model: str = "BAAI/bge-reranker-v2-m3"
reranker_device: str = "cuda"
reranker_batch_size: int = 16

# Caching
embedding_cache_dir: str = "./data/processed/embedding_cache"
embedding_cache_enabled: bool = True
```

## Usage Examples

### Basic Ingestion
```python
from rag.ingestion import create_document_loader
from rag.chunking import create_chunker
from rag.embeddings import create_embedding_service
from rag.vector_store import create_vector_store

# 1. Load document
loader = create_document_loader()
doc = loader.load("nvidia_10k_2024.pdf")

# 2. Chunk
chunker = create_chunker()
chunks = chunker.chunk_document(doc)

# 3. Embed
embedder = create_embedding_service()
texts = [c.text for c in chunks]
embeddings = embedder.embed(texts)

# 4. Store
store = create_vector_store()
chunk_dicts = [c.to_dict() for c in chunks]
store.add_chunks(chunk_dicts, embeddings)
```

### Retrieval with Filters
```python
# Search with metadata filters
query = "NVIDIA revenue growth data center"
query_embedding = embedder.embed_query(query)

results = store.search(
    query_embedding=query_embedding,
    n_results=10,
    where={"company": "NVIDIA", "section_type": "mdna"},
    where_document={"$contains": "revenue"}
)

# Rerank
from rag.embeddings import create_reranker_service
reranker = create_reranker_service()
reranked = reranker.rerank_with_scores(
    query=query,
    documents=[{"text": r.document, "metadata": r.metadata} for r in results.results],
    top_k=5,
    score_threshold=0.3
)
```

### Hybrid Search
```python
# Combine vector + keyword search
response = store.hybrid_search(
    query_embedding=query_embedding,
    query_text="revenue growth data center",
    n_results=15,
    where={"company": "NVIDIA"},
    alpha=0.5  # 0.5 = equal weight
)
```

## Testing

Run tests:
```bash
# Unit tests
pytest tests/test_rag_foundation.py -v

# Specific component tests
pytest tests/test_rag_foundation.py::TestPDFProcessor -v
pytest tests/test_rag_foundation.py::TestEmbeddingService -v
pytest tests/test_rag_foundation.py::TestChromaVectorStore -v

# Integration test (requires mocked dependencies)
pytest tests/test_rag_foundation.py::TestRAGIntegration -v
```

### Test Coverage
- **PDFProcessor**: initialization, config, mock processing, hash calculation, date parsing
- **MetadataExtractor**: initialization, company name, doc type, SEC IDs, fiscal period, section detection
- **DocumentLoader**: initialization, extensions, mock load, validation
- **SectionSplitter**: initialization, SEC structure detection, chunk size limits, overlap
- **EmbeddingService**: cache init, miss/hit, set/get, model separation, clear, mock embedding, stats
- **RerankerService**: mock rerank, rerank with scores
- **ChromaVectorStore**: init, add docs, add chunks, search, filter, get by company, count, stats, reset
- **Integration**: Full pipeline mock test

## Performance Considerations

| Operation | Optimization |
|-----------|--------------|
| PDF processing | PyMuPDF is fast; process in parallel for batch |
| Embedding | Batch size 32; GPU acceleration; cache hits ~80%+ |
| Vector search | HNSW index; filter by metadata first when possible |
| Reranking | Cross-encoder on top-20 only; batch size 16 |
| Memory | Embedding cache on disk; ChromaDB persists to disk |

## Security

- **Document validation**: File type (magic bytes), size limit (100MB), PDF integrity
- **Local processing**: Embeddings generated locally (no data egress)
- **PII handling**: Financial docs low PII; CIK/EIN detection + masking available
- **Citation tracking**: Every chunk linked to source document + page

## Directory Structure

```
rag/
├── __init__.py                 # Package exports
├── ingestion/
│   ├── __init__.py
│   ├── pdf_processor.py        # PyMuPDF extraction
│   ├── metadata_extractor.py   # Financial metadata
│   └── document_loader.py      # Orchestration
├── chunking/
│   ├── __init__.py
│   └── section_splitter.py     # Section detection + chunking
├── embeddings/
│   ├── __init__.py
│   ├── embedding_service.py    # BGE-M3 + cache
│   └── reranker_service.py     # Cross-encoder reranking
└── vector_store/
    ├── __init__.py
    └── chroma_store.py         # ChromaDB wrapper
```

## Next Steps (Phase 2+)

1. **Financial Report Agent**: Build agent that uses this foundation for structured analysis
2. **EDGAR Integration**: Automated 10-K/10-Q fetching and processing
3. **Multi-document Comparison**: Cross-company analysis workflows
4. **Streaming Ingestion**: Incremental updates as new filings arrive
5. **Advanced Reranking**: Financial-domain fine-tuned cross-encoder
6. **Evaluation Framework**: Retrieval metrics (recall@k, MRR) and answer quality benchmarks