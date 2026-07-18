# RAG Pipeline Architecture
## Agentic Financial Intelligence Platform

---

## Overview

The RAG (Retrieval-Augmented Generation) pipeline is the core knowledge retrieval system that enables agents to access and reason over financial documents. The pipeline processes SEC filings, earnings transcripts, analyst reports, and other financial documents through a multi-stage pipeline optimized for financial text.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAG PIPELINE ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   SOURCE    │───▶│  INGESTION  │───▶│  CHUNKING   │───▶│  EMBEDDING  │  │
│  │  DOCUMENTS  │    │  & METADATA │    │  STRATEGY   │    │  & STORAGE  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘  │
│                                                                     │        │
│                              ┌─────────────────────────────────────┘        │
│                              ▼                                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   QUERY     │───▶│  RETRIEVAL  │───▶│  RE-RANKING │───▶│  SYNTHESIS  │  │
│  │  ENCODING   │    │  (HYBRID)   │    │  (CROSS-ENC)│    │  & CITATION │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Document Ingestion

### Source Documents
| Source | Types | Volume | Update Frequency |
|--------|-------|--------|------------------|
| SEC EDGAR | 10-K, 10-Q, 8-K, DEF 14A, S-1, 13F | ~50K/year | Real-time (incremental) |
| Earnings Calls | Transcripts, presentations | ~3K/quarter | Real-time |
| Analyst Reports | PDF, HTML | ~10K/year | Daily |
| News Articles | News APIs, RSS | ~50K/day | Real-time |
| Market Data | Quotes, fundamentals | Real-time | Real-time |

### Ingestion Pipeline (`data/filings/incremental.py`)

```python
class IncrementalUpdater:
    """Scheduled incremental updates for document corpus."""
    
    def __init__(self, interval_hours: int = 24):
        self.interval = interval_hours
        self.downloader = SECDownloader()
        self.cache = VersionedDocumentCache()
        self.rag_index = ChromaVectorStore()
    
    async def run_incremental_update(self):
        """Perform incremental update cycle."""
        # 1. Detect new/changed filings
        new_filings = await self.downloader.detect_new_filings()
        
        # 2. Download and process
        for filing in new_filings:
            content = await self.downloader.download(filing)
            parsed = await self.parse_document(content)
            
            # 3. Cache with versioning
            await self.cache.store(filing.accession_number, parsed)
            
            # 4. Update RAG index
            await self.rag_index.upsert(parsed)
```

### Document Metadata Extraction
```python
@dataclass
class DocumentMetadata:
    accession_number: str
    company_cik: str
    company_name: str
    form_type: str          # 10-K, 10-Q, 8-K, etc.
    filing_date: datetime
    period_end: datetime
    fiscal_year: int
    fiscal_quarter: int
    document_hash: str                # SHA-256 for deduplication
sections: List[SectionMetadata]
```

---

## Stage 2: Section-Aware Chunking

### Section-Aware Splitter (`rag/chunking/section_splitter.py`)

Financial documents have hierarchical structure that must be preserved:

```python
class SectionAwareChunker:
    """Chunk financial documents preserving section boundaries."""
    
    def __init__(
        self,
        max_chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_section_size: int = 100
    ):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_section_size = min_section_size
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split document into chunks preserving section boundaries."""
        
        # 1. Extract section hierarchy
        sections = self._extract_sections(document.content)
        
        # 2. Process each section
        chunks = []
        for section in sections:
            section_chunks = self._chunk_section(section)
            chunks.extend(section_chunks)
        
        # 3. Add overlap between adjacent chunks
        self._add_overlap(chunks)
        
        return chunks
```

### Chunk Structure
```python
@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    content: str
    section_path: List[str]      # ["Item 1", "Business", "Products"]
    section_type: str            # "header", "table", "paragraph", "list"
    start_char: int
    end_char: int
    token_count: int
    metadata: Dict[str, Any]     # Filing metadata, section metadata
```

### Section Type Detection
| Section Type | Detection Method | Chunking Strategy |
|--------------|------------------|-------------------|
| Header | Regex: `^Item \d+[A-Z]?` | Keep with following content |
| Table | HTML `<table>` / Markdown `|---|` | Preserve as unit |
| Paragraph | Text blocks | Standard chunking |
| List | Bullet/number patterns | Keep list intact |
| Footnote | Superscript refs | Attach to reference |

---

## Stage 3: Embedding & Storage

### Embedding Model: BGE-M3
```python
class BGEEmbedder:
    """BAAI BGE-M3 multilingual embeddings for financial text."""
    
    def __init__(self):
        self.model_name = "BAAI/bge-m3"
        self.dimension = 1024
        self.max_seq_length = 8192
    
    async def embed_documents(self, texts: List[str]) -> np.ndarray:
        """Embed document chunks."""
        # Batched inference for throughput
        embeddings = await self._batch_encode(texts)
        return normalize(embeddings)  # L2 normalization
    
    async def embed_query(self, query: str) -> np.ndarray:
        """Embed query with instruction prefix."""
        instructed_query = f"Represent this financial query: {query}"
        return await self.embed_documents([instructed_query])
```

**Why BGE-M3?**
- 1024 dimensions - richer representation than 768-dim models
- Multilingual (supports global financial documents)
- Strong on long-context (8192 tokens)
- State-of-the-art on financial benchmarks

### Vector Store: ChromaDB (`rag/vector_store/chroma_store.py`)

```python
class ChromaVectorStore:
    """ChromaDB wrapper for financial document vectors."""
    
    def __init__(self, collection_name: str = "financial_docs"):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    async def upsert(self, chunks: List[Chunk], embeddings: np.ndarray):
        """Upsert chunks with embeddings."""
        ids = [c.chunk_id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [self._prepare_metadata(c) for c in chunks]
        
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings.tolist(),
            metadatas=metadatas
        )
    
    async def query(
        self,
        query_embedding: np.ndarray,
        n_results: int = 10,
        where: Dict = None,
        where_document: Dict = None
    ) -> RetrievalResult:
        """Hybrid search with metadata filtering."""
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where,
            where_document=where_document
        )
        return self._format_results(results)
```

### Storage Schema (ChromaDB)
| Field | Type | Indexed | Description |
|-------|------|---------|-------------|
| `chunk_id` | STRING | Primary | Unique chunk identifier |
| `document_id` | STRING | Yes | Parent document |
| `company` | STRING | Yes | Company ticker/name |
| `filing_type` | STRING | Yes | 10-K, 10-Q, etc. |
| `section_path` | STRING | Yes | JSON array of section hierarchy |
| `filing_date` | TIMESTAMP | Yes | For temporal queries |
| `content` | STRING | No | Full text content |
| `embedding` | VECTOR(1024) | HNSW | Vector embedding |

---

## Stage 4: Hybrid Retrieval

### Two-Stage Retrieval Pipeline

```python
class HybridRetriever:
    """Hybrid retrieval combining vector + keyword + metadata."""
    
    def __init__(self, vector_store: ChromaVectorStore, embedder: BGEEmbedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.bm25_index = BM25Index()  # For keyword search
    
    async def retrieve(
        self,
        query: str,
        company: str = None,
        filing_types: List[str] = None,
        date_range: Tuple[datetime, datetime] = None,
        top_k: int = 20
    ) -> List[RetrievalResult]:
        """Multi-stage retrieval with fusion."""
        
        # 1. Vector search (semantic)
        query_embedding = await self.embedder.embed_query(query)
        vector_results = await self.vector_store.query(
            query_embedding=query_embedding,
            n_results=top_k * 2,
            where=self._build_metadata_filter(company, filing_types, date_range)
        )
        
        # 2. Keyword search (BM25)
        keyword_results = self.bm25_index.search(query, top_k * 2)
        
        # 3. Metadata filter
        metadata_results = self._metadata_filter(company, filing_types, date_range)
        
        # 4. Reciprocal Rank Fusion (RRF)
        fused = self._reciprocal_rank_fusion(
            vector_results, keyword_results, metadata_results
        )
        
        return fused[:top_k]
```

### Retrieval Fusion Weights
| Method | Weight | Purpose |
|--------|--------|---------|
| Vector (BGE-M3) | 0.50 | Semantic similarity |
| BM25 | 0.30 | Exact keyword matching |
| Metadata Filter | 0.20 | Company/filing/date constraints |

### Metadata Filters
```python
def _build_metadata_filter(
    self,
    company: str = None,
    filing_types: List[str] = None,
    date_range: Tuple[datetime, datetime] = None
) -> Dict:
    """Build ChromaDB where clause."""
    conditions = []
    
    if company:
        conditions.append({"company": {"$eq": company}})
    
    if filing_types:
        conditions.append({"filing_type": {"$in": filing_types}})
    
    if date_range:
        start, end = date_range
        conditions.append({"filing_date": {"$gte": start, "$lte": end}})
    
    if not conditions:
        return None
    
    return {"$and": conditions} if len(conditions) > 1 else conditions[0]
```

---

## Stage 5: Re-Ranking (Cross-Encoder)

### BGE-Reranker-v2-M3

```python
class CrossEncoderReranker:
    """Cross-encoder for precision re-ranking."""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model = CrossEncoder(model_name)
        self.max_length = 512
    
    async def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """Re-rank candidates using cross-encoder."""
        
        if not candidates:
            return []
        
        # Prepare pairs
        pairs = [(query, cand.content) for cand in candidates]
        
        # Batch inference
        scores = await self._batch_score(pairs)
        
        # Attach scores and sort
        for cand, score in zip(candidates, scores):
            cand.rerank_score = score
        
        candidates.sort(key=lambda x: x.rerank_score, reverse=True)
        return candidates[:top_k]
```

**Why Re-rank?**
- Cross-encoder sees query + doc together (bi-directional attention)
- Vector search uses bi-encoder (independent encoding)
- Typical 10-15% precision improvement at top-k

---

## Stage 6: Synthesis & Citation

### Answer Synthesis (`agents/financial_document_agent/agent.py`)

```python
class FinancialDocumentAgent(BaseWorkerAgent):
    async def run(self, company: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Retrieve relevant chunks
        chunks = await self.retriever.retrieve(
            query=context["query"],
            company=company,
            top_k=20
        )
        
        # 2. Build context with citations
        context_text = self._build_context_with_citations(chunks)
        
        # 3. Generate answer with structured prompts
        prompt = self._build_answer_prompt(
            question=context["query"],
            context=context_text,
            company=company
        )
        
        response = await self.llm.agenerate_json(prompt)
        
        # 4. Attach citations
        return {
            "answer": response["answer"],
            "citations": self._format_citations(chunks),
            "confidence": response["confidence"],
            "metadata": {"chunks_used": len(chunks)}
        }
```

### Citation Format
```json
{
  "answer": "NVIDIA's revenue grew 126% YoY in FY2024...",
  "citations": [
    {
      "chunk_id": "chunk_abc123",
      "source": "NVDA 10-K FY2024",
      "section": "Item 1 - Business",
      "excerpt": "Revenue for fiscal year 2024 was $60.9 billion...",
      "relevance": 0.94
    }
  ],
  "confidence": 0.91
}
```

---

## RAG Pipeline Configuration

### Environment Variables
```bash
# Embedding
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIM=1024
EMBEDDING_BATCH_SIZE=32

# Reranking
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANKER_TOP_K=10

# Retrieval
RETRIEVAL_TOP_K=20
RETRIEVAL_FUSION_METHOD=rrf
RERANK_TOP_K=10

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MIN_SECTION_SIZE=100

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION=financial_docs
```

---

## Performance Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Retrieval Latency (p95) | <500ms | ~320ms |
| Rerank Latency (p95) | <200ms | ~120ms |
| End-to-End RAG | <3s | ~2.1s |
| Recall@10 | >0.85 | 0.89 |
| Precision@5 | >0.80 | 0.84 |
| Citation Accuracy | >0.95 | 0.96 |

---

## Monitoring & Observability

### Key Metrics (Prometheus)
```prometheus
# Retrieval latency
rag_retrieval_duration_seconds_bucket{le="0.5"} 12450

# Rerank latency
rag_rerank_duration_seconds_bucket{le="0.2"} 11800

# Retrieval quality
rag_recall_at_10 0.89
rag_precision_at_5 0.84

# Citation quality
rag_citation_accuracy 0.96
```

### Health Checks
```python
async def health_check() -> HealthStatus:
    checks = {
        "vector_store": await vector_store.health_check(),
        "embedder": await embedder.health_check(),
        "reranker": await reranker.health_check(),
        "chroma_db": await chroma_client.heartbeat()
    }
    return HealthStatus(
        healthy=all(c.healthy for c in checks.values()),
        checks=checks
    )
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*